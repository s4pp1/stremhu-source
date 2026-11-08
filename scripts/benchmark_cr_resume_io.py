"""Real disposable SQLite resume writes and loop probes, no network.

The input is a frozen synthetic native save-resume alert. Its added_time field
changes per wave; resume bytes remain a valid libtorrent encoding. DB keys are
synthetic: this is an I/O/ownership fixture, not a native torrent restore test.
"""

import asyncio
import datetime
import importlib.util
import json
import resource
import statistics
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import libtorrent
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.common.database import Base
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrents import background_tasks
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.schemas.internal import TorrentUpdate


async def main():
    modern = importlib.util.find_spec("app.modules.torrents.resume_writer") is not None
    if modern:
        from app.modules.torrents.resume_writer import ResumeWriter
    template = libtorrent.bdecode(Path("/fixtures/resume-256.bin").read_bytes())
    rows = []
    loop = asyncio.get_running_loop()
    with tempfile.TemporaryDirectory() as directory:
        for count in (10, 100, 500):
            for locked in (False, True):
                engine = create_engine(f"sqlite:///{Path(directory) / (str(count)+'-'+str(locked)+'.db')}", connect_args={"check_same_thread":False,"timeout":0.02}, hide_parameters=True)
                Base.metadata.create_all(engine)
                database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
                with Session(engine) as db:
                    db.add(IndexerDefinitionModel(id="fixture", name="fixture", url="https://fixture.invalid", details_path="details")); db.flush()
                    db.add(IndexerAccountModel(indexer_id="fixture", username="synthetic", password="synthetic")); db.flush()
                    stamp = datetime.datetime(2026, 1, 1, 12)
                    db.execute(insert(TorrentFileModel), [dict(indexer_id="fixture", torrent_id=str(i), info_hash=f"{i+1:040x}", torrent_bytes=b"synthetic", last_used_at=stamp, created_at=stamp) for i in range(count+1)])
                    db.execute(insert(TorrentModel), [dict(indexer_id="fixture", torrent_id=str(i), info_hash=f"{i+1:040x}", created_at=stamp, updated_at=stamp) for i in range(count+1)])
                    db.commit()
                background_tasks._get_bg_service = lambda db:SimpleNamespace(save_resume_data=lambda identity, body:TorrentRepository(db).update(identity, TorrentUpdate(resume_bytes=body)))

                def payload(wave):
                    data = dict(template)
                    data[b"added_time"] = template.get(b"added_time", 0) + wave
                    encoded = libtorrent.bencode(data)
                    libtorrent.read_resume_data(encoded)
                    return encoded

                # Real first durable save is separate from warm load.
                cold_started = time.perf_counter_ns()
                if modern:
                    warmup = ResumeWriter()
                    warmup.start()
                    assert warmup.submit(f"{count+1:040x}", payload(0))
                    assert await warmup.flush_and_close()
                else:
                    background_tasks.handle_save_resume_data(f"{count+1:040x}", payload(0))
                cold_ms = (time.perf_counter_ns()-cold_started)/1e6
                counters = {"sql":0, "commits":0}

                def sql(*args):
                    counters["sql"] += 1

                def committed(*args):
                    counters["commits"] += 1

                event.listen(engine, "before_cursor_execute", sql)
                event.listen(engine, "commit", committed)
                lock_ready = threading.Event()

                def lock_database():
                    with engine.connect() as connection:
                        connection.exec_driver_sql("BEGIN IMMEDIATE")
                        lock_ready.set()
                        threading.Event().wait(0.08)
                        connection.rollback()

                lock_thread = None
                if locked:
                    lock_thread = threading.Thread(target=lock_database)
                    lock_thread.start()
                    assert lock_ready.wait(1)
                writer = ResumeWriter() if modern else None
                if writer:
                    writer.start()
                samples, probes, errors = [], [], []
                cpu, wall = time.process_time(), time.perf_counter()
                expected = None
                for wave in range(max(1, 100//count)):
                    expected = payload(wave+1)
                    for index in range(count):
                        probe = loop.create_future()
                        due = loop.time()+0.001
                        loop.call_later(0.001, lambda future=probe, at=due:future.set_result(max(0, loop.time()-at)*1000))
                        probes.append(probe)
                        started = time.perf_counter_ns()
                        if writer:
                            if not writer.submit(f"{index+1:040x}", expected): errors.append("admission-rejected")
                        else:
                            background_tasks.handle_save_resume_data(f"{index+1:040x}", expected)
                        samples.append((time.perf_counter_ns()-started)/1e6)
                flush_started = time.perf_counter_ns()
                if writer and not await writer.flush_and_close(): errors.append("flush-failed")
                flush_ms = (time.perf_counter_ns()-flush_started)/1e6
                lags = await asyncio.gather(*probes)
                cpu_seconds, wall_seconds = time.process_time()-cpu, time.perf_counter()-wall
                if lock_thread: lock_thread.join(timeout=1)
                measured_counts = dict(counters)
                with Session(engine) as db:
                    values = db.scalars(select(TorrentModel.resume_bytes).where(TorrentModel.torrent_id != str(count))).all()
                lost = sum(value != expected for value in values)
                ordered, lag_ordered = sorted(samples), sorted(lags)
                rows.append(dict(workload="resume-80ms-db-lock" if locked else "resume-normal", torrents=count, concurrency=1, submitted=len(samples), samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[int((len(ordered)-1)*.95)], p99_ms=ordered[int((len(ordered)-1)*.99)], loop_lag_samples_ms=lags, loop_lag_p99_ms=lag_ordered[int((len(lag_ordered)-1)*.99)], cpu_seconds=cpu_seconds, wall_seconds=wall_seconds, flush_ms=flush_ms, cold_durable_save_ms=cold_ms, sql_counts=measured_counts, lost_final_rows=lost, errors=errors, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                engine.dispose()
    print(json.dumps(dict(fixture="native-resume-opaque-file-db-alert-loop-v1", scope="Synthetic DB identities and frozen native bytes; no native restore claim", rows=rows)))


asyncio.run(main())
