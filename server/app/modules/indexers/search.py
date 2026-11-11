import asyncio
import math
import time
import weakref
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from fastapi import HTTPException, status

from app.common.async_utils import await_owned_task, owned_to_thread
from app.common.database import shared_read_session
from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.config import config
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.indexer_accounts.schemas import IndexerAccountRef
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    AuthenticationOtherException,
    CredentialsRequiredException,
)
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.indexers.schemas.internal import DownloadedTorrentFile, IndexerTorrent
from app.modules.media_attributes.utils import resolve_attribute_ids
from app.modules.stremio.cache import stream_cache_state

# SP07: ez a puha TTL; a kemény TTL a `config.indexer_cache_hard_ttl_seconds`.
_IMDB_TRACKER_CACHE_TTL = 1800.0
_IMDB_TRACKER_CACHE_MAX = 1000
ImdbCacheKey = tuple[str, str]
_imdb_tracker_cache: dict[ImdbCacheKey, tuple[float, list[Any]]] = {}
# SP07: minden invalidálás növeli (teljes / indexerenkénti); a korábbi generációban indult
# háttérfrissítés eredménye nem kerül a cache-be.
_imdb_cache_generation = 0
_imdb_indexer_generations: dict[str, int] = {}

_QUERY_TRACKER_CACHE_TTL = 300.0
_QUERY_TRACKER_CACHE_MAX = 1000
_query_tracker_cache: dict[tuple[str, str, str], tuple[float, list[Any]]] = {}

# Egy tracker egy keresési hívásának felső határa (SP05/a: egyetlen helyen).
INDEXER_SEARCH_TIMEOUT_SECONDS = 12.5

_T = TypeVar("_T")

# SP05/b: csak ezek számítanak „nem válaszolt” hibának (időtúllépés, kapcsolódási hiba).
_UNREACHABLE_ERRORS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    httpx.TimeoutException,
    httpx.NetworkError,
)
# A tracker válaszolt, csak elutasította a kérést: nem rövidzár-hiba.
_ANSWERED_ERRORS: tuple[type[BaseException], ...] = (
    AuthenticationException,
    AuthenticationOtherException,
    CredentialsRequiredException,
)
_ERROR_CHAIN_DEPTH = 8


def is_unreachable_error(error: BaseException) -> bool:
    """SP05/b: időtúllépés vagy kapcsolódási hiba-e, a becsomagolt okot is nézve.

    Az adapterek a hálózati hibát `IndexerDefinitionException(...) from None` formában adják
    tovább; az eredeti hiba a `__context__`-ben marad. Hitelesítési, feldolgozási és HTTP-
    státuszhiba (a tracker válaszolt) nem számít.
    """
    current: BaseException | None = error
    for _ in range(_ERROR_CHAIN_DEPTH):
        if current is None:
            return False
        if isinstance(current, _UNREACHABLE_ERRORS):
            return True
        if isinstance(current, _ANSWERED_ERRORS):
            return False
        current = current.__cause__ or current.__context__
    return False


class IndexerSkippedError(Exception):
    """SP05/b: a tracker átmenetileg kimarad; hálózati kérés nem indult."""


@dataclass
class _BreakerState:
    failures: int = 0
    # Nyitott állapot: a kihagyás vége (monoton óra). None: zárt.
    open_until: float | None = None
    # Az utolsó nyitás kihagyási ideje; a sikertelen próba duplázza.
    cooldown: float = 0.0
    probing: bool = False


@dataclass(frozen=True)
class _BreakerTicket:
    indexer_id: str
    # None: a rövidzár ki van kapcsolva (legacy út, nincs állapot).
    state: _BreakerState | None = None
    probe: bool = False


_DISABLED_TICKET = _BreakerTicket(indexer_id="")


class IndexerHealth:
    """SP05/b: process-szintű tracker-egészség (rövidzár), `indexer_id` szerint.

    Csak az event loopról használható, egy processzre: az állapotváltások között nincs await,
    ezért zár nem kell. A beállítást (`config.indexer_breaker_*`) hívásonként olvassa; 0-s
    küszöbnél semmilyen állapotot nem tart (a mai viselkedés).
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._states: dict[str, _BreakerState] = {}

    def acquire(self, indexer_id: str, name: str) -> _BreakerTicket:
        """Engedély egy hálózati keresésre; nyitott állapotban `IndexerSkippedError`."""
        if config.indexer_breaker_threshold <= 0:
            return _DISABLED_TICKET
        state = self._states.setdefault(indexer_id, _BreakerState())
        if state.open_until is None:
            return _BreakerTicket(indexer_id, state)
        if state.probing:
            raise IndexerSkippedError(
                f"{name}: átmenetileg kihagyva, nem válaszolt; újrapróba folyamatban"
            )
        remaining = state.open_until - self._clock()
        if remaining > 0:
            raise IndexerSkippedError(
                f"{name}: átmenetileg kihagyva, nem válaszolt; "
                f"újrapróba kb. {max(1, math.ceil(remaining))} s múlva"
            )
        # Lejárt kihagyás: pontosan egy próbakérés; a többi a kimeneteléig kihagy.
        state.probing = True
        return _BreakerTicket(indexer_id, state, probe=True)

    def record(self, ticket: _BreakerTicket, error: BaseException | None) -> None:
        """Egy engedélyezett keresés kimenetele (siker, hiba vagy megszakítás)."""
        state = ticket.state
        # Kikapcsolt rövidzár, vagy közben invalidált (alaphelyzetbe állított) állapot.
        if state is None or self._states.get(ticket.indexer_id) is not state:
            return
        if error is None or (isinstance(error, Exception) and not is_unreachable_error(error)):
            self._answered(ticket.indexer_id, state)
        elif isinstance(error, Exception):
            self._failed(ticket.indexer_id, state, ticket.probe)
        elif ticket.probe and state.probing:
            # Megszakított próba (pl. a megosztott keresés törlése): a következő kérés próbál.
            state.probing = False

    def _answered(self, indexer_id: str, state: _BreakerState) -> None:
        if state.open_until is not None:
            logger.warning("⚠️ Tracker-rövidzár zárva: indexer=%s újra válaszol.", indexer_id)
        state.failures = 0
        state.open_until = None
        state.cooldown = 0.0
        state.probing = False

    def _failed(self, indexer_id: str, state: _BreakerState, probe: bool) -> None:
        base = config.indexer_breaker_cooldown_seconds
        cap = max(base, config.indexer_breaker_cooldown_max_seconds)
        if probe and state.probing:
            state.probing = False
            state.cooldown = min(max(state.cooldown, base) * 2, cap)
        elif state.open_until is not None:
            # Még zárt állapotban indult kérés késői hibája: a nyitott állapot nem hosszabbodik.
            return
        else:
            state.failures += 1
            if state.failures < config.indexer_breaker_threshold:
                return
            state.cooldown = min(base, cap)
        state.open_until = self._clock() + state.cooldown
        logger.warning(
            "⚠️ Tracker-rövidzár nyitva: indexer=%s, kihagyás %.0f s (nem válaszolt).",
            indexer_id,
            state.cooldown,
        )

    def reset(self, indexer_id: str | None = None) -> None:
        """Alaphelyzet (beállítás, bejelentkezés): a futó kérések kimenetele már nem számít."""
        if indexer_id is None:
            self._states.clear()
        else:
            self._states.pop(indexer_id, None)


indexer_health = IndexerHealth()


async def _with_indexer_timeout(
    indexer_account: IndexerAccountRef, operation: Callable[[], Awaitable[_T]]
) -> _T:
    """Egy tracker hálózati keresési hívása: rövidzár (SP05/b) és közös időkorlát (SP05/a).

    Időtúllépéskor olvasható hibaüzenet. Nyitott rövidzárnál az `operation` el sem indul.
    """
    name = indexer_account.indexer_definition.name
    health = indexer_health
    ticket = health.acquire(indexer_account.indexer_id, name)
    try:
        result = await asyncio.wait_for(operation(), timeout=INDEXER_SEARCH_TIMEOUT_SECONDS)
    except TimeoutError:
        error = TimeoutError(f"A(z) '{name}' indexer nem válaszolt időben.")
        health.record(ticket, error)
        raise error
    except BaseException as error:
        health.record(ticket, error)
        raise
    health.record(ticket, None)
    return result


class IndexerSearchResult(tuple[list[IndexerTorrent], list[str]]):
    """`(találatok, hibák)` pár; a kétértékes kicsomagolás és a tuple-egyenlőség változatlan.

    SP07: a `stale` igaz, ha legalább egy tracker puhán lejárt (régi) cache-listája van benne.
    """

    stale: bool

    def __new__(
        cls, torrents: list[IndexerTorrent], errors: list[str], *, stale: bool = False
    ) -> "IndexerSearchResult":
        result = super().__new__(cls, (torrents, errors))
        result.stale = stale
        return result


def stale_imdb_cache_enabled() -> bool:
    """SP07: van-e régi-találat ablak, azaz a kemény TTL a puha TTL fölött van-e."""
    return config.indexer_cache_hard_ttl_seconds > _IMDB_TRACKER_CACHE_TTL


def _imdb_cache_token(indexer_id: str) -> tuple[int, int]:
    return _imdb_cache_generation, _imdb_indexer_generations.get(indexer_id, 0)


def _store_imdb_cache(cache_key: ImdbCacheKey, torrents: list[Any]) -> None:
    # Meglévő kulcs (SP07: a frissített régi bejegyzés) cseréje nem szorít ki más bejegyzést.
    if cache_key not in _imdb_tracker_cache and len(_imdb_tracker_cache) >= _IMDB_TRACKER_CACHE_MAX:
        oldest_key = min(_imdb_tracker_cache, key=lambda k: _imdb_tracker_cache[k][0])
        _imdb_tracker_cache.pop(oldest_key, None)
    _imdb_tracker_cache[cache_key] = (time.monotonic(), list(torrents))


class _ImdbCacheRefresher:
    """SP07: puhán lejárt IMDb-trackerlisták háttérfrissítése; event looponként egy példány.

    Kulcsonként legfeljebb egy frissítés fut (in-flight deduplikáció), egyszerre legfeljebb
    `indexer_cache_refresh_max_in_flight`; a többlet kimarad, a régi lista marad. A frissítés
    a hívó által adott, a normál keresésével azonos úton fut (adapter-szemafor, időkorlát,
    rövidzár). A taskokat ez a példány tulajdonolja: a lifespan lezárása törli és megvárja őket.
    """

    def __init__(self) -> None:
        self.closed = False
        # Deduplikáció: csak az érvényes (nem invalidált) futó frissítések.
        self.flights: dict[ImdbCacheKey, asyncio.Task[list[Any] | None]] = {}
        # Tulajdon: minden még be nem fejeződött frissítés, az invalidálással töröltek is.
        self.tasks: set[asyncio.Task[list[Any] | None]] = set()

    def start(
        self, cache_key: ImdbCacheKey, fetch: Callable[[], Awaitable[list[Any]]]
    ) -> asyncio.Task[list[Any] | None] | None:
        """A kulcs futó frissítése, vagy egy új; `None`, ha a kapacitás tele vagy leállás van."""
        task = self.flights.get(cache_key)
        if task is not None:
            return task
        if self.closed or len(self.flights) >= config.indexer_cache_refresh_max_in_flight:
            return None
        task = asyncio.get_running_loop().create_task(
            self._refresh(cache_key, fetch), name="indexer-cache-refresh"
        )
        self.flights[cache_key] = task
        self.tasks.add(task)

        def finished(done: asyncio.Task[list[Any] | None]) -> None:
            self.tasks.discard(done)
            if self.flights.get(cache_key) is done:
                del self.flights[cache_key]

        task.add_done_callback(finished)
        return task

    async def _refresh(
        self, cache_key: ImdbCacheKey, fetch: Callable[[], Awaitable[list[Any]]]
    ) -> list[Any] | None:
        token = _imdb_cache_token(cache_key[0])
        try:
            torrents = list(await fetch())
        except Exception as error:
            # Frissítési hiba: a régi lista a kemény TTL-ig marad, a következő kérés újrapróbálja.
            logger.debug(
                "operation=indexer-cache-refresh indexer=%s %s",
                cache_key[0],
                network_error_fields(error),
            )
            return None
        if token == _imdb_cache_token(cache_key[0]):
            _store_imdb_cache(cache_key, torrents)
        return torrents

    def cancel(self, indexer_id: str | None) -> None:
        """Invalidálás: az érintett frissítések megszakadnak, és új kérés már nem csatlakozik."""
        for cache_key, task in tuple(self.flights.items()):
            if indexer_id is None or cache_key[0] == indexer_id:
                del self.flights[cache_key]
                task.cancel()

    async def aclose(self) -> None:
        self.closed = True

        async def cancel_all() -> None:
            while self.tasks:
                tasks = tuple(self.tasks)
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                # A done-callbackek később futnak: a befejezetteket itt vesszük ki.
                self.tasks.difference_update(task for task in tasks if task.done())
            self.flights.clear()

        await await_owned_task(asyncio.create_task(cancel_all(), name="indexer-cache-refresh-close"))


_refreshers: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, _ImdbCacheRefresher] = (
    weakref.WeakKeyDictionary()
)


def _refresher() -> _ImdbCacheRefresher:
    loop = asyncio.get_running_loop()
    refresher = _refreshers.get(loop)
    if refresher is None:
        refresher = _refreshers[loop] = _ImdbCacheRefresher()
    return refresher


def open_indexer_cache_refresh() -> None:
    _refresher().closed = False


async def close_indexer_cache_refresh() -> None:
    """Lifespan-lezárás: új háttérfrissítés nem indul, a futók megszakadnak, és bevárja őket."""
    await _refresher().aclose()


def _cancel_imdb_refreshes(indexer_id: str | None) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Event loopon kívül: a generációváltás akadályozza meg a régi eredmény tárolását.
        return
    refresher = _refreshers.get(loop)
    if refresher is not None:
        refresher.cancel(indexer_id)


def invalidate_indexer_cache(indexer_id: str | None = None) -> None:
    """M05: Indexer találati gyorsítótár invalidálása kijelentkezés, törlés vagy új hitelesítés esetén.

    SP05/b: a tracker rövidzár-állapota is alaphelyzetbe kerül.
    SP07: a régi (puhán lejárt) bejegyzés is törlődik, a futó háttérfrissítés nem írhat vissza.
    """
    global _imdb_cache_generation
    indexer_health.reset(indexer_id)
    if indexer_id is None:
        _imdb_cache_generation += 1
    else:
        _imdb_indexer_generations[indexer_id] = _imdb_indexer_generations.get(indexer_id, 0) + 1
    _cancel_imdb_refreshes(indexer_id)
    if indexer_id is None:
        _imdb_tracker_cache.clear()
        _query_tracker_cache.clear()
    else:
        for k in list(_imdb_tracker_cache.keys()):
            if k[0] == indexer_id:
                _imdb_tracker_cache.pop(k, None)
        for k in list(_query_tracker_cache.keys()):
            if k[0] == indexer_id:
                _query_tracker_cache.pop(k, None)


class IndexerSearchService:
    """Request-független indexerkeresés megosztott (Singleflight) taskokhoz.

    Csak a folyamatszintű indexer-definíció registryt tartja; az accountokat saját,
    rövid izolált Sessionben olvassa, és csak Session nélküli értéket ad vissza.
    """

    def __init__(self, indexer_definitions_service: IndexerDefinitionsService):
        self._indexer_definitions_service = indexer_definitions_service

    def _find_account_refs(self) -> list[IndexerAccountRef]:
        # Saját rövid Session: a megosztott keresés nem használhatja a request Sessiont.
        with shared_read_session() as db:
            return [
                IndexerAccountRef.from_model(indexer_account)
                for indexer_account in create_indexer_accounts_service(db).find_list()
            ]

    def _get_account_ref(self, indexer_id: str) -> IndexerAccountRef:
        with shared_read_session() as db:
            return IndexerAccountRef.from_model(
                create_indexer_accounts_service(db).get_by_id(indexer_id)
            )

    async def get_torrents_by_torrent_id(
        self,
        torrent_id: str,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        indexer_accounts = await owned_to_thread(self._find_account_refs)

        async def fetch_and_map(
            indexer_account: IndexerAccountRef,
        ) -> IndexerTorrent | None:
            indexer_definition = self._indexer_definitions_service.get_by_id(
                indexer_account.indexer_id
            )
            indexer_definition_torrent = await _with_indexer_timeout(
                indexer_account,
                lambda: indexer_definition.find_torrent_by_id(torrent_id),
            )

            if not indexer_definition_torrent:
                return None

            return IndexerTorrent(
                indexer_account=indexer_account,
                torrent_id=indexer_definition_torrent.torrent_id,
                download_url=indexer_definition_torrent.download_url,
                imdb_id=indexer_definition_torrent.imdb_id,
                seeders=indexer_definition_torrent.seeders,
                media_attributes=resolve_attribute_ids(
                    indexer_definition_torrent.attribute_ids
                ),
            )

        # A rövidzár és az időkorlát csak a hálózati hívást fogja (cache-találat kihagyáskor is él).
        tasks = [fetch_and_map(indexer_account) for indexer_account in indexer_accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        indexer_torrents: list[IndexerTorrent] = []
        errors: list[str] = []

        for result in results:
            if isinstance(result, BaseException):
                errors.append(str(result))
            elif result is not None:
                indexer_torrents.append(result)

        return indexer_torrents, errors

    async def get_torrent_by_torrent_id(
        self,
        indexer_id: str,
        torrent_id: str,
    ) -> IndexerTorrent:
        indexer_account = await owned_to_thread(self._get_account_ref, indexer_id)

        indexer_definition = self._indexer_definitions_service.get_by_id(
            indexer_account.indexer_id
        )
        indexer_definition_torrent = await indexer_definition.find_torrent_by_id(
            torrent_id
        )

        if not indexer_definition_torrent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A torrent nem található.",
            )

        return IndexerTorrent(
            indexer_account=indexer_account,
            torrent_id=indexer_definition_torrent.torrent_id,
            download_url=indexer_definition_torrent.download_url,
            imdb_id=indexer_definition_torrent.imdb_id,
            seeders=indexer_definition_torrent.seeders,
            media_attributes=resolve_attribute_ids(
                indexer_definition_torrent.attribute_ids
            ),
        )

    async def _imdb_tracker_torrents(
        self,
        indexer_account: IndexerAccountRef,
        cache_key: ImdbCacheKey,
        imdb_id: str,
        allow_stale: bool,
    ) -> tuple[list[Any], bool]:
        """Egy tracker IMDb-listája cache-ből vagy hálózatról; a második érték: régi lista-e (SP07)."""

        def fetch() -> Awaitable[list[Any]]:
            # A normál keresés útja: adapter-szemafor, trackerenkénti időkorlát (SP05/a), rövidzár (SP05/b).
            indexer_definition = self._indexer_definitions_service.get_by_id(
                indexer_account.indexer_id
            )
            return _with_indexer_timeout(
                indexer_account,
                lambda: indexer_definition.find_torrents_by_imdb_id(imdb_id),
            )

        cached = _imdb_tracker_cache.get(cache_key)
        if cached is not None:
            stored_at, cached_torrents = cached
            age = time.monotonic() - stored_at
            if age < _IMDB_TRACKER_CACHE_TTL:
                return cached_torrents, False
            if stale_imdb_cache_enabled() and age < config.indexer_cache_hard_ttl_seconds:
                return await self._stale_imdb_torrents(cache_key, cached_torrents, fetch, allow_stale)
            # Lejárt (kikapcsolt SP07-nél a puha, különben a kemény TTL): szinkron frissítés, mint ma.
            _imdb_tracker_cache.pop(cache_key, None)

        torrents = await fetch()
        _store_imdb_cache(cache_key, torrents)
        return torrents, False

    @staticmethod
    async def _stale_imdb_torrents(
        cache_key: ImdbCacheKey,
        stale_torrents: list[Any],
        fetch: Callable[[], Awaitable[list[Any]]],
        allow_stale: bool,
    ) -> tuple[list[Any], bool]:
        """SP07: puhán lejárt bejegyzés; frissítési hiba esetén mindig a régi lista marad."""
        refresh = _refresher().start(cache_key, fetch)
        if allow_stale:
            # A régi lista azonnal jön; a frissítés a háttérben fut (vagy teli kapacitásnál kimarad).
            return stale_torrents, True
        # Kényszerített frissítés (új epizód védelme): a futó háttérfrissítést várja meg; ha
        # nincs szabad hely, közvetlenül kérdez. A várakozó megszakítása a frissítést nem állítja le.
        if refresh is None:
            token = _imdb_cache_token(cache_key[0])
            try:
                torrents = list(await fetch())
            except Exception as error:
                logger.debug(
                    "operation=indexer-cache-refresh indexer=%s %s",
                    cache_key[0],
                    network_error_fields(error),
                )
                return stale_torrents, True
            if token == _imdb_cache_token(cache_key[0]):
                _store_imdb_cache(cache_key, torrents)
            return torrents, False
        await asyncio.wait({refresh})
        refreshed = None if refresh.cancelled() else refresh.result()
        if refreshed is None:
            return stale_torrents, True
        return refreshed, False

    async def get_torrents_by_imdb_id(
        self,
        imdb_id: str,
        *,
        allow_stale: bool = True,
    ) -> IndexerSearchResult:
        """IMDb-keresés minden trackeren; `allow_stale=False`: régi lista helyett szinkron frissítés (SP07)."""
        source_epoch = stream_cache_state.revision("")[0]
        indexer_accounts = await owned_to_thread(self._find_account_refs)
        stale_served = False

        async def fetch_and_map(
            indexer_account: IndexerAccountRef,
        ) -> list[IndexerTorrent]:
            nonlocal stale_served
            cache_key = (indexer_account.indexer_id, f"{source_epoch}:{imdb_id.strip().lower()}")
            indexer_definition_torrents, stale = await self._imdb_tracker_torrents(
                indexer_account, cache_key, imdb_id, allow_stale
            )
            stale_served = stale_served or stale

            return [
                IndexerTorrent(
                    indexer_account=indexer_account,
                    torrent_id=indexer_definition_torrent.torrent_id,
                    download_url=indexer_definition_torrent.download_url,
                    imdb_id=indexer_definition_torrent.imdb_id,
                    seeders=indexer_definition_torrent.seeders,
                    media_attributes=resolve_attribute_ids(
                        indexer_definition_torrent.attribute_ids
                    ),
                )
                for indexer_definition_torrent in indexer_definition_torrents
            ]

        # A rövidzár és az időkorlát csak a hálózati hívást fogja (cache-találat kihagyáskor is él).
        tasks = [fetch_and_map(indexer_account) for indexer_account in indexer_accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        indexer_torrents: list[IndexerTorrent] = []
        errors: list[str] = []

        for result in results:
            if isinstance(result, BaseException):
                errors.append(str(result))
            else:
                indexer_torrents.extend(result)

        return IndexerSearchResult(indexer_torrents, errors, stale=stale_served)

    async def get_torrents_by_query(
        self,
        query: str,
        media_type: str | None = None,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        indexer_accounts = await owned_to_thread(self._find_account_refs)

        async def fetch_and_map(
            indexer_account: IndexerAccountRef,
        ) -> list[IndexerTorrent]:
            cache_key = (
                indexer_account.indexer_id,
                query.strip().lower(),
                media_type or "all",
            )
            now = time.monotonic()
            indexer_definition_torrents: list[Any] | None = None
            cached = _query_tracker_cache.get(cache_key)
            if cached is not None:
                ts, cached_def_torrents = cached
                if now - ts < _QUERY_TRACKER_CACHE_TTL:
                    indexer_definition_torrents = cached_def_torrents
                else:
                    _query_tracker_cache.pop(cache_key, None)

            if indexer_definition_torrents is None:
                indexer_definition = self._indexer_definitions_service.get_by_id(
                    indexer_account.indexer_id
                )
                indexer_definition_torrents = await _with_indexer_timeout(
                    indexer_account,
                    lambda: indexer_definition.find_torrents_by_query(
                        query, media_type=media_type
                    ),
                )
                if len(_query_tracker_cache) >= _QUERY_TRACKER_CACHE_MAX:
                    oldest_key = min(
                        _query_tracker_cache, key=lambda k: _query_tracker_cache[k][0]
                    )
                    _query_tracker_cache.pop(oldest_key, None)
                _query_tracker_cache[cache_key] = (
                    now,
                    list(indexer_definition_torrents),
                )

            return [
                IndexerTorrent(
                    indexer_account=indexer_account,
                    torrent_id=indexer_definition_torrent.torrent_id,
                    download_url=indexer_definition_torrent.download_url,
                    imdb_id=indexer_definition_torrent.imdb_id,
                    seeders=indexer_definition_torrent.seeders,
                    media_attributes=resolve_attribute_ids(
                        indexer_definition_torrent.attribute_ids
                    ),
                )
                for indexer_definition_torrent in indexer_definition_torrents
            ]

        # A rövidzár és az időkorlát csak a hálózati hívást fogja (cache-találat kihagyáskor is él).
        tasks = [fetch_and_map(indexer_account) for indexer_account in indexer_accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        indexer_torrents: list[IndexerTorrent] = []
        errors: list[str] = []

        for result in results:
            if isinstance(result, BaseException):
                errors.append(str(result))
            else:
                indexer_torrents.extend(result)

        return indexer_torrents, errors

    async def download_torrent(
        self,
        indexer_id: str,
        torrent_id: str,
        download_url: str,
    ) -> DownloadedTorrentFile:
        indexer_definition = self._indexer_definitions_service.get_by_id(indexer_id)
        torrent_bytes = await indexer_definition.download_torrent(download_url)

        return DownloadedTorrentFile(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
            torrent_bytes=torrent_bytes,
        )
