"""Moving / copying the downloads folder with progress.

* `move` renames top-level entries (instant on the same mount). If source and
  destination are separate mounts (EXDEV) it falls back to copy-then-delete,
  file by file, so an interrupted run can simply be started again.
* `copy` leaves the source untouched.
* Copies are sparse-aware: libtorrent allocates files sparsely, and a naive
  copy would inflate every partially downloaded file to its full size.
* Existing destination files are never overwritten: an identical file (same
  size) counts as already done, a different one is reported as a conflict.
"""

from __future__ import annotations

import errno
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .report import Report
from .ui import Steps

SECTION = "Downloads"

# Not available in every Python build; plain pread/pwrite is the fallback.
_copy_file_range = getattr(os, "copy_file_range", None)


@dataclass
class Inventory:
    entries: list[Path] = field(default_factory=list)  # top-level
    files: int = 0
    apparent_bytes: int = 0
    allocated_bytes: int = 0


def inventory(downloads: Path, steps: Steps) -> Inventory:
    inv = Inventory()
    if not downloads.is_dir():
        return inv
    inv.entries = sorted(downloads.iterdir())
    with steps.progress(
        "scanning downloads", len(inv.entries), unit="entries"
    ) as counter:
        for entry in inv.entries:
            for path in _walk_files(entry):
                st = path.lstat()
                inv.files += 1
                inv.apparent_bytes += st.st_size
                inv.allocated_bytes += st.st_blocks * 512
            counter.advance()
    return inv


def _walk_files(entry: Path):
    if entry.is_symlink() or entry.is_file():
        yield entry
        return
    for root, _dirs, files in os.walk(entry):
        for name in files:
            yield Path(root) / name


def check_space(dest: Path, inv: Inventory, steps: Steps) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(dest).free
    need = inv.allocated_bytes
    if need > free:
        raise RuntimeError(
            f"not enough free space in the destination: need {need / 2**30:.1f} GiB, "
            f"have {free / 2**30:.1f} GiB. Use DOWNLOADS=move on the same filesystem, or DOWNLOADS=keep."
        )
    steps.ok(
        f"free space ok ({free / 2**30:.1f} GiB free, {need / 2**30:.1f} GiB needed)"
    )


# --------------------------------------------------------------------------- #
# sparse-aware copy
# --------------------------------------------------------------------------- #


def _copy_sparse(src: Path, dst: Path, on_bytes) -> None:
    size = src.stat().st_size
    tmp = dst.with_name(dst.name + ".stremhu-migrating")
    with open(src, "rb") as fsrc, open(tmp, "wb") as fdst:
        in_fd, out_fd = fsrc.fileno(), fdst.fileno()
        offset = 0
        while offset < size:
            try:
                data_start = os.lseek(in_fd, offset, os.SEEK_DATA)
            except OSError as e:
                if e.errno == errno.ENXIO:  # only a hole remains
                    break
                data_start = offset  # SEEK_DATA unsupported: copy densely
            try:
                data_end = os.lseek(in_fd, data_start, os.SEEK_HOLE)
            except OSError:
                data_end = size
            if data_start > offset:
                on_bytes(data_start - offset)  # skipped hole
            pos = data_start
            while pos < data_end:
                chunk = min(8 * 1024 * 1024, data_end - pos)
                copied = 0
                if _copy_file_range is not None:
                    try:
                        copied = _copy_file_range(in_fd, out_fd, chunk, pos, pos)
                    except OSError:
                        copied = 0
                if copied <= 0:
                    copied = os.pwrite(out_fd, os.pread(in_fd, chunk, pos), pos)
                if copied <= 0:
                    raise OSError(f"short copy at {pos} in {src}")
                pos += copied
                on_bytes(copied)
            offset = data_end
        if offset < size:
            on_bytes(size - offset)
        os.ftruncate(out_fd, size)
    shutil.copystat(src, tmp)
    _copy_owner(src, tmp)
    os.replace(tmp, dst)


def _copy_owner(src: Path, dst: Path) -> None:
    """Keep the original owner (the migrator runs as root in Docker)."""
    try:
        st = src.lstat()
        os.chown(dst, st.st_uid, st.st_gid, follow_symlinks=False)
    except (PermissionError, NotImplementedError):
        pass


def _makedirs_like(src_dir: Path, dst_dir: Path, source_root: Path) -> None:
    """Create missing destination directories with the source's owner/mode."""
    missing = []
    d, s = dst_dir, src_dir
    while not d.exists():
        missing.append((s, d))
        if s == source_root:
            break
        d, s = d.parent, s.parent
    for s, d in reversed(missing):
        d.mkdir(exist_ok=True)
        if s.exists():
            shutil.copystat(s, d)
            _copy_owner(s, d)


# --------------------------------------------------------------------------- #
# transfer
# --------------------------------------------------------------------------- #


def transfer(
    source: Path, dest: Path, mode: str, inv: Inventory, report: Report, steps: Steps
) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    moved_entries = 0
    remaining = list(inv.entries)

    if mode == "move":
        # Fast path: rename whole top-level entries.
        cross_device = False
        with steps.progress(
            "moving (rename)", len(remaining), unit="entries"
        ) as counter:
            still: list[Path] = []
            for entry in remaining:
                target = dest / entry.name
                if cross_device or target.exists() or target.is_symlink():
                    still.append(entry)
                    counter.advance()
                    continue
                try:
                    os.rename(entry, target)
                    moved_entries += 1
                except OSError as e:
                    if e.errno != errno.EXDEV:
                        raise
                    cross_device = True
                    still.append(entry)
                counter.advance()
            remaining = still
        if cross_device:
            steps.note(
                "source and destination are different mounts: falling back to copy + delete per file"
            )
        if moved_entries:
            steps.ok(f"{moved_entries} entries moved instantly by rename")

    if not remaining:
        report.count(
            "Download entries", source=len(inv.entries), migrated=len(inv.entries)
        )
        return

    files = [p for entry in remaining for p in _walk_files(entry)]
    total = sum(p.lstat().st_size for p in files)
    done_files = 0
    identical = 0
    conflicts: list[str] = []
    label = "copying" if mode == "copy" else "moving (copy + delete)"
    with steps.progress(label, total, unit="", as_bytes=True) as counter:
        for src in files:
            rel = src.relative_to(source)
            dst = dest / rel
            size = src.lstat().st_size
            _makedirs_like(src.parent, dst.parent, source)
            if dst.exists():
                if dst.stat().st_size == size:
                    identical += 1
                    if mode == "move":
                        src.unlink()
                else:
                    conflicts.append(str(rel))
                counter.advance(size)
                continue
            if src.is_symlink():
                os.symlink(os.readlink(src), dst)
                _copy_owner(src, dst)
                counter.advance(size)
            else:
                _copy_sparse(src, dst, counter.advance)
            if mode == "move":
                src.unlink()
            done_files += 1

    if mode == "move":
        for entry in remaining:  # remove now-empty directories
            if entry.is_dir():
                for root, dirs, _files in os.walk(entry, topdown=False):
                    for d in dirs:
                        try:
                            (Path(root) / d).rmdir()
                        except OSError:
                            pass
                try:
                    entry.rmdir()
                except OSError:
                    pass

    if identical:
        report.info(
            SECTION,
            f"{identical} files already existed in the destination with the same size; kept as-is",
        )
    for rel in conflicts[:50]:
        report.warn(
            SECTION,
            f"conflict, not overwritten (different size already in destination): {rel}",
        )
    if len(conflicts) > 50:
        report.warn(SECTION, f"... and {len(conflicts) - 50} more conflicts")
    report.count(
        "Download files",
        source=inv.files,
        migrated=inv.files - len(conflicts),
        skipped=len(conflicts),
    )


def orphan_entries(downloads: Path, torrent_names: set[str]) -> list[str]:
    """Top-level download entries that no migrated torrent refers to."""
    if not downloads.is_dir():
        return []
    return sorted(p.name for p in downloads.iterdir() if p.name not in torrent_names)
