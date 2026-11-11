"""Bootstrap/Holm gate rule for stream-performance (used from gsp02-v4 on).

Usage: python decide_sp_gate_bootstrap.py protocol.json complete.json decision.json

Why a second rule: post-seek resume is bimodal (one piece at line rate, or the awaited
piece sharing bandwidth), so a median per 5-run series with a noise band from two C0
medians under-estimates the noise (gsp02-v1..v3). This rule pools both series (n=10 per
variant and cell) and compares means.

- Difference d = mean(candidate) - mean(C0); 10 000 bootstrap resamples per test with a
  fixed seed (protocol["decision_rule"]["seed"]); one-sided p-values from the bootstrap.
- Improvement (primary metric, key cells): p(d >= 0) with Holm correction over the key
  cells at alpha; at least ``improved_required`` key cells must improve.
- Regression (guard metrics, every cell): p(d <= 0) with Holm correction over all guard
  tests of the candidate at alpha; any rejected test is a regression.
- Failed runs and tracebacks with an application frame: candidate total <= C0 total.
- Several passing candidates: larger total mean primary gain over the key cells; a tie goes
  to rule["tie_break"].

Optional rule keys (absent = the gsp02-v4 behaviour, unchanged):
- ``guard_metrics``: the guard metrics instead of GUARD_METRICS (GSP03: range-series TTFB).
- ``zero_required``: dotted paths from the run record root (e.g. ``history_check.lost_writes``);
  every non-failed candidate run must carry each value and its sum must be 0.
- A cell with a ``name`` (GSP03: RTT and DB load per cell) is keyed by that name.
"""

import json
import random
import sys
from pathlib import Path

GUARD_METRICS = ["start.time_to_start_s", "start.ttfb_s", "seek.resume_s", "start.stall_s"]


def metric(record: dict, dotted: str):
    value = record.get("result", {})
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def record_value(record: dict, dotted: str):
    value = record
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def bootstrap(a: list[float], b: list[float], rng: random.Random, n: int) -> tuple[float, float, float]:
    """Returns (mean difference b-a, P(diff >= 0), P(diff <= 0)) over bootstrap resamples."""
    observed = sum(b) / len(b) - sum(a) / len(a)
    ge = le = 0
    for _ in range(n):
        sa = [a[rng.randrange(len(a))] for _ in a]
        sb = [b[rng.randrange(len(b))] for _ in b]
        diff = sum(sb) / len(sb) - sum(sa) / len(sa)
        ge += diff >= 0
        le += diff <= 0
    return observed, (ge + 1) / (n + 1), (le + 1) / (n + 1)


def holm(pvalues: dict, alpha: float) -> set:
    """Keys whose null is rejected by Holm's step-down procedure."""
    rejected = set()
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    m = len(ordered)
    for rank, (key, p) in enumerate(ordered):
        if p <= alpha / (m - rank):
            rejected.add(key)
        else:
            break
    return rejected


def main() -> None:
    protocol = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    records = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["records"]
    rule = protocol["decision_rule"]
    primary = rule["primary_metric"].split(" ")[0]
    alpha = rule.get("alpha", 0.05)
    resamples = rule.get("resamples", 10000)
    rng = random.Random(rule.get("seed", 20261110))
    ok = [r for r in records if not r.get("failed")]

    def cell_of(record: dict) -> str:
        cell = record["cell"]
        if "name" in cell:
            return cell["name"]
        return f"{cell['profile']}/{cell['piece_size'] >> 20}MiB/{cell['bitrate_mbit']}Mbit"

    cells = sorted({cell_of(r) for r in ok})

    def values(label: str, cell: str, name: str) -> list[float]:
        return [float(v) for r in ok if r["label"] == label and cell_of(r) == cell
                if (v := metric(r, name)) is not None]

    guard_metrics = rule.get("guard_metrics", GUARD_METRICS)
    zero_required = rule.get("zero_required", [])

    def zero_check(label: str) -> dict:
        report = {}
        for path in zero_required:
            found = [record_value(r, path) for r in ok if r["label"] == label]
            numbers = [v for v in found if isinstance(v, (int, float))]
            report[path] = {"sum": sum(numbers), "missing": len(found) - len(numbers)}
        return report

    results = {}
    for candidate in rule["candidates"]:
        tests = {}
        for cell in cells:
            for name in guard_metrics:
                a, b = values("C0", cell, name), values(candidate, cell, name)
                if len(a) >= 3 and len(b) >= 3:
                    diff, p_not_better, p_not_worse = bootstrap(a, b, rng, resamples)
                    tests[(cell, name)] = {"mean_c0": round(sum(a) / len(a), 3),
                                           "mean_candidate": round(sum(b) / len(b), 3),
                                           "diff": round(diff, 3), "n": [len(a), len(b)],
                                           "p_improvement_null": p_not_better, "p_regression_null": p_not_worse}
        improved = holm({cell: tests[(cell, primary)]["p_improvement_null"]
                         for cell in rule["key_cells"] if (cell, primary) in tests}, alpha)
        regressions = holm({key: test["p_regression_null"] for key, test in tests.items()}, alpha)
        failed = {label: sum(1 for r in records if r["label"] == label and r.get("failed")) for label in ("C0", candidate)}
        # Only tracebacks with an application frame count (asyncio-internal double connection_lost on client
        # disconnect is benign and present in C0 too: gsp02-v3 finding).
        counter = rule.get("traceback_counter", "app_tracebacks")
        tracebacks = {label: sum(r.get("app_log", {}).get(counter, 0) for r in records if r["label"] == label)
                      for label in ("C0", candidate)}
        gain = round(-sum(tests[(c, primary)]["diff"] for c in rule["key_cells"] if (c, primary) in tests), 3)
        passed = (len(improved) >= rule.get("improved_required", 4) and not regressions
                  and failed[candidate] <= failed["C0"] and tracebacks[candidate] <= tracebacks["C0"])
        results[candidate] = {
            "pass": passed, "improved_key_cells": sorted(improved), "improved_count": len(improved),
            "regressions": sorted(f"{cell} {name}" for cell, name in regressions),
            "failed_runs": failed, "tracebacks_total": tracebacks, "total_primary_gain_s": gain,
            "tests": {f"{cell} {name}": test for (cell, name), test in sorted(tests.items())},
        }
        if zero_required:
            zero = {"C0": zero_check("C0"), candidate: zero_check(candidate)}
            results[candidate]["zero_required"] = zero
            results[candidate]["pass"] = passed and all(
                entry["sum"] == 0 and entry["missing"] == 0 for entry in zero[candidate].values())
    passing = [c for c in rule["candidates"] if results[c]["pass"]]
    if passing:
        tie_break = rule.get("tie_break", rule["candidates"][0])
        best = max(passing, key=lambda c: (results[c]["total_primary_gain_s"], c == tie_break))
        decision = f"PASS:{best}"
    else:
        decision = "FAIL"
    Path(sys.argv[3]).write_text(json.dumps({"protocol": protocol["id"], "decision": decision, "candidates": results},
                                            indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"decision": decision, **{c: {"pass": r["pass"], "improved": r["improved_count"],
                                                    "regressions": r["regressions"], "gain_s": r["total_primary_gain_s"],
                                                    "tracebacks": r["tracebacks_total"]}
                                                for c, r in results.items()}}))


if __name__ == "__main__":
    main()
