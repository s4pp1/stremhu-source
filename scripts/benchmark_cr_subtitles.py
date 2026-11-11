"""Synthetic authenticated subtitle-cache HTTP baseline, no tracker or DB I/O."""

import asyncio
import hashlib
import json
import resource
import statistics
import time
from contextlib import contextmanager
from types import SimpleNamespace

import httpx

from app.main import app
from app.modules.auth.service import AuthService
from app.modules.stream import router
from app.modules.stream.schemas import StreamToken
from app.modules.stream.utils.stream_token import generate_stream_token
from app.modules.users.models import UserModel


@contextmanager
def fixture_db():
    yield None


async def main():
    if not hasattr(router, "_put_cached_subtitle"):
        print(json.dumps({"available": False, "reason": "subtitle cache absent in this baseline"}))
        return
    user = UserModel(id="fixture", username="fixture", api_key="fixture-key")
    auth = AuthService(SimpleNamespace(find_by_api_key=lambda key: user if key == user.api_key else None))
    router.isolated_db_session = fixture_db
    router.create_auth_service = lambda db: auth
    body = b"1\n00:00:00,000 --> 00:00:01,000\nfixture\n\n" * 100
    router._put_cached_subtitle(("fixture", "1", 0, False), "text/plain", "fixture.srt", body)
    token = generate_stream_token(StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id="fixture"))
    path = f"/api/fixture-key/subtitles/{token}"
    rows = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid") as client:
        for method, range_value, expected in [("GET", None, 200), ("HEAD", None, 200), ("GET", "bytes=10-30", 206), ("HEAD", "bytes=10-30", 206), ("GET", "bytes=999999-", 416)]:
            headers = {"Range": range_value} if range_value else {}
            for _ in range(10):
                response = await client.request(method, path, headers=headers)
                assert response.status_code == expected
            for concurrency in (1, 4, 8):
                samples, errors, payloads, policies = [], [], set(), set()
                gate = asyncio.Semaphore(concurrency)

                async def request():
                    async with gate:
                        start = time.perf_counter_ns()
                        response = await client.request(method, path, headers=headers)
                        samples.append((time.perf_counter_ns() - start) / 1e6)
                        if response.status_code != expected:
                            errors.append(response.status_code)
                        payloads.add(hashlib.sha256(response.content).hexdigest())
                        policies.add(response.headers.get("cache-control"))

                cpu = time.process_time()
                await asyncio.gather(*(request() for _ in range(100)))
                ordered = sorted(samples)
                rows.append(dict(workload=f"{method}:{range_value or 'full'}", concurrency=concurrency, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], cpu_seconds=time.process_time()-cpu, errors=errors, payload_hashes=sorted(payloads), cache_control=sorted(policies, key=str)))
    print(json.dumps(dict(available=True, fixture="subtitle-cache-v1-3900-bytes", rows=rows, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))


asyncio.run(main())
