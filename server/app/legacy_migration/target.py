"""Write side: build the new database with the application's own code.

Schema comes from the app's alembic migrations and reference data (roles,
preference categories, media attributes, indexer definitions) from the app's
own boot-time sync, so the result is exactly what a fresh install of this
version would have. Converted rows are then inserted through the app's ORM models in
a single transaction.

Import this module only after `cli._prepare_runtime()` has pointed the app's
data directory (DATA_DIR) at the destination.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import libtorrent
from alembic.config import Config as AlembicConfig
from pydantic import ValidationError

from alembic import command
from app.common.database import db_session, engine
from app.common.validators import validate_domain
from app.config import config as app_config
from app.modules.attribute_exclusions.models import AttributeExclusionModel
from app.modules.attributes.models import AttributeModel
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.media_attributes.dependencies import create_media_attributes_service
from app.modules.preference_definitions.models import (
    PreferenceDefinitionAttributeModel,
    PreferenceDefinitionModel,
)
from app.modules.preferences.dependencies import create_preferences_service
from app.modules.roles.dependencies import create_roles_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.settings.schemas.internal import (
    RelaySettings,
    RelaySettingsUpdate,
    SystemSettings,
    SystemSettingsUpdate,
)
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrents.models import TorrentModel
from app.modules.user_preference_definitions.models import UserPreferenceDefinitionModel
from app.modules.users.models import UserModel

from . import mapping
from .config import Config
from .report import Report
from .source import OldData
from .ui import Steps

log = logging.getLogger(__name__)


@dataclass
class ReferenceData:
    attributes_by_preference: dict[str, set[str]]
    definitions: dict[str, dict[str, Any]]


@dataclass
class MigratedTorrent:
    info_hash: str
    indexer_id: str
    torrent_id: str
    name: str
    torrent_bytes: bytes
    resume_bytes: bytes | None


def data_dir() -> Path:
    return app_config.base_data_dir


def database_path() -> Path:
    return app_config.database_dir / "app.db"


# --------------------------------------------------------------------------- #
# Initialisation
# --------------------------------------------------------------------------- #


def app_version() -> str:
    return app_config.version


def initialize_database(steps: Steps) -> ReferenceData:
    app_root = app_config.root_dir
    app_config.database_dir.mkdir(parents=True, exist_ok=True)
    app_config.downloads_dir.mkdir(parents=True, exist_ok=True)
    app_config.certificates_dir.mkdir(parents=True, exist_ok=True)

    alembic_cfg = AlembicConfig(str(app_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(app_root / "alembic"))
    command.upgrade(alembic_cfg, "head")
    # alembic's fileConfig() resets logging; keep the app quiet again
    logging.getLogger().setLevel(logging.WARNING)
    steps.ok("schema created with the app's alembic migrations (head)")

    with db_session() as db:
        create_roles_service(db).sync_to_db()
        create_preferences_service(db).sync_to_db()
        create_media_attributes_service(db).sync_to_db()
        get_indexer_definitions_service().sync_to_db(db)
    steps.ok(
        "reference data seeded (roles, preference categories, attributes, indexers)"
    )

    with db_session() as db:
        attributes: dict[str, set[str]] = {}
        for attr_id, pref_id in db.query(
            AttributeModel.id, AttributeModel.preference_id
        ):
            if pref_id:
                attributes.setdefault(pref_id, set()).add(attr_id)
        definitions = {
            d.id: {"requires_full_download": d.requires_full_download, "name": d.name}
            for d in db.query(IndexerDefinitionModel).all()
        }
    return ReferenceData(attributes_by_preference=attributes, definitions=definitions)


# --------------------------------------------------------------------------- #
# Insertion
# --------------------------------------------------------------------------- #


def _validated(
    model_cls, update_cls, values: dict[str, Any], section: str, report: Report
):
    """Validate converted settings; fall back per-key to the new default."""
    clean: dict[str, Any] = {}
    defaults = model_cls().model_dump()
    for key, value in values.items():
        try:
            update_cls(**{key: value})
            clean[key] = value
        except ValidationError:
            report.warn(
                section,
                f"{key}={value!r} is invalid in the new version, using default {defaults[key]!r}",
            )
    return update_cls(**clean)


def insert_settings(
    old: OldData,
    cfg: Config,
    network_env: dict[str, str],
    report: Report,
    steps: Steps,
) -> None:
    converted = mapping.convert_settings(old.settings, cfg, report)
    app_settings = old.settings.get("app")
    mapping.suggest_network(
        app_settings if isinstance(app_settings, dict) else {},
        cfg,
        report,
        validate_domain=validate_domain,
        current_env=network_env,
    )
    for e in report.by_level("action"):
        steps.note(e.message)
    with db_session() as db:
        service = create_settings_service(db)
        service.save_system(
            _validated(
                SystemSettings,
                SystemSettingsUpdate,
                converted.system,
                "Settings",
                report,
            )
        )
        service.save_relay(
            _validated(
                RelaySettings, RelaySettingsUpdate, converted.relay, "Settings", report
            )
        )
    report.count("Settings (system + relay)", source=len(old.settings), migrated=2)
    steps.ok("system: " + ", ".join(f"{k}={v}" for k, v in converted.system.items()))
    steps.ok("relay: " + ", ".join(f"{k}={v}" for k, v in converted.relay.items()))


def insert_all(
    old: OldData,
    ref: ReferenceData,
    cfg: Config,
    tz: ZoneInfo,
    report: Report,
    steps: Steps,
) -> list[MigratedTorrent]:
    """Insert users, accounts, preferences, torrent files and torrents atomically."""
    migrated_torrents: list[MigratedTorrent] = []

    with db_session() as db:
        # ---- users ------------------------------------------------------ #
        users = old.tables.get("users", [])
        user_names: dict[str, str] = {}
        with steps.progress("users", len(users), unit="users") as counter:
            for row in users:
                values = mapping.convert_user(row, report)
                db.add(UserModel(**values))
                user_names[values["id"]] = values["username"]
                counter.advance()
        db.flush()
        report.count("Users", source=len(users), migrated=len(users))

        # ---- indexer accounts ------------------------------------------- #
        trackers = old.tables.get("trackers", [])
        accounts: set[str] = set()
        with steps.progress(
            "indexer accounts", len(trackers), unit="accounts"
        ) as counter:
            for row in trackers:
                values = mapping.convert_tracker(row, ref.definitions, tz, report)
                if values is not None:
                    db.add(IndexerAccountModel(**values))
                    accounts.add(values["indexer_id"])
                counter.advance()
        db.flush()
        report.count(
            "Indexer accounts (trackers)",
            source=len(trackers),
            migrated=len(accounts),
            skipped=len(trackers) - len(accounts),
        )

        # ---- preferences + exclusions ------------------------------------ #
        pref_rows = old.tables.get("user_preferences", [])
        by_user: dict[str, list[dict[str, Any]]] = {}
        orphan_prefs = 0
        for row in pref_rows:
            if row["user_id"] not in user_names:
                orphan_prefs += 1
                continue
            by_user.setdefault(row["user_id"], []).append(row)
        if orphan_prefs:
            report.lossy(
                "Preferences",
                f"{orphan_prefs} preference rows belonged to deleted users, dropped",
            )

        pref_count = 0
        excl_count = 0
        with steps.progress(
            "user preferences", len(pref_rows) - orphan_prefs, unit="rows"
        ) as counter:
            for user_id, rows in by_user.items():
                converted = mapping.convert_user_preferences(
                    user_id,
                    user_names[user_id],
                    rows,
                    ref.attributes_by_preference,
                    cfg,
                    report,
                )
                for pref in converted.preferences:
                    definition = PreferenceDefinitionModel(
                        preference_id=pref.preference_id
                    )
                    db.add(definition)
                    db.flush()
                    for order, attribute_id in enumerate(pref.attribute_ids):
                        db.add(
                            PreferenceDefinitionAttributeModel(
                                definition_id=definition.id,
                                attribute_id=attribute_id,
                                order=order,
                            )
                        )
                    db.add(
                        UserPreferenceDefinitionModel(
                            user_id=user_id,
                            definition_id=definition.id,
                            order=pref.order,
                        )
                    )
                    pref_count += 1
                for attribute_id in converted.exclusions:
                    db.add(
                        AttributeExclusionModel(
                            attribute_id=attribute_id, user_id=user_id
                        )
                    )
                    excl_count += 1
                counter.advance(len(rows))
        db.flush()
        report.count(
            "User preferences",
            source=len(pref_rows),
            migrated=pref_count,
            skipped=len(pref_rows) - pref_count,
        )
        blocked_values = sum(
            len(r["blocked"])
            for rows in by_user.values()
            for r in rows
            if isinstance(r.get("blocked"), list)
        )
        report.count(
            "Blocked values → attribute exclusions",
            source=blocked_values,
            migrated=excl_count,
            skipped=max(blocked_values - excl_count, 0),
        )

        # ---- cached .torrent files --------------------------------------- #
        files_by_key: dict[tuple[str, str], TorrentFileModel] = {}
        skipped_no_account: dict[str, int] = {}
        invalid = 0
        with steps.progress(
            ".torrent files", len(old.torrent_files), unit="files"
        ) as counter:
            for cached in old.torrent_files:
                counter.advance()
                if cached.tracker not in accounts:
                    skipped_no_account[cached.tracker] = (
                        skipped_no_account.get(cached.tracker, 0) + 1
                    )
                    continue
                try:
                    model = TorrentFileModel(
                        indexer_id=cached.tracker,
                        torrent_id=cached.torrent_id,
                        torrent_bytes=cached.path.read_bytes(),
                        last_used_at=mapping.to_local_naive(
                            dt.datetime.fromtimestamp(cached.mtime, tz=dt.timezone.utc),
                            tz,
                        ),
                        created_at=mapping.to_local_naive(
                            dt.datetime.fromtimestamp(cached.mtime, tz=dt.timezone.utc),
                            tz,
                        ),
                    )
                except Exception:
                    invalid += 1
                    report.lossy(
                        "Torrent files",
                        f"{cached.tracker}/{cached.torrent_id}.torrent is not a valid torrent, dropped",
                    )
                    continue
                db.add(model)
                files_by_key[(cached.tracker, cached.torrent_id)] = model
        db.flush()
        for tracker, n in skipped_no_account.items():
            report.lossy(
                "Torrent files",
                f"{n} cached .torrent files of '{tracker}' dropped: no {tracker} account was configured",
            )
        report.count(
            "Cached .torrent files",
            source=len(old.torrent_files),
            migrated=len(files_by_key),
            skipped=len(old.torrent_files) - len(files_by_key),
        )

        # ---- torrents (+ libtorrent resume data) ------------------------- #
        torrents = old.tables.get("torrents", [])
        used_resumes: set[str] = set()
        seen_hashes: set[tuple[str, str]] = set()
        with steps.progress("torrents", len(torrents), unit="torrents") as counter:
            for row in torrents:
                counter.advance()
                tracker, torrent_id = row["tracker"], str(row["torrent_id"])
                label = f"{tracker}/{torrent_id}"
                file_model = files_by_key.get((tracker, torrent_id))
                if tracker not in accounts:
                    report.lossy(
                        "Torrents",
                        f"{label}: no {tracker} account, torrent dropped (its downloaded files are still moved)",
                    )
                    continue
                if file_model is None:
                    report.lossy(
                        "Torrents",
                        f"{label}: its .torrent file is missing from the cache, torrent dropped (downloaded files are still moved)",
                    )
                    continue

                info_hash = file_model.info_hash
                old_hash = str(row["info_hash"]).lower()
                if old_hash != info_hash:
                    report.warn(
                        "Torrents",
                        f"{label}: stored info hash {old_hash} ≠ .torrent hash {info_hash}; using the .torrent",
                    )
                if (info_hash, tracker) in seen_hashes:
                    report.info(
                        "Torrents",
                        f"{label}: duplicate of an already migrated torrent, skipped",
                    )
                    continue
                seen_hashes.add((info_hash, tracker))

                resume_bytes = _load_resume(old, info_hash, old_hash, label, report)
                if resume_bytes is not None:
                    used_resumes.add(info_hash)
                    used_resumes.add(old_hash)

                last_played = mapping.parse_old_datetime(row.get("last_played_at"))
                created = mapping.parse_old_datetime(row.get("created_at"))
                updated = mapping.parse_old_datetime(row.get("updated_at")) or created
                # The new cleanup job measures "last played" by playback history
                # and falls back to torrents.created_at. There is no history yet,
                # so created_at must carry the old last_played_at, otherwise the
                # keep-seed timer would restart or expire incorrectly.
                effective_created = (
                    last_played or created or dt.datetime.now(dt.timezone.utc)
                )

                db.add(
                    TorrentModel(
                        info_hash=info_hash,
                        indexer_id=tracker,
                        torrent_id=torrent_id,
                        is_persisted=bool(row.get("is_persisted") or False),
                        full_download=None
                        if row.get("full_download") is None
                        else bool(row["full_download"]),
                        resume_bytes=resume_bytes,
                        created_at=mapping.to_local_naive(effective_created, tz),
                        updated_at=mapping.to_local_naive(
                            updated or effective_created, tz
                        ),
                    )
                )
                migrated_torrents.append(
                    MigratedTorrent(
                        info_hash=info_hash,
                        indexer_id=tracker,
                        torrent_id=torrent_id,
                        name=file_model.info.name,
                        torrent_bytes=file_model.torrent_bytes,
                        resume_bytes=resume_bytes,
                    )
                )
        db.flush()
        report.count(
            "Torrents",
            source=len(torrents),
            migrated=len(migrated_torrents),
            skipped=len(torrents) - len(migrated_torrents),
        )
        with_resume = sum(1 for t in migrated_torrents if t.resume_bytes)
        report.count(
            "Resume data (no re-check needed)",
            source=len(old.resumes),
            migrated=with_resume,
            skipped=len(old.resumes) - with_resume,
        )
        if migrated_torrents and with_resume < len(migrated_torrents):
            report.info(
                "Torrents",
                f"{len(migrated_torrents) - with_resume} torrents have no resume data; "
                "the new app hash-checks their files on first play",
            )
        orphan_resumes = [h for h in old.resumes if h not in used_resumes]
        if orphan_resumes:
            report.info(
                "Torrents",
                f"{len(orphan_resumes)} resume files belonged to no torrent in the DB and were dropped",
            )

        pairings = old.tables.get("pairings", [])
        sessions = old.tables.get("sessions", [])
        report.count(
            "Device pairings", source=len(pairings), migrated=0, skipped=len(pairings)
        )
        report.count(
            "Login sessions", source=len(sessions), migrated=0, skipped=len(sessions)
        )

    return migrated_torrents


def _load_resume(
    old: OldData, info_hash: str, old_hash: str, label: str, report: Report
) -> bytes | None:
    path = old.resumes.get(info_hash) or old.resumes.get(old_hash)
    if path is None:
        return None
    data = path.read_bytes()
    try:
        params = libtorrent.read_resume_data(data)
    except Exception as e:  # corrupt resume -> the app would drop it anyway
        report.warn(
            "Torrents",
            f"{label}: resume data unreadable ({e}); the new app will hash-check the files",
        )
        return None
    resume_hash = str(params.info_hashes.v1) if hasattr(params, "info_hashes") else ""
    if resume_hash and resume_hash != "0" * 40 and resume_hash.lower() != info_hash:
        report.warn(
            "Torrents",
            f"{label}: resume data belongs to another torrent ({resume_hash}), ignored",
        )
        return None
    return data


def dispose() -> None:
    engine.dispose()
