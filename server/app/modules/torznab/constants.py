from typing import NamedTuple

ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
TORZNAB_NAMESPACE = "http://torznab.com/schemas/2015/feed"
NEWZNAB_NAMESPACE = "http://www.newznab.com/DTD/2010/feeds/attributes/"

NAMESPACES = {
    "atom": ATOM_NAMESPACE,
    "torznab": TORZNAB_NAMESPACE,
    "newznab": NEWZNAB_NAMESPACE,
}

SERVER_TITLE = "StremHU Source"
SERVER_VERSION = "1.3"

FEED_TITLE = "StremHU Source"
FEED_DESCRIPTION = "StremHU Source Torznab találatok"
FEED_LANGUAGE = "hu"

LIMIT_MAX = 200
LIMIT_DEFAULT = 100

RSS_CONTENT_TYPE = "application/rss+xml"
FEED_MEDIA_TYPE = f"{RSS_CONTENT_TYPE}; charset=utf-8"
XML_MEDIA_TYPE = "application/xml; charset=utf-8"

TORRENT_MEDIA_TYPE = "application/x-bittorrent"


UNIMPLEMENTED_FUNCTIONS = frozenset(
    {
        "music",
        "book",
        "details",
        "getnfo",
        "get",
        "card-add",
        "card-del",
        "cart-add",
        "cart-del",
        "comments",
        "comments-add",
        "register",
        "user",
    }
)

SEARCH_AVAILABLE = True
SEARCH_SUPPORTED_PARAMS = "q"

TV_SEARCH_AVAILABLE = True
TV_SEARCH_SUPPORTED_PARAMS = "q,imdbid,season,ep"

MOVIE_SEARCH_AVAILABLE = True
MOVIE_SEARCH_SUPPORTED_PARAMS = "q,imdbid"

MOVIE_CATEGORY_ID = 2000
TV_CATEGORY_ID = 5000


class Subcategory(NamedTuple):
    id: int
    name: str


class Category(NamedTuple):
    id: int
    name: str
    subcategories: tuple[Subcategory, ...]


# Specifikációból: https://torznab.github.io/spec-1.3-draft/external/newznab/api.html?highlight=foreign#predefined-categories
CATEGORIES = (
    Category(
        id=MOVIE_CATEGORY_ID,
        name="Movies",
        subcategories=(
            Subcategory(2010, "Foreign"),
            Subcategory(2030, "SD"),
            Subcategory(2040, "HD"),
            Subcategory(2045, "UHD"),
            Subcategory(2060, "3D"),
        ),
    ),
    Category(
        id=TV_CATEGORY_ID,
        name="TV",
        subcategories=(
            Subcategory(5020, "Foreign"),
            Subcategory(5030, "SD"),
            Subcategory(5040, "HD"),
            Subcategory(5045, "UHD"),
        ),
    ),
)
