"""Read side: detect the old release, snapshot + dump its database, scan its files.

What each release looks like (folder layout, last DB migration, resume data)
comes from versions.toml. The source database is never written to: it is
opened read-only and copied with SQLite's online backup API (which also folds
in a pending WAL), and all further reads happen on that snapshot.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Config, Layout, VersionProfile
from .report import Report
from .ui import Steps

REQUIRED_TABLES = ("users", "user_preferences", "trackers", "torrents", "settings")
DUMP_TABLES = (
    "migrations",
    "settings",
    "users",
    "user_preferences",
    "trackers",
    "torrents",
    "pairings",
    "sessions",
)
JSON_COLUMNS = {
    "settings": ("value",),
    "user_preferences": ("preferred", "blocked"),
}


class SourceError(RuntimeError):
    pass


@dataclass
class TorrentCacheFile:
    tracker: str
    torrent_id: str
    path: Path
    mtime: float


@dataclass
class OldData:
    tables: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    torrent_files: list[TorrentCacheFile] = field(default_factory=list)
    resumes: dict[str, Path] = field(default_factory=dict)
    last_migration: str | None = None

    @property
    def settings(self) -> dict[str, Any]:
        return {row["key"]: row["value"] for row in self.tables.get("settings", [])}


@dataclass
class OldPaths:
    root: Path
    layout: Layout

    @property
    def db(self) -> Path:
        return self.root / self.layout.database

    @property
    def torrents(self) -> Path:
        return self.root / self.layout.torrents

    @property
    def resumes(self) -> Path:
        return self.root / self.layout.resumes

    @property
    def downloads(self) -> Path:
        return self.root / self.layout.downloads

    def rebased(self, root: Path) -> OldPaths:
        return OldPaths(root=root, layout=self.layout)


@dataclass
class Detected:
    paths: OldPaths
    profile: VersionProfile
    last_migration: str


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _migration_ts(name: str | None) -> int | None:
    m = re.search(r"(\d{13})$", name or "")
    return int(m.group(1)) if m else None


def database_kind(db: Path) -> str | None:
    """'legacy' (TypeORM, v0.22 or older), 'current' (alembic) or None (no DB).

    Opens the file read-only, so it is safe to call on a live data folder.
    """
    if not db.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            tables = _table_names(conn)
        finally:
            conn.close()
    except sqlite3.DatabaseError as e:
        raise SourceError(f"{db} is not a readable SQLite database: {e}") from e
    if "alembic_version" in tables:
        return "current"
    if "migrations" in tables:
        return "legacy"
    return None


def find_legacy_database(data_dir: Path, cfg: Config | None = None) -> Path | None:
    """The old release's database in `data_dir`, in any known layout, if any."""
    if cfg is None:
        from .config import DEFAULT_PATH, load

        cfg = load(DEFAULT_PATH)
    for layout in cfg.layouts.values():
        db = data_dir / layout.database
        try:
            if database_kind(db) == "legacy":
                return db
        except SourceError:
            continue
    return None


def detect(data_dir: Path, cfg: Config, report: Report) -> Detected:
    """Find the old database (whichever layout it is in) and identify the release.

    Read-only; runs before anything is changed.
    """
    kinds = {
        layout.name: database_kind(data_dir / layout.database)
        for layout in cfg.layouts.values()
    }
    found = [lay for lay in cfg.layouts.values() if kinds[lay.name] == "legacy"]
    if not found:
        if "current" in kinds.values():
            raise SourceError(
                "the database in this data folder is already a v0.23+ (FastAPI) "
                "database; this data folder has been migrated already."
            )
        expected = ", ".join(lay.database for lay in cfg.layouts.values())
        raise SourceError(
            f"no old database found in {data_dir} (expected one of: {expected})."
        )
    if len(found) > 1:
        both = " and ".join(lay.database for lay in found)
        raise SourceError(
            f"found {both}: two old databases in one data folder (probably a half-done "
            "manual move from the v0.20.0 upgrade notes). Keep the one the old app really "
            "used and move the other away."
        )
    layout = found[0]
    paths = OldPaths(root=data_dir, layout=layout)

    conn = sqlite3.connect(f"file:{paths.db}?mode=ro", uri=True)
    try:
        tables = _table_names(conn)
        last = None
        if "migrations" in tables:
            row = conn.execute(
                "SELECT name FROM migrations ORDER BY timestamp DESC, id DESC LIMIT 1"
            ).fetchone()
            last = row[0] if row else None
    finally:
        conn.close()

    profile = cfg.profile_for(last)
    if profile is None:
        oldest = min(_migration_ts(v.last_migration) or 0 for v in cfg.versions)
        ts = _migration_ts(last)
        if ts is not None and ts < oldest:
            raise SourceError(
                f"the database is from a release older than v0.17.0 (last migration {last}). {cfg.unsupported_message}"
            )
        raise SourceError(
            f"unknown database version (last migration {last!r}). Supported: {cfg.supported_range}. "
            f"If this is a newer NestJS release, add it to {cfg.path.name}."
        )

    missing = [t for t in REQUIRED_TABLES if t not in tables]
    if missing:
        raise SourceError(
            f"{layout.database} is missing tables {', '.join(missing)}; the database looks damaged."
        )

    if profile.layout != layout.name:
        report.warn(
            "Source",
            f"the database is from {profile.releases}, which normally uses the '{profile.layout}' layout, "
            f"but it was found in the '{layout.name}' layout ({layout.database}). Using the folders found.",
        )
    for note in profile.notes:
        report.info("Source", note)
    for warning in profile.warnings:
        report.warn("Source", warning)
    return Detected(paths=paths, profile=profile, last_migration=last or "")


def snapshot_database(db_path: Path, target: Path) -> None:
    """Consistent copy of the live DB (including any un-checkpointed WAL)."""
    if not db_path.is_file():
        raise SourceError(f"old database not found: {db_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def dump_database(
    snapshot: Path, dump_dir: Path, steps: Steps, report: Report
) -> dict[str, list[dict[str, Any]]]:
    """Dump every relevant table to JSON (kept as an audit trail) and return rows."""
    dump_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(snapshot)
    conn.row_factory = sqlite3.Row
    tables: dict[str, list[dict[str, Any]]] = {}
    try:
        present = _table_names(conn)
        for table in DUMP_TABLES:
            if table not in present:
                tables[table] = []
                continue
            total = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            rows: list[dict[str, Any]] = []
            with steps.progress(f"{table}", total, unit="rows") as counter:
                for r in conn.execute(f'SELECT * FROM "{table}"'):
                    row = dict(r)
                    for col in JSON_COLUMNS.get(table, ()):
                        raw = row.get(col)
                        if isinstance(raw, str):
                            try:
                                row[col] = json.loads(raw)
                            except json.JSONDecodeError:
                                report.warn(
                                    "Source",
                                    f"{table}.{col} holds invalid JSON, treated as empty: {raw[:80]!r}",
                                )
                                row[col] = None
                    rows.append(row)
                    counter.advance()
            tables[table] = rows
            (dump_dir / f"{table}.json").write_text(
                json.dumps(rows, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
    finally:
        conn.close()
    return tables


def scan_torrent_cache(torrents_dir: Path, steps: Steps) -> list[TorrentCacheFile]:
    if not torrents_dir.is_dir():
        return []
    paths = sorted(
        p
        for p in torrents_dir.glob("*/*")
        if p.is_file() and p.name.lower().endswith(".torrent")
    )
    found: list[TorrentCacheFile] = []
    with steps.progress(".torrent files", len(paths), unit="files") as counter:
        for p in paths:
            found.append(
                TorrentCacheFile(
                    tracker=p.parent.name,
                    torrent_id=p.name[: -len(".torrent")],
                    path=p,
                    mtime=p.stat().st_mtime,
                )
            )
            counter.advance()
    return found


def scan_resumes(resumes_dir: Path, steps: Steps) -> dict[str, Path]:
    if not resumes_dir.is_dir():
        return {}
    paths = sorted(
        p for p in resumes_dir.iterdir() if p.is_file() and p.suffix == ".resume"
    )
    found: dict[str, Path] = {}
    with steps.progress("resume files", len(paths), unit="files") as counter:
        for p in paths:
            found[p.stem.lower()] = p
            counter.advance()
    return found
