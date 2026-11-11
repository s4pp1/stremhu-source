"""Real signed login/me/password/replay on a disposable synthetic database."""

import asyncio
import json
import resource
import statistics
import tempfile
import time
from pathlib import Path

import httpx
from argon2 import PasswordHasher
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.common import auth_rate_limit, database
from app.common.database import Base
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.users.models import UserModel


def summary(samples):
    ordered = sorted(samples)
    return dict(samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98])


async def main():
    clock = [0.0]
    auth_rate_limit.auth_rate_limiter = auth_rate_limit.AuthRateLimiter(now=lambda:clock[0])
    password = "synthetic-first-password"
    with tempfile.TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory)/'sessions.db'}", connect_args={"check_same_thread":False}, hide_parameters=True)
        Base.metadata.create_all(engine)
        database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
        encoded = PasswordHasher().hash(password)
        with Session(engine) as db:
            db.add(RoleModel(id="admin", name="Fixture admin")); db.flush()
            db.add_all([UserModel(id="one", username="one", role_id="admin", password_hash=encoded),UserModel(id="other", username="other", role_id="admin", password_hash=encoded)]);db.commit()
        sql_count = [0]
        event.listen(engine, "before_cursor_execute", lambda *args:sql_count.__setitem__(0,sql_count[0]+1))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://fixture.invalid") as client, httpx.AsyncClient(transport=transport, base_url="https://fixture.invalid") as other:
            for actor, username in [(client,"one"),(other,"other")]:
                assert (await actor.post("/api/auth/login", json={"username":username,"password":password})).status_code == 200
            rows = []
            for _ in range(10):
                assert (await client.get("/api/me/")).status_code == 200
            for concurrency in (1,4,8):
                semaphore = asyncio.Semaphore(concurrency)
                samples, errors = [], []

                async def read():
                    async with semaphore:
                        started = time.perf_counter_ns()
                        result = await client.get("/api/me/")
                        samples.append((time.perf_counter_ns()-started)/1e6)
                        if result.status_code != 200 or result.json() is None:errors.append(result.status_code)

                previous, cpu = sql_count[0], time.process_time()
                await asyncio.gather(*(read() for _ in range(100)))
                rows.append(dict(workload="authenticated-me", concurrency=concurrency, **summary(samples), sql_statements=sql_count[0]-previous, cpu_seconds=time.process_time()-cpu, errors=errors))
            metrics = {name:[] for name in ["login","password-update","replay","unrelated-user"]}
            errors, accepted_stale = [], 0
            previous, cpu = sql_count[0], time.process_time()
            for index in range(100):
                clock[0] += 60  # one legitimate password operation per logical minute
                started = time.perf_counter_ns()
                login = await client.post("/api/auth/login", json={"username":"one","password":password})
                metrics["login"].append((time.perf_counter_ns()-started)/1e6)
                old_cookies = httpx.Cookies(client.cookies)
                password = f"synthetic-next-password-{index}"
                started = time.perf_counter_ns()
                updated = await client.put("/api/me/", json={"password":password})
                metrics["password-update"].append((time.perf_counter_ns()-started)/1e6)
                async with httpx.AsyncClient(transport=transport, base_url="https://fixture.invalid", cookies=old_cookies) as replay:
                    started = time.perf_counter_ns()
                    result = await replay.get("/api/users/")
                    metrics["replay"].append((time.perf_counter_ns()-started)/1e6)
                    accepted_stale += result.status_code == 200
                    expected = 401 if hasattr(UserModel,"session_epoch") else 200
                    if result.status_code != expected:errors.append(["replay",result.status_code])
                started = time.perf_counter_ns()
                unchanged = await other.get("/api/users/")
                metrics["unrelated-user"].append((time.perf_counter_ns()-started)/1e6)
                if login.status_code != 200 or updated.status_code != 200 or unchanged.status_code != 200:errors.append([login.status_code,updated.status_code,unchanged.status_code])
            rows.append(dict(workload="password-and-stale-cookie-replay",concurrency=1,**summary(metrics["password-update"]),per_request={name:summary(values) for name,values in metrics.items()},accepted_stale_sessions=accepted_stale,sql_statements=sql_count[0]-previous,cpu_seconds=time.process_time()-cpu,errors=errors))
        engine.dispose()
        print(json.dumps(dict(fixture="real-session-password-replay-v1",logical_minutes=100,rows=rows,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))


asyncio.run(main())
