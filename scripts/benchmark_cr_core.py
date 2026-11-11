"""Offline CR baseline: run inside a pinned, network-disabled Docker container.

Synthetic dependencies replace storage and tracker work; this measures the HTTP,
session, API-key and response boundary, not end-to-end tracker performance.
The controller supplies HOST_IP and a random SESSION_SECRET without printing them.
"""

import asyncio
import hashlib
import importlib.metadata
import json
import resource
import sys
import time
from pathlib import Path
from types import SimpleNamespace

started = time.perf_counter()

import httpx  # noqa: E402

from app.main import app  # noqa: E402
from app.modules.auth.dependencies import get_auth_service  # noqa: E402
from app.modules.auth.service import AuthService  # noqa: E402
from app.modules.roles.models import RoleModel  # noqa: E402
from app.modules.stremio.dependencies import get_stremio_service  # noqa: E402
from app.modules.stremio.service import StremioService  # noqa: E402
from app.modules.users.dependencies import get_users_service  # noqa: E402
from app.modules.users.models import UserModel  # noqa: E402

startup_seconds = time.perf_counter() - started
user = UserModel(id="fixture-user", username="fixture-user", api_key="fixture-api-key")
user.role = RoleModel(id="user", name="Fixture user")
users = SimpleNamespace(
    find_by_api_key=lambda key: user if key == user.api_key else None,
    find_by_id=lambda identity: user if identity == user.id else None,
)
auth = AuthService(users)
service = StremioService(
    torrent_streams_service=None,
    settings_service=SimpleNamespace(get_app_url=lambda: "https://fixture.invalid"),
)


async def streams(*args, **kwargs):
    return []


service.get_streams = streams
app.dependency_overrides[get_auth_service] = lambda: auth
app.dependency_overrides[get_users_service] = lambda: users
app.dependency_overrides[get_stremio_service] = lambda: service


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


async def main():
    rows = []
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid"
    ) as client:
        paths = {
            "manifest": "/api/fixture-api-key/stremio/manifest.json",
            "streams": "/api/fixture-api-key/stremio/stream/movie/tt1234567.json",
            "rejected_auth": "/api/rejected/stremio/manifest.json",
        }
        for workload, path in paths.items():
            expected = 401 if workload == "rejected_auth" else 200
            # Warm-up is deliberately excluded from samples.
            for _ in range(10):
                response = await client.get(path)
                assert response.status_code == expected
            for concurrency in (1, 4, 8):
                for repetition in range(int(sys.argv[1]) if len(sys.argv) > 1 else 5):
                    gate = asyncio.Semaphore(concurrency)
                    samples = []
                    errors = []
                    payloads = set()

                    async def request():
                        async with gate:
                            before = time.perf_counter_ns()
                            response = await client.get(path)
                            samples.append((time.perf_counter_ns() - before) / 1e6)
                            if response.status_code != expected:
                                errors.append(response.status_code)
                            payloads.add(hashlib.sha256(response.content).hexdigest())

                    cpu = time.process_time()
                    await asyncio.gather(*(request() for _ in range(100)))
                    rows.append(
                        dict(
                            workload=workload,
                            concurrency=concurrency,
                            repetition=repetition,
                            samples_ms=samples,
                            p50_ms=percentile(samples, 0.5),
                            p95_ms=percentile(samples, 0.95),
                            p99_ms=percentile(samples, 0.99),
                            cpu_seconds=time.process_time() - cpu,
                            errors=errors,
                            payload_hashes=sorted(payloads),
                        )
                    )
    print(
        json.dumps(
            dict(
                fixture="core-http-v1-empty-streams",
                scope="in-process HTTP/auth boundary; no DB/tracker/media workload",
                startup_import_seconds=startup_seconds,
                max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                memory_current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()),
                versions={
                    key: importlib.metadata.version(key)
                    for key in ("fastapi", "starlette", "httpx", "SQLAlchemy", "libtorrent")
                },
                rows=rows,
            )
        )
    )


asyncio.run(main())
