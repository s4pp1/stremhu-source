"""Pure conversion rules from StremHU Source v0.17–v0.22 (NestJS) to this version.

The value tables, settings keys and defaults come from versions.toml (see
`config.py`); this module only applies them. Nothing in here touches the
database or the new application code, so every rule can be unit tested in
isolation. Every lossy decision is recorded on the ``Report`` passed in.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, overload
from zoneinfo import ZoneInfo

from .config import Config
from .report import Report

KNOWN_ROLES = {"admin", "user"}


# --------------------------------------------------------------------------- #
# Time handling
# --------------------------------------------------------------------------- #


def parse_old_datetime(value: Any) -> dt.datetime | None:
    """Parse a TypeORM/SQLite timestamp. Old values are always UTC."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # epoch milliseconds (better-sqlite3 may store Date as a number)
        seconds = value / 1000 if value > 10**11 else value
        return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    text = str(value).strip().replace("T", " ").rstrip("Z")
    if text.endswith("+00:00"):
        text = text[: -len("+00:00")]
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


@overload
def to_local_naive(value: dt.datetime, tz: ZoneInfo) -> dt.datetime: ...
@overload
def to_local_naive(value: dt.datetime | None, tz: ZoneInfo) -> dt.datetime | None: ...
def to_local_naive(value: dt.datetime | None, tz: ZoneInfo) -> dt.datetime | None:
    """New tables written with `datetime.now` store naive *local* time."""
    if value is None:
        return None
    return value.astimezone(tz).replace(tzinfo=None)


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #


@dataclass
class ConvertedSettings:
    system: dict[str, Any]
    relay: dict[str, Any]


def convert_settings(
    rows: dict[str, Any], cfg: Config, report: Report
) -> ConvertedSettings:
    section = "Settings"
    app = rows.get("app") or {}
    relay = rows.get("torrent") or {}
    if not isinstance(app, dict):
        report.warn(
            section, f"'app' settings row is not an object, using defaults: {app!r}"
        )
        app = {}
    if not isinstance(relay, dict):
        report.warn(
            section,
            f"'torrent' settings row is not an object, using defaults: {relay!r}",
        )
        relay = {}

    system_out: dict[str, Any] = {}
    for old_key, key in cfg.system_settings.items():
        if old_key in app and app[old_key] is not None:
            system_out[key.to] = app[old_key]
        else:
            system_out[key.to] = key.default
            report.info(
                section,
                f"app.{old_key} was not set; old default {key.default!r} carried over",
            )

    relay_out: dict[str, Any] = {}
    for old_key, key in cfg.relay_settings.items():
        if old_key in relay and relay[old_key] is not None:
            relay_out[key.to] = relay[old_key]
        else:
            relay_out[key.to] = key.default

    for key, why in cfg.dropped_settings.items():
        if app.get(key) not in (None, "", False):
            report.lossy(section, f"app.{key} = {app[key]!r} dropped: {why}")

    network_keys = {cfg.network.get("local_ip_key"), cfg.network.get("address_key")}
    extra = (
        set(app) - set(cfg.system_settings) - set(cfg.dropped_settings) - network_keys
    )
    for key in sorted(extra):
        report.lossy(section, f"app.{key} = {app[key]!r} dropped: unknown key")
    extra_relay = set(relay) - set(cfg.relay_settings)
    for key in sorted(extra_relay):
        report.lossy(section, f"torrent.{key} = {relay[key]!r} dropped: unknown key")
    for key in sorted(set(rows) - {"app", "torrent"}):
        report.lossy(section, f"settings row '{key}' dropped: unknown key")

    return ConvertedSettings(system=system_out, relay=relay_out)


# --------------------------------------------------------------------------- #
# Network address -> container configuration advice
# --------------------------------------------------------------------------- #


def _is_ip(host: str) -> bool:
    import ipaddress

    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _advise_network(
    app: dict[str, Any],
    cfg: Config,
    report: Report,
    validate_domain: Callable[[str], str] | None,
) -> dict[str, str] | None:
    """Translate the old public address into what the new container needs;
    returns the recommended environment variable, if any.

    v0.17–v0.22 (getEndpoint, identical in every release):
      * enebledlocalIp + address (an IP)  -> https://a-b-c-d.local-ip.medicmobile.org:<HTTPS_PORT, 3443>
      * !enebledlocalIp + address (a URL) -> that URL verbatim (reverse proxy)
    new version:
      * HOST_IP                           -> https://a-b-c-d.local-ip.medicmobile.org:7070
      * REVERSE_PROXY_DOMAIN=<domain>     -> https://<domain>  (no scheme, no port)

    Addon URLs are <public URL>/api/<api_key>/stremio/manifest.json in both
    versions and api keys are migrated, so the URL only changes if the public
    base URL changes.
    """
    section = "Network / addon URL"
    net = cfg.network
    old_https_port = net.get("old_https_port", 3443)
    new_port = net.get("new_port", 7070)
    local = app.get(net.get("local_ip_key", "enebledlocalIp"), True) is not False
    address = (app.get(net.get("address_key", "address")) or "").strip()

    if not address:
        report.warn(
            section,
            "no public address was configured in the old version (the addon URLs pointed at 127.0.0.1, "
            "so they only worked on the server itself). Set HOST_IP or REVERSE_PROXY_DOMAIN "
            "on the new container and install the addon from the new web UI",
        )
        return None

    if local:
        host = address.split("://")[-1].split("/")[0].split(":")[0]
        if not _is_ip(host):
            report.warn(
                section,
                f"local-IP mode was on but the address {address!r} is not an IP; "
                "set HOST_IP to the server's LAN IP",
            )
            return None
        local_host = host.replace(".", "-") + ".local-ip.medicmobile.org"
        report.action(
            section,
            f"Old addon base URL: https://{local_host}:{old_https_port} (or your HTTPS_PORT if you changed it). "
            f"Set `HOST_IP={host}` on the new container; the new base URL is https://{local_host}:{new_port} "
            "(only the port changes).",
        )
        report.action(
            section,
            f"To keep the old addon URLs working without re-installing, publish both ports: "
            f"`ports: ['{new_port}:{new_port}', '{old_https_port}:{new_port}']`. "
            "Otherwise re-install the addon for each user from the new web UI.",
        )
        return {"HOST_IP": host}

    # Reverse proxy / custom URL
    from urllib.parse import urlsplit

    parsed = urlsplit(address if "://" in address else f"https://{address}")
    host = parsed.hostname or ""
    path = parsed.path.rstrip("/")
    domain = host + path

    if _is_ip(host):
        report.warn(
            section,
            f"the old public address {address!r} is an IP; the new version needs a domain for REVERSE_PROXY_DOMAIN. "
            "Use a domain (or HOST_IP for LAN access); the addon URL changes, so re-install the addon for each user",
        )
        return None

    problems: list[str] = []
    if parsed.scheme == "http":
        problems.append(
            "it used http://, the new version always builds https:// URLs (terminate TLS on the proxy)"
        )
    if parsed.port not in (None, 443 if parsed.scheme != "http" else 80):
        problems.append(
            f"it used port {parsed.port}, REVERSE_PROXY_DOMAIN cannot contain a port"
        )
    if validate_domain is not None:
        try:
            validate_domain(domain)
        except ValueError as e:
            problems.append(f"{domain!r} is rejected by the new version: {e}")

    report.action(
        section,
        f"Set `REVERSE_PROXY_DOMAIN={domain}` on the new container (HOST_IP is then optional). "
        f"Point the proxy upstream to `http://<container>:{new_port}`: the old app listened on "
        "HTTP_PORT/HTTPS_PORT (default 3000/3443), the new version serves plain HTTP on 7070 "
        "and the proxy does TLS.",
    )
    if problems:
        report.warn(
            section,
            f"the old addon base URL {address!r} cannot be reproduced exactly: "
            + "; ".join(problems)
            + f". The new base URL will be https://{domain}, so re-install the addon for each user.",
        )
    else:
        report.action(
            section,
            f"Addon URLs stay the same (https://{domain}/api/<api key>/stremio/manifest.json); "
            "Stremio installs and paired Kodi devices keep working, nothing to re-install.",
        )
    return {"REVERSE_PROXY_DOMAIN": domain}


def suggest_network(
    app: dict[str, Any],
    cfg: Config,
    report: Report,
    validate_domain: Callable[[str], str] | None = None,
    current_env: dict[str, str] | None = None,
) -> None:
    """Network advice for the new container, checked against the environment
    the migrator runs with (`docker compose run` passes the app's own env)."""
    expected = _advise_network(app, cfg, report, validate_domain)
    if not expected or current_env is None:
        return
    section = "Network / addon URL"
    for key, value in expected.items():
        current = current_env.get(key)
        if current is None:
            continue
        if current.strip().rstrip("/") == value:
            # turn "Set `KEY=value` on the new container" into a confirmation
            for entry in report.entries:
                if (
                    entry.level == "action"
                    and f"Set `{key}={value}` on the new container" in entry.message
                ):
                    entry.message = entry.message.replace(
                        f"Set `{key}={value}` on the new container",
                        f"✓ `{key}={value}` is already set in this container",
                    )
        else:
            report.warn(
                section,
                f"this container has {key}={current}, but the old public address suggests "
                f"{key}={value}. If they differ, the addon URLs change.",
            )


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #


def _is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def convert_user(row: dict[str, Any], report: Report) -> dict[str, Any]:
    section = "Users"
    username = row["username"]
    role = row.get("user_role")
    if role not in KNOWN_ROLES:
        report.warn(
            section, f"user '{username}': unknown role {role!r}, migrated as 'user'"
        )
        role = "user"

    api_key = row.get("token")
    if not api_key or not _is_uuid(api_key):
        api_key = str(uuid.uuid4())
        report.warn(
            section,
            f"user '{username}': missing/invalid token, a new API key was generated (re-install the Stremio addon)",
        )

    if row.get("password_hash") is None and role == "admin":
        report.warn(
            section, f"admin '{username}' has no password; set one in the new UI"
        )

    created = parse_old_datetime(row.get("created_at")) or dt.datetime.now(
        dt.timezone.utc
    )
    updated = parse_old_datetime(row.get("updated_at")) or created

    return {
        "id": row["id"],
        "username": username,
        "password_hash": row.get("password_hash"),
        "api_key": api_key,
        "role_id": role,
        "torrent_seed": row.get("torrent_seed"),
        "enable_smart_filter": bool(row.get("only_best_torrent") or False),
        "smart_filter_limit": 1,
        "smart_filter_grouping_preference_id": None,
        "max_concurrent_streams": None,
        "created_at": created,
        "updated_at": updated,
    }


# --------------------------------------------------------------------------- #
# Indexer accounts (old "trackers")
# --------------------------------------------------------------------------- #


def convert_tracker(
    row: dict[str, Any],
    definitions: dict[str, dict[str, Any]],
    tz: ZoneInfo,
    report: Report,
) -> dict[str, Any] | None:
    section = "Indexer accounts"
    tracker = row["tracker"]
    definition = definitions.get(tracker)
    if definition is None:
        report.lossy(
            section,
            f"tracker '{tracker}' has no the new version indexer; account dropped",
        )
        return None

    download_full = bool(row.get("download_full_torrent") or False)
    if definition["requires_full_download"] and not download_full:
        report.info(
            section,
            f"'{tracker}': full download is mandatory in the new version, enabled",
        )
        download_full = True

    if row.get("order_index") not in (None, 0):
        report.info(
            section,
            f"'{tracker}': order_index={row['order_index']} dropped (site order now comes from the per-user 'Torrent oldal' preference)",
        )

    created = parse_old_datetime(row.get("created_at")) or dt.datetime.now(
        dt.timezone.utc
    )
    updated = parse_old_datetime(row.get("updated_at")) or created
    return {
        "indexer_id": tracker,
        "username": row["username"],
        "password": row["password"],
        "totp_secret": None,
        "hit_and_run": None
        if row.get("hit_and_run") is None
        else bool(row["hit_and_run"]),
        "keep_seed_seconds": row.get("keep_seed_seconds"),
        "download_full_torrent": download_full,
        "cookies": None,
        "created_at": to_local_naive(created, tz),
        "updated_at": to_local_naive(updated, tz),
    }


# --------------------------------------------------------------------------- #
# Preferences
# --------------------------------------------------------------------------- #


@dataclass
class ConvertedPreference:
    preference_id: str
    attribute_ids: list[str]
    order: int


@dataclass
class ConvertedUserPreferences:
    user_id: str
    preferences: list[ConvertedPreference] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)


def _map_values(
    table: dict[str, list[str]],
    values: Any,
    valid_attributes: set[str],
    context: str,
    report: Report,
) -> list[str]:
    section = "Preferences"
    if not isinstance(values, list):
        report.warn(section, f"{context}: expected a list, got {values!r}; ignored")
        return []

    out: list[str] = []
    for value in values:
        key = str(value).lower()
        if key not in table:
            report.lossy(section, f"{context}: value {value!r} is unknown, dropped")
            continue
        targets = table[key]
        if not targets:
            report.lossy(
                section,
                f"{context}: value {value!r} has no the new version equivalent, dropped",
            )
            continue
        if len(targets) > 1:
            report.info(section, f"{context}: {value!r} expanded to {targets}")
        for target in targets:
            if target not in valid_attributes:
                report.lossy(
                    section,
                    f"{context}: {value!r} -> {target!r} is not a the new version attribute, dropped",
                )
                continue
            if target not in out:
                out.append(target)
    return out


def convert_user_preferences(
    user_id: str,
    username: str,
    rows: list[dict[str, Any]],
    attributes_by_preference: dict[str, set[str]],
    cfg: Config,
    report: Report,
) -> ConvertedUserPreferences:
    section = "Preferences"
    result = ConvertedUserPreferences(user_id=user_id)

    # Old order may be NULL: keep ordered rows first, NULLs after (stable).
    def sort_key(r: dict[str, Any]) -> tuple[int, int]:
        order = r.get("order")
        return (1, 0) if order is None else (0, int(order))

    exclusions: list[str] = []
    for row in sorted(rows, key=sort_key):
        old_pref = row["preference"]
        new_pref = cfg.preferences.get(old_pref)
        if new_pref is None:
            report.lossy(
                section, f"user '{username}': unknown preference {old_pref!r} dropped"
            )
            continue

        valid = attributes_by_preference.get(new_pref, set())
        context = f"user '{username}' / {old_pref}"

        table = cfg.values.get(new_pref, {})
        preferred = _map_values(
            table, row.get("preferred"), valid, f"{context} preferred", report
        )
        blocked = _map_values(
            table, row.get("blocked"), valid, f"{context} blocked", report
        )

        if blocked and new_pref == "site":
            report.lossy(
                section,
                f"{context}: blocked sites {blocked} cannot be migrated "
                "(the new version only supports excluding media attributes); "
                "disable the site in the preference list instead",
            )
            blocked = []

        # An attribute both preferred and blocked would be contradictory in the
        # new model; blocking wins because that is what filtered results.
        both = [a for a in preferred if a in blocked]
        if both:
            report.info(
                section,
                f"{context}: {both} were both preferred and blocked; kept as blocked only",
            )
            preferred = [a for a in preferred if a not in blocked]

        result.preferences.append(
            ConvertedPreference(
                preference_id=new_pref,
                attribute_ids=preferred,
                order=len(result.preferences),
            )
        )
        for attribute_id in blocked:
            if attribute_id not in exclusions:
                exclusions.append(attribute_id)

    result.exclusions = exclusions
    return result
