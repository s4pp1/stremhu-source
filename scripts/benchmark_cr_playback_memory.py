"""Thirty-minute invalid-key retention workload; isolated Docker only.

No real user, tracker, seeder, database or external network is used. A valid
synthetic stream token reaches the real route and real API-key rejection.
"""

import asyncio
import gc
import json
import resource
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import httpx

from app.main import app
from app.modules.auth.service import AuthService
from app.modules.stream import active_playback, router
from app.modules.stream.schemas import StreamToken
from app.modules.stream.utils.stream_token import generate_stream_token


@contextmanager
def fixture_db():
    yield None


async def main():
    router.isolated_db_session = fixture_db
    auth = AuthService(SimpleNamespace(find_by_api_key=lambda key: None))
    router.create_auth_service = lambda db: auth
    token = generate_stream_token(StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id="fixture"))
    samples = []
    count = 0
    start = time.monotonic()
    next_sample = start
    # This duration is deliberately not controlled by the short-run controller.
    deadline = start + 1800
    progress = Path("/evidence/playback-memory-progress.jsonl")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid") as client:
        while time.monotonic() < deadline:
            tick = time.monotonic()
            for _ in range(25):
                response = await client.get(f"/api/fixture-invalid-{count}/stream/{token}")
                if response.status_code != 401:
                    raise RuntimeError("unexpected synthetic auth outcome")
                count += 1
            now = time.monotonic()
            if now >= next_sample:
                gc.collect()
                if hasattr(active_playback, "_registry"):
                    users = active_playback._registry.user_count
                    waiters = active_playback._registry.waiter_count
                else:
                    users = len(active_playback._ACTIVE_PLAYBACKS)
                    waiters = sum(len(events) for events in active_playback._PLAYBACK_EVENTS.values())
                row = dict(elapsed_seconds=now-start, rejected_requests=count, registry_users=users, waiters=waiters, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, cgroup_memory_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()))
                samples.append(row)
                with progress.open("a") as handle:
                    handle.write(json.dumps(row) + "\n")
                next_sample = now + 60
            await asyncio.sleep(max(0, min(1 - (time.monotonic() - tick), deadline - time.monotonic())))
    print(json.dumps(dict(fixture="invalid-key-valid-token-25-per-second-v1", duration_seconds=time.monotonic()-start, rejected_requests=count, samples=samples)))


asyncio.run(main())
