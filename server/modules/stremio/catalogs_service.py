from venv import logger

from modules.indexers.service import IndexersService
from modules.network.service import NetworkService
from modules.stremio.constants import (
    SEARCH_ID,
)
from modules.stremio.enums import (
    MediaType,
)
from modules.stremio.schemas import (
    MetaPreview,
    MetaResponse,
    ParsedExtra,
    StremioCatalogResponse,
)
from modules.torrent_files.service import TorrentFilesService
from modules.torrent_source_provider.service import TorrentSourceProviderService
from modules.torrent_streams.service import TorrentStreamsService


class StremioCatalogsService:
    def __init__(
        self,
        torrent_streams_service: TorrentStreamsService,
        network_service: NetworkService,
        indexers_service: IndexersService,
        torrent_files_service: TorrentFilesService,
        torrent_source_provider_service: TorrentSourceProviderService,
    ):
        self._torrent_streams_service = torrent_streams_service
        self._network_service = network_service
        self._indexers_service = indexers_service
        self._torrent_files_service = torrent_files_service
        self._torrent_source_provider_service = torrent_source_provider_service

    async def get_catalog(
        self,
        media_type: MediaType,
        catalog_id: str,
        extra: ParsedExtra = ParsedExtra(),
    ):
        if media_type != MediaType.MOVIE or catalog_id != SEARCH_ID or not extra.search:
            return StremioCatalogResponse(metas=[])

        parts = extra.search.split("-", 1)
        if len(parts) < 2 or parts[0] != "t":
            return StremioCatalogResponse(metas=[])

        torrent_id = parts[1]

        try:
            meta_previews = await self.get_metas(torrent_id)
        except Exception as e:
            logger.error("A lista lekérésénél hiba történt: %s", e)
            meta_previews = []

        return StremioCatalogResponse(metas=meta_previews)

    async def get_metas(self, torrent_id: str) -> list[MetaPreview]:
        (
            torrent_sources,
            indexer_errors,
        ) = await self._torrent_source_provider_service.find_by_torrent_id(torrent_id)

        return []

    async def get_meta(self, indexer_id: str, torrent_id: str) -> MetaResponse:
        torrent_file = self._torrent_files_service.get_one(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )

        if not torrent_file:
            torrent_source = (
                await self._torrent_source_provider_service.find_one_by_indexer(
                    indexer_id=indexer_id,
                    torrent_id=torrent_id,
                )
            )

            if torrent_source:
                torrent_file = torrent_source.torrent_file

        if not torrent_file:
            return MetaResponse(meta={})

        return MetaResponse(meta={})
