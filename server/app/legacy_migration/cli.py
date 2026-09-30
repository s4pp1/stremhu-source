"""Legacy data migration: StremHU Source v0.17–v0.22 (NestJS) -> this version.

Run it with the same image and volumes as the app, while the app is stopped:

    docker compose run --rm stremhu-source python -m app.legacy_migration --dry-run
    docker compose run --rm stremhu-source python -m app.legacy_migration

By default the app's own data folder (/app/data) is migrated in place: the old
release's system folders are set aside under `migration/<timestamp>/old-data/`
and the downloads stay where they are. `--source PATH` migrates from a
separate old data folder into /app/data instead. Which releases are supported,
and how each one is laid out, is defined in versions.toml.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import shutil
import tempfile
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

from .report import Report
from .source import OldPaths
from .ui import Steps, console

STEP_TITLES = [
    "Preflight checks",
    "Preparing the destination",
    "Dumping the old database",
    "Scanning old torrent cache and resume data",
    "Creating the new database (current schema + reference data)",
    "Converting and inserting settings",
    "Converting and inserting users, indexer accounts, preferences and torrents",
    "Downloads",
    "Verifying the result",
    "Writing the report",
]

# server/app/legacy_migration/cli.py -> server/data (= /app/data in the image);
# the same default as app.config.Config.base_data_dir, without importing it.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _same_dir(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except FileNotFoundError:
        return False


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.legacy_migration",
        description=(
            "Migrate StremHU Source v0.17–v0.22 data (users, API keys, tracker logins, "
            "preferences, settings, torrents) to this version. Stop the app first."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="convert into a scratch database and write a report; change nothing",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="old data folder, if it is not the app's own data folder (default: migrate in place)",
    )
    parser.add_argument(
        "--downloads",
        choices=("move", "copy", "keep"),
        default="move",
        help="with --source: what to do with the old downloads/ (default: move)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="with --source: replace an existing new database (it is backed up first)",
    )
    parser.add_argument(
        "--no-verify-torrents",
        dest="verify_torrents",
        action="store_false",
        help="skip the libtorrent check of the torrent data on disk",
    )
    parser.add_argument(
        "--verify-timeout",
        type=float,
        default=300.0,
        help="seconds allowed for that check (default: 300)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="use this versions.toml instead of the built-in one",
    )
    return parser.parse_args(argv)


def _prepare_runtime(target: Path) -> dict[str, str]:
    """Point the app's data dir at `target`; returns the network env the
    container was started with. Must run before anything imports `app.config`."""
    network_env = {
        k: os.environ[k]
        for k in ("HOST_IP", "REVERSE_PROXY_DOMAIN")
        if os.environ.get(k)
    }
    if not network_env:
        # app.config requires one of them; the migrator never uses the network
        os.environ["HOST_IP"] = "192.0.2.1"
    os.environ["DATA_DIR"] = str(target)
    target.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
    )
    return network_env


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    dest_dir = Path(os.environ.get("DATA_DIR") or DEFAULT_DATA_DIR)
    source_dir: Path = args.source or dest_dir
    if args.config:
        os.environ["MIGRATOR_CONFIG"] = str(args.config)

    import tzlocal

    tz = ZoneInfo(tzlocal.get_localzone_name())
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    steps = Steps(len(STEP_TITLES))
    report = Report()
    dry_run: bool = args.dry_run

    console.print()
    console.rule("[bold]StremHU Source · legacy data migration (v0.17–v0.22)[/]")
    if dry_run:
        console.print(
            "[bold yellow]DRY RUN[/] — nothing in the data folders will be changed "
            "(only a report is written)."
        )

    in_place = _same_dir(source_dir, dest_dir)
    if in_place:
        source_dir = dest_dir
    workdir = dest_dir / "migration" / (stamp + ("-dry-run" if dry_run else ""))
    report.context.update(
        {
            "Mode": ("in place" if in_place else "separate source folder")
            + (" (dry run)" if dry_run else ""),
            "Source": str(source_dir),
            "Destination": str(dest_dir),
            "Downloads": "untouched (in place)" if in_place else args.downloads,
            "Timezone": str(tz),
            "Artifacts": str(workdir),
        }
    )

    # Things to undo on failure (real runs only).
    rollback: list[tuple[str, Path, Path | None]] = []
    target_data = dest_dir
    migrated_torrents = []
    torrent_check_downloads: Path | None = None
    network_env: dict[str, str] = {}

    try:
        # ------------------------------------------------------------------ 1
        steps.start(STEP_TITLES[0])
        if not source_dir.is_dir():
            raise RuntimeError(
                f"source folder {source_dir} does not exist (is it mounted?)"
            )
        dest_dir.mkdir(parents=True, exist_ok=True)
        from . import config as config_module
        from .source import database_kind, detect

        cfg = config_module.load()
        detected = detect(source_dir, cfg, report)
        old_paths = detected.paths
        layout = old_paths.layout
        report.context["Detected release"] = (
            f"{detected.profile.releases} ('{layout.name}' layout, "
            f"last DB migration {detected.last_migration})"
        )
        if cfg.path != config_module.DEFAULT_PATH:
            report.context["Config"] = str(cfg.path)
        wal = old_paths.db.with_name("app.db-wal")
        if wal.exists() and wal.stat().st_size > 0:
            steps.warn(
                "the old database has a non-empty WAL file — make sure the old app is stopped"
            )
        steps.ok(
            f"detected {detected.profile.releases} in {source_dir} ({layout.description})"
        )
        steps.ok("mode: " + report.context["Mode"])

        new_db = dest_dir / "system" / "database" / "app.db"
        # A new-version database next to the old data means the app was started
        # before migrating (or the destination is in use): never mix into it.
        replace_new_db = (
            database_kind(new_db) == "current" if in_place else new_db.exists()
        )
        if replace_new_db and not args.overwrite and not dry_run:
            raise RuntimeError(
                f"{new_db} already exists (a database of the new version). "
                f"Use --overwrite to replace it (it will be backed up to {workdir})."
            )
        for name in _unused_entries(old_paths):
            report.info(
                "Source", f"{name} is not used by the new version and was not migrated"
            )

        # ------------------------------------------------------------------ 2
        steps.start(STEP_TITLES[1])
        workdir.mkdir(parents=True, exist_ok=True)
        if dry_run:
            target_data = Path(tempfile.mkdtemp(prefix="stremhu-legacy-dry-run-"))
            steps.ok(f"scratch database in {target_data}")
        elif in_place:
            if replace_new_db:
                aside = workdir / "replaced-system"
                os.rename(dest_dir / "system", aside)
                rollback.append(("restore", aside, dest_dir / "system"))
                steps.ok(f"existing new-version system/ backed up to {aside}")
            aside_root = workdir / "old-data"
            aside_root.mkdir()
            for name in layout.top_level():
                original = dest_dir / name
                if original.exists():
                    os.rename(original, aside_root / name)
                    rollback.append(("restore", aside_root / name, original))
                    steps.ok(
                        f"old {name}/ moved aside to {aside_root / name} (kept as a backup)"
                    )
            old_paths = old_paths.rebased(aside_root)
        elif replace_new_db:
            aside = workdir / "replaced-system"
            os.rename(dest_dir / "system", aside)
            rollback.append(("restore", aside, dest_dir / "system"))
            steps.ok(f"existing system/ backed up to {aside}")
        else:
            steps.ok("destination is ready")
        if not dry_run:
            rollback.append(("remove", target_data / "system", None))

        network_env = _prepare_runtime(target_data)

        # ------------------------------------------------------------------ 3
        steps.start(STEP_TITLES[2])
        from . import source

        snapshot = workdir / "old-app.db"
        source.snapshot_database(old_paths.db, snapshot)
        steps.ok(f"consistent snapshot: {snapshot}")
        old = source.OldData(last_migration=detected.last_migration)
        old.tables = source.dump_database(snapshot, workdir / "dump", steps, report)
        steps.ok(f"JSON dump written to {workdir / 'dump'}")

        # ------------------------------------------------------------------ 4
        steps.start(STEP_TITLES[3])
        old.torrent_files = source.scan_torrent_cache(old_paths.torrents, steps)
        if detected.profile.resume_data:
            old.resumes = source.scan_resumes(old_paths.resumes, steps)
            steps.ok(
                f"{len(old.torrent_files)} cached .torrent files, "
                f"{len(old.resumes)} resume files"
            )
        else:
            steps.ok(
                f"{len(old.torrent_files)} cached .torrent files "
                f"({detected.profile.releases} kept no resume data)"
            )

        # ------------------------------------------------------------------ 5
        steps.start(STEP_TITLES[4])
        from . import target

        ref = target.initialize_database(steps)
        report.context["New version"] = target.app_version()

        # ------------------------------------------------------------------ 6
        steps.start(STEP_TITLES[5])
        target.insert_settings(old, cfg, network_env, report, steps)

        # ------------------------------------------------------------------ 7
        steps.start(STEP_TITLES[6])
        migrated_torrents = target.insert_all(old, ref, cfg, tz, report, steps)
        steps.ok("all rows committed in one transaction")

        # ------------------------------------------------------------------ 8
        steps.start(STEP_TITLES[7])
        from . import files

        src_downloads = old_paths.root / layout.downloads if not in_place else None
        dst_downloads = dest_dir / "downloads"
        if in_place or src_downloads is None:
            steps.ok("in place: downloads stay where they are")
            torrent_check_downloads = dst_downloads
        elif dry_run or args.downloads == "keep":
            inv = files.inventory(src_downloads, steps)
            steps.ok(
                f"{len(inv.entries)} entries, {inv.files} files, "
                f"{inv.apparent_bytes / 2**30:.2f} GiB"
            )
            if args.downloads == "keep":
                report.warn(
                    "Downloads",
                    f"--downloads keep: mount the old downloads folder ({src_downloads}) "
                    "as /app/data/downloads",
                )
            if dry_run and args.downloads != "keep":
                steps.note(f"dry run: would {args.downloads} them")
            torrent_check_downloads = src_downloads
        else:
            inv = files.inventory(src_downloads, steps)
            steps.ok(
                f"{len(inv.entries)} entries, {inv.files} files, "
                f"{inv.apparent_bytes / 2**30:.2f} GiB"
            )
            if args.downloads == "copy":
                files.check_space(dst_downloads, inv, steps)
            files.transfer(
                src_downloads, dst_downloads, args.downloads, inv, report, steps
            )
            steps.ok(
                f"downloads {'moved' if args.downloads == 'move' else 'copied'} "
                f"to {dst_downloads}"
            )
            torrent_check_downloads = dst_downloads

        names = {t.name for t in migrated_torrents}
        orphans = files.orphan_entries(torrent_check_downloads, names)
        if orphans:
            shown = ", ".join(orphans[:20]) + (
                f", … (+{len(orphans) - 20})" if len(orphans) > 20 else ""
            )
            report.info(
                "Downloads",
                f"{len(orphans)} download entries belong to no migrated torrent. They are "
                f"kept on disk; if the same torrent is played again the app finds them "
                f"by hash check: {shown}",
            )

        # ------------------------------------------------------------------ 9
        steps.start(STEP_TITLES[8])
        from . import verify

        verify.verify_database(target.database_path(), report, steps)
        if args.verify_torrents:
            verify.verify_torrent_data(
                migrated_torrents,
                torrent_check_downloads,
                args.verify_timeout,
                report,
                steps,
            )
        else:
            steps.note("torrent data check skipped")
        target.dispose()
        if dry_run:
            shutil.rmtree(target_data, ignore_errors=True)

        report.status = "dry-run" if dry_run else "success"
        rollback.clear()
    except Exception as exc:
        report.status = "failed"
        report.warn("Error", f"{type(exc).__name__}: {exc}")
        steps.fail(f"{type(exc).__name__}: {exc}")
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        _rollback(rollback, steps)
    finally:
        # ----------------------------------------------------------------- 10
        steps.index = len(STEP_TITLES) - 1
        steps.start(STEP_TITLES[-1])
        report.finished_at = dt.datetime.now(dt.timezone.utc)
        if workdir.parent.exists():
            report.write(workdir)
            steps.ok(f"{workdir / 'report.md'} (+ report.json)")
        _summary(report)

    return 0 if report.status in ("success", "dry-run") else 1


def _unused_entries(paths: OldPaths) -> list[str]:
    """Things in the old data folder that no feature of the new version reads."""
    layout = paths.layout
    known_top = set(layout.top_level()) | {
        Path(layout.downloads).parts[0],
        "migration",
    }
    extras = [
        p.name
        for p in sorted(paths.root.iterdir())
        if p.name not in known_top and not p.name.startswith(".")
    ]
    if layout.top_level() == ["system"]:
        used = {
            Path(x).parts[1] for x in (layout.database, layout.torrents, layout.resumes)
        }
        extras += [
            f"system/{p.name}"
            for p in sorted((paths.root / "system").iterdir())
            if p.name not in used
        ]
    return extras


def _rollback(actions: list[tuple[str, Path, Path | None]], steps: Steps) -> None:
    if not actions:
        return
    try:
        from .target import dispose

        dispose()
    except Exception:
        pass
    for action, path, back in reversed(actions):
        try:
            if action == "remove" and path.exists():
                shutil.rmtree(path)
                steps.note(f"rolled back: removed {path}")
            elif action == "restore" and back is not None and path.exists():
                if back.exists():
                    shutil.rmtree(back)
                os.rename(path, back)
                steps.note(f"rolled back: restored {back}")
        except Exception as e:  # keep going, report what could not be undone
            steps.fail(f"rollback of {path} failed: {e}")


def _summary(report: Report) -> None:
    console.print()
    console.rule("[bold]Summary[/]")
    for entity, row in report.counts.items():
        skipped = f"  [yellow]skipped {row['skipped']}[/]" if row.get("skipped") else ""
        of = f" / {row['source']:<7}" if row.get("source") else " " * 10
        console.print(f"  {entity:<42} {row.get('migrated', 0):>7}{of}{skipped}")
    lossy, warns = report.by_level("lossy"), report.by_level("warn")
    console.print()
    if lossy:
        console.print(
            f"[bold yellow]Lossy migration:[/] {len(lossy)} item(s) could not be "
            "carried over — see the report."
        )
        for e in lossy[:10]:
            console.print(f"  [yellow]-[/] [{e.section}] {e.message}")
        if len(lossy) > 10:
            console.print(f"  … {len(lossy) - 10} more in the report")
    if warns:
        console.print(f"[bold]Warnings:[/] {len(warns)}")
        for e in warns[:10]:
            console.print(f"  [yellow]![/] [{e.section}] {e.message}")
    actions = report.by_level("action")
    if actions and report.status in ("success", "dry-run"):
        console.print("\n[bold]What to do next:[/]")
        for e in actions:
            console.print(f"  [cyan]→[/] {e.message}")
    if report.status == "success":
        console.print(
            "\n[bold green]Done.[/] Start the app as usual (e.g. `docker compose up -d`) "
            "with the settings above."
        )
    elif report.status == "dry-run":
        console.print(
            "\n[bold]Dry run finished.[/] Run the same command without --dry-run to migrate."
        )
    else:
        console.print(
            "\n[bold red]Migration failed.[/] Everything was rolled back; "
            "see error.txt in the migration folder."
        )
