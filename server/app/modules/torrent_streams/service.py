import asyncio

import humanize
from sqlalchemy.orm import Session

from app.common.schemas.internal import SeriesInfo
from app.modules.settings.service import SettingsService
from app.modules.torrent_source_provider.service import (
    TorrentSourceProviderService,
)
from app.modules.torrent_streams.schemas import (
    TorrentStream,
)
from app.modules.torrents.schemas.internal import TorrentWithRelay
from app.modules.torrents.service import TorrentsService
from app.modules.users.models import UserModel


class TorrentStreamsService:
    def __init__(
        self,
        db: Session,
        torrent_source_provider_service: TorrentSourceProviderService,
        torrents_service: TorrentsService,
        settings_service: SettingsService,
    ):
        self.db = db
        self._torrent_source_provider_service = torrent_source_provider_service
        self._torrents_service = torrents_service

        self._settings_service = settings_service

    async def find_by_imdb(
        self,
        user: UserModel,
        imdb_id: str,
        series: SeriesInfo | None = None,
    ) -> tuple[list[TorrentStream], list[str]]:
        (
            torrent_sources,
            indexer_errors,
        ) = await self._torrent_source_provider_service.find_by_imdb_id(imdb_id)

        app_url = await asyncio.to_thread(self._settings_service.get_app_url)

        torrent_streams: list[TorrentStream] = []

        for torrent_source in torrent_sources:
            torrent_stream = TorrentStream.from_imdb_id(
                indexer_torrent=torrent_source.indexer_torrent,
                torrent_file=torrent_source.torrent_file,
                series=series,
                app_url=app_url,
                user=user,
            )

            if torrent_stream:
                torrent_streams.append(torrent_stream)

        filtered_torrent_streams = self._filter_torrent_streams(torrent_streams, user)
        sorted_torrent_streams = self._sort_torrent_streams(
            filtered_torrent_streams, user
        )

        if user.only_best_torrent:
            sorted_torrent_streams = sorted_torrent_streams[:1]

        return sorted_torrent_streams, indexer_errors

    async def find_by_torrent_id(
        self,
        indexer_id: str,
        torrent_id: str,
        user: UserModel,
    ) -> list[TorrentStream]:

        torrent_source = (
            await self._torrent_source_provider_service.find_one_by_indexer(
                indexer_id, torrent_id
            )
        )

        if not torrent_source:
            return []

        app_url = await asyncio.to_thread(self._settings_service.get_app_url)

        return TorrentStream.from_torrent_id(
            indexer_torrent=torrent_source.indexer_torrent,
            torrent_file=torrent_source.torrent_file,
            app_url=app_url,
            user=user,
        )

    def _filter_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
        user: UserModel,
    ) -> list[TorrentStream]:
        excluded_attribute_ids = {
            exclusion.attribute_id for exclusion in user.attribute_exclusions
        }

        filtered_torrent_streams: list[TorrentStream] = []
        for torrent_stream in torrent_streams:
            if user.torrent_seed is not None and (
                torrent_stream.seeders is None
                or torrent_stream.seeders <= user.torrent_seed
            ):
                continue

            if any(
                attribute.id in excluded_attribute_ids
                for attribute in torrent_stream.attributes
            ):
                continue

            filtered_torrent_streams.append(torrent_stream)

        return filtered_torrent_streams

    def _sort_torrent_streams(
        self,
        torrent_streams: list[TorrentStream],
        user: UserModel,
    ) -> list[TorrentStream]:
        torrent_with_relays: list[TorrentWithRelay] = (
            self._torrents_service.get_torrents()
        )
        active_hashes = {
            torrent_with_relay.info_hash for torrent_with_relay in torrent_with_relays
        }

        for stream in torrent_streams:
            stream.is_persisted_torrent = stream.info_hash in active_hashes
        sorted_preferences = sorted(
            user.preference_definitions, key=lambda preference: preference.order
        )

        preference_rank_maps: list[tuple[str, dict[str, int], int]] = []
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
