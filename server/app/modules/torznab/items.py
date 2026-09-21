from urllib.parse import quote

from app.common.schemas.internal import SeriesInfo
from app.modules.media_attributes.constants import MediaAttributeKey
from app.modules.media_attributes.parser import parse_torrent_name
from app.modules.preferences.constants import PreferenceKey
from app.modules.torrent_source_provider.schemas import TorrentSource
from app.modules.torrent_streams.utils.stream_file_resolver import StreamFileResolver
from app.modules.torznab.constants import (
    INDEXER_PRIVACY,
    TorznabAttrName,
)
from app.modules.torznab.enums import TorznabCategory
from app.modules.torznab.schemas.xml import (
    FeedItem,
    FeedItemEnclosure,
    FeedItemGuid,
    FeedItemIndexer,
    TorznabAttr,
)
from app.modules.torznab.utils import format_date_to_rfc822

# A kliensek kanonikus angol nyelvneveket várnak, nem ISO kódokat.
_LANGUAGE_NAMES = {
    MediaAttributeKey.HUN: "Hungarian",
    MediaAttributeKey.ENG: "English",
}


def contains_episode(source: TorrentSource, series: SeriesInfo | None) -> bool:
    """Csak azokat a torrenteket tartjuk meg, amikben tényleg benne van a kért epizód."""
    if series is None:
        return True

    try:
        resolver = StreamFileResolver(source.torrent_file.info, series)
    except Exception:
        return False

    return resolver.resolve() is not None


def _build_magnet(info_hash: str, name: str) -> str:
    return f"magnet:?xt=urn:btih:{info_hash}&dn={quote(name)}"


def _language_names(source: TorrentSource) -> list[str]:
    names: list[str] = []

    # A torrent nevéből kiolvasott nyelv megbízható.
    for attribute in parse_torrent_name(
        name=source.torrent_file.info.name,
        use_fallbacks=False,
    ):
        if attribute.preference_id != PreferenceKey.LANGUAGE:
            continue

        name = _LANGUAGE_NAMES.get(attribute.id)
        if name and name not in names:
            names.append(name)

    # Ha a tracker magyar kategóriájából töltöttük le (pl HD/HUN)
    # akkor feltételezzük, hogy van magyar hang,
    # akkor is, ha véletlen kimaradt a fájlnévből.
    for attribute in source.indexer_torrent.media_attributes:
        if attribute.id != MediaAttributeKey.HUN:
            continue

        name = _LANGUAGE_NAMES[MediaAttributeKey.HUN]
        if name not in names:
            names.append(name)

    return names


def _attributes(
    source: TorrentSource,
    category: TorznabCategory,
    magnet: str,
) -> list[TorznabAttr]:
    torrent_info = source.torrent_file.info
    indexer_torrent = source.indexer_torrent

    attributes = [
        TorznabAttr(name=TorznabAttrName.CATEGORY, value=str(category)),
        TorznabAttr(name=TorznabAttrName.SIZE, value=str(torrent_info.size)),
        TorznabAttr(
            name=TorznabAttrName.INFOHASH,
            value=torrent_info.info_hash.lower(),
        ),
        TorznabAttr(name=TorznabAttrName.MAGNET_URL, value=magnet),
        TorznabAttr(
            name=TorznabAttrName.SEEDERS,
            value=str(indexer_torrent.seeders),
        ),
    ]

    if indexer_torrent.imdb_id:
        imdb_id = indexer_torrent.imdb_id.removeprefix("tt")
        attributes.append(TorznabAttr(name=TorznabAttrName.IMDB, value=imdb_id))
        attributes.append(
            TorznabAttr(name=TorznabAttrName.IMDB_ID, value=f"tt{imdb_id}")
        )

    attributes.extend(
        TorznabAttr(name=TorznabAttrName.LANGUAGE, value=language)
        for language in _language_names(source)
    )

    return attributes


def build_feed_item(source: TorrentSource, category: TorznabCategory) -> FeedItem:
    torrent = source.torrent_file.info
    indexer = source.indexer_torrent.indexer_account.indexer_definition

    info_hash = torrent.info_hash.lower()
    magnet = _build_magnet(info_hash, torrent.name)

    return FeedItem(
        title=torrent.name,
        guid=FeedItemGuid(value=f"{indexer.id}:{source.indexer_torrent.torrent_id}"),
        indexer=FeedItemIndexer(id=indexer.id, name=indexer.name),
        type=INDEXER_PRIVACY,
        pub_date=format_date_to_rfc822(source.torrent_file.created_at),
        size=torrent.size,
        link=magnet,
        categories=[category],
        enclosure=FeedItemEnclosure(
            url=magnet, length=torrent.size
        ),  # Ez ideiglenes, magnet link nem megy privát trackerekkel. Kövi PR-ben jön a .torrent letöltő feature.
        attributes=_attributes(source, category, magnet),
    )
