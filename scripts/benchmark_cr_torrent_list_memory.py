"""Real authenticated list HTTP/SQL with synthetic scalar metadata and BLOBs.

No torrent is added to libtorrent. The Relay inventory is a local fixed stub.
The intentionally opaque 64KiB BLOBs test list materialization, not restore.
"""

import asyncio
import datetime
import hashlib
import json
import resource
import statistics
import tempfile
import threading
import time
from pathlib import Path
from typing import Annotated

import httpx
from argon2 import PasswordHasher
from fastapi import Depends
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.common.database import Base, get_db
from app.main import app
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.relay.schemas import RelayTorrent
from app.modules.roles.models import RoleModel
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrents.dependencies import get_torrents_service
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.service import TorrentsService
from app.modules.users.models import UserModel


def memory_probe():
    stopped = threading.Event()
    samples = []
    def sample():
        started = time.monotonic()
        while not stopped.is_set():
            fields = dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
            samples.append(dict(elapsed_seconds=time.monotonic()-started, anon_bytes=int(fields['anon']), file_bytes=int(fields['file']), total_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text())))
            if len(samples)>20000:del samples[0]
            stopped.wait(0.005)
    thread = threading.Thread(target=sample)
    thread.start()
    return stopped, thread, samples


async def main():
    rows = []
    password_hash = PasswordHasher().hash("synthetic-password")
    with tempfile.TemporaryDirectory() as directory:
        for count in (500,):
            engine = create_engine(f"sqlite:///{Path(directory) / (str(count)+'.db')}", connect_args={"check_same_thread":False}, hide_parameters=True)
            Base.metadata.create_all(engine)
            database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
            now = datetime.datetime(2026, 1, 1, 12)
            with Session(engine) as db:
                db.add(RoleModel(id="admin", name="Fixture admin")); db.flush()
                db.add(UserModel(id="admin", username="admin", role_id="admin", password_hash=password_hash))
                for indexer in range(5):
                    identity = f"fixture-{indexer}"
                    db.add(IndexerDefinitionModel(id=identity, name=identity, url="https://fixture.invalid", details_path="details")); db.flush()
                    db.add(IndexerAccountModel(indexer_id=identity, username="synthetic", password="synthetic"))
                db.flush()
                db.execute(insert(TorrentFileModel.__table__), [dict(indexer_id=f"fixture-{i%5}", torrent_id=str(i), info_hash=f"{i+1:040x}", torrent_bytes=b"B"*65536, last_used_at=now, created_at=now) for i in range(count)])
                db.execute(insert(TorrentModel.__table__), [dict(indexer_id=f"fixture-{i%5}", torrent_id=str(i), info_hash=f"{i+1:040x}", resume_bytes=b"R"*65536, is_persisted=i%2==0, full_download=None, created_at=now, updated_at=now) for i in range(count)])
                db.commit()
            inventory = [RelayTorrent(info_hash=f"{i+1:040x}", name=f"fixture-{i}", download_speed=1, upload_speed=2, downloaded=3, uploaded=4, total=5, max_connections=50, connections=1) for i in range(count) if i%5 != 0]

            class FixtureRelay:
                def get_torrents(self):
                    return inventory

            def service(db: Annotated[Session, Depends(get_db, scope="function")]):
                return TorrentsService(TorrentRepository(db), None, None, None, FixtureRelay())

            app.dependency_overrides[get_torrents_service] = service
            sql_count, blob_selects = [0], [0]

            def count_sql(connection, cursor, statement, *args):
                if statement.lstrip().upper().startswith("SELECT"):
                    sql_count[0] += 1
                    blob_selects[0] += "torrent_bytes" in statement or "resume_bytes" in statement

            event.listen(engine, "before_cursor_execute", count_sql)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid") as client:
                assert (await client.post("/api/auth/login", json={"username":"admin", "password":"synthetic-password"})).status_code == 200
                cold_started = time.perf_counter_ns()
                cold = await client.get("/api/torrents/")
                cold_ms = (time.perf_counter_ns()-cold_started)/1e6
                assert cold.status_code == 200
                for _ in range(5):
                    assert (await client.get("/api/torrents/")).status_code == 200
                for concurrency in (8,):
                    semaphore = asyncio.Semaphore(concurrency)
                    samples, errors, payloads = [], [], set()

                    async def request():
                        async with semaphore:
                            started = time.perf_counter_ns()
                            response = await client.get("/api/torrents/")
                            samples.append((time.perf_counter_ns()-started)/1e6)
                            if response.status_code != 200:
                                errors.append(response.status_code)
                            else:
                                data = sorted(response.json(), key=lambda item:item["infoHash"])
                                if len(data) != len(inventory): errors.append("wrong-result-count")
                                payloads.add(hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest())

                    previous, blobs = sql_count[0], blob_selects[0]
                    stopped, monitor, memory_samples = memory_probe()
                    cpu = time.process_time()
                    await asyncio.gather(*(request() for _ in range(100)))
                    stopped.set()
                    monitor.join(timeout=1)
                    if monitor.is_alive(): raise RuntimeError("memory sampler did not close")
                    ordered = sorted(samples)
                    rows.append(dict(workload="torrent-list", torrents=count, concurrency=concurrency, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], errors=errors, cpu_seconds=time.process_time()-cpu, select_count=sql_count[0]-previous, blob_selects=blob_selects[0]-blobs, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, cold_first_request_ms=cold_ms, payload_hashes=sorted(payloads), memory_samples=memory_samples, memory_peaks={key:max(sample[key] for sample in memory_samples) for key in ("anon_bytes","file_bytes","total_bytes")}))
            app.dependency_overrides.clear()
            engine.dispose()
    print(json.dumps(dict(fixture="torrent-list-largest-500-eight-memory-breakdown-v1", blob_bytes_per_column=65536, indexers=5, rows=rows)))


asyncio.run(main())
