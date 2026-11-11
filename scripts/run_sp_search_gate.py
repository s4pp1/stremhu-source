"""Run an H2 search gate (stream-performance) sequentially in disposable containers.

Usage: python run_sp_search_gate.py --plan plan.json --out results.jsonl --workdir <dir>

plan.json: {"image": "...", "arms": {"C0": "legacy", "C5": "candidate"}, "series": 2, "reps_per_series": 5,
            "harness_args": [...], "variants": {"t02": [...], ...} (optional),
            "seed_base": 20261110 (optional: repetition r runs with --seed seed_base + r, both arms alike),
            "cpuset": "0,1", "cpus": 2, "memory": "1g"}

Every run: a fresh `--network none` container of the image under test (product code at /app),
the harness mounted read-only, one policy, its JSON written to the work dir. Arms rotate per
repetition; with variants (extra harness arguments per variant, e.g. a Tech Info latency) the
variant order rotates too and both arms of a variant run back to back. The harness blocks every
external HTTP attempt and uses synthetic trackers only. A run whose `docker run` exits 125 (Docker's
own failure) without a result file is retried once after a pause; the record keeps the first
failure as `infra_retry`. Any other failure, or a second exit 125, stays a failed run.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
# `docker run` exits 125 when Docker itself fails (the daemon refused or lost the container); the
# benchmark never exits 125. gsp07-v1 lost a run to "error waiting for container: unexpected EOF".
DOCKER_RUN_ERROR_EXIT = 125
INFRA_RETRY_PAUSE_S = 30


def run_container(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
                          timeout=7200)


def rotate(items: list[str], by: int) -> list[str]:
    return items[by % len(items):] + items[: by % len(items)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    arms = list(plan["arms"])
    variants: dict[str, list[str]] = plan.get("variants") or {"": []}
    image_id = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", plan["image"]],
                              capture_output=True, text=True, check=True).stdout.strip()
    order = 0
    for series in range(plan["series"]):
        for offset in range(plan["reps_per_series"]):
            rep = series * plan["reps_per_series"] + offset
            seed_args = ["--seed", str(plan["seed_base"] + rep)] if "seed_base" in plan else []
            for variant in rotate(list(variants), rep):
                for arm in rotate(arms, rep):
                    name = f"{rep:02d}-{variant + '-' if variant else ''}{arm}.json"
                    command = [
                        "docker", "run", "--rm", "--network", "none", "--cpuset-cpus", plan.get("cpuset", "0,1"),
                        "--cpus", str(plan.get("cpus", 2)), "--memory", plan.get("memory", "1g"),
                        "-v", f"{SCRIPTS}:/sp/scripts:ro", "-v", f"{workdir}:/sp/out", "-w", "/app",
                        "-e", "PYTHONPATH=/app", "--entrypoint", "python", plan["image"],
                        "/sp/scripts/benchmark_sp_search.py", "--policies", plan["arms"][arm],
                        *plan["harness_args"], *variants[variant], *seed_args, "--out", f"/sp/out/{name}"]
                    started = time.monotonic()
                    proc = run_container(command)
                    infra_retry = None
                    if proc.returncode == DOCKER_RUN_ERROR_EXIT and not (workdir / name).exists():
                        # Docker's own failure (daemon or CLI connection), not the benchmark's: one retry of
                        # the same slot after a pause; the first failure stays on the record.
                        infra_retry = (proc.stderr or "")[-400:]
                        time.sleep(INFRA_RETRY_PAUSE_S)
                        started = time.monotonic()
                        proc = run_container(command)
                    record = {"order": order, "series": series, "rep": rep, "arm": arm, "policy": plan["arms"][arm],
                              "image_id": image_id, "exit": proc.returncode,
                              "wall_s": round(time.monotonic() - started, 1)}
                    if infra_retry is not None:
                        record["infra_retry"] = infra_retry
                    if variant:
                        record["variant"] = variant
                    if seed_args:
                        record["seed"] = int(seed_args[1])
                    result_path = workdir / name
                    if proc.returncode == 0 and result_path.exists():
                        record["result"] = json.loads(result_path.read_text(encoding="utf-8"))
                    else:
                        record["failed"] = (proc.stderr or "")[-400:]
                    with Path(args.out).open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(record) + "\n")
                    print(json.dumps({"order": order, "variant": variant, "arm": arm, "rep": rep,
                                      "exit": proc.returncode, "wall_s": record["wall_s"]}), flush=True)
                    order += 1


if __name__ == "__main__":
    main()
