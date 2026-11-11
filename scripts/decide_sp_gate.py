"""Apply a registered stream-performance gate rule (before/after series) to a summary.

Usage: python decide_sp_gate.py protocol.json summary.json baseline_summary.json complete.json decision.json

Rule (protocol["decision_rule"]): primary metric, key cells, improvement/regression by
median difference beyond the noise J, where J per cell and metric is
max(|median C0 series0 - median C0 series1|, baseline B/B2 J of the same profile/piece at
30 Mbit/s, 0.05 s). C0 = before (legacy). Candidates: rule["candidates"] (default ["C1"]),
each judged against C0; rule["improved_required"] key cells (default 4) must improve in
both series. Several passing candidates: the larger total primary improvement over the key
cells wins, a tie goes to rule["tie_break"] (default the first candidate).
"""

import json
import sys
from pathlib import Path

GUARD_METRICS = ["start.time_to_start_s", "start.ttfb_s", "seek.resume_s", "start.stall_s"]


def median(summary_cell: dict, label: str, metric: str):
    return summary_cell.get(label, {}).get(metric, {}).get("median")


def main() -> None:
    protocol = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    summary = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    baseline = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    records = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))["records"]
    rule = protocol["decision_rule"]
    primary = rule["primary_metric"].split(" ")[0]
    candidates = rule.get("candidates", ["C1"])
    required = rule.get("improved_required", 4)
    cells = summary["cells"]
    cell_names = sorted({key.split("/series")[0] for key in cells})

    def noise(cell: str, metric: str) -> float:
        s0, s1 = cells.get(f"{cell}/series0", {}), cells.get(f"{cell}/series1", {})
        m0, m1 = median(s0, "C0", metric), median(s1, "C0", metric)
        own = abs(m0 - m1) if m0 is not None and m1 is not None else 0.0
        profile, piece, _ = cell.split("/")
        pb0 = baseline["cells"].get(f"{profile}/{piece}/30Mbit", {}).get("noise_J", {}).get(metric, 0.0)
        return round(max(own, pb0, 0.05), 3)

    def judge(candidate: str) -> dict:
        per_cell = {}
        for cell in cell_names:
            entry = {}
            for series in (0, 1):
                data = cells.get(f"{cell}/series{series}", {})
                result = {}
                for metric in GUARD_METRICS:
                    c0, cx = median(data, "C0", metric), median(data, candidate, metric)
                    if c0 is None or cx is None:
                        result[metric] = None
                        continue
                    j = noise(cell, metric)
                    result[metric] = {"c0": c0, "candidate": cx, "delta_c0_minus_candidate": round(c0 - cx, 3),
                                      "J": j, "improved": c0 - cx > j, "regressed": cx - c0 > j}
                entry[f"series{series}"] = result
            per_cell[cell] = entry
        improved = [cell for cell in rule["key_cells"]
                    if all((per_cell.get(cell, {}).get(f"series{s}", {}).get(primary) or {}).get("improved")
                           for s in (0, 1))]
        regressions = [(cell, series, metric) for cell, entry in per_cell.items()
                       for series, result in entry.items() for metric, value in result.items()
                       if value and value["regressed"]]
        failed = {label: sum(1 for r in records if r["label"] == label and r.get("failed"))
                  for label in ("C0", candidate)}
        tracebacks = {label: sum(r.get("app_log", {}).get("tracebacks", 0) for r in records if r["label"] == label)
                      for label in ("C0", candidate)}
        gain = round(sum((per_cell[c][f"series{s}"][primary] or {}).get("delta_c0_minus_candidate", 0.0)
                         for c in rule["key_cells"] if c in per_cell for s in (0, 1)), 3)
        passed = (len(improved) >= required and not regressions and failed[candidate] <= failed["C0"]
                  and tracebacks[candidate] <= tracebacks["C0"])
        return {"pass": passed, "improved_key_cells_both_series": improved, "improved_count": len(improved),
                "improved_required": required, "regressions": regressions, "failed_runs": failed,
                "tracebacks_total": tracebacks, "total_primary_gain_s": gain, "per_cell": per_cell}

    results = {candidate: judge(candidate) for candidate in candidates}
    passing = [c for c in candidates if results[c]["pass"]]
    if passing:
        tie_break = rule.get("tie_break", candidates[0])
        best = max(passing, key=lambda c: (results[c]["total_primary_gain_s"], c == tie_break))
        decision = f"PASS:{best}"
    else:
        decision = "FAIL"
    out = {"protocol": protocol["id"], "decision": decision, "candidates": results}
    Path(sys.argv[5]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"decision": decision, **{c: {"pass": r["pass"], "improved": r["improved_count"],
                                                    "regressions": len(r["regressions"]),
                                                    "gain_s": r["total_primary_gain_s"]}
                                                for c, r in results.items()}}))


if __name__ == "__main__":
    main()
