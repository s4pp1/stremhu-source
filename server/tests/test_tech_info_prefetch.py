"""SP06/b: Tech Info előtöltés a megosztott keresésben, háttérben befejeződő lekéréssel.

- Kikapcsolt kapcsolónál a mai viselkedés: nincs előtöltés, a kérés időtúllépése megszakítja a lekérést.
- Bekapcsolva: kulcsonként egy lekérés, folyamatszintű kapacitás (a többlet kimarad), a kérés csak a
  keretéből hátralévő időt várja, időtúllépés után a háttér befejezi és a következő kérés már nem kér,
  hiba nem kerül cache-be, leállításkor nincs árva task, gyors válasznál az attribútumok azonosak.
"""

import asyncio
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.config import config
from app.modules.indexer_accounts.schemas import IndexerAccountRef, IndexerDefinitionRef
from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.exceptions import TechInfoUnavailableException
from app.modules.indexer_definitions.integrations import discover_indexer_definitions
from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.media_attributes import tech_info_cache
from app.modules.media_attributes.constants import MediaAttributeKey
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.torrent_files.exceptions import InvalidTorrentFileException
from app.modules.torrent_source_provider import service as providers
from app.modules.torrent_streams import service as streams_module
from app.modules.torrent_streams.schemas import TorrentStream
from app.modules.torrent_streams.service import (
    _DEFAULT_ATTRIBUTES_MAP,
    TorrentStreamsService,
)

NFO_JAP = "Audio #1\nLanguage : Japanese\n"
NFO_HUN = "Audio #1\nLanguage : Hungarian\n"
NFO_DUAL = "Audio #1\nLanguage : Japanese\n\nAudio #2\nLanguage : English\n"
DESC_HUN_SUB = "Feliratok: Magyar"


class TechInfoStub:
    """Tech Info-t adó indexer: hívásokat és megszakításokat rögzít; opcionálisan kapuzott/késleltetett."""

    provides_tech_info = True

    def __init__(
        self,
        responses: dict[str, tuple[str | None, str | None]] | None = None,
        *,
        delay: float = 0.0,
        gated: bool = False,
        failures: frozenset[str] = frozenset(),
    ) -> None:
        self.responses = responses or {}
        self.delay = delay
        self.gate = asyncio.Event() if gated else None
        self.failures = failures
        self.calls: list[str] = []
        self.cancelled: list[str] = []

    def release(self) -> None:
        assert self.gate is not None
        self.gate.set()

    async def fetch_tech_info(self, torrent_id: str) -> tuple[str | None, str | None]:
        self.calls.append(torrent_id)
        try:
            if self.gate is not None:
                await self.gate.wait()
            if self.delay:
                await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled.append(torrent_id)
            raise
        if torrent_id in self.failures:
            raise TechInfoUnavailableException("synthetic")
        return self.responses.get(torrent_id, (NFO_JAP, DESC_HUN_SUB))


class Definitions:
    def __init__(self, **by_id: Any) -> None:
        self.by_id = by_id

    def get_by_id(self, indexer_id: str) -> Any:
        if indexer_id not in self.by_id:
            raise HTTPException(status_code=400, detail="unknown")
        return self.by_id[indexer_id]


def non_provider() -> SimpleNamespace:
    return SimpleNamespace(provides_tech_info=False, fetch_tech_info=AsyncMock(return_value=(None, None)))


def account(indexer_id: str = "ncore") -> IndexerAccountRef:
    return IndexerAccountRef(
        indexer_id=indexer_id,
        indexer_definition=IndexerDefinitionRef(
            id=indexer_id,
            name=indexer_id,
            url=f"https://{indexer_id}.invalid",
            details_path="/",
            requires_full_download=False,
            supports_totp=False,
            disabled=False,
            order=0,
        ),
    )


def candidate(torrent_id: str, seeders: int = 0, indexer_id: str = "ncore") -> IndexerTorrent:
    return IndexerTorrent(
        indexer_account=account(indexer_id),
        torrent_id=torrent_id,
        download_url=f"https://{indexer_id}.invalid/{torrent_id}",
        seeders=seeders,
    )


def stream(torrent_id: str, indexer_id: str = "ncore", file_index: int = 0) -> TorrentStream:
    ref = account(indexer_id)
    return TorrentStream(
        indexer_account=ref,
        torrent_id=torrent_id,
        info_hash=f"hash-{indexer_id}-{torrent_id}",
        torrent_name=f"Show.{torrent_id}.720p",
        file_name=f"show-{torrent_id}-{file_index}.mkv",
        file_size=800 * 1024 * 1024,
        file_index=file_index,
        play_url="https://localhost.invalid/play",
        seeders=10,
        attributes=[_DEFAULT_ATTRIBUTES_MAP[MediaAttributeKey.ENG], ref.indexer_definition],
    )


def streams_service(definitions: Definitions) -> TorrentStreamsService:
    service = object.__new__(TorrentStreamsService)
    service._indexer_definitions_service = cast(Any, definitions)
    return service


def source_search(definitions: Definitions, indexers: Any = None) -> providers._SourceSearch:
    return providers._SourceSearch(cast(Any, indexers), cast(Any, NoFiles()), cast(Any, definitions))


def language_ids(ts: TorrentStream) -> list[str]:
    return [a.id for a in ts.attributes if isinstance(a, MediaAttributeModel)]


def snapshot(streams: list[TorrentStream]) -> list[tuple[str, int, list[str], bool]]:
    return [(ts.torrent_id, ts.file_index, [a.id for a in ts.attributes], ts.has_hungarian_sub) for ts in streams]


class NoFiles:
    def find_snapshots(self, identifiers: Any) -> list[Any]:
        return []

    def touch(self, identifiers: Any) -> None:
        return None


class GatedDownloads:
    """A trackerfázis kész jelöltekkel tér vissza; a .torrent letöltés a kapuig vár, majd érvénytelen."""

    def __init__(self, items: list[IndexerTorrent]) -> None:
        self.items = items
        self.downloading = asyncio.Event()
        self.release = asyncio.Event()

    async def get_torrents_by_imdb_id(self, imdb_id: str) -> tuple[list[IndexerTorrent], list[str]]:
        return list(self.items), []

    async def download_torrent(self, indexer_id: str, torrent_id: str, download_url: str) -> Any:
        self.downloading.set()
        await self.release.wait()
        raise InvalidTorrentFileException


@pytest.fixture
def budget(monkeypatch) -> Iterator[None]:
    """Rövid kérésoldali keret a gyors tesztekhez (élesben 1,5 s)."""
    monkeypatch.setattr(streams_module, "_TECH_INFO_BUDGET_SECONDS", 0.3)
    yield


@pytest.fixture
async def prefetch_on(monkeypatch):
    monkeypatch.setattr(tech_info_cache, "_TECH_INFO_CACHE", {})
    monkeypatch.setattr(config, "tech_info_prefetch", True)
    tech_info_cache.open_tech_info_prefetch()
    yield
    await tech_info_cache.close_tech_info_prefetch()
    tech_info_cache.open_tech_info_prefetch()
    await providers._torrent_download_singleflight.cancel_all()


def test_capability_marker_matches_fetch_tech_info_override():
    providers_found = []
    for definition_class in discover_indexer_definitions():
        overrides = definition_class.fetch_tech_info is not BaseIndexerDefinition.fetch_tech_info
        instance = object.__new__(definition_class)
        assert instance.provides_tech_info is overrides, definition_class.__name__
        if overrides:
            providers_found.append(instance.id)
    assert providers_found == ["ncore"]


@pytest.mark.anyio
async def test_switch_off_keeps_legacy_behaviour(prefetch_on, budget, monkeypatch):
    monkeypatch.setattr(config, "tech_info_prefetch", False)
    stub = TechInfoStub(gated=True)
    definitions = Definitions(ncore=stub)

    downloads = GatedDownloads([candidate("a", seeders=5)])
    search = asyncio.create_task(source_search(definitions, downloads).find_by_imdb_id("tt0000001"))
    await asyncio.wait_for(downloads.downloading.wait(), 1)
    downloads.release.set()
    assert await asyncio.wait_for(search, 1) == ([], [])
    assert stub.calls == []  # no prefetch in the shared search
    assert tech_info_cache.in_flight_count() == 0

    # Request: fetched inline and cancelled at the 1.5 s-style budget, as today.
    ts = stream("a")
    await streams_service(definitions)._enrich_torrent_streams_with_tech_info([ts])
    assert stub.calls == ["a"]
    assert stub.cancelled == ["a"]
    assert tech_info_cache.in_flight_count() == 0
    assert tech_info_cache.get_cached(("ncore", "a")) is None
    assert MediaAttributeKey.JAP not in language_ids(ts)


@pytest.mark.anyio
async def test_prefetch_runs_beside_downloads_and_never_extends_the_search(prefetch_on):
    stub = TechInfoStub(gated=True)
    downloads = GatedDownloads([candidate("a", seeders=5)])
    search = asyncio.create_task(source_search(Definitions(ncore=stub), downloads).find_by_imdb_id("tt0000001"))

    await asyncio.wait_for(downloads.downloading.wait(), 1)
    await asyncio.sleep(0)
    assert stub.calls == ["a"]  # Tech Info is already being fetched while the .torrent download runs

    downloads.release.set()
    assert await asyncio.wait_for(search, 1) == ([], [])
    flight = tech_info_cache.in_flight(("ncore", "a"))
    assert flight is not None and not flight.task.done()  # the search did not wait for it


@pytest.mark.anyio
async def test_top_n_by_seeders_among_tech_info_indexers_only(prefetch_on, monkeypatch):
    monkeypatch.setattr(config, "tech_info_prefetch_top_n", 2)
    stub = TechInfoStub(gated=True)
    other = non_provider()
    search = source_search(Definitions(ncore=stub, other=other))

    search._prefetch_tech_info(
        [
            candidate("o1", seeders=900, indexer_id="other"),  # no Tech Info support
            candidate("g1", seeders=800, indexer_id="ghost"),  # unknown/disabled indexer
            candidate("low", seeders=5),
            candidate("top", seeders=50),
            candidate("mid", seeders=20),
        ]
    )
    await asyncio.sleep(0)

    started = {key for key in [("ncore", "low"), ("ncore", "top"), ("ncore", "mid")] if tech_info_cache.in_flight(key)}
    assert started == {("ncore", "top"), ("ncore", "mid")}
    assert sorted(stub.calls) == ["mid", "top"]
    other.fetch_tech_info.assert_not_awaited()


@pytest.mark.anyio
async def test_one_fetch_per_key(prefetch_on):
    stub = TechInfoStub(gated=True)
    definitions = Definitions(ncore=stub)
    items = [candidate("a", seeders=10), candidate("a", seeders=10)]

    # Two shared searches for the same title, an explicit prefetch and a waiting request.
    source_search(definitions)._prefetch_tech_info(items)
    source_search(definitions)._prefetch_tech_info(items)
    assert tech_info_cache.prefetch([(("ncore", "a"), stub)]) == 0
    assert tech_info_cache.start_fetch(("ncore", "a"), stub) is tech_info_cache.in_flight(("ncore", "a"))
    streams =[stream("a", file_index=0), stream("a", file_index=1)]
    request = asyncio.create_task(streams_service(definitions)._enrich_torrent_streams_with_tech_info(streams))
    await asyncio.sleep(0.05)

    stub.release()
    await asyncio.wait_for(request, 2)
    assert stub.calls == ["a"]
    assert all(MediaAttributeKey.JAP in language_ids(ts) and ts.has_hungarian_sub for ts in streams)

    # Cached now: neither a new search nor a new request fetches again.
    source_search(definitions)._prefetch_tech_info(items)
    await streams_service(definitions)._enrich_torrent_streams_with_tech_info([stream("a")])
    assert stub.calls == ["a"]


@pytest.mark.anyio
async def test_process_wide_cap_skips_the_excess(prefetch_on, budget, monkeypatch):
    monkeypatch.setattr(config, "tech_info_prefetch_max_in_flight", 3)
    stub = TechInfoStub(gated=True)
    definitions = Definitions(ncore=stub)

    assert tech_info_cache.prefetch([(("ncore", f"t{i}"), stub) for i in range(5)]) == 3
    await asyncio.sleep(0)
    assert tech_info_cache.in_flight_count() == 3
    assert stub.calls == ["t0", "t1", "t2"]

    # At full capacity the request falls back to today's inline, cancellable fetch: no new owned task.
    ts = stream("t9")
    await streams_service(definitions)._enrich_torrent_streams_with_tech_info([ts])
    assert tech_info_cache.in_flight_count() == 3
    assert stub.cancelled == ["t9"]

    stub.release()
    flights = [tech_info_cache.in_flight(("ncore", f"t{i}")) for i in range(3)]
    await asyncio.gather(*(flight.task for flight in flights if flight is not None))
    assert sorted(stub.calls) == ["t0", "t1", "t2", "t9"]  # the skipped t3/t4 were never queued
    assert tech_info_cache.in_flight_count() == 0


@pytest.mark.anyio
async def test_request_waits_only_the_remaining_budget(prefetch_on, budget):
    stub = TechInfoStub(gated=True)
    service = streams_service(Definitions(ncore=stub))
    loop = asyncio.get_running_loop()

    tech_info_cache.prefetch([(("ncore", "early"), stub)])
    await asyncio.sleep(0.25)  # the source search downloads .torrent files meanwhile
    began = loop.time()
    await service._enrich_torrent_streams_with_tech_info([stream("early")])
    assert loop.time() - began < 0.2  # only the ~0.05 s left of the 0.3 s budget

    # A key the request itself starts gets the whole budget, never more.
    began = loop.time()
    await service._enrich_torrent_streams_with_tech_info([stream("late")])
    assert 0.2 <= loop.time() - began < 1.0
    assert stub.cancelled == []  # timeouts do not cancel owned background work


@pytest.mark.anyio
async def test_after_timeout_background_fills_cache_and_next_request_does_not_fetch(prefetch_on, budget):
    stub = TechInfoStub(delay=0.5)
    service = streams_service(Definitions(ncore=stub))
    loop = asyncio.get_running_loop()

    first = stream("a")
    began = loop.time()
    await service._enrich_torrent_streams_with_tech_info([first])
    assert loop.time() - began < 0.5
    assert MediaAttributeKey.JAP not in language_ids(first)

    flight = tech_info_cache.in_flight(("ncore", "a"))
    assert flight is not None
    await asyncio.wait_for(flight.task, 2)
    assert tech_info_cache.get_cached(("ncore", "a")) is not None
    assert tech_info_cache.in_flight_count() == 0

    second = stream("a")
    await service._enrich_torrent_streams_with_tech_info([second])
    assert stub.calls == ["a"]
    assert MediaAttributeKey.JAP in language_ids(second)
    assert MediaAttributeKey.ENG not in language_ids(second)
    assert second.has_hungarian_sub


@pytest.mark.anyio
async def test_failure_is_not_cached_but_empty_result_is(prefetch_on):
    stub = TechInfoStub({"empty": (None, None)}, failures=frozenset({"bad"}))
    keys = [("ncore", "bad"), ("ncore", "empty")]

    assert tech_info_cache.prefetch([(key, stub) for key in keys]) == 2
    flights = [tech_info_cache.in_flight(key) for key in keys]
    results = await asyncio.gather(*(flight.task for flight in flights if flight is not None))
    assert results[0] is None and results[1] is not None
    assert tech_info_cache.get_cached(("ncore", "bad")) is None
    assert tech_info_cache.get_cached(("ncore", "empty")) is not None
    assert tech_info_cache.in_flight_count() == 0

    await streams_service(Definitions(ncore=stub))._enrich_torrent_streams_with_tech_info([stream("bad"), stream("empty")])
    assert sorted(stub.calls) == ["bad", "bad", "empty"]  # the failure is retried, the empty result is not


@pytest.mark.anyio
async def test_cancelled_request_leaves_background_running(prefetch_on, budget, monkeypatch):
    monkeypatch.setattr(config, "tech_info_prefetch_max_in_flight", 1)
    stub = TechInfoStub(gated=True)
    service = streams_service(Definitions(ncore=stub))
    tech_info_cache.prefetch([(("ncore", "owned"), stub)])

    request = asyncio.create_task(service._enrich_torrent_streams_with_tech_info([stream("owned"), stream("inline")]))
    await asyncio.sleep(0.05)
    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await request
    assert stub.cancelled == ["inline"]  # the request's own inline fetch is joined, not orphaned
    flight = tech_info_cache.in_flight(("ncore", "owned"))
    assert flight is not None and not flight.task.done()


@pytest.mark.anyio
async def test_shutdown_cancels_and_awaits_every_prefetch(prefetch_on):
    stub = TechInfoStub(gated=True)
    keys = [("ncore", "a"), ("ncore", "b")]
    tech_info_cache.prefetch([(key, stub) for key in keys])
    await asyncio.sleep(0)
    tasks = [flight.task for key in keys if (flight := tech_info_cache.in_flight(key)) is not None]
    assert len(tasks) == 2

    await tech_info_cache.close_tech_info_prefetch()
    assert all(task.cancelled() for task in tasks)
    assert sorted(stub.cancelled) == ["a", "b"]
    assert tech_info_cache.in_flight_count() == 0
    assert not [task for task in asyncio.all_tasks() if task.get_name().startswith("tech-info-prefetch")]
    assert tech_info_cache.get_cached(("ncore", "a")) is None

    # Closed: no new owned work until the next lifespan opens it again.
    assert tech_info_cache.prefetch([(("ncore", "c"), stub)]) == 0
    tech_info_cache.open_tech_info_prefetch()
    assert tech_info_cache.prefetch([(("ncore", "c"), stub)]) == 1


@pytest.mark.anyio
async def test_attributes_identical_to_legacy_when_details_are_fast(prefetch_on, monkeypatch):
    responses: dict[str, tuple[str | None, str | None]] = {
        "jap": (NFO_JAP, DESC_HUN_SUB),
        "hun": (NFO_HUN, None),
        "dual": (NFO_DUAL, None),
        "empty": (None, None),
        "late": (NFO_JAP, None),  # 6th group: beyond the per-request enrichment limit
    }

    def build() -> list[TorrentStream]:
        return [
            stream("jap"),
            stream("jap", file_index=1),
            stream("hun"),
            stream("dual"),
            stream("bad"),
            stream("x", indexer_id="other"),
            stream("empty"),
            stream("late"),
        ]

    def definitions() -> Definitions:
        return Definitions(ncore=TechInfoStub(responses, failures=frozenset({"bad"})), other=non_provider())

    monkeypatch.setattr(config, "tech_info_prefetch", False)
    legacy = build()
    await streams_service(definitions())._enrich_torrent_streams_with_tech_info(legacy)

    monkeypatch.setattr(tech_info_cache, "_TECH_INFO_CACHE", {})
    monkeypatch.setattr(config, "tech_info_prefetch", True)
    current = definitions()
    source_search(current)._prefetch_tech_info(
        [candidate(tid, seeders=100 - i) for i, tid in enumerate(["late", "jap", "hun", "dual", "bad"])]
    )
    prefetched = build()
    await streams_service(current)._enrich_torrent_streams_with_tech_info(prefetched)

    assert snapshot(prefetched) == snapshot(legacy)
    assert MediaAttributeKey.JAP in language_ids(legacy[0]) and legacy[0].has_hungarian_sub  # the fixture enriches


def test_defaults_are_the_gate_passed_prefetch():
    from app.config import Config

    fields = Config.model_fields
    assert fields["tech_info_prefetch"].default is True
    assert fields["tech_info_prefetch_top_n"].default == 5
    assert fields["tech_info_prefetch_max_in_flight"].default == 20
    assert fields["tech_info_prefetch_timeout_seconds"].default == 10.0
    assert Config.model_validate({"tech_info_prefetch": "false"}).tech_info_prefetch is False
