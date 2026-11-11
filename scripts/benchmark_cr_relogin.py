"""Offline owner/joiner cancellation reproduction and normal dedup baseline."""

import asyncio
import json
import statistics
import time

from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition


async def main():
    rows = []
    for scenario in ("normal", "cancel-owner", "cancel-joiner"):
        outcomes, samples, calls = {}, [], 0
        for _ in range(100):
            adapter = NcoreIndexerDefinition()
            started, release = asyncio.Event(), asyncio.Event()

            async def login():
                nonlocal calls
                calls += 1
                started.set()
                await release.wait()

            adapter.login = login
            owner = asyncio.create_task(adapter.relogin())
            await started.wait()
            joiner = asyncio.create_task(adapter.relogin())
            await asyncio.sleep(0)
            before = time.perf_counter_ns()
            if scenario != "normal":
                cancelled = owner if scenario == "cancel-owner" else joiner
                cancelled.cancel()
                await asyncio.gather(cancelled, return_exceptions=True)
            release.set()
            alive = [task for task in (owner, joiner) if not task.cancelled()]
            try:
                results = await asyncio.wait_for(asyncio.gather(*alive, return_exceptions=True), timeout=0.05)
                outcome = ",".join(type(result).__name__ for result in results)
            except TimeoutError:
                outcome = "TimeoutError"
            samples.append((time.perf_counter_ns() - before) / 1e6)
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            for task in (owner, joiner):
                if not task.done():
                    task.cancel()
            await asyncio.gather(owner, joiner, return_exceptions=True)
            await adapter.close()
        ordered = sorted(samples)
        rows.append(dict(workload=scenario, concurrency=2, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], login_calls=calls, outcomes=outcomes, errors=[]))
    print(json.dumps(dict(fixture="relogin-gated-login-v1", rows=rows)))


asyncio.run(main())
