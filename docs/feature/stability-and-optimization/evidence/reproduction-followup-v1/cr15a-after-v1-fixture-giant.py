"""CR15a giant-body control: chunked-large (64 MiB) and gzip-large (134217728 B decoded) through the real
adapter.download_torrent at concurrency 1/4/8, 100 requests per cell. Every request's outcome is recorded:
the exception class summary kind (no message text, no URL) or an unexpected success. Container memory peaks
are sampled like the normal probe. Exits non-zero only on harness failure; outcomes are data."""
import asyncio
import gc
import json
import os
import resource
import sys
import time
from collections import Counter, deque
from pathlib import Path

import httpx

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.exceptions import IndexerDefinitionException
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition

SMOKE = '--fixture-smoke' in sys.argv
COUNT = 4 if SMOKE else 100
BASE = os.environ['TEST_BASE_URL']
if httpx.URL(BASE).host != 'tracker.fixture.invalid':
    raise RuntimeError('Private fixture required')
KINDS = ('chunked-large', 'gzip-large')


def memory():
    stat = dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
    return dict(anon_bytes=int(stat['anon']), file_bytes=int(stat['file']), current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()),
                peak_bytes=int(Path('/sys/fs/cgroup/memory.peak').read_text()), max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def outcome(exc):
    # Only the class-name summary embedded by download_torrent, never message/URL text.
    if isinstance(exc, IndexerDefinitionException):
        text = str(exc)
        return 'too-large' if '(IndexerResponseTooLargeException)' in text else 'adapter-error-other'
    return 'other:' + type(exc).__name__


async def main():
    original = httpx.AsyncClient.send
    outbound = 0

    async def guarded(client, request, *args, **kwargs):
        nonlocal outbound
        if request.url.host not in {'tracker.fixture.invalid', 'cdn.other.invalid'}:
            outbound += 1
            raise RuntimeError('External HTTP blocked')
        return await original(client, request, *args, **kwargs)
    httpx.AsyncClient.send = guarded
    rows = []
    output = Path('/fixture-output/rows.jsonl')
    try:
        for kind in KINDS:
            for concurrency in ([1] if SMOKE else [1, 4, 8]):
                adapter = NcoreIndexerDefinition()
                await adapter._client.aclose()
                adapter._client = IndexerClient(adapter, base_url=BASE, follow_redirects=True, timeout=20, trust_env=False)
                adapter._detect_authentication_error = lambda response: None
                outcomes = Counter()
                walls = []

                async def request():
                    began = time.perf_counter_ns()
                    try:
                        async with asyncio.timeout(90):
                            body = await adapter.download_torrent(BASE + '/payload/' + kind)
                        del body
                        result = 'unexpected-success'
                    except Exception as exc:  # outcome is the measured datum
                        result = outcome(exc)
                    walls.append((time.perf_counter_ns() - began) / 1e6)
                    outcomes[result] += 1
                try:
                    gc.collect()
                    gate = asyncio.Semaphore(concurrency)
                    done = asyncio.Event()
                    samples = deque(maxlen=100)
                    peaks = {}

                    async def monitor():
                        while not done.is_set():
                            m = memory()
                            samples.append(m)
                            for key, value in m.items():
                                peaks[key] = max(peaks.get(key, 0), value)
                            await asyncio.sleep(.05)

                    async def measured():
                        async with gate:
                            await request()
                    ticker = asyncio.create_task(monitor())
                    began, cpu = time.perf_counter(), time.process_time()
                    try:
                        await asyncio.gather(*(measured() for _ in range(COUNT)))
                    finally:
                        done.set()
                        await ticker
                    gc.collect()
                    walls.sort()
                    row = dict(kind=kind, concurrency=concurrency, count=COUNT, outcomes=dict(outcomes), p50_ms=walls[len(walls) // 2],
                               p95_ms=walls[int((len(walls) - 1) * .95)], wall_seconds=time.perf_counter() - began, cpu_seconds=time.process_time() - cpu,
                               memory_after_gc=memory(), memory_peaks=peaks, memory_samples=list(samples))
                    with output.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(row) + '\n')
                    rows.append(row)
                    print(json.dumps(dict(kind=kind, concurrency=concurrency, outcomes=dict(outcomes))), file=sys.stderr, flush=True)
                finally:
                    await adapter.close()
    finally:
        httpx.AsyncClient.send = original
    print(json.dumps(dict(fixture='cr15a-giant-control-v1', is_measurement=not SMOKE, rows=rows, external_http_attempts=outbound)))

asyncio.run(main())
