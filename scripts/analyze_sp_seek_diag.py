"""Seek-timeline analysis for diagnostic runs with SPDIAG logs (stream-performance).

Usage: python analyze_sp_seek_diag.py <results.jsonl> <runs_dir>

For every run: when the player stopped/closed phase 1, when the old stream noticed it
(disconnect_seen / stream_cancelled / stream_end / stream_destroy), what the old stream was
doing at that moment (waiting for a piece or not), which pieces were urgent (deadline 0)
after the seek request, and when the first post-seek piece finished. Times are seconds
relative to the seek request (CLOCK_MONOTONIC, shared by the containers of one host).
"""

import json
import re
import sys
from pathlib import Path

LINE = re.compile(r"SPDIAG (\w+) t=([\d.]+) ?(.*)")


def parse(path: Path) -> list[tuple[str, float, dict]]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = LINE.search(line)
        if not m:
            continue
        fields = dict(re.findall(r"(\w+)=(\[[^\]]*\]|\S+)", m.group(3)))
        events.append((m.group(1), float(m.group(2)), fields))
    return events


def main() -> None:
    results = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
    runs_dir = Path(sys.argv[2])
    for record in results:
        log = runs_dir / record["run_id"] / "diag.log"
        res = record.get("result", {})
        seek_t = res.get("seek_request_monotonic")
        if not log.exists() or seek_t is None:
            print(record["run_id"], "no diag log or seek mark")
            continue
        events = parse(log)
        rel = lambda t: round(t - seek_t, 3)  # noqa: E731
        opens = [(t, f) for e, t, f in events if e == "stream_open"]
        main_sid = opens[0][1]["sid"] if opens else None
        seek_sid = next((f["sid"] for t, f in opens if t >= seek_t - 0.5 and int(f["start"]) > 0), None)
        seek_start = next((int(f["start"]) for t, f in opens if f.get("sid") == seek_sid), None)
        old = [(e, rel(t), f) for e, t, f in events if f.get("sid") == main_sid and t >= seek_t - 15]
        last_wait = None
        for e, t, f in old:
            if e == "piece_wait" and t <= 0:
                last_wait = (f["piece"], t)
            if e == "piece_ready" and last_wait and f["piece"] == last_wait[0] and t <= 0:
                last_wait = None
        old_after = [(e, t, f.get("piece"), f.get("where")) for e, t, f in old if t >= -2 and e != "piece_wait"][:8]
        urgent_after = [(rel(t), f.get("urgent"), f.get("streams")) for e, t, f in events
                        if e == "deadlines" and 0 <= t - seek_t <= 12][:6]
        seek_piece_done = next((rel(t) for e, t, f in events
                                if e == "piece_finished" and seek_start is not None and int(f["piece"]) == seek_start
                                and t >= seek_t), None)
        print(f"== {record['run_id']}  seek_ttfb={res.get('seek', {}).get('ttfb_s')}")
        print(f"   phase1 stop={rel(res['phase1_stop_monotonic']) if res.get('phase1_stop_monotonic') else None} "
              f"closed={rel(res['phase1_closed_monotonic']) if res.get('phase1_closed_monotonic') else None}")
        print(f"   old stream waiting at seek: {last_wait}")
        print(f"   old stream events after: {old_after}")
        print(f"   seek piece {seek_start} finished at {seek_piece_done}")
        for item in urgent_after:
            print(f"   urgent {item}")


if __name__ == "__main__":
    main()
