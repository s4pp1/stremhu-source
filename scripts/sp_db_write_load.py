"""H1 synthetic SQLite write load (stream-performance, GSP03), inside a disposable product container.

Run with ``docker exec -d`` in the product container (``PYTHONPATH=/app``), next to the
product process: it writes the product's own SQLite file (WAL, synchronous=NORMAL, as the
product) from a second connection, so the product's playback-history write competes for the
database write lock, as with the resume writer or torrent writes. Only its own scratch table
(``sp_write_load``) is touched, and it keeps at most ``--keep-rows`` rows.

Each cycle: ``BEGIN IMMEDIATE``, insert ``--payload-bytes`` random bytes, hold the write lock
``--hold-ms``, ``COMMIT``, then pause ``--pause-ms``. Writes ``{"ready": true}`` to ``--stats``
when the first cycle committed; stops when ``--stop-file`` exists (or after ``--max-s``) and
then writes the final counters (no paths, keys or tokens).

Usage: python sp_db_write_load.py --stats /sp/shared/db-load.json --stop-file /sp/shared/db-load.stop
"""

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

from app.config import config


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--payload-bytes", type=int, default=256 * 1024)
    parser.add_argument("--hold-ms", type=float, default=20.0)
    parser.add_argument("--pause-ms", type=float, default=20.0)
    parser.add_argument("--keep-rows", type=int, default=64)
    parser.add_argument("--max-s", type=float, default=900.0)
    args = parser.parse_args()

    stats_path, stop_file = Path(args.stats), Path(args.stop_file)
    connection = sqlite3.connect(config.database_dir / "app.db", timeout=30.0, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("CREATE TABLE IF NOT EXISTS sp_write_load (id INTEGER PRIMARY KEY, payload BLOB NOT NULL)")
    counters = {"transactions": 0, "errors": 0, "error_kinds": {}, "lock_held_s": 0.0}
    started = time.monotonic()
    ready = False
    while not stop_file.exists() and time.monotonic() - started < args.max_s:
        try:
            connection.execute("BEGIN IMMEDIATE")
            locked_at = time.monotonic()
            connection.execute("INSERT INTO sp_write_load (payload) VALUES (randomblob(?))", (args.payload_bytes,))
            connection.execute("DELETE FROM sp_write_load WHERE id <= (SELECT MAX(id) FROM sp_write_load) - ?",
                               (args.keep_rows,))
            if args.hold_ms > 0:
                time.sleep(args.hold_ms / 1000.0)
            connection.execute("COMMIT")
            counters["lock_held_s"] += time.monotonic() - locked_at
            counters["transactions"] += 1
        except sqlite3.Error as error:
            counters["errors"] += 1
            kind = type(error).__name__
            counters["error_kinds"][kind] = counters["error_kinds"].get(kind, 0) + 1
            if connection.in_transaction:
                connection.execute("ROLLBACK")
        if not ready and counters["transactions"]:
            write_json(stats_path, {"ready": True})
            ready = True
        if args.pause_ms > 0:
            time.sleep(args.pause_ms / 1000.0)
    duration = time.monotonic() - started
    connection.close()
    write_json(stats_path, {
        "ready": ready, "done": True, "duration_s": round(duration, 3), "transactions": counters["transactions"],
        "errors": counters["errors"], "error_kinds": counters["error_kinds"],
        "lock_duty": round(counters["lock_held_s"] / duration, 3) if duration > 0 else None,
        "stopped_by": "stop-file" if stop_file.exists() else "max-s",
        "args": {"payload_bytes": args.payload_bytes, "hold_ms": args.hold_ms, "pause_ms": args.pause_ms,
                 "keep_rows": args.keep_rows},
    })


if __name__ == "__main__":
    main()
