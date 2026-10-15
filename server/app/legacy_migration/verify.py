"""Post-migration verification using the new application's own code paths."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import libtorrent
from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError

from app.common.database import db_session
from app.modules.attribute_exclusions.repository import AttributeExclusionsRepository
from app.modules.attribute_exclusions.schemas.internal import AttributeExclusionFilter
from app.modules.settings.dependencies import create_settings_service
from app.modules.torrents.repository import TorrentRepository
from app.modules.user_preference_definitions.repository import (
    UserPreferenceDefinitionsRepository,
)
from app.modules.users.models import UserModel

from .report import Report
from .target import MigratedTorrent
from .ui import Steps

SECTION = "Verification"


def verify_database(db_path: Path, report: Report, steps: Steps) -> None:
    conn = sqlite3.connect(db_path)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    if fk_errors:
        raise RuntimeError(
            f"foreign key violations in the new database: {fk_errors[:5]}"
        )
    steps.ok("SQLite integrity + foreign keys ok")

    with db_session() as db:
        settings = create_settings_service(db)
        settings.get_system()
        settings.get_relay()

        users = db.query(UserModel).all()
        prefs_repo = UserPreferenceDefinitionsRepository(db)
        excl_repo = AttributeExclusionsRepository(db)
        with steps.progress(
            "users (as the app loads them)", len(users), unit="users"
        ) as counter:
            for user in users:
                prefs_repo.find_list(user.id)
                excl_repo.find_list(AttributeExclusionFilter(user_id=user.id))
                if user.password_hash:
                    try:
                        extract_parameters(user.password_hash)
                    except InvalidHashError:
                        report.warn(
                            SECTION,
                            f"user '{user.username}': password hash is not a valid argon2 hash; "
                            "reset the password in the new UI",
                        )
                counter.advance()
        torrents = TorrentRepository(db).find()
        for t in torrents:
            _ = t.torrent_file.info  # parses the stored .torrent like the app does
    steps.ok(
        f"{len(users)} users and {len(torrents)} torrents load through the app's repositories"
    )


def _offline_torrent_info(torrent_bytes: bytes) -> libtorrent.torrent_info:
    """The torrent without its announce URLs (the info hash is unaffected)."""
    decoded = libtorrent.bdecode(torrent_bytes)
    decoded.pop(b"announce", None)
    decoded.pop(b"announce-list", None)
    return libtorrent.torrent_info(decoded)


def verify_torrent_data(
    torrents: list[MigratedTorrent],
    downloads: Path,
    timeout: float,
    report: Report,
    steps: Steps,
) -> None:
    """Add every torrent (paused, offline) the way the new relay does, with its
    resume data, and see how much of it libtorrent accepts from disk."""
    if not torrents:
        steps.ok("no torrents to check")
        return

    params = libtorrent.session_params()
    params.settings = {
        "listen_interfaces": "127.0.0.1:0",
        "enable_dht": False,
        "enable_lsd": False,
        "enable_upnp": False,
        "enable_natpmp": False,
        "alert_mask": 0,
    }
    session = libtorrent.session(params)
    handles: list[tuple[MigratedTorrent, libtorrent.torrent_handle]] = []
    for t in torrents:
        params = (
            libtorrent.read_resume_data(t.resume_bytes)
            if t.resume_bytes
            else libtorrent.add_torrent_params()
        )
        params.ti = _offline_torrent_info(t.torrent_bytes)
        params.trackers = []
        params.save_path = str(downloads)
        params.storage_mode = libtorrent.storage_mode_t.storage_mode_sparse
        # Paused torrents are never file-checked; stop_when_ready checks and
        # then pauses by itself. Without trackers/DHT nothing is announced.
        params.flags &= ~libtorrent.torrent_flags.paused
        params.flags &= ~libtorrent.torrent_flags.auto_managed
        params.flags |= libtorrent.torrent_flags.stop_when_ready
        handles.append((t, session.add_torrent(params)))

    checking = {
        libtorrent.torrent_status.checking_resume_data,
        libtorrent.torrent_status.checking_files,
    }
    complete = partial = empty = unsettled = 0
    deadline = time.monotonic() + timeout
    with steps.progress(
        "checking torrent data on disk", len(handles), unit="torrents"
    ) as counter:
        pending = list(handles)
        while pending:
            still = []
            for t, h in pending:
                st = h.status()
                if st.state in checking and time.monotonic() < deadline:
                    still.append((t, h))
                    continue
                counter.advance()
                if st.state in checking:
                    unsettled += 1
                    report.info(
                        SECTION,
                        f"{t.name}: still being checked after {timeout:.0f}s, not verified",
                    )
                elif st.errc.value() != 0:
                    empty += 1
                    report.warn(
                        SECTION,
                        f"{t.name}: {st.errc.message()} — the new app will re-download",
                    )
                elif st.progress >= 0.9999:
                    complete += 1
                elif st.progress > 0:
                    partial += 1
                else:
                    empty += 1
            pending = still
            if pending:
                time.sleep(0.2)

    del session
    report.count("Torrent data: complete on disk", migrated=complete)
    report.count("Torrent data: partial on disk", migrated=partial)
    report.count("Torrent data: nothing on disk", migrated=empty)
    if unsettled:
        report.count("Torrent data: not verified (timeout)", migrated=unsettled)
    steps.ok(
        f"complete: {complete}, partial: {partial}, nothing on disk: {empty}, not verified: {unsettled}"
    )
