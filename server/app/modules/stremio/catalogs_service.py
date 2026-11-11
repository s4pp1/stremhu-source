
from app.common.async_utils import owned_to_thread
from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.common.singleflight import SearchOverloadedError
from app.modules.stremio.constants import (
    SEARCH_ID,
)
from app.modules.stremio.enums import (
    ContentType,
    MediaType,
)
from app.modules.stremio.schemas import (
    MetaDetail,
    MetaPreview,
    ParsedExtra,
    StremioCatalogResponse,
)
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_files.schemas import (
    TorrentFileIdentifier,
    TorrentFileSnapshot,
)
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.torrent_source_provider.service import TorrentSourceProviderService
from app.modules.users.models import UserModel

_TORRENT_IMDB_CACHE: dict[tuple[str, str], str] = {}
_MAX_TORRENT_IMDB_CACHE = 2000


class StremioCatalogsService:
    def __init__(
        self,
        torrent_files_service: TorrentFilesService,
        torrent_source_provider_service: TorrentSourceProviderService,
        isolated_torrent_files_service: IsolatedTorrentFilesService,
    ):
        self._torrent_files_service = torrent_files_service
        self._torrent_source_provider_service = torrent_source_provider_service
        self._isolated_torrent_files_service = isolated_torrent_files_service

    async def get_catalog(
        self,
        media_type: MediaType,
        catalog_id: str,
        extra: ParsedExtra = ParsedExtra(),
        user: UserModel | None = None,
    ):
        if (
            media_type not in (MediaType.MOVIE, MediaType.SERIES)
            or catalog_id != SEARCH_ID
            or not extra.search
            or (user is not None and not getattr(user, "enable_catalog_search", True))
        ):
            return StremioCatalogResponse(metas=[])

        parts = extra.search.split("-", 1)
        if len(parts) >= 2 and parts[0] == "t":
            torrent_id = parts[1]
            try:
                meta_previews = await self.get_metas(torrent_id, media_type=media_type)
            except SearchOverloadedError:
                raise
            except Exception as e:
                logger.error("operation=catalog-id-search %s", network_error_fields(e))
                meta_previews = []
            return StremioCatalogResponse(metas=meta_previews)

        # Ha nem t-<torrent_id> formátumú, közvetlen név/cím szerinti keresést futtatunk a trackereken
        media_type_str = "movie" if media_type == MediaType.MOVIE else "series"
        try:
            torrent_sources, _ = (
                await self._torrent_source_provider_service.find_by_query(
                    extra.search, media_type=media_type_str
                )
            )

            # 2. szintű védelem SeriesParser-rel
            from app.modules.torrent_streams.utils.series_parser import SeriesParser

            filtered_sources = []
            for ts in torrent_sources:
                tf = ts.torrent_file
                if not tf or not tf.info:
                    filtered_sources.append(ts)
                    continue

                t_seasons, t_episodes = SeriesParser(tf.info.name).parse()
                has_episodes = bool(
                    t_seasons
                    or t_episodes
                    or (
                        tf.info.files
                        and any(
                            SeriesParser(f.path or f.name).parse()[1]
                            for f in tf.info.files
                            if f.is_video
                        )
                    )
                )

                if media_type == MediaType.MOVIE:
                    # Filmek közé nem engedünk be epizódos tartalmakat
                    if not has_episodes:
                        filtered_sources.append(ts)
                else:
                    # Sorozatok közé epizódos tartalmakat engedünk, vagy több videofájlt tartalmazó csomagokat
                    if has_episodes or (
                        tf.info.files
                        and len([f for f in tf.info.files if f.is_video]) > 1
                    ):
                        filtered_sources.append(ts)

            torrent_sources = filtered_sources

            torrent_sources.sort(
                key=lambda ts: getattr(ts.indexer_torrent, "seeders", 0) or 0,
                reverse=True,
            )

            for ts in torrent_sources:
                it = ts.indexer_torrent
                if it and it.imdb_id and getattr(it, "indexer_account", None):
                    if len(_TORRENT_IMDB_CACHE) >= _MAX_TORRENT_IMDB_CACHE:
                        for k in list(_TORRENT_IMDB_CACHE.keys())[:250]:
                            _TORRENT_IMDB_CACHE.pop(k, None)
                    _TORRENT_IMDB_CACHE[
                        (it.indexer_account.indexer_id, it.torrent_id)
                    ] = it.imdb_id

            content_type = (
                ContentType.SERIES if media_type == MediaType.SERIES else ContentType.MOVIE
            )
            meta_previews = [
                MetaPreview.from_torrent_file(
                    torrent_source.torrent_file,
                    content_type=content_type,
                    imdb_id=getattr(torrent_source.indexer_torrent, "imdb_id", None),
                )
                for torrent_source in torrent_sources
            ]
        except SearchOverloadedError:
            raise
        except Exception as e:
            logger.error(
                "operation=catalog-name-search %s", network_error_fields(e)
            )
            meta_previews = []

        return StremioCatalogResponse(metas=meta_previews)

    async def get_metas(
        self,
        torrent_id: str,
        media_type: MediaType = MediaType.MOVIE,
    ) -> list[MetaPreview]:
        (
            torrent_sources,
            _,
        ) = await self._torrent_source_provider_service.find_by_torrent_id(torrent_id)

        content_type = (
            ContentType.SERIES if media_type == MediaType.SERIES else ContentType.MOVIE
        )
        return [
            MetaPreview.from_torrent_file(
                torrent_source.torrent_file,
                content_type=content_type,
            )
            for torrent_source in torrent_sources
        ]

    def _find_torrent_file_snapshot(
        self, indexer_id: str, torrent_id: str
    ) -> TorrentFileSnapshot | None:
        torrent_file = self._torrent_files_service.find_by_id(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )
        return TorrentFileSnapshot.from_model(torrent_file) if torrent_file else None

    async def get_meta(
        self,
        indexer_id: str,
        torrent_id: str,
        media_type: MediaType = MediaType.MOVIE,
    ) -> MetaDetail | None:

        self._isolated_torrent_files_service.touch(
            TorrentFileIdentifier(
                indexer_id=indexer_id,
                torrent_id=torrent_id,
            ),
        )

        torrent_file = await owned_to_thread(
            self._find_torrent_file_snapshot, indexer_id, torrent_id
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

        imdb_id = _TORRENT_IMDB_CACHE.get((indexer_id, torrent_id))
        content_type = (
            ContentType.SERIES if media_type == MediaType.SERIES else ContentType.MOVIE
        )
        return MetaDetail.from_torrent_file(
            torrent_file, content_type=content_type, imdb_id=imdb_id
        )
