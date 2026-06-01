from venv import logger

from config import NodeEnv, config
from modules.network.service import NetworkService
from modules.stremio.constants import (
    ADDON_APP_PREFIX_ID,
    SEARCH_ID,
)
from modules.stremio.enums import (
    ContentType,
    ExtraName,
    MediaType,
    ShortManifestResource,
)
from modules.stremio.schemas import (
    Manifest,
    ManifestBehaviorHints,
    ManifestCatalog,
    ManifestExtra,
    MetaPreview,
    MetaResponse,
    ParsedExtra,
    ParsedStreamId,
    ParsedTorrentStreamId,
    StremioCatalogResponse,
    StremioStream,
)
from modules.torrent_streams.service import TorrentStreamsService
from modules.users.models import UserModel


class StremioService:
    def __init__(
        self,
        torrent_streams_service: TorrentStreamsService,
        network_service: NetworkService,
    ):
        self._torrent_streams_service = torrent_streams_service
        self._network_service = network_service

    def manifest(self, user: UserModel) -> Manifest:
        app_url = self._network_service.get_app_url()

        addon_id = "hu.stremhu-source.addon"
        name = "StremHU Source"

        if config.node_env != NodeEnv.PRODUCTION:
            addon_id = f"{addon_id}.dev"
            name = f"{name} (DEV)"

        catalogs: list[ManifestCatalog] = [
            ManifestCatalog(
                id=SEARCH_ID,
                name="🔍 Torrent - StremHU",
                type=ContentType.MOVIE,
                extra=[
                    ManifestExtra(
                        name=ExtraName.SEARCH,
                        is_required=True,
                    )
                ],
            ),
        ]

        return Manifest(
            id=addon_id,
            version=config.version,
            name=name,
            description=config.description,
            resources=[
                ShortManifestResource.STREAM,
                ShortManifestResource.CATALOG,
                ShortManifestResource.META,
            ],
            types=[ContentType.MOVIE, ContentType.SERIES],
            id_prefixes=["tt", ADDON_APP_PREFIX_ID],
            catalogs=catalogs,
            behavior_hints=ManifestBehaviorHints(
                configurable=True,
                configuration_required=False,
            ),
            logo=f"{app_url}/logo.png",
        )

    async def get_streams(
        self,
        user: UserModel,
        parsed_id: ParsedStreamId,
    ) -> list[StremioStream]:
        """Lekéri a lejátszható streameket az adatbázisból vagy indexerekből."""
        if isinstance(parsed_id, ParsedTorrentStreamId):
            torrent_stream = await self._torrent_streams_service.find_one_by_torrent_id(
                indexer_id=parsed_id.indexer_id,
                torrent_id=parsed_id.torrent_id,
                user=user,
            )

            stremio_streams = []
            if torrent_stream:
                stremio_streams.append(
                    StremioStream.from_torrent_stream(
                        torrent_stream=torrent_stream,
                    )
                )
            return stremio_streams

        # IMDb alapú stream lekérdezés kereséssel és feloldással
        torrent_streams, errors = await self._torrent_streams_service.find_by_imdb(
            user=user,
            imdb_id=parsed_id.imdb_id,
            series=parsed_id.series,
        )

        stremio_streams = [
            StremioStream.from_torrent_stream(torrent_stream=torrent_stream)
            for torrent_stream in torrent_streams
        ]

        return stremio_streams

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
        torrent_streams = await self._torrent_streams_service.find_by_torrent_ids(
            indexer_id="",
            torrent_id=torrent_id,
            user=user,
        )

        return []

    async def get_meta(self, tracker_id: str, torrent_id: str) -> MetaResponse:
        pass
