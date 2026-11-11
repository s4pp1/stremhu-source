"""Functional slow/cancel observations, not latency or production deadline tuning."""
import asyncio
import hashlib
import json
import os
import time

import httpx

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition

BASE = os.environ['TEST_BASE_URL']
assert BASE == 'http://tracker.fixture.invalid:8080'


async def main():
    adapter = NcoreIndexerDefinition()
    await adapter._client.aclose()
    adapter._client = IndexerClient(adapter, base_url=BASE, timeout=20, trust_env=False, follow_redirects=True)
    adapter._semaphore = asyncio.Semaphore(1)
    adapter._detect_authentication_error = lambda response: None
    rows = []
    async with httpx.AsyncClient(base_url=BASE, trust_env=False, timeout=3) as observer:
        async def poll(case, predicate):
            deadline = time.monotonic() + 5
            while True:
                row = (await observer.get('/stats')).json().get(case, {})
                if predicate(row):
                    return row
                if time.monotonic() > deadline:
                    raise RuntimeError('Synthetic slow-body state deadline failed')
                await asyncio.sleep(.02)

        async def small():
            async with asyncio.timeout(5):
                body = await adapter.download_torrent(BASE + '/small')
            assert len(body) == 82073
            assert hashlib.sha256(body).hexdigest() == 'cadbdf8e5a280df14c4d6151d6bfecdf7a695c64cabdaffaf2c9e1886f1836e0'

        async def cancel(task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                return
            raise RuntimeError('Cancelled request unexpectedly returned')

        try:
            await small()
            started = time.monotonic()
            async with asyncio.timeout(40):
                body = await adapter.download_torrent(BASE + '/drip?case=long')
            elapsed = time.monotonic() - started
            assert body == b'x' * 51200 and elapsed >= 24
            rows.append(dict(case='read-timeout-is-not-total-deadline', client_timeout_seconds=20, elapsed_seconds=elapsed, bytes=len(body), stats=await poll('long', lambda row: row.get('completed') == 1)))
            del body
            for case in ['caller-cancel', 'external-timeout', 'queued-waiter-cancel']:
                if case == 'external-timeout':
                    try:
                        async with asyncio.timeout(1):
                            await adapter.download_torrent(BASE + '/drip?case=' + case)
                    except TimeoutError:
                        pass
                    else:
                        raise RuntimeError('External timeout did not fire')
                else:
                    owner = asyncio.create_task(adapter.download_torrent(BASE + '/drip?case=' + case))
                    await poll(case, lambda row: row.get('active') == 1)
                    if case == 'queued-waiter-cancel':
                        waiter = asyncio.create_task(adapter.download_torrent(BASE + '/small'))
                        deadline = time.monotonic() + 3
                        while not adapter._semaphore._waiters:
                            assert time.monotonic() < deadline
                            await asyncio.sleep(0)
                        await cancel(waiter)
                    await cancel(owner)
                stats = await poll(case, lambda row: row.get('active') == 0 and row.get('closed_early') == 1)
                assert stats['sent_bytes'] < 51200 and stats['completed'] == 0
                await small()
                assert adapter._semaphore._value == 1
                rows.append(dict(case=case, stats=stats, subsequent_native_valid_download=True, semaphore_available=1))
        finally:
            await adapter.close()
    print(json.dumps(dict(fixture='g15-slow-body-cancel-functional-v1', is_measurement=False, rows=rows, client_closed=adapter._client.is_closed, scope='Actual IndexerClient, private plaintext tracker, no native parser for deliberately invalid drip bytes. Three functional observations per A/B/C; timings document deadline behavior only, not performance acceptance. External1s timeout is a fixture intervention, not a proposed production limit. No application policy change.')))


asyncio.run(main())
