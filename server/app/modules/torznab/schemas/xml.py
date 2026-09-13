from typing import Annotated

from pydantic import BeforeValidator, Field, PlainSerializer
from pydantic_xml import BaseXmlModel, attr, element

from app.modules.torznab.constants import (
    NAMESPACES,
    RSS_CONTENT_TYPE,
    TORRENT_MEDIA_TYPE,
)
from app.modules.torznab.utils import clean_xml_text

XmlText = Annotated[str, BeforeValidator(clean_xml_text)]

YesNo = Annotated[
    bool,
    PlainSerializer(lambda value: "yes" if value else "no", return_type=str),
]


class TorznabError(BaseXmlModel, tag="error"):
    code: int = attr()
    description: XmlText = attr()


class CapsServer(BaseXmlModel, tag="server"):
    version: str = attr()
    title: str = attr()


class CapsLimits(BaseXmlModel, tag="limits"):
    max: int = attr()
    default: int = attr()


class CapsSearchMode(BaseXmlModel):
    available: YesNo = attr()
    supported_params: str = attr(name="supportedParams")


class CapsSearching(BaseXmlModel, tag="searching"):
    search: CapsSearchMode = element(tag="search")
    tv_search: CapsSearchMode = element(tag="tv-search")
    movie_search: CapsSearchMode = element(tag="movie-search")


class CapsSubcategory(BaseXmlModel, tag="subcat"):
    id: int = attr()
    name: str = attr()


class CapsCategory(BaseXmlModel, tag="category"):
    id: int = attr()
    name: str = attr()
    subcategories: list[CapsSubcategory] = Field(default_factory=list)


class CapsCategories(BaseXmlModel, tag="categories"):
    categories: list[CapsCategory] = Field(default_factory=list)


class Caps(BaseXmlModel, tag="caps"):
    server: CapsServer
    limits: CapsLimits
    searching: CapsSearching
    categories: CapsCategories


class AtomLink(BaseXmlModel, tag="link", ns="atom", nsmap=NAMESPACES):
    href: XmlText = attr()
    rel: str = attr(default="self")
    type: str = attr(default=RSS_CONTENT_TYPE)


class NewznabResponse(BaseXmlModel, tag="response", ns="newznab", nsmap=NAMESPACES):
    offset: int = attr()
    total: int = attr()


class TorznabAttr(BaseXmlModel, tag="attr", ns="torznab", nsmap=NAMESPACES):
    name: str = attr()
    value: XmlText = attr()


class FeedItemGuid(BaseXmlModel, tag="guid"):
    is_perma_link: str = attr(name="isPermaLink", default="false")
    value: XmlText


class FeedItemEnclosure(BaseXmlModel, tag="enclosure"):
    url: XmlText = attr()
    length: int = attr()
    type: str = attr(default=TORRENT_MEDIA_TYPE)


class FeedItemIndexer(BaseXmlModel, tag="jackettindexer"):
    id: str = attr()
    name: XmlText


class FeedItem(BaseXmlModel, tag="item"):
    title: XmlText = element()
    guid: FeedItemGuid
    indexer: FeedItemIndexer | None = None
    type: XmlText | None = element(default=None)
    pub_date: XmlText = element(tag="pubDate")
    size: int | None = element(default=None)
    link: XmlText | None = element(default=None)
    categories: list[int] = element(tag="category", default_factory=list)
    enclosure: FeedItemEnclosure
    attributes: list[TorznabAttr] = Field(default_factory=list)


class FeedChannel(BaseXmlModel, tag="channel"):
    atom_link: AtomLink
    title: XmlText = element()
    description: XmlText = element()
    link: XmlText = element()
    language: str = element()
    response: NewznabResponse
    items: list[FeedItem] = Field(default_factory=list)


class Feed(BaseXmlModel, tag="rss", nsmap=NAMESPACES):
    version: str = attr(default="2.0")
    channel: FeedChannel
