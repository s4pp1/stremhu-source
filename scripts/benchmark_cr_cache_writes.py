"""Real login, user write, commit and stream-cache read on a disposable DB."""

import asyncio
import json
import statistics
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import httpx
from argon2 import PasswordHasher
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.common.database import Base
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.stremio.schemas import StremioStream
from app.modules.stremio import service as stream_service_module
from app.modules.users.models import UserModel

if not hasattr(stream_service_module, "invalidate_stream_cache"):
    print(json.dumps(dict(available=False, reason="generation stream cache absent upstream")))
    raise SystemExit(0)

StremioService = stream_service_module.StremioService
invalidate_stream_cache = stream_service_module.invalidate_stream_cache


async def main():
    with tempfile.TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory) / 'fixture.db'}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
        password = "synthetic-fixture-password"
        with Session(engine) as db:
            db.add(RoleModel(id="user", name="Fixture"))
            db.flush()
            db.add_all([UserModel(id="one", username="one", password_hash=PasswordHasher().hash(password), api_key="fixture-one", torrent_seed=0), UserModel(id="two", username="two", api_key="fixture-two", torrent_seed=2)])
            db.commit()
        sql_count = 0

        def count_sql(*args):
            nonlocal sql_count
            sql_count += 1

        event.listen(engine, "before_cursor_execute", count_sql)
        service = StremioService(Mock(), Mock())
        fetches = {"one": 0, "two": 0}

        async def fetch(user, parsed_id):
            fetches[user.id] += 1
            return [StremioStream(name=f"seed:{user.torrent_seed}", description="fixture", url="https://fixture.invalid/media")]

        service._get_streams_uncached = fetch
        app.dependency_overrides[get_stremio_service] = lambda: service
        invalidate_stream_cache()
        rows = []
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid") as client:
            assert (await client.post("/api/auth/login", json={"username":"one", "password":password})).status_code == 200
            first = "/api/fixture-one/stremio/stream/movie/tt1234567.json"
            other = "/api/fixture-two/stremio/stream/movie/tt1234567.json"
            assert (await client.get(first)).status_code == 200
            assert (await client.get(other)).status_code == 200
            samples, errors, stale = [], [], 0
            sql_before = sql_count
            cpu = time.process_time()
            for value in range(1, 101):
                started = time.perf_counter_ns()
                saved = await client.put("/api/me/", json={"torrentSeed":value})
                result = await client.get(first)
                unrelated = await client.get(other)
                if saved.status_code != 200 or result.status_code != 200 or unrelated.status_code != 200:
                    errors.append([saved.status_code,result.status_code,unrelated.status_code])
                else:
                    stale += result.json()["streams"][0]["name"] != f"seed:{value}"
                samples.append((time.perf_counter_ns()-started)/1e6)
            ordered = sorted(samples)
            rows.append(dict(workload="committed-user-seed-write-and-immediate-stream",concurrency=1,samples_ms=samples,p50_ms=statistics.median(samples),p95_ms=ordered[94],p99_ms=ordered[98],cpu_seconds=time.process_time()-cpu,sql_statements=sql_count-sql_before,errors=errors,stale_responses=stale,fetches=fetches))
        print(json.dumps(dict(fixture="real-user-commit-stream-cache-v1",rows=rows)))
        app.dependency_overrides.clear()
        engine.dispose()


asyncio.run(main())
