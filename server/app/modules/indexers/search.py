import asyncio
import time
from typing import Any

from fastapi import HTTPException, status

from app.common.async_utils import owned_to_thread
from app.common.database import shared_read_session
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.indexer_accounts.schemas import IndexerAccountRef
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.indexers.schemas.internal import DownloadedTorrentFile, IndexerTorrent
from app.modules.media_attributes.utils import resolve_attribute_ids
from app.modules.stremio.cache import stream_cache_state

_IMDB_TRACKER_CACHE_TTL = 1800.0
_IMDB_TRACKER_CACHE_MAX = 1000
_imdb_tracker_cache: dict[tuple[str, str], tuple[float, list[Any]]] = {}

_QUERY_TRACKER_CACHE_TTL = 300.0
_QUERY_TRACKER_CACHE_MAX = 1000
_query_tracker_cache: dict[tuple[str, str, str], tuple[float, list[Any]]] = {}


def invalidate_indexer_cache(indexer_id: str | None = None) -> None:
    """M05: Indexer találati gyorsítótár invalidálása kijelentkezés, törlés vagy új hitelesítés esetén."""
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
            indexer_definition_torrent = await indexer_definition.find_torrent_by_id(
                torrent_id
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

        async def fetch_and_map_with_timeout(
            indexer_account: IndexerAccountRef,
        ) -> IndexerTorrent | None:
            try:
                return await asyncio.wait_for(
                    fetch_and_map(indexer_account), timeout=12.5
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"A(z) '{indexer_account.indexer_definition.name}' indexer nem válaszolt időben."
                )

        tasks = [
            fetch_and_map_with_timeout(indexer_account)
            for indexer_account in indexer_accounts
        ]
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

    async def get_torrents_by_imdb_id(
        self,
        imdb_id: str,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        source_epoch = stream_cache_state.revision("")[0]
        indexer_accounts = await owned_to_thread(self._find_account_refs)

        async def fetch_and_map(
            indexer_account: IndexerAccountRef,
        ) -> list[IndexerTorrent]:
            cache_key = (indexer_account.indexer_id, f"{source_epoch}:{imdb_id.strip().lower()}")
            now = time.monotonic()
            indexer_definition_torrents: list[Any] | None = None
            cached = _imdb_tracker_cache.get(cache_key)
            if cached is not None:
                ts, cached_def_torrents = cached
                if now - ts < _IMDB_TRACKER_CACHE_TTL:
                    indexer_definition_torrents = cached_def_torrents
                else:
                    _imdb_tracker_cache.pop(cache_key, None)

            if indexer_definition_torrents is None:
                indexer_definition = self._indexer_definitions_service.get_by_id(
                    indexer_account.indexer_id
                )
                indexer_definition_torrents = (
                    await indexer_definition.find_torrents_by_imdb_id(imdb_id)
                )
                if len(_imdb_tracker_cache) >= _IMDB_TRACKER_CACHE_MAX:
                    oldest_key = min(
                        _imdb_tracker_cache, key=lambda k: _imdb_tracker_cache[k][0]
                    )
                    _imdb_tracker_cache.pop(oldest_key, None)
                _imdb_tracker_cache[cache_key] = (
                    time.monotonic(),
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

        async def fetch_and_map_with_timeout(
            indexer_account: IndexerAccountRef,
        ) -> list[IndexerTorrent]:
            try:
                return await asyncio.wait_for(
                    fetch_and_map(indexer_account), timeout=12.5
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"A(z) '{indexer_account.indexer_definition.name}' indexer nem válaszolt időben."
                )

        tasks = [
            fetch_and_map_with_timeout(indexer_account)
            for indexer_account in indexer_accounts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        indexer_torrents: list[IndexerTorrent] = []
        errors: list[str] = []

        for result in results:
            if isinstance(result, BaseException):
                errors.append(str(result))
            else:
                indexer_torrents.extend(result)

        return indexer_torrents, errors

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
                indexer_definition_torrents = (
                    await indexer_definition.find_torrents_by_query(
                        query, media_type=media_type
                    )
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

        async def fetch_and_map_with_timeout(
            indexer_account: IndexerAccountRef,
        ) -> list[IndexerTorrent]:
            try:
                return await asyncio.wait_for(
                    fetch_and_map(indexer_account), timeout=12.5
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"A(z) '{indexer_account.indexer_definition.name}' indexer nem válaszolt időben."
                )

        tasks = [
            fetch_and_map_with_timeout(indexer_account)
            for indexer_account in indexer_accounts
        ]
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
