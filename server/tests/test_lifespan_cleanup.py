import asyncio
import threading
from contextlib import suppress
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from app.common import singleflight
from app.common.sensitive_responses import SensitiveResponsePolicy
from app.exceptions import setup_exception_handlers
from app.modules.indexer_definitions.service import IndexerDefinitionsService

pytestmark = pytest.mark.anyio


async def test_one_adapter_close_failure_does_not_skip_other_adapters_or_log_its_text(caplog):
    marker = "synthetic-sensitive-close-marker"
    called = []

    async def first():
        called.append("first")
        raise RuntimeError(marker)

    async def second():
        called.append("second")

    async def third():
        called.append("third")

    service = object.__new__(IndexerDefinitionsService)
    service._definitions = cast(Any, {"first":SimpleNamespace(close=first), "second":SimpleNamespace(close=second), "third":SimpleNamespace(close=third)})
    assert await service.close_all() is False
    assert called == ["first", "second", "third"]
    assert "RuntimeError" in caplog.text
    assert marker not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


async def test_singleflight_close_latches_admission_and_awaits_shared_cleanup():
    registry = singleflight.Singleflight[int]()
    entered, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = 0

    async def factory():
        nonlocal calls
        calls += 1
        entered.set()
        try:
            await asyncio.Future()
        finally:
            cleaning.set()
            await release.wait()
        return 7

    owner = asyncio.create_task(registry.run("same", factory))
    joiner = asyncio.create_task(registry.run("same", factory))
    closing = None
    try:
        await asyncio.wait_for(entered.wait(), 1)
        closing = asyncio.create_task(registry.aclose())
        await asyncio.wait_for(cleaning.wait(), 1)
        assert registry.closed
        assert not closing.done()
        with pytest.raises(singleflight.SearchStoppingError):
            await registry.run("new", factory)
        assert calls == 1
        release.set()
        await asyncio.wait_for(closing, 1)
        assert not registry.is_running("same")
        results = await asyncio.gather(owner, joiner, return_exceptions=True)
        assert all(isinstance(value, asyncio.CancelledError) for value in results)
        await registry.aclose()
    finally:
        release.set()
        await registry.cancel_all()
        await asyncio.gather(owner, joiner, return_exceptions=True)
        if closing is not None:
            with suppress(asyncio.CancelledError):
                await closing


async def test_cancelling_a_close_waiter_does_not_abandon_the_shared_cleanup():
    registry = singleflight.Singleflight[None]()
    entered, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def factory():
        entered.set()
        try:
            await asyncio.Future()
        finally:
            cleaning.set()
            await release.wait()

    owner = asyncio.create_task(registry.run("one", factory))
    closing = None
    try:
        await asyncio.wait_for(entered.wait(), 1)
        closing = asyncio.create_task(registry.aclose())
        await asyncio.wait_for(cleaning.wait(), 1)
        closing.cancel()
        await asyncio.sleep(0)
        assert not closing.done()
        assert registry.closed
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await closing
        await registry.aclose()
        assert not registry.is_running("one")
    finally:
        release.set()
        await registry.cancel_all()
        await asyncio.gather(owner, return_exceptions=True)
        if closing is not None:
            with suppress(asyncio.CancelledError):
                await closing


async def test_cancel_all_remains_a_reusable_wave_operation_until_aclose():
    registry = singleflight.Singleflight[int]()

    async def result():
        return 11

    assert await registry.run("one", result) == 11
    await registry.cancel_all()
    assert not registry.closed
    assert await registry.run("two", result) == 11
    await registry.aclose()
    with pytest.raises(singleflight.SearchStoppingError):
        await registry.run("three", result)


async def test_owned_thread_cancellation_waits_for_real_completion_and_keeps_loop_live():
    from app.common.async_utils import owned_to_thread

    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    loop_thread = threading.get_ident()
    observed = []

    def worker():
        observed.append(threading.get_ident())
        entered.set()
        assert release.wait(2)
        finished.set()
        return 3

    owner = asyncio.create_task(owned_to_thread(worker))
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        owner.cancel()
        await asyncio.sleep(0)
        heartbeat = asyncio.Event()
        asyncio.get_running_loop().call_soon(heartbeat.set)
        await asyncio.wait_for(heartbeat.wait(), 1)
        assert not owner.done()
        assert not finished.is_set()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await owner
        assert finished.is_set()
        assert observed and observed[0] != loop_thread
    finally:
        release.set()
        await asyncio.gather(owner, return_exceptions=True)


async def test_owned_thread_preserves_each_callers_context_and_keyword_arguments():
    import contextvars

    from app.common.async_utils import owned_to_thread

    context = contextvars.ContextVar("fixture-owned-thread", default="root")
    barrier = threading.Barrier(2)

    def work(value: int, *, suffix: int):
        observed = context.get()
        assert barrier.wait(2) in (0, 1)
        context.set("worker-local")
        return observed, value + suffix

    context.set("first")
    first = asyncio.create_task(owned_to_thread(work, 2, suffix=3))
    context.set("second")
    second = asyncio.create_task(owned_to_thread(work, 7, suffix=4))
    context.set("root")
    assert await asyncio.gather(first, second) == [("first", 5), ("second", 11)]
    assert context.get() == "root"


async def test_cancelled_stream_preparation_keeps_its_lock_and_session_until_db_work_finishes(tmp_path):
    from app.modules.stream.service import StreamService, torrent_locks

    engine = create_engine(f"sqlite:///{tmp_path/'prepare.db'}",connect_args={"check_same_thread":False},hide_parameters=True)
    entered,release,finished = threading.Event(),threading.Event(),threading.Event()
    db = Session(engine)
    owner_closed,second_entered = [],asyncio.Event()

    def find(**kwargs):
        entered.set()
        assert release.wait(2)
        try:
            assert db.execute(text('SELECT 1')).scalar_one() == 1
            return None
        finally:
            finished.set()

    service = StreamService(
        torrents_service=cast(Any,SimpleNamespace(find_by_id=find)),
        torrent_files_service=cast(Any,None),indexers_service=cast(Any,None),relay_service=cast(Any,None),
        isolated_torrent_files_service=cast(Any,SimpleNamespace(touch=lambda _:None)),
    )

    async def owner():
        try:
            await service.prepare_for_stream(None,'fixture','same',0)
        finally:
            owner_closed.append(finished.is_set())
            db.close()

    async def second():
        async with torrent_locks('fixture:same'):
            second_entered.set()

    task = asyncio.create_task(owner())
    other = None
    try:
        assert await asyncio.to_thread(entered.wait,1)
        task.cancel()
        other = asyncio.create_task(second())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not task.done()
        assert not second_entered.is_set()
        assert owner_closed == []
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(other,1)
        assert owner_closed == [True]
        assert cast(QueuePool, engine.pool).checkedout() == 0
    finally:
        release.set()
        await asyncio.to_thread(finished.wait,2)
        await asyncio.gather(task,*([other] if other is not None else []),return_exceptions=True)
        db.close()
        engine.dispose()


async def test_cancelled_owned_worker_failure_is_consumed_without_replacing_cancellation(caplog):
    from app.common.async_utils import owned_to_thread

    entered, release = threading.Event(), threading.Event()
    marker = "synthetic-sensitive-worker-error"

    def work():
        entered.set()
        assert release.wait(2)
        raise RuntimeError(marker)

    task = asyncio.create_task(owned_to_thread(work))
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert "RuntimeError" in caplog.text
        assert marker not in caplog.text
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_search_stopping_maps_to_safe_503_and_sensitive_no_store():
    app = FastAPI()
    setup_exception_handlers(app)
    app.add_middleware(SensitiveResponsePolicy)
    marker = "synthetic-sensitive-stopping-marker"

    @app.get("/api/auth/stopping")
    async def stopping():
        raise singleflight.SearchStoppingError(marker)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid") as client:
        response = await client.get("/api/auth/stopping")
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    assert response.headers["Cache-Control"] == "no-store"
    assert marker not in response.text
    assert isinstance(response.json()["detail"], str)


async def test_producer_failure_is_partial_while_other_producers_are_still_awaited(caplog):
    from app.main import _cancel_producers

    stopped = []

    async def failed():
        raise RuntimeError("synthetic-sensitive-producer-marker")

    async def running():
        try:
            await asyncio.Future()
        finally:
            stopped.append(True)

    first, second = asyncio.create_task(failed()), asyncio.create_task(running())
    await asyncio.sleep(0)
    assert await _cancel_producers([first,second]) is False
    assert first.done() and second.done() and stopped == [True]
    assert "RuntimeError" in caplog.text
    assert "synthetic-sensitive-producer-marker" not in caplog.text


@pytest.mark.parametrize("cancel_close_waiter", [False, True])
async def test_scheduler_close_waits_for_sync_job_session_owner(tmp_path, cancel_close_waiter):
    from app import scheduler as scheduling

    engine = create_engine(f"sqlite:///{tmp_path/'scheduled.db'}", connect_args={"check_same_thread":False}, hide_parameters=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE fixture (value INTEGER)"))
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    lifecycle = []
    loop_thread = threading.get_ident()

    class OwnedSession(Session):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            lifecycle.append(("open",threading.get_ident()))

        def close(self):
            lifecycle.append(("close",threading.get_ident()))
            super().close()

    def work():
        with OwnedSession(engine) as db:
            db.execute(text("INSERT INTO fixture VALUES (1)"))
            entered.set()
            assert release.wait(2)
            db.commit()
        finished.set()

    scheduler = scheduling.ManagedScheduler()
    scheduler.add_owned_job(work, trigger="date", run_date=datetime.now(timezone.utc), id="fixture-job")
    scheduler.start()
    closing = None
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        closing = asyncio.create_task(scheduler.aclose())
        await asyncio.sleep(0)
        if cancel_close_waiter:
            closing.cancel()
            await asyncio.sleep(0)
        assert not closing.done()
        assert not finished.is_set()
        release.set()
        if cancel_close_waiter:
            with pytest.raises(asyncio.CancelledError):
                await closing
        else:
            await closing
        await scheduler.aclose()
        assert finished.is_set()
        assert not scheduler.running
        assert scheduler.active_jobs == 0
        assert [kind for kind,_ in lifecycle] == ["open","close"]
        assert all(thread != loop_thread for _,thread in lifecycle)
        assert lifecycle[0][1] == lifecycle[1][1]
        with Session(engine) as db:
            assert db.execute(text("SELECT COUNT(*) FROM fixture")).scalar_one() == 1
    finally:
        release.set()
        await scheduler.aclose()
        if closing is not None:
            with suppress(asyncio.CancelledError):
                await closing
        engine.dispose()


async def test_scheduled_error_is_reported_without_remote_exception_text(caplog):
    from apscheduler.events import EVENT_JOB_ERROR

    from app import scheduler as scheduling

    marker = "synthetic-sensitive-scheduled-error"
    handled = asyncio.Event()

    def bad():
        raise RuntimeError(marker)

    scheduler = scheduling.ManagedScheduler()
    scheduler.add_listener(lambda _:handled.set(), EVENT_JOB_ERROR)
    scheduler.add_owned_job(bad, trigger="date", run_date=datetime.now(timezone.utc), id="fixture-job")
    scheduler.start()
    try:
        await asyncio.wait_for(handled.wait(), 2)
    finally:
        await scheduler.aclose()
    assert marker not in caplog.text
    assert "RuntimeError" in caplog.text
    assert scheduler.active_jobs == 0


@pytest.fixture
def lifecycle_harness(monkeypatch):
    from functools import lru_cache
    from unittest.mock import AsyncMock

    from fastapi.middleware.cors import CORSMiddleware

    from app import main
    from app.common.lifecycle import StoppingPolicy
    from app.modules.relay.service import ResumeSaveResult
    from app.modules.stremio import service as streams
    from app.modules.torrent_source_provider import service as sources
    from app.modules.torrents import background_tasks
    from app.modules.torrents.resume_writer import ResumeWriter
    from app.scheduler import ManagedScheduler

    events, relays, adapters, saved = [], [], [], {}
    close_entered, close_release = asyncio.Event(), asyncio.Event()
    close_release.set()
    faults = set()

    class Relay:
        def __init__(self):
            self.on_save_resume = []
            self.closed = False
            relays.append(self)

        async def priority_manager_loop(self):
            try:
                await asyncio.Future()
            finally:
                events.append("priority-stopped")

        def stop_admission(self):
            events.append("relay-stopping")

        async def close_piece_requests(self):
            events.append("pieces-closed")

        async def save_final_resume(self):
            events.append("final-snapshot")
            for callback in self.on_save_resume:
                assert callback("fixture", b"last state") is True
            if "native" in faults:
                return ResumeSaveResult(2, 1, 0, 1)
            return ResumeSaveResult(1, 1, 0, 0)

        async def close_native(self):
            assert not self.on_save_resume
            self.closed = True
            events.append("native-closed")

    class Adapters:
        def __init__(self):
            self.closed = False
            adapters.append(self)

        def stop_admission(self):
            events.append("adapters-stopping")

        async def close_logins(self):
            events.append("logins-stopped")

        async def close_all(self):
            close_entered.set()
            await close_release.wait()
            events.append("http-closed")
            self.closed = True
            if "adapter" in faults:
                raise RuntimeError("synthetic-sensitive-lifecycle-marker")
            return True

    @lru_cache(maxsize=1)
    def relay_factory():
        return Relay()

    @lru_cache(maxsize=1)
    def adapters_factory():
        return Adapters()

    async def producer():
        try:
            await asyncio.Future()
        finally:
            events.append("resume-producer-stopped")

    def sync(app):
        if "startup" in faults:
            raise RuntimeError("synthetic startup failure")

    monkeypatch.setattr(main, "get_relay_service", relay_factory)
    monkeypatch.setattr(background_tasks, "get_relay_service", relay_factory)
    monkeypatch.setattr(main, "get_indexer_definitions_service", adapters_factory)
    monkeypatch.setattr(main, "sync_database_and_settings", sync)
    monkeypatch.setattr(main, "initialize_bootstrap_state", lambda:None)
    monkeypatch.setattr(main, "restore_torrents", lambda:None)
    monkeypatch.setattr(main, "ResumeWriter", lambda:ResumeWriter(lambda batch:saved.update((item.info_hash,item.data) for item in batch)))
    monkeypatch.setattr(main, "setup_scheduler", ManagedScheduler)
    monkeypatch.setattr(main, "resume_save_loop", producer)
    monkeypatch.setattr(main, "tvdb_resolver", SimpleNamespace(aclose=AsyncMock()))
    monkeypatch.setattr(main, "close_network_setup", AsyncMock())
    monkeypatch.setattr(main.config, "reverse_proxy_domain", "fixture.invalid")
    monkeypatch.setattr(main, "clear_active_playbacks", lambda:None)
    monkeypatch.setattr(main, "invalidate_indexer_cache", lambda:None)
    for module, names in [(streams,["_stream_singleflight"]),(sources,["_sources_singleflight","_single_source_singleflight","_torrent_download_singleflight"])]:
        for name in names:
            monkeypatch.setattr(module, name, singleflight.Singleflight())
    app = FastAPI()
    app.add_middleware(StoppingPolicy)
    app.add_middleware(CORSMiddleware, allow_origins=["*"])
    requests = []

    @app.get("/fixture")
    async def endpoint():
        requests.append(1)
        return {"ready": True}

    return SimpleNamespace(app=app, lifespan=main.lifespan, events=events, relays=relays, adapters=adapters, saved=saved, faults=faults, close_entered=close_entered, close_release=close_release, requests=requests, relay_factory=relay_factory, adapters_factory=adapters_factory)


async def test_repeated_lifespan_gets_fresh_resources_and_stopping_requests_cannot_recreate_them(lifecycle_harness):
    fixture = lifecycle_harness
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=fixture.app),base_url="https://fixture.invalid") as client:
        for _ in range(2):
            async with fixture.lifespan(fixture.app):
                assert (await client.get("/fixture")).status_code == 200
                assert not fixture.relays[-1].closed
                assert not fixture.adapters[-1].closed
                assert len(fixture.relays[-1].on_save_resume) == 1
            assert fixture.app.state.shutdown_result["complete"]
            assert fixture.relays[-1].closed and fixture.adapters[-1].closed
            assert fixture.relays[-1].on_save_resume == []
            assert fixture.relay_factory.cache_info().currsize == fixture.adapters_factory.cache_info().currsize == 0
            denied = await client.get("/fixture",headers={"Origin":"https://another.invalid"})
            assert denied.status_code == 503
            assert denied.headers["Cache-Control"] == "no-store"
            assert denied.headers["Retry-After"] == "1"
            assert denied.headers["Access-Control-Allow-Origin"] == "*"
    assert fixture.saved == {"fixture":b"last state"}
    assert len(fixture.requests) == 2
    assert fixture.relays[0] is not fixture.relays[1]
    assert fixture.adapters[0] is not fixture.adapters[1]
    assert fixture.events.count("priority-stopped") == fixture.events.count("resume-producer-stopped") == 2


async def test_startup_failure_closes_already_acquired_resources(lifecycle_harness):
    fixture = lifecycle_harness
    fixture.faults.add("startup")
    with pytest.raises(RuntimeError,match="synthetic startup failure"):
        async with fixture.lifespan(fixture.app):
            pytest.fail("Startup must not yield")
    assert fixture.app.state.stopping
    assert fixture.app.state.shutdown_result["complete"]
    assert fixture.relays[0].closed and fixture.adapters[0].closed
    assert fixture.relay_factory.cache_info().currsize == fixture.adapters_factory.cache_info().currsize == 0


async def test_adapter_failure_keeps_all_later_cleanup_stages_and_reports_partial(lifecycle_harness, caplog):
    fixture = lifecycle_harness
    fixture.faults.add("adapter")
    async with fixture.lifespan(fixture.app):
        await asyncio.sleep(0)
    assert fixture.relays[0].closed
    assert fixture.saved == {"fixture":b"last state"}
    assert fixture.app.state.shutdown_result["failed_stages"] == ["indexer-http"]
    assert not fixture.app.state.shutdown_result["complete"]
    assert "synthetic-sensitive-lifecycle-marker" not in caplog.text
    assert fixture.events.index("final-snapshot") < fixture.events.index("http-closed") < fixture.events.index("native-closed")


async def test_final_snapshot_deadline_is_reported_while_accepted_data_still_drains(lifecycle_harness, caplog):
    fixture = lifecycle_harness
    fixture.faults.add("native")
    async with fixture.lifespan(fixture.app):
        await asyncio.sleep(0)
    report = fixture.app.state.shutdown_result
    assert not report["complete"]
    assert report["failed_stages"] == ["final-resume"]
    assert report["final_resume"] == {"requested":2,"accepted":1,"failed":0,"timed_out":1}
    assert report["resume_completed"] == 1
    assert fixture.saved == {"fixture":b"last state"}
    assert fixture.relays[0].closed
    assert "timed_out=1" in caplog.text


async def test_cancelled_lifespan_owner_waits_for_remaining_cleanup(lifecycle_harness):
    fixture = lifecycle_harness
    fixture.close_release.clear()

    async def owner():
        async with fixture.lifespan(fixture.app):
            await asyncio.sleep(0)

    task = asyncio.create_task(owner())
    try:
        await asyncio.wait_for(fixture.close_entered.wait(), 1)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert fixture.app.state.stopping
        assert not fixture.relays[0].closed
        fixture.close_release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert fixture.relays[0].closed
        assert fixture.app.state.shutdown_result["complete"]
        assert fixture.saved == {"fixture":b"last state"}
    finally:
        fixture.close_release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_background_cleanup_is_drained_without_treating_waiter_cancel_as_worker_stop(monkeypatch):
    from app.common import async_utils

    pending = set()
    monkeypatch.setattr(async_utils, "_background_tasks", pending)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def worker():
        entered.set()
        assert release.wait(2)
        finished.set()

    async_utils.fire_and_forget(async_utils.owned_to_thread(worker))
    assert await asyncio.to_thread(entered.wait, 1)
    closing = asyncio.create_task(async_utils.drain_background_tasks())
    try:
        closing.cancel()
        # Cancellation before the coroutine starts has no owned work to join;
        # use a second, started waiter to exercise the real drain boundary.
        await asyncio.gather(closing, return_exceptions=True)
        closing = asyncio.create_task(async_utils.drain_background_tasks())
        await asyncio.sleep(0)
        closing.cancel()
        await asyncio.sleep(0)
        assert not closing.done()
        assert pending and not finished.is_set()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await closing
        assert finished.is_set() and not pending
    finally:
        release.set()
        await async_utils.drain_background_tasks()
        await asyncio.gather(closing, return_exceptions=True)


async def test_network_restart_is_one_owned_task_and_stops_with_network_setup(monkeypatch):
    from app.modules.network import service as network

    entered = asyncio.Event()
    finished = []
    calls = 0

    async def restart():
        nonlocal calls
        calls += 1
        entered.set()
        try:
            await asyncio.Future()
        finally:
            finished.append(True)

    monkeypatch.setattr(network, "_restart_task", None)
    monkeypatch.setattr(network, "_active_setup_task", None)
    service = object.__new__(network.NetworkService)
    service._system_service = cast(Any, SimpleNamespace(restart=restart))
    service._schedule_restart()
    await asyncio.wait_for(entered.wait(), 1)
    service._schedule_restart()
    try:
        await network.close_network_setup()
        assert calls == 1 and finished == [True]
        assert network._restart_task is None
        await network.close_network_setup()
    finally:
        await network.close_network_setup()
