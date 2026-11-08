"""Real disposable SQLite resume writes and loop probes, no network.

The input is a frozen synthetic native save-resume alert. Its added_time field
changes per wave; resume bytes remain a valid libtorrent encoding. DB keys are
synthetic: this is an I/O/ownership fixture, not a native torrent restore test.
"""

import asyncio
import base64
import hashlib
from dataclasses import asdict
import datetime
import importlib.util
import json
import resource
import statistics
import sys
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
from app.modules.relay.service import RelayService
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrents import background_tasks
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.schemas.internal import TorrentUpdate


OVERLOAD = "--overload" in sys.argv


def native_template():
    name = "overload-256gib-partial" if OVERLOAD else "normal-16gib-partial"
    record = json.loads(Path("/fixture/resume-native-large.json").read_text())["payloads"][name]
    value = base64.b64decode(record["base64"], validate=True)
    assert hashlib.sha256(value).hexdigest() == record["sha256"]
    assert len(value) == record["size"]
    return value


def container_memory():
    root = Path("/sys/fs/cgroup")
    stat = dict(line.split() for line in (root/"memory.stat").read_text().splitlines())
    return {"anon_bytes":int(stat["anon"]), "file_bytes":int(stat["file"]), "current_bytes":int((root/"memory.current").read_text()), "peak_bytes":int((root/"memory.peak").read_text())}


async def arm_piece_waiters(loop):
    service = object.__new__(RelayService)
    service._loop = loop
    service._piece_fetch_tasks = {}
    service._pending_piece_reads = {}
    identity = "f" * 40
    expected = b"synthetic piece data"
    class Handle:
        read_calls = 0
        def info_hash(self): return identity
        def have_piece(self, index): return True
        def read_piece(self, index):
            self.read_calls += 1
            def deliver():
                future = service._pending_piece_reads.get((identity,index))
                if future is not None and not future.done():future.set_result(expected)
            loop.call_later(0.001, deliver)
    handle = Handle()
    async def read():
        started = time.perf_counter_ns()
        value = await service.get_piece_data(handle, 0)
        return (time.perf_counter_ns()-started)/1e6, value == expected
    tasks = [asyncio.create_task(read()) for _ in range(100)]
    async with asyncio.timeout(2):
        while (identity,0) not in service._pending_piece_reads:await asyncio.sleep(0)
    return service, handle, tasks


async def main():
    modern = importlib.util.find_spec("app.modules.torrents.resume_writer") is not None
    if modern:
        from app.modules.torrents.resume_writer import ResumeWriter
    template_bytes = native_template()
    template = libtorrent.bdecode(template_bytes)
    rows = []
    loop = asyncio.get_running_loop()
    with tempfile.TemporaryDirectory() as directory:
        for count in ((500,) if OVERLOAD else (10, 100, 500)):
            for locked in ((False,) if OVERLOAD else (False, True)):
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
                piece_service, piece_handle, piece_tasks = await arm_piece_waiters(loop)
                samples, probes, errors, accepted_ids = [], [], [], set()
                cpu, wall = time.process_time(), time.perf_counter()
                expected_digests = {}
                for wave in range(max(1, 100//count)):
                    for index in range(count):
                        # Each identity owns different native bytes. Sharing
                        # one bytes object across500 hashes would understate
                        # physical queue retention, especially at overload.
                        expected = payload(wave+1+index*1000)
                        expected_digests[str(index)] = hashlib.sha256(expected).hexdigest()
                        probe = loop.create_future()
                        due = loop.time()+0.001
                        loop.call_later(0.001, lambda future=probe, at=due:future.set_result(max(0, loop.time()-at)*1000))
                        probes.append(probe)
                        started = time.perf_counter_ns()
                        if writer:
                            accepted = writer.submit(f"{index+1:040x}", expected)
                            if accepted:
                                accepted_ids.add(index)
                            elif not OVERLOAD:
                                errors.append("admission-rejected")
                        else:
                            background_tasks.handle_save_resume_data(f"{index+1:040x}", expected)
                            accepted_ids.add(index)
                        samples.append((time.perf_counter_ns()-started)/1e6)
                flush_started = time.perf_counter_ns()
                complete = await writer.flush_and_close() if writer else True
                if not complete and not OVERLOAD: errors.append("flush-failed")
                flush_ms = (time.perf_counter_ns()-flush_started)/1e6
                lags = await asyncio.gather(*probes)
                pieces = await asyncio.gather(*piece_tasks)
                piece_samples = [value[0] for value in pieces]
                if not all(value[1] for value in pieces):errors.append("incorrect-piece-bytes")
                if piece_handle.read_calls != 1:errors.append("duplicate-piece-read")
                if piece_service._pending_piece_reads or piece_service._piece_fetch_tasks:errors.append("piece-registry-retained")
                cpu_seconds, wall_seconds = time.process_time()-cpu, time.perf_counter()-wall
                if lock_thread: lock_thread.join(timeout=1)
                measured_counts = dict(counters)
                with Session(engine) as db:
                    values = dict(db.execute(select(TorrentModel.torrent_id, TorrentModel.resume_bytes).where(TorrentModel.torrent_id != str(count))).all())
                def differs(identity):
                    value = values[identity]
                    return value is None or hashlib.sha256(value).hexdigest() != expected_digests[identity]
                lost = sum(differs(identity) for identity in values)
                lost_accepted = sum(differs(str(index)) for index in accepted_ids)
                if modern and lost_accepted: errors.append("accepted-state-not-durable")
                if writer and OVERLOAD:
                    if complete or not writer.stats.rejected: errors.append("overload-not-visible")
                    if writer.stats.peak_bytes > 8*1024*1024: errors.append("byte-cap-exceeded")
                    if writer.stats.peak_hashes > 1024: errors.append("hash-cap-exceeded")
                    if writer.stats.leased_bytes or writer.stats.distinct_hashes: errors.append("lease-retained")
                ordered, lag_ordered = sorted(samples), sorted(lags)
                rows.append(dict(workload="resume-overload" if OVERLOAD else "resume-80ms-db-lock" if locked else "resume-normal", torrents=count, concurrency=1, submitted=len(samples), accepted_final_rows=len(accepted_ids), lost_accepted_final_rows=lost_accepted, close_complete=complete, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[int((len(ordered)-1)*.95)], p99_ms=ordered[int((len(ordered)-1)*.99)], loop_lag_samples_ms=lags, loop_lag_p99_ms=lag_ordered[int((len(lag_ordered)-1)*.99)], cpu_seconds=cpu_seconds, wall_seconds=wall_seconds, flush_ms=flush_ms, cold_durable_save_ms=cold_ms, sql_counts=measured_counts, lost_final_rows=lost, errors=errors, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, container_memory=container_memory(), writer_stats=asdict(writer.stats) if writer else None, piece_samples_ms=piece_samples, piece_p95_ms=sorted(piece_samples)[94], piece_p99_ms=sorted(piece_samples)[98], piece_read_calls=piece_handle.read_calls))
                engine.dispose()
    print(json.dumps(dict(fixture="native-resume-opaque-file-db-alert-loop-resources-v2", overload=OVERLOAD, native_template_sha256=hashlib.sha256(template_bytes).hexdigest(), scope="Synthetic DB identities and frozen native bytes; No native restore or seeder claim; real Relay get_piece_data with100 joined waiters and a1ms native-read stub", rows=rows)))


asyncio.run(main())
