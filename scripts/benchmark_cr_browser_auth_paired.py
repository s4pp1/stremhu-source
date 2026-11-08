"""Offline real HTTP auth/pairing; ten legitimate devices per transport peer.

The admission clock advances one minute per ten-device wave, so 100 samples
represent ten normal waves, not an unapproved 100-login instantaneous burst.
Every request carries the configured browser Origin. A disposable network record is seeded. HTTP latency and CPU use the real clock. No real dotenv, tracker or user data.
"""

import asyncio
import importlib.util
import json
import resource
import statistics
import tempfile
import time
from pathlib import Path

import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import_started = time.perf_counter()

from app.common import database
from app.common.database import Base
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.settings.models import SettingModel
from app.modules.users.models import UserModel

import_seconds = time.perf_counter() - import_started

def container_memory():
    root = Path("/sys/fs/cgroup")
    stat = dict(line.split() for line in (root / "memory.stat").read_text().splitlines())
    return {"anon_bytes":int(stat["anon"]), "file_bytes":int(stat["file"]), "current_bytes":int((root / "memory.current").read_text()), "peak_bytes":int((root / "memory.peak").read_text())}



async def main():
    with tempfile.TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory) / 'auth.db'}", connect_args={"check_same_thread": False, "timeout": 2}, hide_parameters=True)
        Base.metadata.create_all(engine)
        database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
        password = "synthetic-fixture-password"
        fixed = json.loads(Path("/fixture/auth-fixed.json").read_text())
        import hashlib
        encoded = fixed["password_hash"]
        if hashlib.sha256(encoded.encode()).hexdigest() != fixed["password_hash_sha256"]:
            raise RuntimeError("Synthetic auth fixture digest mismatch")
        with Session(engine) as db:
            db.add(RoleModel(id="user", name="Fixture")); db.flush()
            db.add(SettingModel(key="network", value={"mode":"manual", "host":"fixture.invalid"}))
            db.add(UserModel(id="one", username="one", password_hash=encoded, api_key="fixture-key")); db.commit()
        sql_count = 0

        def count_sql(*args):
            nonlocal sql_count
            sql_count += 1

        event.listen(engine, "before_cursor_execute", count_sql)
        rows = []
        for mode in ("direct-https",):
            for concurrency in (1, 4):
                logical_time = [0.0]
                if importlib.util.find_spec("app.common.auth_rate_limit"):
                    from app.common import auth_rate_limit
                    auth_rate_limit.auth_rate_limiter = auth_rate_limit.AuthRateLimiter(now=lambda: logical_time[0])
                semaphore = asyncio.Semaphore(concurrency)
                samples, errors = [], []
                request_samples = {name: [] for name in ("login", "init", "status-pending", "verify", "status-linked")}
                peer = "192.0.2.1" if mode == "direct-https" else "192.0.2.2"

                async def timed(client, measured, name, method, path, **kwargs):
                    started = time.perf_counter_ns()
                    response = await client.request(method, path, **kwargs)
                    if measured:
                        request_samples[name].append((time.perf_counter_ns()-started)/1e6)
                    return response

                async def cycle(index, measured):
                    async with semaphore:
                        # Spoofed forwarded data must never create fresh source buckets.
                        headers = {"X-Forwarded-For": f"198.51.100.{index % 10 + 1}"} if mode.startswith("shared") else {}
                        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(peer, 1234)), base_url="https://fixture.invalid", headers={**headers, "Origin":"https://fixture.invalid"}) as client:
                            started = time.perf_counter_ns()
                            login = await timed(client, measured, "login", "POST", "/api/auth/login", json={"username":"one", "password":password})
                            initialized = await timed(client, measured, "init", "POST", "/api/auth/pair/init")
                            statuses = [login.status_code, initialized.status_code]
                            if initialized.status_code == 200:
                                pair = initialized.json()
                                path = "/api/auth/pair/status/" + pair["deviceCode"]
                                statuses.append((await timed(client, measured, "status-pending", "GET", path)).status_code)
                                statuses.append((await timed(client, measured, "verify", "POST", "/api/auth/pair/verify", json={"userCode":pair["userCode"]})).status_code)
                                polled = await timed(client, measured, "status-linked", "GET", path)
                                statuses.append(polled.status_code)
                                if polled.status_code == 200 and polled.json()["status"] != "linked":
                                    statuses.append("incorrect-state")
                            if measured:
                                samples.append((time.perf_counter_ns()-started)/1e6)
                                if statuses != [200]*5:
                                    errors.append(statuses)

                await asyncio.gather(*(cycle(i, False) for i in range(10)))
                sql_before, cpu = sql_count, time.process_time()
                for wave in range(10):
                    logical_time[0] += 60
                    await asyncio.gather(*(cycle(wave*10+i, True) for i in range(10)))
                request_metrics = {name: dict(samples_ms=values, p50_ms=statistics.median(values), p95_ms=sorted(values)[94], p99_ms=sorted(values)[98]) for name, values in request_samples.items()}
                ordered = sorted(samples)
                rows.append(dict(workload=mode, concurrency=concurrency, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], errors=errors, per_request=request_metrics, sql_statements=sql_count-sql_before, cpu_seconds=time.process_time()-cpu, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, container_memory=container_memory()))
        print(json.dumps(dict(fixture="browser-origin-direct1-4-identical-prefix-fixed-argon2-v5", startup_import_seconds=import_seconds, credential_fixture_sha256=fixed["password_hash_sha256"], logical_seconds_per_wave=60, warmup_devices=10, rows=rows)))
        engine.dispose()


asyncio.run(main())
