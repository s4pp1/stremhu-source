"""HTTP latency with the production persistent-adapter relogin lifecycle."""

import asyncio
import json
import resource
import statistics
import time
from pathlib import Path

import httpx
from fastapi import FastAPI

from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition


async def main():
    adapter = NcoreIndexerDefinition()
    calls = 0

    async def login(credential=None):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)

    adapter.login = login
    application = FastAPI()

    @application.get("/fixture/relogin")
    async def relogin():
        await adapter.relogin()
        return {"ok": True}

    rows = []
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="https://fixture.invalid") as client:
            for _ in range(10):
                assert (await client.get("/fixture/relogin")).status_code == 200
            for concurrency in (1, 4, 8):
                gate = asyncio.Semaphore(concurrency)
                samples, errors = [], []
                before_calls = calls

                async def request():
                    async with gate:
                        started = time.perf_counter_ns()
                        response = await client.get("/fixture/relogin")
                        samples.append((time.perf_counter_ns() - started) / 1e6)
                        if response.status_code != 200 or response.json() != {"ok": True}:
                            errors.append(response.status_code)

                cpu = time.process_time()
                await asyncio.gather(*(request() for _ in range(100)))
                ordered = sorted(samples)
                rows.append(dict(workload="persistent-adapter-relogin-http", concurrency=concurrency, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], errors=errors, login_calls=calls-before_calls, cpu_seconds=time.process_time()-cpu))
    finally:
        await adapter.close()
    print(json.dumps(dict(fixture="persistent-adapter-relogin-http-v1", rows=rows, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, memory_current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()))))


asyncio.run(main())
