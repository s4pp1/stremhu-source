import asyncio
import datetime
import gc
import threading
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.common import database
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrents import background_tasks
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.resume_writer import ResumeEnvelope, ResumeWriter

pytestmark = pytest.mark.anyio


async def thread_ready(event):
    assert await asyncio.to_thread(event.wait, 2)


async def test_burst_keeps_latest_state_and_writes_bounded_batches_off_loop():
    saved, sizes, threads = {}, [], []
    loop_thread = threading.get_ident()

    def save(batch):
        sizes.append(len(batch))
        threads.append(threading.get_ident())
        saved.update((item.info_hash, item.data) for item in batch)

    writer = ResumeWriter(save, batch_size=2)
    writer.start()
    writer.start()
    for value in range(100):
        assert writer.submit("one", str(value).encode())
    for value in range(5):
        assert writer.submit(str(value), b"final")
    assert await writer.flush_and_close()
    assert saved == {"one":b"99", **{str(value):b"final" for value in range(5)}}
    assert max(sizes) <= 2
    assert all(worker != loop_thread for worker in threads)
    assert writer.stats.coalesced == 99
    assert writer.stats.leased_bytes == writer.stats.distinct_hashes == 0
    assert writer.stats.pending == writer.stats.in_flight == 0
    assert await writer.flush_and_close()
    assert not writer.submit("closed", b"ignored")
    assert await writer.flush_and_close()  # same completed close result


async def test_capacity_counts_inflight_bytes_and_distinct_hashes():
    entered, release = threading.Event(), threading.Event()
    saved = {}

    def save(batch):
        entered.set()
        assert release.wait(2)
        saved.update((item.info_hash, item.data) for item in batch)

    writer = ResumeWriter(save, max_bytes=5, max_hashes=2, batch_size=1)
    writer.start()
    assert writer.submit("one", b"aaa")
    await thread_ready(entered)
    try:
        assert writer.stats.in_flight == 1
        assert writer.submit("two", b"bb")
        assert not writer.submit("three", b"")  # hash cap, despite zero bytes
        assert not writer.submit("two", b"bbb")  # old pending remains intact
        assert writer.stats.leased_bytes == 5
        assert writer.stats.distinct_hashes == 2
    finally:
        release.set()
    assert not await writer.flush_and_close()  # explicit admission failures
    assert saved == {"one":b"aaa", "two":b"bb"}
    assert writer.stats.rejected == 2
    assert writer.stats.peak_bytes == 5
    assert writer.stats.peak_hashes == 2
    assert writer.stats.leased_bytes == writer.stats.distinct_hashes == 0


async def test_newer_pending_update_survives_old_failed_inflight_retry():
    entered, release = threading.Event(), threading.Event()
    calls, saved = [], {}

    def save(batch):
        calls.append(tuple(item.data for item in batch))
        if len(calls) == 1:
            entered.set()
            assert release.wait(2)
            raise RuntimeError("synthetic sensitive write failure")
        saved.update((item.info_hash, item.data) for item in batch)

    writer = ResumeWriter(save, retry_delay=0)
    writer.start()
    assert writer.submit("one", b"old")
    await thread_ready(entered)
    try:
        assert writer.submit("one", b"new")
        assert writer.stats.distinct_hashes == 1
        assert writer.stats.leased_bytes == 6
    finally:
        release.set()
    assert await writer.flush_and_close()
    assert calls == [(b"old",), (b"new",)]
    assert saved == {"one":b"new"}
    assert writer.stats.superseded_retries == 1
    assert writer.stats.leased_bytes == writer.stats.distinct_hashes == 0


@pytest.mark.parametrize("permanent", [False, True])
async def test_write_failure_has_one_retry_and_safe_visible_result(permanent, caplog):
    calls = 0
    marker = "synthetic-sensitive-resume-error"

    def save(batch):
        nonlocal calls
        calls += 1
        if permanent or calls == 1:
            raise RuntimeError(marker)

    writer = ResumeWriter(save, retry_delay=0)
    writer.start()
    assert writer.submit("synthetic-sensitive-hash", b"synthetic-private-body")
    assert await writer.flush_and_close() is (not permanent)
    assert calls == 2
    assert writer.stats.retry_batches == 1
    assert writer.stats.failed == int(permanent)
    assert writer.stats.leased_bytes == writer.stats.distinct_hashes == 0
    assert marker not in caplog.text
    assert "synthetic-sensitive-hash" not in caplog.text
    assert "synthetic-private-body" not in caplog.text


async def test_cancelling_close_waits_for_real_thread_completion_and_drain():
    entered, release = threading.Event(), threading.Event()
    saved = {}

    def save(batch):
        entered.set()
        assert release.wait(2)
        saved.update((item.info_hash, item.data) for item in batch)

    writer = ResumeWriter(save, batch_size=1)
    writer.start()
    assert writer.submit("one", b"one")
    await thread_ready(entered)
    assert writer.submit("two", b"two")
    closing = asyncio.create_task(writer.flush_and_close())
    await asyncio.sleep(0)
    closing.cancel()
    await asyncio.sleep(0)
    try:
        assert not closing.done()
        heartbeat = asyncio.Event()
        asyncio.get_running_loop().call_soon(heartbeat.set)
        await asyncio.wait_for(heartbeat.wait(), 1)
        assert not closing.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert await writer.flush_and_close()
    assert saved == {"one":b"one", "two":b"two"}
    assert writer.stats.leased_bytes == writer.stats.distinct_hashes == 0


async def test_not_started_oversized_and_wrong_thread_admission_are_explicit():
    writer = ResumeWriter(lambda batch:None, max_bytes=2)
    assert not writer.submit("early", b"x")
    writer.start()
    assert not writer.submit("large", b"xxx")
    with pytest.raises(RuntimeError):
        await asyncio.to_thread(writer.submit, "wrong-thread", b"x")
    assert not await writer.flush_and_close()
    assert writer.stats.accepted == 0
    assert writer.stats.rejected == 2
    assert writer.stats.leased_bytes == writer.stats.distinct_hashes == 0


async def test_idle_worker_releases_completed_payloads_before_close():
    writer = ResumeWriter(lambda batch:None)
    writer.start()
    assert writer.submit("one", b"synthetic-large-resume" * 1000)
    try:
        async with asyncio.timeout(2):
            while writer.stats.pending or writer.stats.in_flight:
                await asyncio.sleep(0)
        gc.collect()
        assert sum(isinstance(item, ResumeEnvelope) for item in gc.get_objects()) == 0
    finally:
        assert await writer.flush_and_close()


@pytest.fixture
def resume_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'resume.db'}", connect_args={"check_same_thread":False}, hide_parameters=True)
    database.Base.metadata.create_all(engine)
    stamp = datetime.datetime(2026, 1, 1)
    with Session(engine) as db:
        for indexer in ["one","two"]:
            db.add(IndexerDefinitionModel(id=indexer, name="Synthetic", url="https://fixture.invalid", details_path="details"))
        db.flush()
        db.add_all([IndexerAccountModel(indexer_id=indexer, username="synthetic", password="synthetic") for indexer in ["one","two"]])
        db.flush()
        db.execute(insert(TorrentFileModel), [dict(indexer_id=indexer, torrent_id="1", info_hash="a"*40, torrent_bytes=b"synthetic fixture", created_at=stamp, last_used_at=stamp) for indexer in ["one","two"]])
        db.add_all([TorrentModel(info_hash="a"*40, indexer_id=indexer, torrent_id="1") for indexer in ["one","two"]])
        db.commit()
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    try:
        yield engine
    finally:
        engine.dispose()


async def test_real_batch_owns_its_session_rolls_back_and_keeps_first_hash_match(resume_engine, monkeypatch):
    lifecycle, threads = [], []
    loop_thread = threading.get_ident()
    attempts = 0

    class TrackedSession(Session):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            lifecycle.append((id(self),"open",threading.get_ident()))

        def close(self):
            lifecycle.append((id(self),"close",threading.get_ident()))
            super().close()

    def first_commit_fails(db):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            with Session(resume_engine) as independent:
                assert all(value is None for value in independent.scalars(select(TorrentModel.resume_bytes)))
            raise RuntimeError("synthetic transaction failure")

    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=resume_engine, class_=TrackedSession, autoflush=False))
    with Session(resume_engine) as request_session:
        expected = TorrentRepository(request_session).find_by_info_hash("a"*40)
        assert expected is not None
        first_indexer = expected.indexer_id
        request_session.rollback()
        event.listen(TrackedSession, "before_commit", first_commit_fails)
        event.listen(resume_engine, "before_cursor_execute", lambda *args:threads.append(threading.get_ident()))
        writer = ResumeWriter(retry_delay=0)
        writer.start()
        assert writer.submit("a"*40, b"latest synthetic resume")
        assert writer.submit("missing", b"do not resurrect deleted torrents")
        assert await writer.flush_and_close()
    event.remove(TrackedSession, "before_commit", first_commit_fails)
    assert attempts == 2
    assert lifecycle and all(identity != loop_thread for _, _, identity in lifecycle)
    assert all(identity != loop_thread for identity in threads)
    assert [kind for _,kind,_ in lifecycle] == ["open","close","open","close"]
    with Session(resume_engine) as db:
        states = {row.indexer_id:row.resume_bytes for row in db.scalars(select(TorrentModel))}
        assert states[first_indexer] == b"latest synthetic resume"
        assert list(states.values()).count(None) == 1
        assert len(states) == 2


async def test_callback_registration_is_removable_and_lifespan_does_not_duplicate(monkeypatch):
    relay = SimpleNamespace(on_save_resume=[])
    monkeypatch.setattr(background_tasks, "get_relay_service", lambda:relay)
    saved = {}
    for _ in range(2):
        writer = ResumeWriter(lambda batch:saved.update((item.info_hash,item.data) for item in batch))
        writer.start()
        unregister = background_tasks.register_persisted_torrents_callbacks(writer)
        again = background_tasks.register_persisted_torrents_callbacks(writer)
        assert len(relay.on_save_resume) == 1
        assert relay.on_save_resume[0]("one", b"latest")
        unregister()
        again()
        assert relay.on_save_resume == []
        assert await writer.flush_and_close()
    assert saved == {"one":b"latest"}


@pytest.mark.parametrize("fault", ["startup", "cleanup"])
async def test_lifespan_always_unregisters_and_drains_its_writer(monkeypatch, fault):
    from contextlib import nullcontext
    from functools import lru_cache
    from unittest.mock import AsyncMock

    from fastapi import FastAPI

    producers, writers, saved = [], [], {}

    async def producer():
        task = asyncio.current_task()
        assert task is not None
        producers.append(task)
        await asyncio.Future()

    async def close():
        return None

    async def fail_cleanup():
        raise RuntimeError("synthetic legacy cleanup failure")

    def restore():
        if fault == "startup":
            raise RuntimeError("synthetic startup failure")

    def writer_factory():
        writer = ResumeWriter(lambda batch:saved.update((item.info_hash,item.data) for item in batch))
        writers.append(writer)
        return writer

    relay = SimpleNamespace(on_save_resume=[], priority_manager_loop=producer, stop_admission=lambda:None, close_piece_requests=close, save_final_resume=close, close_native=close)
    @lru_cache
    def relay_factory():
        return relay

    @lru_cache
    def definitions_factory():
        return SimpleNamespace(stop_admission=lambda:None, close_logins=close, close_all=fail_cleanup)

    monkeypatch.setattr(main, "sync_database_and_settings", lambda app:None)
    monkeypatch.setattr(main, "initialize_bootstrap_state", lambda:None)
    monkeypatch.setattr(main, "resume_save_loop", producer)
    monkeypatch.setattr(main, "setup_scheduler", lambda:SimpleNamespace(start=lambda:None, stop_admission=lambda:None, aclose=close))
    monkeypatch.setattr(main, "get_relay_service", relay_factory)
    monkeypatch.setattr(background_tasks, "get_relay_service", relay_factory)
    monkeypatch.setattr(main, "restore_torrents", restore)
    monkeypatch.setattr(main, "ResumeWriter", writer_factory)
    monkeypatch.setattr(main.config, "reverse_proxy_domain", "fixture.invalid")
    monkeypatch.setattr(main, "get_indexer_definitions_service", definitions_factory)
    monkeypatch.setattr(main, "tvdb_resolver", SimpleNamespace(aclose=close))
    for name in ["open_stream_searches","open_source_searches","invalidate_stream_cache","invalidate_indexer_cache","clear_active_playbacks"]:
        monkeypatch.setattr(main, name, lambda:None)
    for name in ["close_stream_searches","close_source_searches","close_network_setup"]:
        monkeypatch.setattr(main, name, AsyncMock())
    app = FastAPI()
    with pytest.raises(RuntimeError, match="synthetic startup failure") if fault == "startup" else nullcontext():
        async with main.lifespan(app):
            assert relay.on_save_resume[0]("one", b"latest")
            await asyncio.sleep(0)
    assert relay.on_save_resume == []
    assert writers[0].stats.leased_bytes == writers[0].stats.distinct_hashes == 0
    assert await writers[0].flush_and_close()
    assert all(task.done() for task in producers)
    assert app.state.shutdown_result["failed_stages"] == ["indexer-http"]
    assert not app.state.shutdown_result["complete"]
    if fault == "cleanup":
        assert saved == {"one":b"latest"}
