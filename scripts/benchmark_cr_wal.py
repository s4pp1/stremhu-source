"""G02 isolated SQLite workload: full 60 minutes, no production PRAGMA change.

Nine 400s cells: short readers / request-like SELECT+await / explicit snapshot,
each with1/4/8 independent writer-owned Sessions. Diagnostic PASSIVE is opt-in
and requires a separate complete run. This script never reads dotenv or trackers.
"""

import datetime
import hashlib
import itertools
import json
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, event, insert, select, text, update
from sqlalchemy.orm import Session

from app.common.database import Base
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.repository import TorrentFilesRepository
from app.modules.torrent_files.schemas import TorrentFileIdentifier


DURATION_SECONDS = 3600
DIAGNOSTIC = "--diagnostic-passive" in sys.argv
SMOKE = "--fixture-smoke" in sys.argv
CELL_SECONDS = 2 if SMOKE else 400


def percentile(values, fraction):
    return sorted(values)[int((len(values)-1)*fraction)] if values else None


def main():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory)/"wal.db"
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread":False,"timeout":10}, hide_parameters=True)
        Base.metadata.create_all(engine)
        stamp = datetime.datetime.now()
        with Session(engine) as db:
            db.add(IndexerDefinitionModel(id="fixture", name="Fixture", url="https://fixture.invalid", details_path="details"));db.flush()
            db.add(IndexerAccountModel(indexer_id="fixture",username="synthetic",password="synthetic"));db.flush()
            db.execute(insert(TorrentFileModel),[dict(indexer_id="fixture",torrent_id=str(i),info_hash=f"{i+1:040x}",torrent_bytes=b"synthetic"*2048,last_used_at=stamp-datetime.timedelta(minutes=20 if i%2 else 0),created_at=stamp) for i in range(500)])
            db.commit()
        with engine.connect() as connection:
            pragmas={name:connection.exec_driver_sql("PRAGMA "+name).scalar() for name in ["page_size","journal_mode","synchronous","wal_autocheckpoint","journal_size_limit"]}
        trace_counts, transaction_states = Counter(), Counter()
        trace_lock = threading.Lock()
        connection_ids = itertools.count(1)
        connection_trace = []
        native_trace_sample = []

        def instrument(dbapi, record):
            identity = next(connection_ids)
            connection_trace.append(dict(connection=identity,thread=threading.get_ident(),event="create"))
            def trace(statement):
                verb=statement.lstrip().split(" ",1)[0].upper()
                if verb in {"BEGIN","COMMIT","ROLLBACK","SELECT","UPDATE"}:
                    with trace_lock:
                        trace_counts[verb]+=1
                        transaction_states[f"{verb}:{bool(dbapi.in_transaction)}"]+=1
                        if len(native_trace_sample)<256:
                            native_trace_sample.append(dict(time_ns=time.monotonic_ns(),connection=identity,thread=threading.get_ident(),verb=verb,native_in_transaction=bool(dbapi.in_transaction)))
            dbapi.set_trace_callback(trace)
        event.listen(engine,"connect",instrument)
        # Drop idle setup connections; every measurement checkout is traced.
        engine.dispose()
        measurements, cells, checkpoint_samples = [], [], []
        started=time.monotonic()
        origin_cpu=time.process_time()
        for reader_mode in ["short","select-await","explicit-snapshot"]:
            for writer_count in [1,4,8]:
                cell_started=time.monotonic()
                cell_deadline=cell_started+CELL_SECONDS
                stop=threading.Event()
                commits, transactions, errors, readers = [], [], [], []
                counters=Counter()
                data_lock=threading.Lock()
                def writer(identity):
                    iteration=0
                    while not stop.is_set():
                        due=time.monotonic()+0.1
                        transaction_started=time.perf_counter_ns()
                        try:
                            with Session(engine) as db:
                                row=(iteration*writer_count+identity)%500
                                if iteration%3:
                                    if iteration%5==0:
                                        db.execute(update(TorrentFileModel).where(TorrentFileModel.torrent_id==str(row)).values(last_used_at=stamp-datetime.timedelta(minutes=20)))
                                    TorrentFilesRepository(db).touch(TorrentFileIdentifier(indexer_id="fixture",torrent_id=str(row)))
                                else:
                                    body=(f"synthetic-{identity}-{iteration}:".encode()+b"x"*16384)[:16384]
                                    db.execute(update(TorrentFileModel).where(TorrentFileModel.torrent_id.in_([str(row),str((row+1)%500)])).values(torrent_bytes=body))
                                began=time.perf_counter_ns();db.commit();elapsed=(time.perf_counter_ns()-began)/1e6
                            with data_lock:
                                commits.append(elapsed)
                                transactions.append((time.perf_counter_ns()-transaction_started)/1e6)
                                counters["transactions"]+=1
                        except Exception as error:
                            with data_lock:errors.append(type(error).__name__)
                        iteration+=1
                        stop.wait(max(0,due-time.monotonic()))
                def reader():
                    durations=itertools.cycle([5,30,120])
                    while not stop.is_set():
                        hold=(1 if SMOKE else next(durations)) if reader_mode=="explicit-snapshot" else (1 if SMOKE else 5) if reader_mode=="select-await" else 0
                        if hold and time.monotonic()+hold>cell_deadline:
                            stop.wait(max(0,cell_deadline-time.monotonic()));break
                        began=time.monotonic()
                        try:
                            with Session(engine) as db:
                                if reader_mode=="explicit-snapshot":db.execute(text("BEGIN"))
                                db.scalars(select(TorrentFileModel.torrent_id).limit(20)).all()
                                raw=db.connection().connection.driver_connection
                                native_transaction=bool(raw.in_transaction)
                                if hold:stop.wait(hold)
                            with data_lock:readers.append(dict(hold_seconds=hold,observed_seconds=time.monotonic()-began,native_in_transaction_after_select=native_transaction))
                        except Exception as error:
                            with data_lock:errors.append(type(error).__name__)
                        stop.wait(0.1)
                workers=[threading.Thread(target=writer,args=(i,)) for i in range(writer_count)]+[threading.Thread(target=reader)]
                for worker in workers:worker.start()
                next_sample=cell_started
                next_diagnostic=cell_started+10
                next_progress=cell_started+60
                while time.monotonic()<cell_deadline:
                    now=time.monotonic()
                    wal=Path(str(db_path)+"-wal")
                    try:
                        with wal.open("rb") as stream:header=stream.read(32)
                        size=wal.stat().st_size
                    except FileNotFoundError:header=b"";size=0
                    measurements.append(dict(seconds=now-started,reader=reader_mode,writers=writer_count,wal_bytes=size,wal_header_sha256=hashlib.sha256(header).hexdigest()))
                    if now>=next_progress:
                        print(json.dumps(dict(progress_seconds=now-started,reader=reader_mode,writers=writer_count,wal_bytes=size,transactions=counters["transactions"],errors=len(errors))),file=sys.stderr,flush=True)
                        next_progress+=60
                    if DIAGNOSTIC and now>=next_diagnostic:
                        with sqlite3.connect(db_path,timeout=10) as diagnostic:
                            busy,log,checkpointed=diagnostic.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
                        checkpoint_samples.append(dict(seconds=time.monotonic()-started,reader=reader_mode,writers=writer_count,busy=busy,log=log,checkpointed=checkpointed))
                        next_diagnostic+=10
                    next_sample+=1
                    stop.wait(max(0,min(next_sample,cell_deadline)-time.monotonic()))
                stop.set()
                for worker in workers:worker.join()
                cells.append(dict(reader=reader_mode,writers=writer_count,elapsed_seconds=time.monotonic()-cell_started,commit_samples_ms=commits,transaction_samples_ms=transactions,transaction_p95_ms=percentile(transactions,.95),transaction_p99_ms=percentile(transactions,.99),commit_p50_ms=statistics.median(commits) if commits else None,commit_p95_ms=percentile(commits,.95),commit_p99_ms=percentile(commits,.99),errors=errors,counters=dict(counters),readers=readers))
        measured_seconds=time.monotonic()-started
        # Explicitly outside both measurement windows: all reader owners have
        # closed, then the next actual PASSIVE checkpoint can show progress.
        with sqlite3.connect(db_path,timeout=10) as final_connection:
            final_checkpoint=final_connection.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
        final_checkouts=engine.pool.checkedout()
        engine.dispose()
        print(json.dumps(dict(fixture="g02-smoke-only-not-measurement-v1" if SMOKE else "g02-file-db-touch-blob-wal-60min-v1",diagnostic_passive=DIAGNOSTIC,is_measurement=not SMOKE,duration_required_seconds=None if SMOKE else DURATION_SECONDS,measured_seconds=measured_seconds,sqlite_version=sqlite3.sqlite_version,pragmas=pragmas,blob_bytes=16384,write_target_interval_seconds=.1,cells=cells,wal_samples=measurements,checkpoint_samples=checkpoint_samples,final_checkpoint_after_all_readers_closed=final_checkpoint,final_checkouts=final_checkouts,trace_counts=dict(trace_counts),native_trace_sample=native_trace_sample,native_transaction_states=dict(transaction_states),connection_trace=connection_trace,cpu_seconds=time.process_time()-origin_cpu,scope="Disposable synthetic file DB; no native torrent restore, real user, tracker or production PRAGMA tuning. Explicit BEGIN is a stress control. Smoke validates wiring only and cannot satisfy the60minute gate.")))


main()
