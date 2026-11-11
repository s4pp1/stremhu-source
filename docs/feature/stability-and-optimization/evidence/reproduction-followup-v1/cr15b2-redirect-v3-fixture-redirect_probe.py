"""Packet 26b functional probe (v3): real NcoreIndexerDefinition download path on the private fixture.

giant: 302 with a 64 MiB body to /final, 20 sequential + 20 at concurrency 4 (redirect bytes, anon peak).
subdomain: 10 downloads redirected to dl.tracker.fixture.invalid. foreign: 10 downloads redirected to
cdn.other.invalid. Outcomes per request, final hash and the server's per-host /final counts.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path

import httpx

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition

BASE = os.environ["TEST_BASE_URL"]
if httpx.URL(BASE).host != "tracker.fixture.invalid":
    raise RuntimeError("Private fixture required")
ALLOWED = {"tracker.fixture.invalid", "dl.tracker.fixture.invalid", "cdn.other.invalid"}
SMOKE = os.environ.get("REDIRECT_SMOKE") == "1"
COUNT = 2 if SMOKE else 20
SMALL = 2 if SMOKE else 10


def anon():
    stat = dict(line.split() for line in Path("/sys/fs/cgroup/memory.stat").read_text().splitlines())
    return int(stat["anon"])


async def stats():
    async with httpx.AsyncClient(base_url=BASE, trust_env=False) as client:
        return (await client.get("/fixture/stats")).json()


def delta(after, before, key):
    return after.get(key, 0) - before.get(key, 0)


async def main():
    original = httpx.AsyncClient.send
    outbound = 0

    async def guarded(client, request, *args, **kwargs):
        nonlocal outbound
        if request.url.host not in ALLOWED:
            outbound += 1
            raise RuntimeError("External HTTP blocked")
        return await original(client, request, *args, **kwargs)

    httpx.AsyncClient.send = guarded
    adapter = NcoreIndexerDefinition()
    await adapter._client.aclose()
    adapter._client = IndexerClient(adapter, base_url=BASE, follow_redirects=True, timeout=20, trust_env=False)
    adapter._detect_authentication_error = lambda response: None
    peak = 0
    stop = asyncio.Event()

    async def sample():
        nonlocal peak
        while not stop.is_set():
            peak = max(peak, anon())
            await asyncio.sleep(0.02)

    async def download(path):
        try:
            return hashlib.sha256(await adapter.download_torrent(BASE + path)).hexdigest()
        except Exception as error:
            return "error:" + type(error).__name__

    rows = []
    sampler = asyncio.create_task(sample())
    for case, path, count, concurrency in [("giant", "/redirect-giant", COUNT, 1), ("giant", "/redirect-giant", COUNT, 4),
                                           ("subdomain", "/redirect-sub", SMALL, 1), ("foreign", "/redirect-foreign", SMALL, 1)]:
        before_stats, before_anon = await stats(), anon()
        peak = before_anon
        semaphore = asyncio.Semaphore(concurrency)

        async def one():
            async with semaphore:
                return await download(path)

        outcomes = await asyncio.gather(*(one() for _ in range(count)))
        after_stats = await stats()
        rows.append(dict(case=case, concurrency=concurrency, requests=count, outcomes=sorted(set(outcomes)),
                         successes=sum(not o.startswith("error:") for o in outcomes),
                         redirect_body_bytes=delta(after_stats, before_stats, "redirect-body-bytes"),
                         redirect_body_complete=delta(after_stats, before_stats, "redirect-body-complete"),
                         final_by_host={h: delta(after_stats, before_stats, f"final@{h}") for h in sorted(ALLOWED)},
                         anon_before=before_anon, anon_peak_delta=peak - before_anon))
    stop.set()
    await sampler
    await adapter.close()
    httpx.AsyncClient.send = original
    print(json.dumps(dict(probe="cr15b2-redirect-v3", is_measurement=not SMOKE, rows=rows, external_http_attempts=outbound)))


asyncio.run(main())
