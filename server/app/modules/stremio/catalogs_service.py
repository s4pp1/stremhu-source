from venv import logger

from app.modules.stremio.constants import (
    SEARCH_ID,
)
from app.modules.stremio.enums import (
    MediaType,
)
from app.modules.stremio.schemas import (
    MetaDetail,
    MetaPreview,
    ParsedExtra,
    StremioCatalogResponse,
)
from app.modules.torrent_files.schemas import TorrentFileIdentifier
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.torrent_source_provider.service import TorrentSourceProviderService


class StremioCatalogsService:
    def __init__(
        self,
        torrent_files_service: TorrentFilesService,
        torrent_source_provider_service: TorrentSourceProviderService,
    ):
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
            _,
        ) = await self._torrent_source_provider_service.find_by_torrent_id(torrent_id)

        return [
            MetaPreview.from_torrent_file(torrent_source.torrent_file)
            for torrent_source in torrent_sources
        ]

    async def get_meta(self, indexer_id: str, torrent_id: str) -> MetaDetail | None:
        self._torrent_files_service.touch(
            TorrentFileIdentifier(indexer_id=indexer_id, torrent_id=torrent_id)
        )
        torrent_file = self._torrent_files_service.find_by_id(
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
            return None

        return MetaDetail.from_torrent_file(torrent_file)
