"""CR15/c: bounded admission, bounded download/batch work and the overall search deadline."""

import asyncio
import threading
import time
from types import SimpleNamespace
from typing import Any, cast

import libtorrent
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common import database
from app.common.async_utils import owned_to_thread
from app.common.database import Base
from app.common.singleflight import AdmissionGate, SearchOverloadedError, Singleflight
from app.config import config
from app.exceptions import setup_exception_handlers
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import IndexerAccountRef
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexers.schemas.internal import DownloadedTorrentFile, IndexerTorrent
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_source_provider import service as providers

INDEXER_ID = "admission-indexer"


def torrent_bytes(index: int, padding: int = 0) -> bytes:
    info = {b"name": f"admission-{index:03d}.mkv".encode(), b"piece length": 16384, b"pieces": b"\0" * 20, b"length": 1}
    if padding:
        info[b"comment"] = b"x" * padding
    return libtorrent.bencode({b"info": info})


@pytest.fixture
def file_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'admission.db'}", connect_args={"check_same_thread": False}, hide_parameters=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    with database.SessionLocal() as db:
        definition = IndexerDefinitionModel(id=INDEXER_ID, name="Admission Indexer", url="https://admission.invalid", details_path="/")
        account = IndexerAccountModel(indexer_id=INDEXER_ID, username="fixture", password="fixture")
        account.indexer_definition = definition
        db.add_all([definition, account])
        db.commit()
    try:
        yield
    finally:
        engine.dispose()


def account_ref() -> IndexerAccountRef:
    with database.isolated_db_session() as db:
        return IndexerAccountRef.from_model(db.get_one(IndexerAccountModel, INDEXER_ID))


class NoTouchFiles(IsolatedTorrentFilesService):
    def touch(self, identifiers):
        return None


def candidates(count: int) -> list[IndexerTorrent]:
    ref = account_ref()
    return [IndexerTorrent(indexer_account=ref, torrent_id=f"t{index:03d}", download_url=f"https://admission.invalid/{index}") for index in range(count)]


class Indexers:
    """Search returns fixed candidates; downloads are observable and optionally gated."""

    def __init__(self, items, bodies, hang=frozenset()):
        self.items, self.bodies, self.hang = items, bodies, hang
        self.active = self.peak = 0
        self.never = asyncio.Event()

    async def get_torrents_by_imdb_id(self, imdb_id):
        return list(self.items), []

    async def download_torrent(self, indexer_id, torrent_id, download_url):
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            if torrent_id in self.hang:
                await self.never.wait()
            await asyncio.sleep(0.01)
            return DownloadedTorrentFile(indexer_id=indexer_id, torrent_id=torrent_id, torrent_bytes=self.bodies[torrent_id])
        finally:
            self.active -= 1


def provider(indexers) -> providers.TorrentSourceProviderService:
    return providers.TorrentSourceProviderService(indexers_service=cast(Any, indexers), isolated_torrent_files_service=NoTouchFiles())


@pytest.fixture
async def clean_singleflights():
    yield
    await providers._sources_singleflight.cancel_all()
    await providers._single_source_singleflight.cancel_all()
    await providers._torrent_download_singleflight.cancel_all()


def test_admission_gate_counts_leases_and_rejects_release_without_lease():
    gate = AdmissionGate(2)
    assert gate.try_acquire() and gate.try_acquire()
    assert not gate.try_acquire()
    gate.release()
    assert gate.try_acquire()
    gate.release()
    gate.release()
    with pytest.raises(RuntimeError):
        gate.release()
    with pytest.raises(ValueError):
        AdmissionGate(0)


@pytest.mark.anyio
async def test_new_key_over_the_limit_fails_fast_and_joiner_takes_no_slot():
    gate, flight, release = AdmissionGate(1), Singleflight[str](), asyncio.Event()

    async def work():
        await release.wait()
        return "shared"

    owner = asyncio.create_task(flight.run("a", work, gate))
    await asyncio.sleep(0)
    joiner = asyncio.create_task(flight.run("a", work, gate))
    await asyncio.sleep(0)
    assert gate.active == 1
    began = time.monotonic()
    with pytest.raises(SearchOverloadedError):
        await flight.run("b", work, gate)
    assert time.monotonic() - began < 0.1
    release.set()
    assert await asyncio.gather(owner, joiner) == ["shared", "shared"]
    assert gate.active == 0
    assert await flight.run("b", work, gate) == "shared"
    assert gate.active == 0


@pytest.mark.anyio
async def test_cancelled_waiter_keeps_the_lease_until_owned_thread_work_finishes():
    gate, flight = AdmissionGate(1), Singleflight[str]()
    started, finish = threading.Event(), threading.Event()

    def blocking():
        started.set()
        finish.wait(5)
        return "done"

    async def work():
        return await owned_to_thread(blocking)

    waiter = asyncio.create_task(flight.run("a", work, gate))
    await asyncio.to_thread(started.wait, 5)
    waiter.cancel()
    flight.cancel("a")
    await asyncio.gather(waiter, return_exceptions=True)
    # The shared task is cancelled, but its thread still runs: the slot stays taken.
    with pytest.raises(SearchOverloadedError):
        await flight.run("b", work, gate)
    assert gate.active == 1
    finish.set()
    deadline = time.monotonic() + 5
    while gate.active and time.monotonic() < deadline:
        await asyncio.sleep(0.01)
    assert gate.active == 0


@pytest.mark.anyio
async def test_failed_task_releases_its_lease():
    gate, flight = AdmissionGate(1), Singleflight[str]()

    async def boom():
        raise RuntimeError("synthetic")

    with pytest.raises(RuntimeError):
        await flight.run("a", boom, gate)
    await asyncio.sleep(0)
    assert gate.active == 0


@pytest.mark.anyio
async def test_overload_maps_to_fast_503_without_caching():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/search")
    async def search():
        raise SearchOverloadedError()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://fixture.invalid") as client:
        response = await client.get("/search")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "2"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_provider_admits_unique_searches_through_the_shared_gate(file_db, monkeypatch, clean_singleflights):
    monkeypatch.setattr(providers, "_source_search_admission", AdmissionGate(1))
    entered, release = asyncio.Event(), asyncio.Event()

    class Gated(Indexers):
        async def get_torrents_by_imdb_id(self, imdb_id):
            entered.set()
            await release.wait()
            return [], []

    service = provider(Gated([], {}))
    owner = asyncio.create_task(service.find_by_imdb_id("tt0000001"))
    await asyncio.wait_for(entered.wait(), 3)
    joiner = asyncio.create_task(service.find_by_imdb_id("tt0000001"))
    with pytest.raises(SearchOverloadedError):
        await service.find_by_imdb_id("tt0000002")
    release.set()
    assert await asyncio.wait_for(asyncio.gather(owner, joiner), 5) == [([], []), ([], [])]
    assert await service.find_by_imdb_id("tt0000002") == ([], [])


@pytest.mark.anyio
async def test_downloads_pass_the_per_indexer_gate_and_store_in_byte_bounded_batches_in_order(file_db, monkeypatch, clean_singleflights):
    items = candidates(7)
    bodies = {item.torrent_id: torrent_bytes(index, padding=4000) for index, item in enumerate(items)}
    size = max(len(body) for body in bodies.values())
    monkeypatch.setattr(config, "source_search_downloads_per_indexer", 2)
    monkeypatch.setattr(config, "source_search_batch_max_bytes", 2 * size)
    batches: list[int] = []
    original = providers._SourceSearch._store_snapshots

    def store(self, batch):
        batches.append(sum(len(item[2]) for item in batch))
        return original(self, batch)

    monkeypatch.setattr(providers._SourceSearch, "_store_snapshots", store)
    indexers = Indexers(items, bodies)
    sources, errors = await provider(indexers).find_by_imdb_id("tt0000003")

    assert errors == []
    assert [source.torrent_file.torrent_id for source in sources] == [item.torrent_id for item in items]
    assert indexers.peak == 2
    assert len(batches) >= 3 and sum(batches) == sum(len(body) for body in bodies.values())
    assert max(batches) <= 2 * size
    assert providers._pending_budget().used == 0


@pytest.mark.anyio
async def test_pending_budget_bounds_bytes_and_concurrent_searches_never_deadlock(file_db, monkeypatch, clean_singleflights):
    ref = account_ref()
    first = [IndexerTorrent(indexer_account=ref, torrent_id=f"a{index:03d}", download_url=f"https://admission.invalid/a{index}") for index in range(8)]
    second = [IndexerTorrent(indexer_account=ref, torrent_id=f"b{index:03d}", download_url=f"https://admission.invalid/b{index}") for index in range(8)]
    bodies = {item.torrent_id: torrent_bytes(index, padding=4000) for index, item in enumerate(first + second)}
    size = max(len(body) for body in bodies.values())
    monkeypatch.setattr(config, "source_search_downloads_per_indexer", 2)
    monkeypatch.setattr(config, "source_search_batch_max_bytes", 100 * size)
    monkeypatch.setattr(config, "source_search_pending_max_bytes", 2 * size)
    peak = 0
    original_add = providers._PendingBudget.add

    def add(self, amount):
        nonlocal peak
        original_add(self, amount)
        peak = max(peak, self.used)

    monkeypatch.setattr(providers._PendingBudget, "add", add)

    class TwoSets(Indexers):
        async def get_torrents_by_imdb_id(self, imdb_id):
            return (list(first) if imdb_id.endswith("1") else list(second)), []

    service = provider(TwoSets(first + second, bodies))
    (a, a_errors), (b, b_errors) = await asyncio.wait_for(
        asyncio.gather(service.find_by_imdb_id("tt0000011"), service.find_by_imdb_id("tt0000012")), 10)

    assert a_errors == [] and b_errors == []
    assert [s.torrent_file.torrent_id for s in a] == [i.torrent_id for i in first]
    assert [s.torrent_file.torrent_id for s in b] == [i.torrent_id for i in second]
    # Budget plus at most one admitted download per gate slot in flight.
    assert peak <= 2 * size + 2 * size
    assert providers._pending_budget().used == 0


@pytest.mark.anyio
async def test_cancelled_search_returns_its_pending_bytes_to_the_budget(file_db, monkeypatch, clean_singleflights):
    items = candidates(4)
    bodies = {item.torrent_id: torrent_bytes(index) for index, item in enumerate(items)}
    monkeypatch.setattr(config, "source_search_batch_max_bytes", 1 << 30)
    indexers = Indexers(items, bodies, hang=frozenset({"t002", "t003"}))
    search = providers._SourceSearch(cast(Any, indexers), NoTouchFiles())
    task = asyncio.create_task(search.find_by_imdb_id("tt0000013"))
    deadline = time.monotonic() + 3
    while providers._pending_budget().used == 0 and time.monotonic() < deadline:
        await asyncio.sleep(0.01)
    assert providers._pending_budget().used > 0
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert providers._pending_budget().used == 0


@pytest.mark.anyio
async def test_deadline_returns_stored_results_and_a_partial_error(file_db, monkeypatch, clean_singleflights):
    items = candidates(4)
    bodies = {item.torrent_id: torrent_bytes(index) for index, item in enumerate(items)}
    monkeypatch.setattr(config, "source_search_downloads_per_indexer", 2)
    monkeypatch.setattr(config, "source_search_deadline_seconds", 0.3)
    indexers = Indexers(items, bodies, hang=frozenset({"t002", "t003"}))
    began = time.monotonic()
    sources, errors = await asyncio.wait_for(provider(indexers).find_by_imdb_id("tt0000004"), 5)

    assert time.monotonic() - began < 2
    assert [source.torrent_file.torrent_id for source in sources] == ["t000", "t001"]
    assert errors == [providers.DEADLINE_ERROR]
    with database.isolated_db_session() as db:
        from app.modules.torrent_files.models import TorrentFileModel

        assert sorted(row.torrent_id for row in db.query(TorrentFileModel).all()) == ["t000", "t001"]


@pytest.mark.anyio
async def test_search_stage_deadline_yields_empty_partial_result(file_db, monkeypatch, clean_singleflights):
    monkeypatch.setattr(config, "source_search_deadline_seconds", 0.2)
    never = asyncio.Event()

    async def hanging(imdb_id):
        await never.wait()

    service = provider(SimpleNamespace(get_torrents_by_imdb_id=hanging))
    assert await asyncio.wait_for(service.find_by_imdb_id("tt0000005"), 5) == ([], [providers.DEADLINE_ERROR])


@pytest.mark.anyio
async def test_arrival_right_after_completion_is_not_rejected():
    # Regression: the slot is freed at the end of the work itself, before the task's
    # done-callbacks, so a caller in that window must not see a false overload.
    gate, flight, release = AdmissionGate(1), Singleflight[str](), asyncio.Event()

    async def work():
        await release.wait()
        return "x"

    owner = asyncio.create_task(flight.run("a", work, gate))
    await asyncio.sleep(0)
    late = asyncio.create_task(flight.run("a", work, gate))
    release.set()
    assert await asyncio.gather(owner, late) == ["x", "x"]
    assert gate.active == 0


def streams_service(find_by_imdb_id):
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.torrent_streams.service import TorrentStreamsService

    settings, preferences, torrents = MagicMock(), MagicMock(), MagicMock()
    settings.get_app_url.return_value = "http://localhost:7070"
    preferences.get_list.return_value = []
    preferences.get_system_preferences.return_value = []
    torrents.get_torrents.return_value = []
    source_provider = AsyncMock()
    source_provider.find_by_imdb_id.side_effect = find_by_imdb_id
    return TorrentStreamsService(db=AsyncMock(), torrent_source_provider_service=source_provider, torrents_service=torrents,
                                 settings_service=settings, preferences_service=preferences)


@pytest.mark.anyio
async def test_multi_id_stream_search_never_drops_overload_silently():
    from app.modules.users.models import UserModel
    from tests.helpers import create_torrent_source

    source = create_torrent_source(indexer_id="ncore", indexer_name="nCore", torrent_id="t1", name="Fixture.Movie.2024.1080p.mkv",
                                   seeders=10, files=["Fixture.Movie.2024.1080p.mkv"])

    async def partly(imdb_id):
        if imdb_id == "tt0000010":
            return [source], []
        raise SearchOverloadedError()

    async def fully(imdb_id):
        raise SearchOverloadedError()

    user = UserModel(id="u1", username="test", enable_smart_filter=False)
    streams, errors = await streams_service(partly).find_by_imdb(user=user, imdb_id="tt0000010", alternate_imdb_ids=["tt0000011"])
    assert [stream.torrent_id for stream in streams] == ["t1"]
    assert errors == [str(SearchOverloadedError())]
    with pytest.raises(SearchOverloadedError):
        await streams_service(fully).find_by_imdb(user=user, imdb_id="tt0000010", alternate_imdb_ids=["tt0000011"])
