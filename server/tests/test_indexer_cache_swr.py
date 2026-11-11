"""SP07: lejárt tracker IMDb-cache — régi lista azonnal, frissítés a háttérben (hamis órával).

Mátrix (implementation-plan #sp07): friss találat; puhán lejárt → azonnal régi lista és pontosan
egy frissítés; párhuzamos kérések egy frissítésen osztoznak; frissítési hiba → a régi marad a kemény
TTL-ig; keményen lejárt → szinkron; invalidálás és epoch-váltás → nincs régi; új epizód → a
kényszerített frissítés megtalálja; lezárás → nincs árva task; kikapcsolt állapot = a korábbi út. Alapérték: 24 órás kemény TTL (gsp07-v2).
Valódi fájl-SQLite az account-sorokhoz; a tracker-adapterek szintetikusak.
"""

import asyncio
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common import database
from app.common.database import Base
from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.config import config
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import IndexerAccountRef
from app.modules.indexer_definitions.exceptions import IndexerDefinitionException
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexers import search
from app.modules.indexers.search import (
    IndexerHealth,
    IndexerSearchResult,
    IndexerSearchService,
    invalidate_indexer_cache,
)
from app.modules.preferences.service import PreferencesService
from app.modules.settings.service import SettingsService
from app.modules.stremio.cache import stream_cache_state
from app.modules.torrent_source_provider import service as providers
from app.modules.torrent_source_provider.service import SourceSearchResult
from app.modules.torrent_streams.service import TorrentStreamsService
from app.modules.users.models import UserModel

SOFT = 1800.0
HARD = 86400.0
IMDB = "tt0000701"


class _Clock:
    def __init__(self) -> None:
        self.now = 10_000.0

    def __call__(self) -> float:
        return self.now


class _Tracker:
    """Szintetikus tracker: a `version` a trackeren aktuális lista, a `gate` nyitva tartja a hívást."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.version = 1
        self.mode = "ok"
        self.calls = 0
        self.gate: asyncio.Event | None = None

    async def find_torrents_by_imdb_id(self, imdb_id: str) -> list[SimpleNamespace]:
        self.calls += 1
        if self.gate is not None:
            await self.gate.wait()
        if self.mode == "timeout":
            await asyncio.sleep(30)
        elif self.mode == "connect":
            try:
                raise httpx.ConnectError("refused")
            except httpx.ConnectError:
                raise IndexerDefinitionException("nem érhető el") from None
        torrent_id = f"{self.prefix}-v{self.version}"
        return [SimpleNamespace(torrent_id=torrent_id, download_url=f"https://{self.prefix}.invalid/{torrent_id}",
                                imdb_id=imdb_id, seeders=3, attribute_ids=[])]


@pytest.fixture
async def swr(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'swr.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    with session_factory() as db:
        for indexer_id in ("a", "b"):
            definition = IndexerDefinitionModel(id=indexer_id, name=f"Tracker {indexer_id}",
                                                url=f"https://{indexer_id}.invalid", details_path="/")
            account = IndexerAccountModel(indexer_id=indexer_id, username="fixture", password="fixture")
            account.indexer_definition = definition
            db.add_all([definition, account])
        db.commit()
    clock = _Clock()
    monkeypatch.setattr(search, "time", SimpleNamespace(monotonic=clock))
    monkeypatch.setattr(search, "indexer_health", IndexerHealth(clock))
    monkeypatch.setattr(search, "INDEXER_SEARCH_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(config, "indexer_breaker_threshold", 0)
    monkeypatch.setattr(config, "indexer_cache_hard_ttl_seconds", HARD)
    monkeypatch.setattr(config, "indexer_cache_refresh_max_in_flight", 4)
    invalidate_indexer_cache()
    search.open_indexer_cache_refresh()
    trackers = {"a": _Tracker("a"), "b": _Tracker("b")}
    service = IndexerSearchService(cast(Any, SimpleNamespace(get_by_id=trackers.__getitem__)))
    try:
        yield SimpleNamespace(service=service, a=trackers["a"], b=trackers["b"], clock=clock, trackers=trackers)
    finally:
        await search.close_indexer_cache_refresh()
        search.open_indexer_cache_refresh()
        invalidate_indexer_cache()
        engine.dispose()


async def _find(fx, imdb_id: str = IMDB, **kwargs: Any) -> tuple[list[str], list[str], bool]:
    result = await asyncio.wait_for(fx.service.get_torrents_by_imdb_id(imdb_id, **kwargs), 5)
    torrents, errors = result
    return sorted(t.torrent_id for t in torrents), errors, result.stale


def _flights() -> dict:
    return search._refresher().flights


async def _settle() -> None:
    tasks = tuple(search._refresher().tasks)
    if tasks:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 5)
    await asyncio.sleep(0)


def _new_upload(fx) -> None:
    for tracker in fx.trackers.values():
        tracker.version = 2


def _gate(fx) -> asyncio.Event:
    gate = asyncio.Event()
    for tracker in fx.trackers.values():
        tracker.gate = gate
    return gate


def _calls(fx) -> int:
    return fx.a.calls + fx.b.calls


@pytest.mark.anyio
async def test_fresh_entry_is_served_from_cache_without_refresh(swr):
    assert await _find(swr) == (["a-v1", "b-v1"], [], False)
    _new_upload(swr)
    swr.clock.now += SOFT - 1

    assert await _find(swr) == (["a-v1", "b-v1"], [], False)
    assert _calls(swr) == 2
    assert not _flights()


@pytest.mark.anyio
async def test_soft_expired_serves_old_list_immediately_and_starts_exactly_one_refresh(swr):
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += SOFT

    # A frissítés a kapunál áll, a kérés mégis azonnal a régi listát kapja.
    assert await _find(swr) == (["a-v1", "b-v1"], [], True)
    assert await _find(swr) == (["a-v1", "b-v1"], [], True)
    await asyncio.sleep(0)
    assert _calls(swr) == 4
    assert len(_flights()) == 2

    gate.set()
    await _settle()
    assert not _flights()
    assert await _find(swr) == (["a-v2", "b-v2"], [], False)
    assert _calls(swr) == 4


@pytest.mark.anyio
async def test_parallel_requests_share_one_refresh_per_key(swr):
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += SOFT

    results = await asyncio.gather(*(_find(swr) for _ in range(6)))
    assert all(result == (["a-v1", "b-v1"], [], True) for result in results)
    await asyncio.sleep(0)
    assert (swr.a.calls, swr.b.calls) == (2, 2)

    gate.set()
    await _settle()
    assert await _find(swr) == (["a-v2", "b-v2"], [], False)


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["connect", "timeout"])
async def test_refresh_failure_keeps_old_list_until_hard_ttl(swr, mode):
    await _find(swr)
    _new_upload(swr)
    swr.b.mode = mode
    swr.clock.now += SOFT

    assert await _find(swr) == (["a-v1", "b-v1"], [], True)
    await _settle()
    # A sikeres tracker friss, a hibás régi listája marad, és a következő kérés újrapróbálja.
    assert await _find(swr) == (["a-v2", "b-v1"], [], True)
    await _settle()
    assert swr.b.calls == 3

    # Kemény lejárat: a régi lista eltűnik, a szinkron kérés hibája látszik (mint ma).
    swr.clock.now += HARD - SOFT
    torrents, errors, _ = await _find(swr)
    assert torrents == ["a-v2"] and len(errors) == 1
    assert ("b", f"{stream_cache_state.revision('')[0]}:{IMDB}") not in search._imdb_tracker_cache


@pytest.mark.anyio
async def test_refresh_uses_the_breaker_path_and_a_skip_keeps_the_old_list(swr, monkeypatch):
    monkeypatch.setattr(config, "indexer_breaker_threshold", 1)
    monkeypatch.setattr(config, "indexer_breaker_cooldown_seconds", 10 * HARD)
    monkeypatch.setattr(config, "indexer_breaker_cooldown_max_seconds", 10 * HARD)
    await _find(swr)
    swr.b.mode = "timeout"
    torrents, errors, _ = await _find(swr, "tt0000702")
    assert torrents == ["a-v1"] and len(errors) == 1
    assert search.indexer_health._states["b"].open_until is not None
    calls_before = swr.b.calls
    swr.clock.now += SOFT

    # Nyitott rövidzár: a háttérfrissítés hálózati hívás nélkül kimarad, a régi lista marad.
    assert await _find(swr) == (["a-v1", "b-v1"], [], True)
    await _settle()
    assert swr.b.calls == calls_before
    assert await _find(swr) == (["a-v1", "b-v1"], [], True)


@pytest.mark.anyio
async def test_hard_expired_entry_refreshes_synchronously(swr):
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += HARD

    pending = asyncio.create_task(_find(swr))
    await asyncio.sleep(0.05)
    assert not pending.done()
    gate.set()
    assert await pending == (["a-v2", "b-v2"], [], False)
    assert not _flights()


@pytest.mark.anyio
async def test_invalidation_drops_the_old_entry_and_cancels_its_refresh(swr):
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += SOFT
    assert await _find(swr) == (["a-v1", "b-v1"], [], True)
    await asyncio.sleep(0)
    refreshes = tuple(search._refresher().tasks)
    assert len(refreshes) == 2

    invalidate_indexer_cache("a")
    await asyncio.wait(refreshes, timeout=0.05)
    assert [task.cancelled() for task in refreshes].count(True) == 1
    assert list(_flights()) == [("b", f"{stream_cache_state.revision('')[0]}:{IMDB}")]

    # Az invalidált tracker nem ad régi listát: a következő kérés szinkron kérdez.
    pending = asyncio.create_task(_find(swr))
    await asyncio.sleep(0.05)
    assert not pending.done()
    gate.set()
    assert await pending == (["a-v2", "b-v1"], [], True)


@pytest.mark.anyio
async def test_refresh_finishing_after_invalidation_is_not_stored(swr):
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += SOFT
    await _find(swr)
    await asyncio.sleep(0)
    refresher = search._refresher()
    flights = dict(refresher.flights)

    # Event loopon kívüli invalidálás (nincs task-megszakítás): a generáció akadályozza a tárolást.
    search._imdb_cache_generation += 1
    search._imdb_tracker_cache.clear()
    gate.set()
    await _settle()
    assert all(task.result() is not None for task in flights.values())
    assert search._imdb_tracker_cache == {}


@pytest.mark.anyio
async def test_epoch_change_never_serves_the_old_list(swr):
    await _find(swr)
    _new_upload(swr)
    swr.clock.now += SOFT
    stream_cache_state.invalidate_all()

    assert await _find(swr) == (["a-v2", "b-v2"], [], False)
    assert not _flights()


@pytest.mark.anyio
async def test_forced_refresh_waits_for_the_refresh_and_returns_the_new_list(swr):
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += SOFT
    assert await _find(swr) == (["a-v1", "b-v1"], [], True)

    forced = asyncio.create_task(_find(swr, allow_stale=False))
    await asyncio.sleep(0.05)
    assert not forced.done()
    gate.set()
    # A futó háttérfrissítésre csatlakozik: trackerenként nincs második hívás.
    assert await forced == (["a-v2", "b-v2"], [], False)
    assert _calls(swr) == 4


@pytest.mark.anyio
async def test_forced_refresh_failure_keeps_old_list(swr):
    await _find(swr)
    _new_upload(swr)
    swr.b.mode = "connect"
    swr.clock.now += SOFT

    assert await _find(swr, allow_stale=False) == (["a-v2", "b-v1"], [], True)


@pytest.mark.anyio
async def test_full_capacity_serves_old_list_without_refresh_and_forced_asks_inline(swr, monkeypatch):
    monkeypatch.setattr(config, "indexer_cache_refresh_max_in_flight", 1)
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += SOFT

    assert await _find(swr) == (["a-v1", "b-v1"], [], True)
    await asyncio.sleep(0)
    assert [key[0] for key in _flights()] == ["a"]
    assert (swr.a.calls, swr.b.calls) == (2, 1)

    # Kényszerítve: „a” a futó frissítésre vár, „b” szabad hely híján közvetlenül kérdez.
    forced = asyncio.create_task(_find(swr, allow_stale=False))
    await asyncio.sleep(0.05)
    assert not forced.done()
    gate.set()
    assert await forced == (["a-v2", "b-v2"], [], False)
    assert (swr.a.calls, swr.b.calls) == (2, 2)
    assert await _find(swr) == (["a-v2", "b-v2"], [], False)


@pytest.mark.anyio
async def test_close_cancels_and_awaits_refreshes_and_starts_no_new_one(swr):
    await _find(swr)
    _gate(swr)
    swr.clock.now += SOFT
    await _find(swr)
    await asyncio.sleep(0)
    tasks = tuple(search._refresher().tasks)
    assert len(tasks) == 2

    await search.close_indexer_cache_refresh()
    assert all(task.cancelled() for task in tasks)
    assert not search._refresher().tasks and not _flights()
    assert not [task for task in asyncio.all_tasks() if task.get_name().startswith("indexer-cache-refresh")]

    # Lezárva: a régi lista jön, új tulajdonolt munka nem indul.
    assert await _find(swr) == (["a-v1", "b-v1"], [], True)
    assert not search._refresher().tasks
    search.open_indexer_cache_refresh()
    await _find(swr)
    assert len(search._refresher().tasks) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("hard_ttl", [0.0, SOFT, SOFT - 1])
async def test_disabled_hard_ttl_is_the_legacy_path(swr, monkeypatch, hard_ttl):
    monkeypatch.setattr(config, "indexer_cache_hard_ttl_seconds", hard_ttl)
    await _find(swr)
    _new_upload(swr)
    gate = _gate(swr)
    swr.clock.now += SOFT

    for allow_stale in (True, False):
        pending = asyncio.create_task(_find(swr, allow_stale=allow_stale))
        await asyncio.sleep(0.05)
        assert not pending.done()
        gate.set()
        assert await pending == (["a-v2", "b-v2"], [], False)
        assert not _flights() and not search._refresher().tasks
        gate.clear()
        swr.clock.now += SOFT


def test_result_keeps_the_two_value_contract():
    result = IndexerSearchResult([], ["hiba"], stale=True)
    torrents, errors = result
    assert result == ([], ["hiba"]) and result.stale and torrents == [] and errors == ["hiba"]
    assert not IndexerSearchResult([], []).stale
    assert SourceSearchResult([], [], stale=True) == ([], []) and not providers.is_stale_result(([], []))


class _Files:
    def find_snapshots(self, identifiers):
        return []

    def touch(self, identifiers):
        return None


@pytest.mark.anyio
@pytest.mark.parametrize("allow_stale", [True, False])
async def test_provider_passes_the_flag_and_reports_stale(monkeypatch, allow_stale):
    monkeypatch.setattr(config, "indexer_cache_hard_ttl_seconds", HARD)
    calls: list[tuple[str, dict]] = []

    async def get_torrents_by_imdb_id(imdb_id, **kwargs):
        calls.append((imdb_id, kwargs))
        return IndexerSearchResult([], [], stale=allow_stale)

    indexers = SimpleNamespace(get_torrents_by_imdb_id=get_torrents_by_imdb_id)
    keys: list[str] = []
    real = providers._sources_singleflight

    class _Recording:
        async def run(self, key, factory, admission=None):
            keys.append(key)
            return await real.run(key, factory, admission)

    monkeypatch.setattr(providers, "_sources_singleflight", _Recording())
    service = providers.TorrentSourceProviderService(cast(Any, indexers), cast(Any, _Files()))

    result = await asyncio.wait_for(service.find_by_imdb_id(IMDB, allow_stale=allow_stale), 5)
    assert result == ([], []) and providers.is_stale_result(result) is allow_stale
    assert calls == [(IMDB, {} if allow_stale else {"allow_stale": False})]
    assert keys[0].endswith(f":imdb:{IMDB}" if allow_stale else f":imdb-fresh:{IMDB}")


@pytest.mark.anyio
async def test_provider_ignores_the_flag_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "indexer_cache_hard_ttl_seconds", 0.0)
    calls: list[str] = []

    async def find_by_imdb_id(imdb_id):  # a mai, jelző nélküli hívás alakja
        calls.append(imdb_id)
        return [], []

    service = providers.TorrentSourceProviderService(cast(Any, None), cast(Any, _Files()))
    monkeypatch.setattr(service, "_shared_search", lambda: SimpleNamespace(find_by_imdb_id=find_by_imdb_id))

    assert await asyncio.wait_for(service.find_by_imdb_id(IMDB, allow_stale=False), 5) == ([], [])
    assert calls == [IMDB]


def _source(torrent_id: str, episode: int) -> MagicMock:
    account = IndexerAccountModel(indexer_id="ncore", username="fixture", password="fixture")
    account.indexer_definition = IndexerDefinitionModel(id="ncore", name="ncore", url="https://ncore.invalid",
                                                        details_path="")
    name = f"Show.S01E{episode:02d}.1080p.mkv"
    source = MagicMock()
    source.indexer_torrent.indexer_account = IndexerAccountRef.from_model(account)
    source.indexer_torrent.torrent_id = torrent_id
    source.indexer_torrent.imdb_id = IMDB
    source.indexer_torrent.seeders = 10
    source.indexer_torrent.media_attributes = []
    source.torrent_file.info = TorrentInfo(
        info_hash=f"hash{torrent_id}", name=name, size=1_000_000, piece_size=1_000_000,
        files=[TorrentFileInfo(index=0, name=name, path=name, size=1_000_000, offset=0,
                               start_piece_index=0, end_piece_index=0, is_video=True)],
    )
    source.torrent_file.torrent_id = torrent_id
    source.torrent_file.info_hash = f"hash{torrent_id}"
    return source


def _streams_service(find_by_imdb_id) -> tuple[TorrentStreamsService, AsyncMock]:
    provider = AsyncMock(spec=providers.TorrentSourceProviderService)
    provider.find_by_imdb_id.side_effect = find_by_imdb_id
    provider.find_by_query.return_value = ([], [])
    settings = AsyncMock(spec=SettingsService)
    settings.get_app_url.return_value = "http://fixture.invalid"
    preferences = MagicMock(spec=PreferencesService)
    preferences.get_list.return_value = []
    torrents = MagicMock()
    torrents.get_torrents.return_value = []
    service = TorrentStreamsService(db=AsyncMock(), torrent_source_provider_service=provider,
                                    torrents_service=torrents, settings_service=settings,
                                    preferences_service=preferences)
    return service, provider


@pytest.mark.anyio
async def test_new_episode_missing_from_old_list_triggers_forced_refresh():
    old, new = _source("100", 1), _source("200", 2)

    async def find_by_imdb_id(imdb_id, allow_stale=True):
        if allow_stale:
            return SourceSearchResult([old], [], stale=True)
        return SourceSearchResult([old, new], [])

    service, provider = _streams_service(find_by_imdb_id)
    user = UserModel(id="user1", username="fixture", enable_smart_filter=False)
    streams, errors = await service.find_by_imdb(user=user, imdb_id=IMDB, series=SeriesInfo(season=1, episode=2))

    assert [stream.torrent_id for stream in streams] == ["200"] and errors == []
    assert [call.args + tuple(call.kwargs.items()) for call in provider.find_by_imdb_id.await_args_list] == [
        (IMDB,), (IMDB, ("allow_stale", False))]
    provider.find_by_query.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(("stale", "episode"), [(True, 1), (False, 2)])
async def test_no_forced_refresh_when_old_list_plays_or_list_is_fresh(stale, episode):
    async def find_by_imdb_id(imdb_id, allow_stale=True):
        return SourceSearchResult([_source("100", 1)], [], stale=stale)

    service, provider = _streams_service(find_by_imdb_id)
    user = UserModel(id="user1", username="fixture", enable_smart_filter=False)
    streams, _ = await service.find_by_imdb(user=user, imdb_id=IMDB, series=SeriesInfo(season=1, episode=episode))

    assert len(streams) == (1 if episode == 1 else 0)
    provider.find_by_imdb_id.assert_awaited_once_with(IMDB)


@pytest.mark.anyio
async def test_forced_refresh_overload_keeps_old_list_and_falls_back_by_name():
    from app.common.singleflight import SearchOverloadedError

    async def find_by_imdb_id(imdb_id, allow_stale=True):
        if allow_stale:
            return SourceSearchResult([_source("100", 1)], [], stale=True)
        raise SearchOverloadedError()

    service, provider = _streams_service(find_by_imdb_id)
    user = UserModel(id="user1", username="fixture", enable_smart_filter=False)
    streams, _ = await service.find_by_imdb(user=user, imdb_id=IMDB, series=SeriesInfo(season=1, episode=2))

    assert streams == []
    assert provider.find_by_imdb_id.await_count == 2
    provider.find_by_query.assert_awaited()


def test_default_is_the_gate_passed_24_hour_hard_ttl():
    from app.config import Config

    assert Config.model_fields["indexer_cache_hard_ttl_seconds"].default == 86400.0
    assert Config.model_fields["indexer_cache_refresh_max_in_flight"].default == 4
    assert Config.model_validate({"indexer_cache_hard_ttl_seconds": "0"}).indexer_cache_hard_ttl_seconds == 0.0
