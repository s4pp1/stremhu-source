from app.modules.settings.service import SettingsService
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
    def __init__(self, settings_service: SettingsService):
        self._settings_service = settings_service

    def feed_link(self, path: str) -> str:
        app_url = self._settings_service.get_app_url()

        return f"{app_url.rstrip('/')}{path}"

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
