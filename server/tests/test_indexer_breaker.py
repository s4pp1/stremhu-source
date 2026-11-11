"""SP05/b: tracker circuit breaker (IndexerHealth) on the IMDb, query and torrent-id searches.

Plan E/B/M/V matrix: healthy path unchanged, K timeouts open, open skips without a network
call, exactly one probe after the cooldown, probe success closes / failure doubles up to the
cap, invalidation resets, auth/parse errors and slow successes do not count, trackers are
independent, threshold 0 is the legacy path. Real file SQLite for the account rows; tracker
adapters are synthetic doubles (one real BaseIndexerDefinition subclass for the wrapping).
"""

import asyncio
import itertools
import time
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common import database
from app.common.database import Base
from app.config import config
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
    IndexerClient,
)
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    IndexerDefinitionException,
)
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexer_definitions.schemas.internal import (
    AuthCredentialError,
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionTorrent,
)
from app.modules.indexers import search
from app.modules.indexers.search import (
    IndexerHealth,
    IndexerSearchService,
    invalidate_indexer_cache,
    is_unreachable_error,
)

TIMEOUT = "A(z) 'Bad Tracker' indexer nem válaszolt időben."
WRAPPED = "Bad Tracker nem érhető el vagy megváltozott a struktúrája."
PROBING = "Bad Tracker: átmenetileg kihagyva, nem válaszolt; újrapróba folyamatban"


def skipped(seconds: int) -> str:
    return f"Bad Tracker: átmenetileg kihagyva, nem válaszolt; újrapróba kb. {seconds} s múlva"


METHODS = [
    ("get_torrents_by_imdb_id", "tt0000001"),
    ("get_torrents_by_query", "fixture title"),
    ("get_torrents_by_torrent_id", "fixture-id"),
]


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _raise_wrapped(error: Exception) -> None:
    # Like BaseIndexerDefinition._find_all: every error becomes a generic one "from None".
    try:
        raise error
    except Exception:
        raise IndexerDefinitionException(WRAPPED) from None


class _Scripted:
    """Synthetic tracker; `mode` decides the next answer, `gate` holds a call open."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.mode = "ok"
        self.delay = 0.0
        self.calls = 0
        self.downloads = 0
        self.gate: asyncio.Event | None = None

    async def _answer(self, torrent_id: str) -> SimpleNamespace:
        self.calls += 1
        if self.gate is not None:
            await self.gate.wait()
        if self.mode == "timeout":
            await asyncio.sleep(30)
        elif self.mode == "connect":
            _raise_wrapped(httpx.ConnectError("refused"))
        elif self.mode == "auth":
            _raise_wrapped(AuthenticationException("Sikertelen bejelentkezés."))
        elif self.mode == "parse":
            _raise_wrapped(ValueError("unexpected markup"))
        if self.delay:
            await asyncio.sleep(self.delay)
        return SimpleNamespace(torrent_id=torrent_id, download_url=f"https://{self.prefix}.invalid/{torrent_id}",
                               imdb_id="tt0000001", seeders=3, attribute_ids=[])

    async def find_torrents_by_imdb_id(self, imdb_id):
        return [await self._answer(f"{self.prefix}-imdb")]

    async def find_torrents_by_query(self, query, media_type=None):
        return [await self._answer(f"{self.prefix}-query")]

    async def find_torrent_by_id(self, torrent_id):
        return await self._answer(f"{self.prefix}-{torrent_id}")

    async def download_torrent(self, download_url):
        self.downloads += 1
        return b"d4:infod4:name1:xee"


@pytest.fixture
def trackers(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'breaker.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    with session_factory() as db:
        for indexer_id, name in (("good", "Good Tracker"), ("bad", "Bad Tracker")):
            definition = IndexerDefinitionModel(id=indexer_id, name=name, url=f"https://{indexer_id}.invalid",
                                                details_path="/")
            account = IndexerAccountModel(indexer_id=indexer_id, username="fixture", password="fixture")
            account.indexer_definition = definition
            db.add_all([definition, account])
        db.commit()
    clock = _Clock()
    monkeypatch.setattr(search, "indexer_health", IndexerHealth(clock))
    monkeypatch.setattr(search, "INDEXER_SEARCH_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(config, "indexer_breaker_threshold", 2)
    monkeypatch.setattr(config, "indexer_breaker_cooldown_seconds", 120.0)
    monkeypatch.setattr(config, "indexer_breaker_cooldown_max_seconds", 600.0)
    invalidate_indexer_cache()
    adapters = {"good": _Scripted("good"), "bad": _Scripted("bad")}
    service = IndexerSearchService(cast(Any, SimpleNamespace(get_by_id=adapters.__getitem__)))
    try:
        yield SimpleNamespace(service=service, good=adapters["good"], bad=adapters["bad"], clock=clock)
    finally:
        invalidate_indexer_cache()
        engine.dispose()


def _state(indexer_id: str) -> Any:
    return search.indexer_health._states.get(indexer_id)


_fresh_ids = itertools.count(1_000_000)


async def _search(fx, method: str = "get_torrents_by_imdb_id", argument: str | None = None):
    # A fresh IMDb id per call by default: a tracker-cache hit would make no network call.
    argument = argument or f"tt{next(_fresh_ids)}"
    torrents, errors = await asyncio.wait_for(getattr(fx.service, method)(argument), 5)
    return sorted(t.torrent_id for t in torrents), errors


async def _open_bad(fx, method: str = "get_torrents_by_imdb_id", argument: str | None = None) -> None:
    fx.bad.mode = "timeout"
    for _ in range(2):
        assert (await _search(fx, method, argument))[1] == [TIMEOUT]
    assert _state("bad").open_until is not None


# E: healthy tracker -> no extra latency, never opens.
@pytest.mark.anyio
@pytest.mark.parametrize(("method", "argument"), METHODS)
async def test_healthy_trackers_keep_results_without_delay_and_never_open(trackers, method, argument):
    fx = trackers
    began = time.perf_counter()
    for index in range(10):
        ids, errors = await _search(fx, method, f"{argument}-{index}")
        assert errors == []
        assert len(ids) == 2
    # Ten searches with instant adapters: any breaker wait would show up as seconds.
    assert time.perf_counter() - began < 2.0
    assert fx.bad.calls == fx.good.calls == 10
    for indexer_id in ("good", "bad"):
        state = _state(indexer_id)
        assert state.failures == 0 and state.open_until is None and not state.probing


# E: K timeouts -> open; the next search answers without a network call.
@pytest.mark.anyio
@pytest.mark.parametrize(("method", "argument"), METHODS)
async def test_k_timeouts_open_and_open_breaker_skips_without_network_call(trackers, method, argument):
    fx = trackers
    await _open_bad(fx, method, argument)
    assert fx.bad.calls == 2

    began = time.perf_counter()
    ids, errors = await _search(fx, method, argument)
    assert time.perf_counter() - began < 0.2  # no wait for the 0.2 s timeout
    assert fx.bad.calls == 2
    assert errors == [skipped(120)]
    assert len(ids) == 1 and ids[0].startswith("good-")

    fx.clock.now += 30.4
    assert (await _search(fx, method, argument))[1] == [skipped(90)]
    assert fx.bad.calls == 2


@pytest.mark.anyio
async def test_connection_errors_count_like_timeouts(trackers):
    fx = trackers
    fx.bad.mode = "connect"
    assert (await _search(fx))[1] == [WRAPPED]
    assert _state("bad").open_until is None
    assert (await _search(fx))[1] == [WRAPPED]
    assert (await _search(fx))[1] == [skipped(120)]
    assert fx.bad.calls == 2


@pytest.mark.anyio
async def test_only_consecutive_failures_open(trackers):
    fx = trackers
    for mode in ["timeout", "ok", "timeout", "ok", "timeout"]:
        fx.bad.mode = mode
        await _search(fx)
    state = _state("bad")
    assert state.open_until is None and state.failures == 1
    assert fx.bad.calls == 5


# E: expired cooldown with concurrent searches -> exactly one probe, the others skip.
@pytest.mark.anyio
async def test_expired_cooldown_sends_exactly_one_probe_while_others_skip(trackers):
    fx = trackers
    await _open_bad(fx)
    fx.clock.now += 120.0
    fx.bad.mode = "ok"
    fx.bad.gate = asyncio.Event()

    tasks = [asyncio.create_task(_search(fx, argument=f"tt00000{index:02d}")) for index in range(5)]
    for _ in range(300):
        await asyncio.sleep(0.01)
        if sum(task.done() for task in tasks) == 4:
            break
    assert fx.bad.calls == 3  # two failures + exactly one probe
    finished = [task.result() for task in tasks if task.done()]
    assert len(finished) == 4
    assert all(errors == [PROBING] for _, errors in finished)
    assert _state("bad").probing

    fx.bad.gate.set()
    ids, errors = await [task for task in tasks if not task.done()][0]
    assert errors == [] and "bad-imdb" in ids
    # Probe success: closed, counter zero, cooldown back to the base.
    state = _state("bad")
    assert state.open_until is None and state.failures == 0 and state.cooldown == 0.0 and not state.probing
    fx.bad.gate = None
    assert (await _search(fx, argument="tt0000099"))[1] == []
    assert fx.bad.calls == 4


@pytest.mark.anyio
async def test_probe_success_restarts_from_base_cooldown(trackers):
    fx = trackers
    await _open_bad(fx)
    fx.clock.now += 121.0
    fx.bad.mode = "ok"
    assert (await _search(fx))[1] == []
    # One later timeout is below K again; the next opening uses the base 120 s.
    fx.bad.mode = "timeout"
    assert (await _search(fx))[1] == [TIMEOUT]
    assert _state("bad").open_until is None
    assert (await _search(fx))[1] == [TIMEOUT]
    assert (await _search(fx))[1] == [skipped(120)]


# E: failed probe -> doubled cooldown, capped.
@pytest.mark.anyio
async def test_failed_probe_doubles_cooldown_up_to_the_cap(trackers):
    fx = trackers
    await _open_bad(fx)
    calls = fx.bad.calls
    for expected in [240, 480, 600, 600]:
        fx.clock.now += _state("bad").cooldown + 0.5
        assert (await _search(fx))[1] == [TIMEOUT]  # the probe went out and failed
        calls += 1
        assert fx.bad.calls == calls
        assert _state("bad").cooldown == expected
        assert (await _search(fx))[1] == [skipped(expected)]
        assert fx.bad.calls == calls


@pytest.mark.anyio
async def test_cancelled_probe_frees_the_probe_slot(trackers):
    fx = trackers
    await _open_bad(fx)
    fx.clock.now += 121.0
    fx.bad.gate = asyncio.Event()
    probe = asyncio.create_task(_search(fx))
    for _ in range(300):
        await asyncio.sleep(0.01)
        if fx.bad.calls == 3:
            break
    assert _state("bad").probing
    probe.cancel()
    with pytest.raises(asyncio.CancelledError):
        await probe
    assert not _state("bad").probing
    fx.bad.gate = None
    fx.bad.mode = "ok"
    assert (await _search(fx))[1] == []
    assert fx.bad.calls == 4


# E: invalidation -> closed.
@pytest.mark.anyio
@pytest.mark.parametrize("scope", ["bad", None])
async def test_invalidation_resets_an_open_breaker(trackers, scope):
    fx = trackers
    await _open_bad(fx)
    invalidate_indexer_cache(scope)
    assert _state("bad") is None
    fx.bad.mode = "ok"
    assert (await _search(fx))[1] == []
    assert fx.bad.calls == 3


@pytest.mark.anyio
async def test_outcome_of_a_request_started_before_invalidation_is_ignored(trackers):
    fx = trackers
    await _open_bad(fx)
    fx.clock.now += 121.0
    fx.bad.gate = asyncio.Event()
    fx.bad.mode = "connect"
    probe = asyncio.create_task(_search(fx))
    for _ in range(300):
        await asyncio.sleep(0.01)
        if fx.bad.calls == 3:
            break
    invalidate_indexer_cache("bad")
    fx.bad.gate.set()
    assert (await probe)[1] == [WRAPPED]
    # The stale failure neither reopened nor counted towards the fresh state.
    assert _state("bad") is None
    fx.bad.gate = None
    assert (await _search(fx))[1] == [WRAPPED]
    assert _state("bad").failures == 1 and _state("bad").open_until is None


# E: auth error / slow success -> not a failure.
@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auth", "parse"])
async def test_answered_errors_never_open(trackers, mode):
    fx = trackers
    fx.bad.mode = mode
    for _ in range(5):
        assert (await _search(fx))[1] == [WRAPPED]
    assert fx.bad.calls == 5
    state = _state("bad")
    assert state.open_until is None and state.failures == 0


@pytest.mark.anyio
async def test_answered_error_resets_the_consecutive_count(trackers):
    fx = trackers
    for mode in ["timeout", "auth", "timeout"]:
        fx.bad.mode = mode
        await _search(fx)
    assert _state("bad").open_until is None and _state("bad").failures == 1


@pytest.mark.anyio
async def test_slow_but_successful_answers_never_open(trackers, monkeypatch):
    fx = trackers
    monkeypatch.setattr(search, "INDEXER_SEARCH_TIMEOUT_SECONDS", 3.0)
    fx.bad.delay = 0.3
    for index in range(4):
        ids, errors = await _search(fx, argument=f"tt00001{index:02d}")
        assert errors == [] and "bad-imdb" in ids
    assert fx.bad.calls == 4
    assert _state("bad").open_until is None and _state("bad").failures == 0


# E: several trackers -> independent.
@pytest.mark.anyio
async def test_trackers_are_independent(trackers):
    fx = trackers
    await _open_bad(fx)
    good_calls = fx.good.calls
    for index in range(3):
        ids, errors = await _search(fx, argument=f"tt00002{index:02d}")
        assert ids == ["good-imdb"] and errors == [skipped(120)]
    assert fx.good.calls == good_calls + 3
    assert _state("good").open_until is None and _state("good").failures == 0


def test_defaults_are_the_gate_passed_breaker():
    # gsp05-v1 PASS (2026-11-10): K = 2, 120 s doubling to 600 s (UX frame row 4); 0 switches it off.
    from app.config import Config

    fields = Config.model_fields
    assert fields["indexer_breaker_threshold"].default == 2
    assert fields["indexer_breaker_cooldown_seconds"].default == 120.0
    assert fields["indexer_breaker_cooldown_max_seconds"].default == 600.0
    assert Config.model_validate({"indexer_breaker_threshold": 0}).indexer_breaker_threshold == 0


# E: threshold 0 -> legacy behaviour, no state at all.
@pytest.mark.anyio
@pytest.mark.parametrize(("method", "argument"), METHODS)
async def test_threshold_zero_is_the_legacy_path(trackers, monkeypatch, method, argument):
    fx = trackers
    monkeypatch.setattr(config, "indexer_breaker_threshold", 0)
    fx.bad.mode = "timeout"
    for _ in range(4):
        ids, errors = await _search(fx, method, argument)
        assert errors == [TIMEOUT] and len(ids) == 1
    assert fx.bad.calls == 4
    assert search.indexer_health._states == {}


@pytest.mark.anyio
async def test_cached_results_are_served_while_the_tracker_is_skipped(trackers):
    fx = trackers
    assert "bad-imdb" in (await _search(fx, argument="tt0000500"))[0]
    await _open_bad(fx, argument="tt0000501")
    ids, errors = await _search(fx, argument="tt0000500")
    # Tracker cache hit: no network call, so nothing to skip and no error.
    assert "bad-imdb" in ids and errors == []
    assert fx.bad.calls == 3


@pytest.mark.anyio
async def test_torrent_downloads_are_not_gated(trackers):
    fx = trackers
    await _open_bad(fx)
    downloaded = await fx.service.download_torrent("bad", "bad-imdb", "https://bad.invalid/bad-imdb")
    assert downloaded.torrent_bytes and fx.bad.downloads == 1


def test_error_classification():
    def wrapped(error: Exception) -> BaseException:
        try:
            _raise_wrapped(error)
        except IndexerDefinitionException as result:
            return result
        raise AssertionError

    assert is_unreachable_error(TimeoutError())
    assert is_unreachable_error(wrapped(httpx.ConnectError("x")))
    assert is_unreachable_error(wrapped(httpx.ReadTimeout("x")))
    assert is_unreachable_error(wrapped(ConnectionResetError()))
    assert not is_unreachable_error(wrapped(AuthenticationException("x")))
    assert not is_unreachable_error(wrapped(ValueError("x")))
    response = httpx.Response(503, request=httpx.Request("GET", "https://bad.invalid"))
    assert not is_unreachable_error(wrapped(httpx.HTTPStatusError("x", request=response.request, response=response)))
    assert not is_unreachable_error(IndexerDefinitionException("Az indexer leállítás alatt áll."))


class _RealAdapter(BaseIndexerDefinition):
    """Real base-class wrapping: transport errors and auth answers as the product sees them."""

    def __init__(self, handler) -> None:
        super().__init__()
        self._client = IndexerClient(definition=self, base_url=self.url, transport=httpx.MockTransport(handler))

    @property
    def id(self) -> str:
        return "bad"

    @property
    def name(self) -> str:
        return "Bad Tracker"

    @property
    def url(self) -> str:
        return "https://bad.invalid"

    @property
    def login_path(self) -> str:
        return "/login"

    @property
    def details_path(self) -> str:
        return "/details/{torrent_id}"

    @property
    def requires_full_download(self) -> bool:
        return False

    def _detect_authentication_error(self, response):
        return AuthCredentialError(message="Hibás jelszó.") if response.status_code == 403 else None

    async def _login(self, payload):
        raise NotImplementedError

    async def _fetch_torrents(self, imdb_id, page=None):
        response = await self._client.get("/search")
        return IndexerDefinitionFindTorrentsResult(
            torrents=[IndexerDefinitionTorrent(torrent_id="real", download_url="https://bad.invalid/real",
                                               imdb_id=imdb_id, seeders=1)] if response.status_code == 200 else [])

    async def _fetch_torrent(self, torrent_id):
        return None

    async def _fetch_hit_and_run_ids(self):
        return []


@pytest.mark.anyio
@pytest.mark.parametrize(("failure", "opens"), [("connect", True), ("auth", False)])
async def test_real_adapter_wrapping_is_classified(trackers, failure, opens):
    fx = trackers

    def handler(request: httpx.Request) -> httpx.Response:
        if failure == "connect":
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(403, request=request)

    adapter = _RealAdapter(handler)
    service = IndexerSearchService(cast(Any, SimpleNamespace(get_by_id={"good": fx.good, "bad": adapter}.__getitem__)))
    try:
        seen = [(await asyncio.wait_for(service.get_torrents_by_imdb_id(f"tt00003{index:02d}"), 5))[1]
                for index in range(3)]
        # Auth answers and transport errors both surface as the base class's generic text.
        assert seen[:2] == [[WRAPPED], [WRAPPED]]
        assert seen[2] == ([skipped(120)] if opens else [WRAPPED])
        assert (_state("bad").open_until is not None) is opens
    finally:
        await adapter.close()
