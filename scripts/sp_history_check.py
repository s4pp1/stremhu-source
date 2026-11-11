"""H1 playback-history check (stream-performance, GSP03), inside a disposable product container.

Run with ``docker exec`` in the product container (``PYTHONPATH=/app``) after the client
finished: every playback the client used (``targets.json`` from ``sp_app_fixture.py
--playbacks N``) must have exactly one ``playback_histories`` row. Polls until all rows
exist or ``--deadline-s`` passes (a background write may still be finishing), then prints
one JSON line: expected, found, lost_writes = expected - found. Reads only playback ids,
never the API key or a token, and prints no id.

Usage: python sp_history_check.py --targets /sp/shared/targets.json [--deadline-s 10]
"""

import argparse
import json
import time
from pathlib import Path

from sqlalchemy import select

from app.common.database import isolated_db_session
from app.modules.playback_histories.models import PlaybackHistoryModel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--deadline-s", type=float, default=10.0)
    args = parser.parse_args()

    data = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    expected = {playback["playback_id"] for target in data["targets"] for playback in target.get("playbacks", [])}
    started = time.monotonic()
    while True:
        with isolated_db_session() as db:
            found = set(db.scalars(select(PlaybackHistoryModel.playback_id)
                                   .where(PlaybackHistoryModel.playback_id.in_(expected))).all())
        if found >= expected or time.monotonic() - started >= args.deadline_s:
            break
        time.sleep(0.2)
    print(json.dumps({"expected": len(expected), "found": len(found), "lost_writes": len(expected - found),
                      "waited_s": round(time.monotonic() - started, 2)}))


if __name__ == "__main__":
    main()
