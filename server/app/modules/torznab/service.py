import asyncio
from urllib.parse import parse_qsl, urlencode

from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.common.schemas.internal import SeriesInfo
from app.modules.settings.service import SettingsService
from app.modules.stremio.tvdb_resolver import TvdbResolver, tvdb_resolver
from app.modules.torrent_source_provider.schemas import TorrentSource
from app.modules.torrent_source_provider.service import TorrentSourceProviderService
from app.modules.torznab.constants import (
    CATEGORIES,
    FEED_DESCRIPTION,
    FEED_LANGUAGE,
    FEED_TITLE,
    LIMIT_DEFAULT,
    LIMIT_MAX,
    MOVIE_SEARCH_AVAILABLE,
    MOVIE_SEARCH_SUPPORTED_PARAMS,
    SEARCH_AVAILABLE,
    SEARCH_SUPPORTED_PARAMS,
    SERVER_TITLE,
    SERVER_VERSION,
    TV_SEARCH_AVAILABLE,
    TV_SEARCH_SUPPORTED_PARAMS,
)
from app.modules.torznab.enums import (
    TorznabCategory,
    TorznabErrorCode,
    TorznabFunction,
)
from app.modules.torznab.exceptions import TorznabProtocolError
from app.modules.torznab.items import build_feed_item, contains_episode
from app.modules.torznab.query import TorznabQuery
from app.modules.torznab.schemas.xml import (
    AtomLink,
    Caps,
    CapsCategories,
    CapsCategory,
    CapsLimits,
    CapsSearching,
    CapsSearchMode,
    CapsServer,
    CapsSubcategory,
    Feed,
    FeedChannel,
    FeedItem,
    NewznabResponse,
)


class TorznabService:
    def __init__(
        self,
        settings_service: SettingsService,
        torrent_source_provider_service: TorrentSourceProviderService,
        tvdb_resolver: TvdbResolver = tvdb_resolver,
    ):
        self._settings_service = settings_service
        self._torrent_source_provider_service = torrent_source_provider_service
        self._tvdb_resolver = tvdb_resolver

    def feed_link(self, path: str, query: str = "") -> str:
        try:
            app_url = self._settings_service.get_app_url()
        except ValueError as error:
            raise TorznabProtocolError(
                TorznabErrorCode.UNKNOWN_ERROR,
                str(error),
            ) from error

        link = f"{app_url.rstrip('/')}{path}"
        safe_query = self._strip_api_key(query)

        return f"{link}?{safe_query}" if safe_query else link

    async def search(self, query: TorznabQuery) -> tuple[list[FeedItem], int]:
        imdb_id = query.imdb_id
        is_series = bool(
            query.function is TorznabFunction.TV_SEARCH or query.season is not None
        )

        resolved_title: str | None = None

        if not imdb_id and query.tvdb_id:
            resolved_imdb, resolved_title = await self._tvdb_resolver.resolve_tvdb(
                query.tvdb_id,
                is_series=is_series,
            )
            if resolved_imdb:
                imdb_id = resolved_imdb

        if not imdb_id and query.tmdb_id:
            resolved_imdb, resolved_title = await self._tvdb_resolver.resolve_tmdb(
                query.tmdb_id,
                is_series=is_series,
            )
            if resolved_imdb:
                imdb_id = resolved_imdb

        search_query = query.q or resolved_title

        if not imdb_id and not search_query:
            return [], 0

        series_info = (
            SeriesInfo(season=query.season, episode=query.episode)
            if query.season is not None and isinstance(query.episode, int)
            else None
        )

        if imdb_id:
            alternate_ids = await self._tvdb_resolver.get_alternate_imdb_ids(imdb_id)
            all_imdb_ids = [imdb_id] + [aid for aid in alternate_ids if aid != imdb_id]

            if len(all_imdb_ids) > 1:
                # SP07: az automatizált kliensek (Sonarr/Radarr) régi trackerlistát nem kapnak.
                results = await asyncio.gather(
                    *(
                        self._torrent_source_provider_service.find_by_imdb_id(
                            iid, allow_stale=False
                        )
                        for iid in all_imdb_ids
                    ),
                    return_exceptions=True,
                )
                seen_keys: set[tuple[str, str]] = set()
                candidates: list[TorrentSource] = []
                errors: list[str] = []
                for res in results:
                    if isinstance(res, BaseException):
                        errors.append(str(res))
                        continue
                    res_candidates, res_errors = res
                    errors.extend(res_errors)
                    for cand in res_candidates:
                        key = (
                            cand.indexer_torrent.indexer_account.indexer_id,
                            cand.indexer_torrent.torrent_id,
                        )
                        if key not in seen_keys:
                            seen_keys.add(key)
                            candidates.append(cand)
            else:
                (
                    candidates,
                    errors,
                ) = await self._torrent_source_provider_service.find_by_imdb_id(
                    imdb_id, allow_stale=False
                )
        else:
            assert search_query is not None
            (
                candidates,
                errors,
            ) = await self._torrent_source_provider_service.find_by_query(
                search_query
            )

        # Részleges hiba elfogadható, pl egyik szolgáltatónál outage van.
        # De ha az összes error-ral válaszol, akkor mi is.
        if errors and not candidates:
            raise TorznabProtocolError(
                TorznabErrorCode.UNKNOWN_ERROR,
                " | ".join(errors),
            )

        matching = [
            candidate
            for candidate in candidates
            if contains_episode(candidate, series_info)
        ]
        matching.sort(key=self._ordering)

        page = matching[query.offset : query.offset + query.limit]

        return self._to_feed_items(page, self._category(query)), len(matching)

    def capabilities(self) -> Caps:
        return Caps(
            server=CapsServer(version=SERVER_VERSION, title=SERVER_TITLE),
            limits=CapsLimits(max=LIMIT_MAX, default=LIMIT_DEFAULT),
            searching=CapsSearching(
                search=CapsSearchMode(
                    available=SEARCH_AVAILABLE,
                    supported_params=SEARCH_SUPPORTED_PARAMS,
                ),
                tv_search=CapsSearchMode(
                    available=TV_SEARCH_AVAILABLE,
                    supported_params=TV_SEARCH_SUPPORTED_PARAMS,
                ),
                movie_search=CapsSearchMode(
                    available=MOVIE_SEARCH_AVAILABLE,
                    supported_params=MOVIE_SEARCH_SUPPORTED_PARAMS,
                ),
            ),
            categories=CapsCategories(
                categories=[
                    CapsCategory(
                        id=category.id,
                        name=category.name,
                        subcategories=[
                            CapsSubcategory(id=subcategory.id, name=subcategory.name)
                            for subcategory in category.subcategories
                        ],
                    )
                    for category in CATEGORIES
                ]
            ),
        )

    def feed(
        self,
        link: str,
        items: list[FeedItem] | None = None,
        offset: int = 0,
        total: int | None = None,
    ) -> Feed:
        feed_items = items or []

        return Feed(
            channel=FeedChannel(
                atom_link=AtomLink(href=link),
                title=FEED_TITLE,
                description=FEED_DESCRIPTION,
                link=link,
                language=FEED_LANGUAGE,
                response=NewznabResponse(
                    offset=offset,
                    total=len(feed_items) if total is None else total,
                ),
                items=feed_items,
            )
        )

    @staticmethod
    def _category(query: TorznabQuery) -> TorznabCategory:
        if query.function is TorznabFunction.MOVIE:
            return TorznabCategory.MOVIE

        if query.function is TorznabFunction.TV_SEARCH:
            return TorznabCategory.TV

        return TorznabCategory.TV if query.season is not None else TorznabCategory.MOVIE

    @staticmethod
    def _strip_api_key(query: str) -> str:
        pairs = [
            (name, value)
            for name, value in parse_qsl(query, keep_blank_values=True)
            if name.casefold() != "apikey"
        ]

        return urlencode(pairs)

    @staticmethod
    def _ordering(source: TorrentSource) -> tuple[int, str, str]:
        torrent = source.indexer_torrent

        return (
            -torrent.seeders,
            torrent.indexer_account.indexer_id,
            torrent.torrent_id,
        )

    @staticmethod
    def _to_feed_items(
        sources: list[TorrentSource],
        category: TorznabCategory,
    ) -> list[FeedItem]:
        items: list[FeedItem] = []

        for source in sources:
            try:
                items.append(build_feed_item(source, category))
            except Exception as error:
                logger.warning(
                    "operation=torznab-item %s", network_error_fields(error),
                )

        return items
