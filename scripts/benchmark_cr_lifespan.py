"""CR17 cleanup baseline, synthetic DB and no external network.

Full heap profile is30 real minutes after a separate warmup. A40s smoke is
wiring validation only. Four finite shared tasks and a real owned DB worker
cross shutdown; they are controlled stimuli, not a production leak claim.
Raw per-cycle data is streamed to an owned output directory so the probe does
not retain all response/sample arrays in the measured Python heap.
"""

import asyncio
import gc
import json
import resource
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc
import weakref
from pathlib import Path
from types import SimpleNamespace

import httpx
import libtorrent
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app import main as application
from app.boot.settings import ensure_default_settings
from app.common import database
from app.config import config
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.relay.dependencies import get_relay_service
from app.modules.roles.models import RoleModel
from app.modules.settings.models import SettingModel
from app.modules.stremio import service as streams
from app.modules.torrent_source_provider import service as sources


SMOKE = "--fixture-smoke" in sys.argv
DURATION = 40 if SMOKE else 1800
INTERVAL = 20 if SMOKE else 30
SHARED_SECONDS = 3 if SMOKE else 15
OUTPUT = Path("/fixture-output")


def p95(values):
    return sorted(values)[int((len(values)-1)*.95)]


def controlled_retainers(registries):
    records=[]
    for index,registry in enumerate(registries):
        for task in tuple(registry._tasks.values()):
            frame=getattr(task.get_coro(),"cr_frame",None)
            body=frame.f_locals.get("body") if frame is not None else None
            if isinstance(body,bytes):
                records.append(dict(registry=index,payload_bytes=len(body),chain="module registry -> Singleflight._tasks -> Task coroutine frame -> controlled body bytes"))
    return records


async def main():
    if not OUTPUT.is_dir():
        raise RuntimeError("An owned fixture output directory is required")
    rows_file = OUTPUT/"lifespan-rows.jsonl"
    if rows_file.exists():
        raise RuntimeError("Refusing to overwrite an earlier lifecycle profile")
    statements = 0
    attempted_external = 0
    original_send = httpx.AsyncClient.send

    async def offline_send(client, request, *args, **kwargs):
        nonlocal attempted_external
        if request.url.host != "fixture.invalid":
            attempted_external += 1
            raise RuntimeError("Offline lifecycle fixture blocked external HTTP")
        return await original_send(client, request, *args, **kwargs)

    httpx.AsyncClient.send = offline_send
    config.reverse_proxy_domain = "fixture.invalid"
    # No torrents from disk or live accounts enter this lifetime experiment.
    # Real non-empty native save acknowledgements are a separate native probe.
    application.restore_torrents = lambda: None
    previous_relay = previous_definitions = None
    with tempfile.TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory)/'lifespan.db'}", connect_args={"check_same_thread":False,"timeout":10}, hide_parameters=True)
        database.Base.metadata.create_all(engine)
        database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
        ensure_default_settings()

        def sql(*args):
            nonlocal statements
            statements += 1

        event.listen(engine, "before_cursor_execute", sql)

        async def cycle(index):
            nonlocal previous_relay, previous_definitions
            opened = time.perf_counter()
            entered, finished = threading.Event(), threading.Event()
            relay = definitions = None
            identity = "e"*40
            native_identity = libtorrent.sha1_hash(bytes.fromhex(identity))
            responses = []
            errors = []

            def priority_worker():
                try:
                    with Session(engine) as db:
                        db.scalars(select(SettingModel.key)).all()
                        entered.set()
                        # Controlled real worker: cancellation must not be
                        # mistaken for its completion or Session close.
                        threading.Event().wait(2)
                finally:
                    finished.set()

            async with application.lifespan(application.app):
                startup_seconds = time.perf_counter()-opened
                with Session(engine) as ready:
                    role_ids=set(ready.scalars(select(RoleModel.id)).all())
                    setting_keys=set(ready.scalars(select(SettingModel.key)).all())
                if not {"admin","user"}.issubset(role_ids) or not {"system","relay"}.issubset(setting_keys):
                    raise RuntimeError("Synthetic startup DB readiness failed")
                relay = get_relay_service()
                definitions = get_indexer_definitions_service()
                relay_reused = previous_relay is not None and previous_relay() is relay
                definitions_reused = previous_definitions is not None and previous_definitions() is definitions
                previous_relay, previous_definitions = weakref.ref(relay), weakref.ref(definitions)
                adapters = definitions.get_list()
                active_adapter_count = len(adapters)
                resume_callbacks_at_start = len(relay.on_save_resume)
                closed_clients_at_start = sum(adapter._client.is_closed for adapter in adapters)
                registries = [streams._stream_singleflight,sources._sources_singleflight,sources._single_source_singleflight,sources._torrent_download_singleflight]
                waiters = []
                for number, registry in enumerate(registries):
                    payload = bytes([number])*262144

                    async def pending(body=payload, ordinal=number):
                        task = asyncio.current_task()
                        if task is not None:task.set_name(f"cr-fixture-shared-{ordinal}")
                        await asyncio.sleep(SHARED_SECONDS)
                        assert len(body)==262144
                        return [] if ordinal==0 else ([],[]) if ordinal==1 else None

                    waiters.append(asyncio.create_task(registry.run(f"fixture-{index}-{number}",pending)))
                del payload,pending
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                for waiter in waiters:waiter.cancel()
                await asyncio.gather(*waiters,return_exceptions=True)
                waiters.clear()

                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app),base_url="https://fixture.invalid") as client:
                    concurrency = [1,4,8][index%3]
                    semaphore = asyncio.Semaphore(concurrency)
                    sql_before, cpu_before = statements,time.process_time()

                    async def request(path, expected):
                        async with semaphore:
                            began=time.perf_counter_ns()
                            result=await client.get(path)
                            if result.status_code!=expected:errors.append(result.status_code)
                            return (time.perf_counter_ns()-began)/1e6

                    for path,status in [("/api/health",200),("/api/fixture-invalid/stremio/manifest.json",401)]:
                        values=await asyncio.gather(*(request(path,status) for _ in range(100)))
                        responses.append(dict(expected_status=status,samples_ms=values,p95_ms=p95(values)))
                    request_cpu=time.process_time()-cpu_before
                    request_sql=statements-sql_before

                relay._torrents[native_identity] = SimpleNamespace(priority_manager=priority_worker)
                relay.priority_update_queue.put_nowait(identity)
                deadline=asyncio.get_running_loop().time()+3
                while not entered.is_set():
                    if asyncio.get_running_loop().time()>=deadline:raise TimeoutError("Priority worker did not start")
                    await asyncio.sleep(.01)
                shutdown_started=time.perf_counter()
            shutdown_seconds=time.perf_counter()-shutdown_started
            worker_finished_at_close=finished.is_set()
            shared_at_close=sum(len(registry._tasks) for registry in registries)
            retainers_at_close=controlled_retainers(registries)
            resume_callbacks_after = len(relay.on_save_resume)
            closed_clients_after=sum(adapter._client.is_closed for adapter in adapters)
            gc.collect()
            heap_at_close=tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else None
            deadline=asyncio.get_running_loop().time()+5
            while not finished.is_set():
                if asyncio.get_running_loop().time()>=deadline:raise TimeoutError("Owned DB worker did not finish")
                await asyncio.sleep(.01)
            getattr(relay,"_torrents",{}).pop(native_identity,None)
            # Original finite shared work is allowed to finish naturally for
            # the quiescent sample. The immediate-close count above is retained.
            deadline=asyncio.get_running_loop().time()+SHARED_SECONDS+2
            while any(registry._tasks for registry in registries):
                if asyncio.get_running_loop().time()>=deadline:raise TimeoutError("Finite fixture searches did not finish")
                await asyncio.sleep(.02)
            del adapters,relay,definitions,registries
            gc.collect()
            return dict(cycle=index,startup_seconds=startup_seconds,shutdown_seconds=shutdown_seconds,concurrency=concurrency,http=responses,http_cpu_seconds=request_cpu,sql_statements=request_sql,errors=errors,worker_finished_at_close=worker_finished_at_close,shared_tasks_at_close=shared_at_close,controlled_retainers_at_close=retainers_at_close,active_adapter_count=active_adapter_count,closed_clients_at_start=closed_clients_at_start,closed_clients_after=closed_clients_after,resume_callbacks_at_start=resume_callbacks_at_start,resume_callbacks_after=resume_callbacks_after,relay_reused=relay_reused,definitions_reused=definitions_reused,heap_bytes_at_close=heap_at_close,heap_bytes_quiescent=tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else None,python_tasks_quiescent=len(asyncio.all_tasks()),pool_checked_out_quiescent=engine.pool.checkedout(),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,external_http_attempts=attempted_external)

        cold = None
        tracemalloc.start()
        if not SMOKE:
            cold = await cycle(-1)
        tracemalloc.reset_peak()
        started=time.monotonic()
        index=0
        with rows_file.open("x",encoding="utf-8") as output:
            while time.monotonic()-started<DURATION:
                row=await cycle(index)
                row["elapsed_seconds"]=time.monotonic()-started
                output.write(json.dumps(row)+"\n");output.flush()
                print(json.dumps(dict(progress_seconds=row["elapsed_seconds"],cycle=index,shared_at_close=row["shared_tasks_at_close"],worker_finished_at_close=row["worker_finished_at_close"],pool_quiescent=row["pool_checked_out_quiescent"],errors=len(row["errors"]))),file=sys.stderr,flush=True)
                del row
                index+=1
                remaining=min(started+index*INTERVAL,started+DURATION)-time.monotonic()
                if remaining>0:await asyncio.sleep(remaining)
        measured_seconds=time.monotonic()-started
        tracemalloc.stop()
        # Teardown of task-owned synthetic resources is outside the window.
        definitions=previous_definitions() if previous_definitions is not None else None
        if definitions is not None:await definitions.close_all()
        relay=previous_relay() if previous_relay is not None else None
        native=getattr(relay,"_libtorrent_session",None)
        if native is not None:
            native.set_alert_notify(lambda:None)
            native.pause()
        get_indexer_definitions_service.cache_clear()
        get_relay_service.cache_clear()
        del native,relay,definitions
        gc.collect()
        final_checkouts=engine.pool.checkedout()
        engine.dispose()
    httpx.AsyncClient.send=original_send
    print(json.dumps(dict(fixture="cr17-lifespan-smoke-not-measurement-v1" if SMOKE else "cr17-lifespan-finite-work-30min-v1",is_measurement=not SMOKE,required_seconds=None if SMOKE else 1800,measured_seconds=measured_seconds,cold=cold,rows=[json.loads(line) for line in rows_file.read_text().splitlines()],final_checkouts=final_checkouts,external_http_attempts=attempted_external,scope="Real application lifespan, synthetic fileDB, no persisted/native torrent restore. Finite injected shared tasks and a2s priority DB worker cross shutdown. No production memory-leak claim. Raw arrays streamed outside measured heap; quiescent GC and immediate-close samples separate.")))


asyncio.run(main())
