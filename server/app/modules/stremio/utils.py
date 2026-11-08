from fastapi import HTTPException, status

from app.common.schemas.internal import SeriesInfo
from app.common.validators import validate_numeric_media_id
from app.modules.stremio.constants import ADDON_APP_PREFIX_ID
from app.modules.stremio.enums import StreamIdType
from app.modules.stremio.schemas import (
    ImdbStreamId,
    KitsuStreamId,
    MalStreamId,
    ParsedCatalogId,
    ParsedExtra,
    StreamId,
    TmdbStreamId,
    TorrentStreamId,
    TvdbStreamId,
)


def _numeric_media_id(value: str) -> str:
    try:
        return validate_numeric_media_id(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Érvénytelen numerikus médiaazonosító.") from None


def parse_stream_id(value: str) -> StreamId:
    """
    Támogatott formátumok:
    - "stremhu-source:<indexer_id>:<torrent_id>" → torrent stream
    - "tt1234567" → IMDB stream
    - "tt1234567:1:2" → IMDB stream sorozattal (season=1, episode=2)
    - "tvdb:12345" → TVDB stream
    - "tvdb:12345:1:2" → TVDB stream sorozattal (season=1, episode=2)
    - "kitsu:12345:1" → Kitsu anime stream
    - "tmdb:12345" vagy "tmdb:12345:1:2" → TMDB stream
    - "mal:12345:1" → MyAnimeList stream
    """
    if value.startswith("anime:"):
        value = value.removeprefix("anime:")

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
        file_index: int | None = None
        if len(parts) > 2 and parts[2].isdigit():
            file_index = int(_numeric_media_id(parts[2]))

        if not indexer_id or not torrent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Érvénytelen stream azonosító formátum.",
            )

        return TorrentStreamId(
            type=StreamIdType.TORRENT,
            indexer_id=indexer_id,
            torrent_id=torrent_id,
            file_index=file_index,
        )

    if value.startswith("tvdb"):
        if value.startswith("tvdb:"):
            tvdb_val = value[5:]
        elif value.startswith("tvdb_"):
            tvdb_val = value[5:]
        else:
            tvdb_val = value[4:]

        parts = tvdb_val.split(":")
        tvdb_id = _numeric_media_id(parts[0])

        if not tvdb_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Érvénytelen TVDB stream azonosító formátum.",
            )

        season: int | None = None
        if len(parts) > 1 and parts[1]:
            try:
                season = int(parts[1])
            except ValueError:
                season = None

        episode: int | None = None
        if len(parts) > 2 and parts[2]:
            try:
                episode = int(parts[2])
            except ValueError:
                episode = None

        series_info: SeriesInfo | None = None
        if season is not None and episode is not None:
            series_info = SeriesInfo(
                season=season,
                episode=episode,
            )

        return TvdbStreamId(
            type=StreamIdType.TVDB,
            tvdb_id=tvdb_id,
            series_info=series_info,
        )

    if value.startswith("kitsu"):
        if value.startswith("kitsu:"):
            kitsu_val = value[6:]
        elif value.startswith("kitsu_"):
            kitsu_val = value[6:]
        else:
            kitsu_val = value[5:]

        parts = kitsu_val.split(":")
        kitsu_id = _numeric_media_id(parts[0])

        if not kitsu_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Érvénytelen Kitsu stream azonosító formátum.",
            )

        episode = None
        if len(parts) > 1 and parts[1]:
            try:
                episode = int(parts[1])
            except ValueError:
                episode = None

        series_info = None
        if episode is not None:
            series_info = SeriesInfo(
                season=1,
                episode=episode,
            )

        return KitsuStreamId(
            type=StreamIdType.KITSU,
            kitsu_id=kitsu_id,
            episode=episode,
            series_info=series_info,
        )

    if value.startswith("tmdb"):
        if value.startswith("tmdb:"):
            tmdb_val = value[5:]
        elif value.startswith("tmdb_"):
            tmdb_val = value[5:]
        else:
            tmdb_val = value[4:]

        parts = tmdb_val.split(":")
        tmdb_id = _numeric_media_id(parts[0])

        if not tmdb_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Érvénytelen TMDB stream azonosító formátum.",
            )

        season = None
        if len(parts) > 1 and parts[1]:
            try:
                season = int(parts[1])
            except ValueError:
                season = None

        episode = None
        if len(parts) > 2 and parts[2]:
            try:
                episode = int(parts[2])
            except ValueError:
                episode = None

        series_info = None
        if season is not None and episode is not None:
            series_info = SeriesInfo(
                season=season,
                episode=episode,
            )

        return TmdbStreamId(
            type=StreamIdType.TMDB,
            tmdb_id=tmdb_id,
            series_info=series_info,
        )

    if value.startswith("mal"):
        if value.startswith("mal:"):
            mal_val = value[4:]
        elif value.startswith("mal_"):
            mal_val = value[4:]
        else:
            mal_val = value[3:]

        parts = mal_val.split(":")
        mal_id = _numeric_media_id(parts[0])

        if not mal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Érvénytelen MyAnimeList stream azonosító formátum.",
            )

        episode = None
        if len(parts) > 1 and parts[1]:
            try:
                episode = int(parts[1])
            except ValueError:
                episode = None

        series_info = None
        if episode is not None:
            series_info = SeriesInfo(
                season=1,
                episode=episode,
            )

        return MalStreamId(
            type=StreamIdType.MAL,
            mal_id=mal_id,
            episode=episode,
            series_info=series_info,
        )

    parts = value.split(":")
    imdb_id = parts[0]

    season = None
    if len(parts) > 1 and parts[1]:
        try:
            season = int(parts[1])
        except ValueError:
            season = None

    episode = None
    if len(parts) > 2 and parts[2]:
        try:
            episode = int(parts[2])
        except ValueError:
            episode = None

    series_info = None
    if season is not None and episode is not None:
        series_info = SeriesInfo(
            season=season,
            episode=episode,
        )

    return ImdbStreamId(
        type=StreamIdType.IMDB,
        imdb_id=imdb_id,
        series_info=series_info,
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
        indexer_id=parts[0],
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
        return ParsedExtra(
            search=search,
            genre=genre,
            skip=skip,
        )

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

    return ParsedExtra(
        search=search,
        genre=genre,
        skip=skip,
    )
