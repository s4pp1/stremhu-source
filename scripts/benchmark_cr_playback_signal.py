"""Synthetic real stream HEAD + Stremio subtitles HTTP, both start orders."""

import asyncio
import gc
import importlib.util
import json
import resource
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import httpx

from app.main import app
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService

if importlib.util.find_spec("app.modules.stream.active_playback") is None:
    print(json.dumps(dict(available=False, reason="active-playback module absent upstream")))
    raise SystemExit(0)

from app.modules.stream import active_playback, router
from app.modules.stream.schemas import StreamToken
from app.modules.stream.utils.stream_token import generate_stream_token
from app.modules.stremio import service as stremio_module
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.users.models import UserModel


@contextmanager
def fixture_db():
    yield None


async def main():
    if not hasattr(stremio_module, "wait_for_active_binge_group"):
        print(json.dumps(dict(available=False, reason="active-playback subtitle selection absent upstream")))
        return
    from app.modules.stream.service import parse_range_header
    from app.modules.stremio.schemas import BehaviorHints, StremioStream, StremioSubtitle
    users = {}
    auth = AuthService(SimpleNamespace(find_by_api_key=users.get))
    router.isolated_db_session = fixture_db
    router.create_auth_service = lambda db: auth
    router.get_relay_service = lambda: None
    router.create_playback_histories_service = lambda db: None
    router.create_playbacks_service = lambda **kwargs: SimpleNamespace(check_playback_limit=lambda **kwargs:None)

    class StreamFixture:
        async def prepare_for_stream(self, **kwargs):
            return parse_range_header(10), SimpleNamespace(name="fixture.mkv", size=10)

        async def save_playback_history(self, **kwargs):
            pass

    router.create_stream_service = lambda db: StreamFixture()
    service = stremio_module.StremioService(None, None)
    streams = [StremioStream(name="fixture", description="fixture", url="https://fixture.invalid/media", behavior_hints=BehaviorHints(binge_group=f"fixture-{i}"), subtitles=[StremioSubtitle(id=str(i), url=f"https://fixture.invalid/sub-{i}", lang="hun")]) for i in (1, 2)]

    async def get_streams(*args, **kwargs):
        return streams

    service.get_streams = get_streams
    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_stremio_service] = lambda: service
    original_wait = stremio_module.wait_for_active_binge_group
    registrations = {}

    async def observed_wait(**kwargs):
        identity = kwargs.get("user_id", kwargs.get("api_key"))
        if identity in registrations:
            registrations[identity].set()
        return await original_wait(**kwargs)

    stremio_module.wait_for_active_binge_group = observed_wait
    token = generate_stream_token(StreamToken(indexer_id="fixture", torrent_id="2", file_index=0, playback_id="fixture"))
    rows = []
    serial = 0
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid") as client:
        for order in ("stream-first", "subtitle-first"):
            for concurrency in (1, 4, 8):
                active_playback.clear_active_playbacks()
                gate = asyncio.Semaphore(concurrency)
                samples, errors = [], []

                async def cycle(measured):
                    nonlocal serial
                    async with gate:
                        serial += 1
                        user = UserModel(id=f"fixture-user-{serial}", username="fixture", api_key=f"fixture-key-{serial}")
                        users[user.api_key] = user
                        event = asyncio.Event()
                        registrations[user.api_key] = registrations[user.id] = event
                        sub_path = f"/api/{user.api_key}/stremio/subtitles/movie/tt1234567.json"
                        start = time.perf_counter_ns()
                        if order == "stream-first":
                            head = await client.head(f"/api/{user.api_key}/stream/{token}")
                            sub = await client.get(sub_path)
                        else:
                            task = asyncio.create_task(client.get(sub_path))
                            await asyncio.wait_for(event.wait(), 2)
                            head = await client.head(f"/api/{user.api_key}/stream/{token}")
                            sub = await task
                        if measured:
                            samples.append((time.perf_counter_ns()-start)/1e6)
                            if head.status_code != 200 or sub.status_code != 200:
                                errors.append([head.status_code, sub.status_code])
                            elif [item["id"] for item in sub.json()["subtitles"]] != ["2"]:
                                errors.append("incorrect-subtitle")
                        registrations.pop(user.id); registrations.pop(user.api_key); users.pop(user.api_key)

                await asyncio.gather(*(cycle(False) for _ in range(10)))
                cpu = time.process_time()
                await asyncio.gather(*(cycle(True) for _ in range(100)))
                ordered = sorted(samples)
                rows.append(dict(workload=order, concurrency=concurrency, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], cpu_seconds=time.process_time()-cpu, errors=errors))
    active_playback.clear_active_playbacks()
    for i in range(1025):
        if hasattr(active_playback, "_registry"):
            active_playback.record_active_playback(user_id=str(i), indexer_id="fixture", torrent_id="2")
        else:
            active_playback.record_active_playback(api_key=str(i), indexer_id="fixture", torrent_id="2")
    gc.collect()
    registry_users = active_playback._registry.user_count if hasattr(active_playback, "_registry") else len(active_playback._ACTIVE_PLAYBACKS)
    print(json.dumps(dict(available=True, fixture="stream-head-and-real-subtitle-selection-v1", rows=rows, users_after_1025_intents=registry_users, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, memory_current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()))))
    app.dependency_overrides.clear()
    active_playback.clear_active_playbacks()


asyncio.run(main())
