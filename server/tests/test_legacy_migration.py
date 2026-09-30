"""Legacy (v0.17–v0.22) data migration: config, conversion rules, end to end."""

import datetime as dt
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from argon2 import PasswordHasher

from app.common.validators import validate_domain
from app.legacy_migration import mapping
from app.legacy_migration.config import DEFAULT_PATH, load
from app.legacy_migration.report import Report
from app.legacy_migration.source import SourceError, detect, find_legacy_database
from app.modules.indexer_definitions.integrations import discover_indexer_definitions
from app.modules.media_attributes.seeds import DEFAULT_ATTRIBUTES
from tests.legacy_fixture import ADMIN_PASSWORD, SCHEMAS, build_legacy_data

CFG = load(DEFAULT_PATH)
SERVER_DIR = Path(__file__).resolve().parent.parent
# schema snapshot -> the releases it must be detected as (versions.toml)
SUPPORTED_AS = {
    "v0.18.6": "v0.17.0 – v0.18.6",
    "v0.19.1": "v0.19.0 – v0.19.1",
    "v0.21.1": "v0.20.0 – v0.21.1",
    "v0.22.0": "v0.22.0",
}
SUPPORTED = list(SUPPORTED_AS)

# Every value the old releases could store (their enums, identical v0.17–v0.22).
OLD_VALUES = {
    "tracker": ["ncore", "bithumen", "majomparade", "insane", "filelist"],
    "language": ["hu", "en"],
    "resolution": ["2160p", "1080p", "720p", "576p", "540p", "480p"],
    "video-quality": ["dolby-vision", "hdr10+", "hdr10", "hlg", "sdr"],
    "source": ["disc-remux", "disc-rip", "web-dl", "web-rip", "broadcast", "theatrical", "unknown"],
    "audio-quality": ["truehd", "dts-hd-ma", "ddp", "dts", "dd", "aac", "unknown"],
    "audio-spatial": ["dolby-atmos", "dts-x"],
}


def _app_attributes() -> dict[str, set[str]]:
    """Attribute ids per preference, as this app seeds them."""
    attrs: dict[str, set[str]] = {}
    for attribute in DEFAULT_ATTRIBUTES:
        if attribute.preference_id:
            attrs.setdefault(attribute.preference_id, set()).add(attribute.id)
    attrs["site"] = {cls(None).id for cls in discover_indexer_definitions()}
    return attrs


# --------------------------------------------------------------------------- #
# versions.toml against this app
# --------------------------------------------------------------------------- #


def test_every_old_value_maps_to_an_attribute_of_this_app():
    attrs = _app_attributes()
    for old_pref, values in OLD_VALUES.items():
        new_pref = CFG.preferences[old_pref]
        assert new_pref in attrs, new_pref
        for value in values:
            assert value in CFG.values[new_pref], (old_pref, value)
            for target in CFG.values[new_pref][value]:
                assert target in attrs[new_pref], (old_pref, value, target)


def test_old_trackers_are_indexers_of_this_app():
    indexers = _app_attributes()["site"]
    for profile in CFG.versions:
        assert set(profile.trackers) <= indexers, profile.releases


@pytest.mark.parametrize("release", SUPPORTED)
def test_schema_snapshot_is_detected(tmp_path: Path, release: str):
    fixture = build_legacy_data(tmp_path / "data", release)
    detected = detect(fixture.root, CFG, Report())
    assert detected.profile.releases == SUPPORTED_AS[release]
    assert detected.paths.layout.name == fixture.layout


def test_older_release_is_refused(tmp_path: Path):
    fixture = build_legacy_data(tmp_path / "data", "v0.16.1")
    with pytest.raises(SourceError, match="older than v0.17.0"):
        detect(fixture.root, CFG, Report())


def test_schema_snapshots_cover_every_profile():
    lasts = set()
    for sql in SCHEMAS.glob("*.sql"):
        conn = sqlite3.connect(":memory:")
        conn.executescript(sql.read_text())
        lasts.add(
            conn.execute(
                "SELECT name FROM migrations ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()[0]
        )
        conn.close()
    assert {v.last_migration for v in CFG.versions} <= lasts


# --------------------------------------------------------------------------- #
# conversion rules
# --------------------------------------------------------------------------- #


def test_preferences_keep_order_expand_and_block():
    report = Report()
    rows = [
        {"preference": "source", "preferred": ["disc-remux", "disc-rip"], "blocked": ["theatrical", "unknown"], "order": 1},
        {"preference": "tracker", "preferred": ["insane", "ncore"], "blocked": ["bithumen"], "order": 0},
        {"preference": "language", "preferred": ["hu"], "blocked": ["en"], "order": None},
    ]
    out = mapping.convert_user_preferences("u1", "admin", rows, _app_attributes(), CFG, report)
    assert [p.preference_id for p in out.preferences] == ["site", "source", "language"]
    assert out.preferences[1].attribute_ids == ["remux", "uhd", "bluray", "bdrip", "dvd-rip"]
    assert out.exclusions == ["cam", "eng"]  # blocked sites cannot be excluded
    lossy = " ".join(e.message for e in report.by_level("lossy"))
    assert "blocked sites ['bithumen']" in lossy and "'unknown'" in lossy


def test_settings_use_old_defaults_and_report_dropped_keys():
    report = Report()
    converted = mapping.convert_settings(
        {"app": {"hitAndRun": False, "catalogToken": "t"}, "torrent": {"port": 7000}},
        CFG,
        report,
    )
    assert converted.system == {"hit_and_run": False, "keep_seed_seconds": 0, "cache_retention_seconds": 1209600}
    assert converted.relay["port"] == 7000 and converted.relay["connections_limit"] == 200
    assert any("catalogToken" in e.message for e in report.by_level("lossy"))


def test_tracker_full_download_is_enforced_and_times_are_local():
    report = Report()
    out = mapping.convert_tracker(
        {"tracker": "majomparade", "username": "u", "password": "p", "download_full_torrent": 0,
         "created_at": "2026-01-01 00:00:00", "updated_at": "2026-01-01 00:00:00"},
        {"majomparade": {"requires_full_download": True}},
        ZoneInfo("Europe/Budapest"),
        report,
    )
    assert out is not None
    assert out["download_full_torrent"] is True
    assert out["created_at"] == dt.datetime(2026, 1, 1, 1, 0)


@pytest.mark.parametrize(
    ("app", "env", "expected_action", "expected_warn"),
    [
        ({"enebledlocalIp": False, "address": "https://stremhu.example.com/"}, {}, "REVERSE_PROXY_DOMAIN=stremhu.example.com`", None),
        ({"enebledlocalIp": False, "address": "https://example.com:8443"}, {}, "REVERSE_PROXY_DOMAIN=example.com`", "port 8443"),
        ({"enebledlocalIp": True, "address": "192.168.1.50"}, {}, "HOST_IP=192.168.1.50", None),
        ({"enebledlocalIp": False, "address": "https://a.example.com"}, {"REVERSE_PROXY_DOMAIN": "b.example.com"}, "REVERSE_PROXY_DOMAIN=a.example.com`", "this container has REVERSE_PROXY_DOMAIN=b.example.com"),
        ({"enebledlocalIp": False, "address": "https://a.example.com"}, {"REVERSE_PROXY_DOMAIN": "a.example.com"}, "✓ `REVERSE_PROXY_DOMAIN=a.example.com` is already set", None),
        ({"enebledlocalIp": True, "address": "10.0.0.2"}, {"HOST_IP": "10.0.0.2"}, "✓ `HOST_IP=10.0.0.2` is already set", None),
    ],
)
def test_network_advice(app, env, expected_action, expected_warn):
    report = Report()
    mapping.suggest_network(app, CFG, report, validate_domain=validate_domain, current_env=env)
    assert any(expected_action in e.message for e in report.by_level("action"))
    warns = " ".join(e.message for e in report.by_level("warn"))
    if expected_warn:
        assert expected_warn in warns
    else:
        assert not warns


# --------------------------------------------------------------------------- #
# end to end: `python -m app.legacy_migration`, as users run it
# --------------------------------------------------------------------------- #


def _migrate(data: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATA_DIR": str(data), "TZ": "Europe/Budapest"}
    env.pop("REVERSE_PROXY_DOMAIN", None)
    env.setdefault("HOST_IP", "192.168.1.100")
    return subprocess.run(
        [sys.executable, "-m", "app.legacy_migration", *args],
        cwd=SERVER_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _db(data: Path) -> sqlite3.Connection:
    return sqlite3.connect(data / "system" / "database" / "app.db")


def _files(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and "migration" not in p.relative_to(root).parts
    }


@pytest.mark.parametrize("release", SUPPORTED)
def test_in_place_migration(tmp_path: Path, release: str):
    data = tmp_path / "data"
    fixture = build_legacy_data(data, release)

    result = _migrate(data)
    assert result.returncode == 0, result.stdout + result.stderr

    conn = _db(data)
    users = dict(conn.execute("SELECT username, api_key FROM users"))
    assert users == {"admin": fixture.admin_token, "family": fixture.user_token}
    (password_hash,) = conn.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
    assert PasswordHasher().verify(password_hash, ADMIN_PASSWORD)

    expected_accounts = {"ncore", "insane", "majomparade"} | ({"filelist"} if release == "v0.22.0" else set())
    assert {r[0] for r in conn.execute("SELECT indexer_id FROM indexer_accounts")} == expected_accounts
    (full,) = conn.execute("SELECT download_full_torrent FROM indexer_accounts WHERE indexer_id='majomparade'").fetchone()
    assert full == 1  # required by the new version

    torrents = {r[0]: r[1] for r in conn.execute("SELECT torrent_id, resume_bytes IS NOT NULL FROM torrents")}
    expected_torrents = {"3512001", "88001", "3512002"} | ({"990011"} if release == "v0.22.0" else set())
    assert set(torrents) == expected_torrents  # missing .torrent and no-account ones are reported, not migrated
    assert torrents["3512001"] == fixture.resume_data
    assert torrents["3512002"] == 0

    # created_at carries the old last_played_at, in local time (keep-seed cleanup)
    (created,) = conn.execute("SELECT created_at FROM torrents WHERE torrent_id='3512001'").fetchone()
    assert created.startswith("2026-09-20 20:00:00")

    site = [r[0] for r in conn.execute(
        "SELECT pda.attribute_id FROM preference_definition_attributes pda "
        "JOIN preference_definitions pd ON pd.id = pda.definition_id "
        "JOIN user_preference_definitions upd ON upd.definition_id = pd.id "
        "JOIN users u ON u.id = upd.user_id "
        "WHERE u.username='admin' AND pd.preference_id='site' ORDER BY pda.\"order\""
    )]
    assert site == ["ncore", "insane", "majomparade"] + (["filelist"] if release == "v0.22.0" else [])
    conn.close()

    # old system folders are kept as a backup, downloads untouched
    backups = list((data / "migration").glob("*/old-data"))
    assert len(backups) == 1
    assert (data / "downloads" / "Show.S01E01.1080p.mkv").stat().st_size == 400_000
    report = next((data / "migration").glob("*/report.md")).read_text()
    assert "REVERSE_PROXY_DOMAIN=stremhu.example.com" in report
    assert "complete on disk" in report

    # a second run refuses: the folder is migrated already
    again = _migrate(data)
    assert again.returncode == 1
    assert "migrated already" in again.stdout


def test_dry_run_changes_nothing(tmp_path: Path):
    data = tmp_path / "data"
    build_legacy_data(data, "v0.21.1")
    before = _files(data)

    result = _migrate(data, "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _files(data) == before
    assert list((data / "migration").glob("*-dry-run/report.md"))


def test_separate_source_folder_moves_downloads(tmp_path: Path):
    old = tmp_path / "old"
    build_legacy_data(old, "v0.19.1")
    new = tmp_path / "new"

    result = _migrate(new, "--source", str(old))
    assert result.returncode == 0, result.stdout + result.stderr
    assert (new / "downloads" / "Complete.Pack" / "Movie.2160p.mkv").is_file()
    assert not (old / "downloads" / "Complete.Pack").exists()
    assert (old / "database" / "app.db").is_file()  # the source DB is never modified
    conn = _db(new)
    assert conn.execute("SELECT COUNT(*) FROM torrents").fetchone()[0] == 3
    conn.close()


def test_new_database_next_to_old_data_needs_overwrite(tmp_path: Path):
    data = tmp_path / "data"
    build_legacy_data(data, "v0.18.6")  # root layout: database/, torrents/
    new_db = data / "system" / "database" / "app.db"
    new_db.parent.mkdir(parents=True)
    conn = sqlite3.connect(new_db)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.close()

    refused = _migrate(data)
    assert refused.returncode == 1
    assert "--overwrite" in refused.stdout
    assert (data / "database" / "app.db").is_file()  # nothing moved

    result = _migrate(data, "--overwrite")
    assert result.returncode == 0, result.stdout + result.stderr
    assert list((data / "migration").glob("*/replaced-system/database/app.db"))


# --------------------------------------------------------------------------- #
# the app refuses to start on old data
# --------------------------------------------------------------------------- #


def test_startup_guard_points_to_the_migration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.boot import setup
    from app.config import config

    data = tmp_path / "data"
    build_legacy_data(data, "v0.19.1")
    assert find_legacy_database(data) == data / "database" / "app.db"

    monkeypatch.setattr(config, "data_dir", data)
    with pytest.raises(SystemExit):
        setup.exit_if_legacy_data()

    migrated = tmp_path / "migrated"
    migrated.mkdir()
    monkeypatch.setattr(config, "data_dir", migrated)
    setup.exit_if_legacy_data()  # nothing old here: no exit
