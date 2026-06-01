import asyncio
from collections.abc import Awaitable

import humanize
from modules.attributes.service import AttributesService
from modules.indexers.schemas import DownloadedTorrentFile, IndexerTorrent
from modules.indexers.service import IndexersService
from modules.network.service import NetworkService
from modules.preferences.enums import PreferenceEnum
from modules.stremio.schemas import ParsedStreamSeries
from modules.torrent_files.models import TorrentFileModel
from modules.torrent_files.schemas import TorrentFileIdentifier, TorrentFilesFilter
from modules.torrent_files.service import TorrentFilesService
from modules.torrent_streams.schemas import (
    TorrentStream,
)
from modules.torrent_streams.utils.torrent_stream_resolver import (
    TorrentStreamResolver,
)
from modules.torrents.service import TorrentPair, TorrentsService
from modules.users.models import UserModel
from sqlalchemy.orm import Session


class TorrentStreamsService:
    def __init__(
        self,
        db: Session,
        indexers_service: IndexersService,
        torrent_files_service: TorrentFilesService,
        torrents_service: TorrentsService,
        attributes_service: AttributesService,
        network_service: NetworkService,
    ):
        self.db = db
        self._indexers_service = indexers_service
        self._torrents_service = torrents_service
        self._torrent_files_service = torrent_files_service
        self._attributes_service = attributes_service
        self._network_service = network_service

    async def find_by_imdb(
        self,
        user: UserModel,
        imdb_id: str,
        series: ParsedStreamSeries | None = None,
    ) -> tuple[list[TorrentStream], list[str]]:
        (
            indexer_torrents,
            indexer_errors,
        ) = await self._indexers_service.get_torrents_by_imdb_id(imdb_id)

        attributes_map = await asyncio.to_thread(
            self._attributes_service.get_all_as_map
        )

        app_url = await asyncio.to_thread(self._network_service.get_app_url)

        torrent_file_ids: list[TorrentFileIdentifier] = [
            TorrentFileIdentifier(
                indexer_id=indexer_torrent.indexer_account.indexer_id,
                torrent_id=indexer_torrent.torrent_id,
            )
            for indexer_torrent in indexer_torrents
        ]

        current_torrent_files = await asyncio.to_thread(
            self._torrent_files_service.get_list,
            filter=TorrentFilesFilter(identifiers=torrent_file_ids),
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
                continue

            torrent_file = await asyncio.to_thread(
                self._torrent_files_service.create,
                indexer_id=downloaded_torrent_file.indexer_account.indexer_id,
                torrent_id=downloaded_torrent_file.torrent_id,
                torrent_bytes=downloaded_torrent_file.torrent_bytes,
            )
            created_torrent_files.append(torrent_file)

        torrent_files = current_torrent_files + created_torrent_files

        indexer_torrents_map: dict[tuple[str, str], IndexerTorrent] = {
            (
                indexer_torrent.indexer_account.indexer_id,
                indexer_torrent.torrent_id,
            ): indexer_torrent
            for indexer_torrent in indexer_torrents
        }

        torrent_streams: list[TorrentStream] = []

        for torrent_file in torrent_files:
            indexer_torrent = indexer_torrents_map.get(
                (torrent_file.indexer_id, torrent_file.torrent_id)
            )

            if indexer_torrent is None:
                continue

            torrent_stream = TorrentStreamResolver(
                indexer_torrent=indexer_torrent,
                torrent_file=torrent_file,
                series=series,
                attribute_map=attributes_map,
                app_url=app_url,
                user=user,
            ).resolve()

            if torrent_stream:
                torrent_streams.append(torrent_stream)

        filtered_torrent_streams = self._filter_torrent_streams(torrent_streams, user)
        sorted_torrent_streams = self._sort_torrent_streams(
            filtered_torrent_streams, user
        )

        return sorted_torrent_streams, indexer_errors

    async def find_by_torrent_id(
        self,
        indexer_id: str,
        torrent_id: str,
        user: UserModel,
    ) -> TorrentStream | None:

        indexer_torrent = await self._indexers_service.get_torrent_by_torrent_id(
            indexer_id, torrent_id
        )

        attributes_map = await asyncio.to_thread(
            self._attributes_service.get_all_as_map
        )

        app_url = await asyncio.to_thread(self._network_service.get_app_url)

        current_torrent_file = await asyncio.to_thread(
            self._torrent_files_service.get_one,
            indexer_torrent.indexer_account.indexer_id,
            indexer_torrent.torrent_id,
        )

        if current_torrent_file is None:
            downloaded_torrent_file = await self._indexers_service.download_torrent(
                indexer_torrent.indexer_account.indexer_id,
                indexer_torrent.torrent_id,
                indexer_torrent.download_url,
            )
            current_torrent_file = await asyncio.to_thread(
                self._torrent_files_service.create,
                indexer_id=downloaded_torrent_file.indexer_account.indexer_id,
                torrent_id=downloaded_torrent_file.torrent_id,
                torrent_bytes=downloaded_torrent_file.torrent_bytes,
            )

        torrent_stream = TorrentStreamResolver(
            indexer_torrent=indexer_torrent,
            torrent_file=current_torrent_file,
            series=None,
            attribute_map=attributes_map,
            app_url=app_url,
            user=user,
        ).resolve()

        return torrent_stream

    def _filter_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
        user: UserModel,
    ) -> list[TorrentStream]:
        filtered_torrent_streams: list[TorrentStream] = []
        for torrent_stream in torrent_streams:
            if user.torrent_seed is not None and (
                torrent_stream.seeders is None
                or torrent_stream.seeders <= user.torrent_seed
            ):
                continue

            filtered_torrent_streams.append(torrent_stream)

        return filtered_torrent_streams

    def _sort_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
        user: UserModel,
    ) -> list[TorrentStream]:
        torrent_pairs: list[TorrentPair] = self._torrents_service.get_torrents()
        active_hashes = {torrent_pair.info_hash for torrent_pair in torrent_pairs}

        for stream in torrent_streams:
            stream.is_persisted_torrent = stream.info_hash in active_hashes
        sorted_preferences = sorted(
            user.preferences, key=lambda preference: preference.order
        )

        preference_rank_maps: list[tuple[PreferenceEnum, dict[str, int], int]] = []
        for sorted_preference in sorted_preferences:
            definition_attributes = sorted(
                sorted_preference.definition.definition_attributes,
                key=lambda def_attr: def_attr.order,
            )
            rank_map = {
                def_attr.attribute_id: idx
                for idx, def_attr in enumerate(definition_attributes)
            }
            fallback_rank = len(definition_attributes)
            preference_rank_maps.append(
                (sorted_preference.definition.preference_id, rank_map, fallback_rank)
            )

        def sort_key(stream: TorrentStream):
            relay_rank = 0 if stream.is_persisted_torrent else 1
            pref_ranks: list[int] = []
            for pref_id, rank_map, fallback in preference_rank_maps:
                best_rank = fallback
                for attr in stream.attributes:
                    if attr.preference_id == pref_id and attr.id in rank_map:
                        best_rank = min(best_rank, rank_map[attr.id])
                pref_ranks.append(best_rank)

            seeders_rank = -(stream.seeders or 0)

            return (relay_rank, *pref_ranks, seeders_rank)

        torrent_streams.sort(key=sort_key)
        return torrent_streams

    def _format_filesize(self, bytes_size: int) -> str:
        return humanize.naturalsize(bytes_size, binary=True)
