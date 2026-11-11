"""Közös Tech Info gyorsítótár és háttérlekérés (SP06/b).

A cache-t a streamválasz dúsítása (``torrent_streams``) és a megosztott forráskeresés
előtöltése (``torrent_source_provider``) is használja. A Tech Info felhasználófüggetlen,
a kulcs ``(indexer_id, torrent_id)``.

- Csak sikeres lekérés kerül cache-be (SP06/a): a ``TechInfoUnavailableException`` vagy
  bármely más hiba nem mérgezi a cache-t, a következő kérés újrapróbálja.
- Háttérlekérés kulcsonként legfeljebb egy fut (in-flight deduplikáció); egyszerre
  legfeljebb ``tech_info_prefetch_max_in_flight``, a többlet kimarad.
- A háttértaskokat ez a modul tulajdonolja: a lifespan lezárása törli és megvárja őket.
"""

import asyncio
import time
import weakref
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from app.common.async_utils import await_owned_task
from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.config import config
from app.modules.media_attributes.tech_info_parser import (
    TechInfoMetadata,
    parse_tech_info_metadata,
)

TechInfoKey = tuple[str, str]

TECH_INFO_CACHE_TTL = 3600.0
TECH_INFO_CACHE_MAX = 5000
_TECH_INFO_CACHE: dict[TechInfoKey, tuple[float, TechInfoMetadata]] = {}


class TechInfoSource(Protocol):
    async def fetch_tech_info(self, torrent_id: str) -> tuple[str | None, str | None]: ...


def get_cached(key: TechInfoKey) -> TechInfoMetadata | None:
    """Friss cache-bejegyzés, vagy ``None``; a lejártat eltávolítja."""
    cached = _TECH_INFO_CACHE.get(key)
    if cached is None:
        return None
    stored_at, meta = cached
    if time.monotonic() - stored_at >= TECH_INFO_CACHE_TTL:
        _TECH_INFO_CACHE.pop(key, None)
        return None
    return meta


def store(key: TechInfoKey, meta: TechInfoMetadata, stored_at: float | None = None) -> None:
    if len(_TECH_INFO_CACHE) >= TECH_INFO_CACHE_MAX:
        _TECH_INFO_CACHE.pop(next(iter(_TECH_INFO_CACHE)), None)
    _TECH_INFO_CACHE[key] = (time.monotonic() if stored_at is None else stored_at, meta)


async def fetch_metadata(source: TechInfoSource, torrent_id: str) -> TechInfoMetadata:
    """Egy lekérés és feldolgozás; a hibát (pl. ``TechInfoUnavailableException``) továbbadja."""
    nfo_text, desc_text = await source.fetch_tech_info(torrent_id)
    return parse_tech_info_metadata(nfo_text or "", desc_text or "")


@dataclass(eq=False)
class TechInfoFlight:
    """Egy futó háttérlekérés; ``started`` az event loop ideje az indításkor."""

    task: asyncio.Task[TechInfoMetadata | None]
    started: float


class _TechInfoPrefetcher:
    """Event looponként egy példány (mint a forráskeresés függőbájt-kerete)."""

    def __init__(self) -> None:
        self.closed = False
        self.flights: dict[TechInfoKey, TechInfoFlight] = {}

    def start(self, key: TechInfoKey, source: TechInfoSource) -> TechInfoFlight | None:
        flight = self.flights.get(key)
        if flight is not None:
            return flight
        if self.closed or len(self.flights) >= config.tech_info_prefetch_max_in_flight:
            return None
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._fetch(key, source), name="tech-info-prefetch")
        flight = TechInfoFlight(task=task, started=loop.time())
        self.flights[key] = flight

        def finished(_: asyncio.Task[TechInfoMetadata | None]) -> None:
            if self.flights.get(key) is flight:
                del self.flights[key]

        task.add_done_callback(finished)
        return flight

    async def _fetch(self, key: TechInfoKey, source: TechInfoSource) -> TechInfoMetadata | None:
        try:
            async with asyncio.timeout(config.tech_info_prefetch_timeout_seconds):
                meta = await fetch_metadata(source, key[1])
        except Exception as error:
            # SP06/a: a sikertelen lekérés nem kerül cache-be; a következő kérés újrapróbálja.
            logger.debug("operation=tech-info-prefetch %s", network_error_fields(error))
            return None
        store(key, meta)
        return meta

    async def aclose(self) -> None:
        self.closed = True

        async def cancel_all() -> None:
            while self.flights:
                tasks = [flight.task for flight in self.flights.values()]
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                for key, flight in tuple(self.flights.items()):
                    if flight.task.done():
                        self.flights.pop(key, None)

        await await_owned_task(asyncio.create_task(cancel_all(), name="tech-info-prefetch-close"))


_prefetchers: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, _TechInfoPrefetcher] = (
    weakref.WeakKeyDictionary()
)


def _prefetcher() -> _TechInfoPrefetcher:
    loop = asyncio.get_running_loop()
    prefetcher = _prefetchers.get(loop)
    if prefetcher is None:
        prefetcher = _prefetchers[loop] = _TechInfoPrefetcher()
    return prefetcher


def in_flight(key: TechInfoKey) -> TechInfoFlight | None:
    return _prefetcher().flights.get(key)


def in_flight_count() -> int:
    return len(_prefetcher().flights)


def start_fetch(key: TechInfoKey, source: TechInfoSource) -> TechInfoFlight | None:
    """Futó lekérés a kulcsra, vagy egy új; ``None``, ha a kapacitás tele vagy leállás van."""
    return _prefetcher().start(key, source)


def prefetch(candidates: Iterable[tuple[TechInfoKey, TechInfoSource]]) -> int:
    """Háttérlekérést indít a nem cache-elt, nem futó kulcsokra; nem vár. Az indítottak száma."""
    prefetcher = _prefetcher()
    started = skipped = 0
    for key, source in candidates:
        if key in prefetcher.flights or get_cached(key) is not None:
            continue
        if prefetcher.start(key, source) is None:
            skipped += 1
        else:
            started += 1
    if skipped:
        logger.debug("operation=tech-info-prefetch skipped=%s in_flight=%s", skipped, len(prefetcher.flights))
    return started


def open_tech_info_prefetch() -> None:
    _prefetcher().closed = False


async def close_tech_info_prefetch() -> None:
    """Lifespan-lezárás: új lekérés nem indul, a futók megszakadnak, és bevárja őket."""
    await _prefetcher().aclose()
