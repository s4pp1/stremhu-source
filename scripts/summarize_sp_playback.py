"""Summarise H1 playback results (stream-performance) per cell and label.

Usage: python summarize_sp_playback.py results.jsonl protocol.json summary.json [complete.json]

Per cell and label: n, median, p95 (nearest rank), min, max of each protocol metric;
failures and tracebacks are counted, never dropped. Noise J per metric and cell is
max(|median(B) - median(B2)|, resolution) when both noise labels exist. The
optional complete file holds every run record (no API keys or tokens are ever
written into run records).
"""

import json
import math
import sys
from pathlib import Path

RESOLUTION = {"bytes": 1 << 20, "count": 1, "time": 0.05, "pct": 0.1, "mib": 1}


def _walk(value, dotted: str):
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def get(record: dict, dotted: str):
    # Protocol names "start.*" / "seek.*" are the player emulator's result; the rest are run-level.
    value = _walk(record, dotted)
    return value if value is not None else _walk(record.get("result", {}), dotted)


def kind(metric: str) -> str:
    if "bytes" in metric:
        return "bytes"
    if metric.endswith(("stalls", "tracebacks")):
        return "count"
    if "cpu_pct" in metric:
        return "pct"
    if "mem_mib" in metric:
        return "mib"
    return "time"


def stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    p95 = ordered[min(n - 1, math.ceil(0.95 * n) - 1)]
    return {"n": n, "median": round(median, 3), "p95": round(p95, 3), "min": round(ordered[0], 3),
            "max": round(ordered[-1], 3)}


def main() -> None:
    results_path, protocol_path, summary_path = (Path(a) for a in sys.argv[1:4])
    complete_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    metrics = [m for m in protocol["metrics"] if m != "failed"]
    records = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    cells: dict[str, dict] = {}
    for record in records:
        cell = record["cell"]
        # A named cell (GSP03: RTT and DB load per cell) keys by its name; the rest as before.
        key = cell["name"] if "name" in cell else f"{cell['profile']}/{cell['piece_size'] >> 20}MiB/{cell['bitrate_mbit']}Mbit"
        if "series" in cell:
            key += f"/series{cell['series']}"
        entry = cells.setdefault(key, {}).setdefault(record["label"], {"runs": 0, "failed": 0, "values": {}})
        entry["runs"] += 1
        if record.get("failed"):
            entry["failed"] += 1
            continue
        for metric in metrics:
            value = get(record, metric)
            if isinstance(value, (int, float)):
                entry["values"].setdefault(metric, []).append(float(value))
    summary = {"protocol": protocol["id"], "runs": len(records),
               "failed_runs": sum(1 for r in records if r.get("failed")), "cells": {}}
    for key, labels in sorted(cells.items()):
        out: dict = {}
        for label, entry in labels.items():
            out[label] = {"runs": entry["runs"], "failed": entry["failed"],
                          **{m: stats(entry["values"].get(m, [])) for m in metrics}}
        if "B" in out and "B2" in out:
            noise = {}
            for metric in metrics:
                b, b2 = out["B"][metric], out["B2"][metric]
                if b.get("n") and b2.get("n"):
                    noise[metric] = round(max(abs(b["median"] - b2["median"]), RESOLUTION[kind(metric)]), 3)
            out["noise_J"] = noise
        summary["cells"][key] = out
    summary_path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    if complete_path:
        complete_path.write_text(json.dumps({"protocol": protocol["id"], "records": records}, indent=None) + "\n",
                                 encoding="utf-8", newline="\n")
    print(json.dumps({"runs": summary["runs"], "failed": summary["failed_runs"], "cells": len(summary["cells"])}))


if __name__ == "__main__":
    main()
