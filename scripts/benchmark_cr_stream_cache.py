"""Offline cache-hit and global-reset/in-flight reproduction."""

import asyncio
import json
import statistics
import time
from unittest.mock import Mock

from app.modules.stremio.schemas import ImdbStreamId, StremioStream
from app.modules.stremio import service as stream_service_module
from app.modules.users.models import UserModel

if not hasattr(stream_service_module, "invalidate_stream_cache"):
    print(json.dumps(dict(available=False, reason="generation stream cache absent upstream")))
    raise SystemExit(0)

StremioService = stream_service_module.StremioService
invalidate_stream_cache = stream_service_module.invalidate_stream_cache

async def main():
    rows = []
    for scenario in ("cache-hit", "global-reset-inflight"):
        samples, outcomes = [], {}
        for index in range(100):
            invalidate_stream_cache()
            service = StremioService(Mock(), Mock())
            user = UserModel(id=f"fixture-{index}", username="fixture", api_key="fixture-key")
            identity = ImdbStreamId(imdb_id="tt1234567")
            started, release = asyncio.Event(), asyncio.Event()
            calls = 0

            async def fetch(user, identity):
                nonlocal calls
                calls += 1
                if scenario == "global-reset-inflight" and calls == 1:
                    started.set()
                    await release.wait()
                    return [StremioStream(name="old", description="fixture", url="https://fixture.invalid/old")]
                return [StremioStream(name="new", description="fixture", url="https://fixture.invalid/new")]

            service._get_streams_uncached = fetch
            before = time.perf_counter_ns()
            if scenario == "cache-hit":
                await service.get_streams(user, identity)
                result = await service.get_streams(user, identity)
                outcome = f"{result[0].name}:calls={calls}"
            else:
                owner = asyncio.create_task(service.get_streams(user, identity))
                await started.wait()
                invalidate_stream_cache()
                joiner = asyncio.create_task(service.get_streams(user, identity))
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                release.set()
                first, second = await asyncio.gather(owner, joiner)
                last = await service.get_streams(user, identity)
                outcome = f"{first[0].name},{second[0].name},{last[0].name}:calls={calls}"
            samples.append((time.perf_counter_ns() - before) / 1e6)
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        ordered = sorted(samples)
        rows.append(dict(workload=scenario, concurrency=2 if scenario.endswith('inflight') else 1, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], outcomes=outcomes, errors=[]))
    print(json.dumps(dict(fixture="global-reset-inflight-v1", rows=rows)))


asyncio.run(main())
