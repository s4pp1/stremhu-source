"""Builds data folders of old (v0.17–v0.22, NestJS) releases for the legacy
migration tests.

The schema comes from tests/data/legacy/<release>.sql (produced by replaying
every TypeORM migration of that git tag); the folder layout and whether resume
files exist come from app/legacy_migration/versions.toml. Torrents, downloads
and resume data are created with libtorrent the way the old relay did.
"""

import json
import shutil
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import libtorrent
from argon2 import PasswordHasher

from app.legacy_migration.config import DEFAULT_PATH, load

SCHEMAS = Path(__file__).parent / "data" / "legacy"

# @node-rs/argon2 defaults used by the old server: argon2id, m=19456, t=2, p=1
OLD_PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
ADMIN_PASSWORD = "admin-pass"


@dataclass
class LegacyFixture:
    root: Path
    release: str
    layout: str
    resume_data: bool
    admin_token: str
    user_token: str
    info_hashes: dict[str, str] = field(default_factory=dict)


@dataclass
class _Spec:
    key: str
    tracker: str
    torrent_id: str
    files: dict[str, int]
    partial: bool = False
    in_cache: bool = True
    resume: bool = True


def _content(staging: Path, spec: _Spec, seed: int) -> Path:
    pattern = bytes((i * seed + i // 7) % 256 for i in range(4096))
    for rel, size in spec.files.items():
        path = staging / spec.key / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            left = size
            while left:
                chunk = pattern[: min(left, len(pattern))]
                f.write(chunk)
                left -= len(chunk)
    first = next(iter(spec.files)).split("/")[0]
    return staging / spec.key / first


def _torrent(content: Path) -> bytes:
    storage = libtorrent.file_storage()
    libtorrent.add_files(storage, str(content))
    creator = libtorrent.create_torrent(
        storage, 16384, flags=libtorrent.create_torrent.v1_only
    )
    libtorrent.set_piece_hashes(creator, str(content.parent))
    return libtorrent.bencode(creator.generate())


def _info_hash(torrent: bytes) -> str:
    return str(libtorrent.torrent_info(torrent).info_hash())


def _resume(torrent: bytes, downloads: Path) -> bytes:
    params = libtorrent.session_params()
    params.settings = {
        "listen_interfaces": "127.0.0.1:0",
        "enable_dht": False,
        "enable_lsd": False,
        "enable_upnp": False,
        "enable_natpmp": False,
        "alert_mask": libtorrent.alert_category.status
        | libtorrent.alert_category.storage,
    }
    session = libtorrent.session(params)
    add = libtorrent.add_torrent_params()
    add.ti = libtorrent.torrent_info(torrent)
    add.save_path = str(downloads)
    handle = session.add_torrent(add)
    handle.force_recheck()
    checking = {
        libtorrent.torrent_status.checking_files,
        libtorrent.torrent_status.checking_resume_data,
    }
    deadline = time.time() + 30
    while time.time() < deadline and handle.status().state in checking:
        time.sleep(0.05)
    handle.pause()
    handle.save_resume_data(libtorrent.save_resume_flags_t.flush_disk_cache)
    deadline = time.time() + 10
    while time.time() < deadline:
        for alert in session.pop_alerts():
            if isinstance(alert, libtorrent.save_resume_data_alert):
                return libtorrent.bencode(libtorrent.write_resume_data(alert.params))
        time.sleep(0.05)
    raise RuntimeError("libtorrent produced no resume data")


def build_legacy_data(root: Path, release: str) -> LegacyFixture:
    """A data folder of `release` (a file name in tests/data/legacy) at `root`."""
    schema = (SCHEMAS / f"{release}.sql").read_text()
    root.mkdir(parents=True, exist_ok=True)
    tmp_db = root / ".schema.db"
    conn = sqlite3.connect(tmp_db)
    conn.executescript(schema)
    last = conn.execute(
        "SELECT name FROM migrations ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()[0]
    conn.close()

    cfg = load(DEFAULT_PATH)
    profile = cfg.profile_for(last)
    if profile is None:  # releases the migrator refuses: DB only
        (root / "database").mkdir()
        tmp_db.rename(root / "database" / "app.db")
        return LegacyFixture(root, release, "root", False, "", "")

    layout = cfg.layouts[profile.layout]
    db = root / layout.database
    db.parent.mkdir(parents=True, exist_ok=True)
    tmp_db.rename(db)
    torrents_dir = root / layout.torrents
    resumes_dir = root / layout.resumes
    downloads = root / layout.downloads
    downloads.mkdir(parents=True)
    has_filelist = "filelist" in profile.trackers

    specs = [
        _Spec("complete", "ncore", "3512001", {"Complete.Pack/Movie.2160p.mkv": 300_000, "Complete.Pack/Sample/sample.mkv": 20_000}),
        _Spec("partial", "insane", "88001", {"Show.S01E01.1080p.mkv": 400_000}, partial=True),
        _Spec("noresume", "ncore", "3512002", {"Old.Film.DVDRip.avi": 120_000}, resume=False),
        _Spec("missing", "majomparade", "777", {"Lost.Torrent.720p.mkv": 50_000}, in_cache=False),
        _Spec("noaccount", "bithumen", "4242", {"Bithumen.Movie.mkv": 60_000}),
    ]
    if has_filelist:
        specs.append(_Spec("filelist", "filelist", "990011", {"FileList.Movie.mkv": 70_000}))

    staging = root.parent / f".{root.name}-staging"
    torrents: dict[str, tuple[_Spec, bytes]] = {}
    for seed, spec in enumerate(specs, start=3):
        content = _content(staging, spec, seed)
        torrent = _torrent(content)
        torrents[spec.key] = (spec, torrent)
        target = downloads / content.name
        if content.is_dir():
            shutil.copytree(content, target)
        else:
            shutil.copy2(content, target)
        if spec.partial:  # keep the first 40%, sparse hole after it
            size = target.stat().st_size
            with open(target, "r+b") as f:
                f.truncate(int(size * 0.4))
                f.truncate(size)
        if spec.in_cache:
            (torrents_dir / spec.tracker).mkdir(parents=True, exist_ok=True)
            (torrents_dir / spec.tracker / f"{spec.torrent_id}.torrent").write_bytes(
                torrent
            )
        if profile.resume_data and spec.resume:
            resumes_dir.mkdir(parents=True, exist_ok=True)
            (resumes_dir / f"{_info_hash(torrent)}.resume").write_bytes(
                _resume(torrent, downloads)
            )
    shutil.rmtree(staging)
    (downloads / "Orphan.Folder").mkdir()
    (downloads / "Orphan.Folder" / "readme.txt").write_text("orphan")
    (torrents_dir / "ncore" / "999.torrent").write_bytes(b"not a torrent")

    admin_id, user_id = str(uuid.uuid4()), str(uuid.uuid4())
    admin_token, user_token = str(uuid.uuid4()), str(uuid.uuid4())
    conn = sqlite3.connect(db)
    users_sql = (
        "INSERT INTO users (id, username, password_hash, user_role, torrent_seed, "
        "token, updated_at, created_at, only_best_torrent) VALUES (?,?,?,?,?,?,?,?,?)"
    )
    conn.execute(
        users_sql,
        (admin_id, "admin", OLD_PASSWORD_HASHER.hash(ADMIN_PASSWORD), "admin", 3,
         admin_token, "2026-05-01 10:00:00", "2025-11-10 08:30:00", 1),
    )
    conn.execute(
        users_sql,
        (user_id, "family", None, "user", None, user_token,
         "2026-04-01 10:00:00", "2026-01-02 08:30:00", 0),
    )
    trackers = [
        ("ncore", "ncuser", "nc-pass", 1, 172800, 0, 0),
        ("insane", "insuser", "ins-pass", None, None, 0, 1),
        ("majomparade", "mpuser", "mp-pass", 0, None, 0, 2),
    ]
    if has_filelist:
        trackers.append(("filelist", "fluser", "fl-pass", None, None, 0, 3))
    conn.executemany(
        "INSERT INTO trackers (tracker, username, password, hit_and_run, "
        "keep_seed_seconds, download_full_torrent, order_index) VALUES (?,?,?,?,?,?,?)",
        trackers,
    )
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('app', ?)",
        (json.dumps({
            "instanceId": str(uuid.uuid4()), "enebledlocalIp": False,
            "address": "https://stremhu.example.com", "hitAndRun": False,
            "keepSeedSeconds": 3600, "cacheRetentionSeconds": 7 * 86400,
            "catalogToken": "catalog-secret",
        }),),
    )
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('torrent', ?)",
        (json.dumps({"port": 6882, "downloadLimit": 5_000_000, "connectionsLimit": 300}),),
    )
    sites = ["ncore", "insane", "majomparade"] + (["filelist"] if has_filelist else [])
    prefs: list[tuple[str, str, list[str], list[str], int | None]] = [
        (admin_id, "tracker", sites, ["bithumen"], 0),
        (admin_id, "language", ["hu", "en"], [], 1),
        (admin_id, "source", ["disc-remux", "disc-rip", "web-dl"], ["theatrical", "unknown"], 2),
        (admin_id, "audio-quality", ["truehd", "ddp", "unknown"], [], 3),
        (user_id, "resolution", ["1080p", "720p"], [], None),
        (user_id, "language", ["hu"], ["en"], None),
    ]
    conn.executemany(
        'INSERT INTO user_preferences (preference, user_id, preferred, blocked, "order") '
        "VALUES (?,?,?,?,?)",
        [(p, u, json.dumps(a), json.dumps(b), o) for u, p, a, b, o in prefs],
    )
    played = {
        "complete": "2026-09-20 18:00:00",
        "partial": "2026-09-29 21:15:00",
        "noresume": "2026-06-01 12:00:00",
        "missing": "2026-09-01 12:00:00",
        "noaccount": "2026-09-02 12:00:00",
        "filelist": "2026-09-25 20:00:00",
    }
    for key, (spec, torrent) in torrents.items():
        conn.execute(
            "INSERT INTO torrents (tracker, torrent_id, info_hash, is_persisted, "
            "last_played_at, full_download, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (spec.tracker, spec.torrent_id, _info_hash(torrent), int(key == "complete"),
             played[key], None, "2026-03-03 03:03:03", played[key]),
        )
    conn.commit()
    conn.close()

    return LegacyFixture(
        root=root,
        release=release,
        layout=layout.name,
        resume_data=profile.resume_data,
        admin_token=admin_token,
        user_token=user_token,
        info_hashes={k: _info_hash(t) for k, (_, t) in torrents.items()},
    )
