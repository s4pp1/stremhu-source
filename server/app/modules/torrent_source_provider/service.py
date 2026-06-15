import asyncio
from collections.abc import Awaitable
from typing import overload

from app.common.logger import logger
from app.modules.indexers.schemas.internal import DownloadedTorrentFile, IndexerTorrent
from app.modules.indexers.service import IndexersService
from app.modules.torrent_files.exceptions import InvalidTorrentFileException
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileIdentifier, TorrentFilesFilter
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.torrent_source_provider.schemas import TorrentSource


class TorrentSourceProviderService:
    def __init__(
        self,
        indexers_service: IndexersService,
        torrent_files_service: TorrentFilesService,
    ):
        self._indexers_service = indexers_service
        self._torrent_files_service = torrent_files_service

    async def find_by_imdb_id(
        self,
        imdb_id: str,
    ) -> tuple[list[TorrentSource], list[str]]:
        (
            indexer_torrents,
            indexer_errors,
        ) = await self._indexers_service.get_torrents_by_imdb_id(imdb_id)

        torrent_files = await self._sync_torrent_files(indexer_torrents)

        return torrent_files, indexer_errors

    async def find_by_torrent_id(
        self,
        torrent_id: str,
    ) -> tuple[list[TorrentSource], list[str]]:
        (
            indexer_torrents,
            indexer_errors,
        ) = await self._indexers_service.get_torrents_by_torrent_id(torrent_id)

        torrent_files = await self._sync_torrent_files(indexer_torrents)

        return torrent_files, indexer_errors

    async def find_one_by_indexer(
        self,
        indexer_id: str,
        torrent_id: str,
    ) -> TorrentSource | None:
        indexer_torrent = await self._indexers_service.get_torrent_by_torrent_id(
            indexer_id, torrent_id
        )

        torrent_file = await self._sync_torrent_files(indexer_torrent)

        return torrent_file

    @overload
    async def _sync_torrent_files(
        self,
        indexer_torrents: IndexerTorrent,
    ) -> TorrentSource | None: ...

    @overload
    async def _sync_torrent_files(
        self,
        indexer_torrents: list[IndexerTorrent],
    ) -> list[TorrentSource]: ...
    async def _sync_torrent_files(
        self,
        indexer_torrents: list[IndexerTorrent] | IndexerTorrent,
    ) -> list[TorrentSource] | TorrentSource | None:
        is_single = isinstance(indexer_torrents, IndexerTorrent)
        if is_single:
            indexer_torrents = [indexer_torrents]

        torrent_file_ids: list[TorrentFileIdentifier] = [
            TorrentFileIdentifier(
                indexer_id=indexer_torrent.indexer_account.indexer_id,
                torrent_id=indexer_torrent.torrent_id,
            )
            for indexer_torrent in indexer_torrents
        ]

        current_torrent_files = await asyncio.to_thread(
            self._torrent_files_service.find_list,
            filter=TorrentFilesFilter(identifiers=torrent_file_ids),
        )

        await asyncio.to_thread(
            self._torrent_files_service.touch,
            torrent_file_ids,
        )

        current_torrent_files_map: dict[tuple[str, str], TorrentFileModel] = {
            (
                current_torrent_file.indexer_id,
                current_torrent_file.torrent_id,
            ): current_torrent_file
            for current_torrent_file in current_torrent_files
        }

        download_tasks: list[Awaitable[DownloadedTorrentFile]] = []
        for indexer_torrent in indexer_torrents:
            if (
                indexer_torrent.indexer_account.indexer_id,
                indexer_torrent.torrent_id,
            ) in current_torrent_files_map:
                continue

            download_tasks.append(
                self._indexers_service.download_torrent(
                    indexer_torrent.indexer_account.indexer_id,
                    indexer_torrent.torrent_id,
                    indexer_torrent.download_url,
                )
            )

        downloaded_torrent_files = await asyncio.gather(
            *download_tasks, return_exceptions=True
        )

        created_torrent_files: list[TorrentFileModel] = []
        for downloaded_torrent_file in downloaded_torrent_files:
            if isinstance(downloaded_torrent_file, BaseException):
                logger.warning(
                    f"⚠️ Hibas a torrent letöltése, átugorva: {downloaded_torrent_file}"
                )
                continue

            try:
                torrent_file = await asyncio.to_thread(
                    self._torrent_files_service.create,
                    indexer_id=downloaded_torrent_file.indexer_id,
                    torrent_id=downloaded_torrent_file.torrent_id,
                    torrent_bytes=downloaded_torrent_file.torrent_bytes,
                )
                created_torrent_files.append(torrent_file)
            except InvalidTorrentFileException:
                logger.warning(
                    f"⚠️ Érvénytelen torrent fájl átugorva: indexer: {downloaded_torrent_file.indexer_id}, torrent_id: {downloaded_torrent_file.torrent_id}"
                )
                continue

        torrent_files = current_torrent_files + created_torrent_files

        indexer_torrent_map: dict[tuple[str, str], IndexerTorrent] = {
            (
                indexer_torrent.indexer_account.indexer_id,
                indexer_torrent.torrent_id,
            ): indexer_torrent
            for indexer_torrent in indexer_torrents
        }

        torrent_sources: list[TorrentSource] = []
        for torrent_file in torrent_files:
            indexer_torrent = indexer_torrent_map.get(
                (
                    torrent_file.indexer_id,
                    torrent_file.torrent_id,
                )
            )
            if indexer_torrent is None:
                continue

            torrent_sources.append(
                TorrentSource(
                    indexer_torrent=indexer_torrent,
                    torrent_file=torrent_file,
                )
            )

        if is_single:
            return torrent_sources[0] if torrent_sources else None

        return torrent_sources
