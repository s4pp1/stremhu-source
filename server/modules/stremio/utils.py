from fastapi import HTTPException, status
from modules.stremio.constants import ADDON_APP_PREFIX_ID
from modules.stremio.enums import StreamIdType
from modules.stremio.schemas import (
    ParsedCatalogId,
    ParsedExtra,
    ParsedImdbStreamId,
    ParsedStreamId,
    ParsedStreamSeries,
    ParsedTorrentStreamId,
)


def parse_stream_id(value: str) -> ParsedStreamId:
    """
    Támogatott formátumok:
    - "stremhu-source:<indexer_id>:<torrent_id>" → torrent stream
    - "tt1234567" → IMDB stream
    - "tt1234567:1:2" → IMDB stream sorozattal (season=1, episode=2)
    """
    is_app = value.startswith(ADDON_APP_PREFIX_ID)

    if is_app:
        app_id = value.removeprefix(ADDON_APP_PREFIX_ID)
        parts = app_id.split(":")

        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Érvénytelen stream azonosító formátum.",
            )

        indexer_id = parts[0]
        torrent_id = parts[1]

        if not indexer_id or not torrent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Érvénytelen stream azonosító formátum.",
            )

        return ParsedTorrentStreamId(
            type=StreamIdType.TORRENT,
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )

    parts = value.split(":")
    imdb_id = parts[0]

    season: int | None = None
    if len(parts) > 1 and parts[1]:
        season = int(parts[1])

    episode: int | None = None
    if len(parts) > 2 and parts[2]:
        episode = int(parts[2])

    series: ParsedStreamSeries | None = None
    if season is not None and episode is not None:
        series = ParsedStreamSeries(season=season, episode=episode)

    return ParsedImdbStreamId(
        type=StreamIdType.IMDB,
        imdb_id=imdb_id,
        series=series,
    )


def parse_catalog_id(value: str) -> ParsedCatalogId | None:
    """
    Formátum: "stremhu-source:<trackerId>:<torrentId>"
    """
    meta_id = value

    is_app = meta_id.startswith(ADDON_APP_PREFIX_ID)
    if is_app:
        meta_id = value.removeprefix(ADDON_APP_PREFIX_ID)
    else:
        return None

    parts = meta_id.split(":")

    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Érvénytelen katalógus azonosító formátum.",
        )

    return ParsedCatalogId(
        tracker_id=parts[0],
        torrent_id=parts[1],
    )


def parse_extra(value: str | None) -> ParsedExtra:
    """
    Az NestJS ParseExtraPipe logikájának portolása.

    Formátum: "search=valami&skip=20&genre=action"
    """
    search: str | None = None
    genre: str | None = None
    skip: int | None = None

    if not value:
        return ParsedExtra(search=search, genre=genre, skip=skip)

    parts = value.split("&")

    for part in parts:
        key_value = part.split("=", 1)
        if len(key_value) != 2:
            continue

        key, value = key_value

        if key == "skip":
            skip = int(value)
        elif key == "search":
            search = value
        elif key == "genre":
            genre = value

    return ParsedExtra(search=search, genre=genre, skip=skip)
