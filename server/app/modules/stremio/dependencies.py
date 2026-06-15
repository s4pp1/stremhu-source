from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.settings.dependencies import create_settings_service
from app.modules.stremio.catalogs_service import StremioCatalogsService
from app.modules.stremio.schemas import (
    ParsedCatalogId,
    ParsedExtra,
    StreamId,
)
from app.modules.stremio.service import StremioService
from app.modules.stremio.utils import parse_catalog_id, parse_extra, parse_stream_id
from app.modules.torrent_files.dependencies import create_torrent_files_service
from app.modules.torrent_source_provider.dependencies import (
    create_torrent_source_provider_service,
)
from app.modules.torrent_streams.dependencies import (
    create_torrent_streams_service,
)


def create_stremio_catalogs_service(
    db: Session,
) -> StremioCatalogsService:
    torrent_files_service = create_torrent_files_service(db)
    torrent_source_provider_service = create_torrent_source_provider_service(db)

    return StremioCatalogsService(
        torrent_files_service=torrent_files_service,
        torrent_source_provider_service=torrent_source_provider_service,
    )


def get_stremio_catalogs_service(
    db: Annotated[Session, Depends(get_db)],
) -> StremioCatalogsService:
    return create_stremio_catalogs_service(db)


def create_stremio_service(
    db: Session,
) -> StremioService:
    torrent_streams_service = create_torrent_streams_service(db)
    settings_service = create_settings_service(db)

    return StremioService(
        torrent_streams_service=torrent_streams_service,
        settings_service=settings_service,
    )


def get_stremio_service(
    db: Annotated[Session, Depends(get_db)],
) -> StremioService:
    return create_stremio_service(db)


def get_parsed_stream_id(
    stream_id: Annotated[
        str, Path(..., description="Stream azonosító (IMDB ID vagy torrent ID)")
    ],
) -> StreamId:
    return parse_stream_id(stream_id)


def get_parsed_catalog_id(
    meta_id: Annotated[
        str, Path(..., description="Katalógus / Meta azonosító (trackerId:torrentId)")
    ],
) -> ParsedCatalogId | None:
    return parse_catalog_id(meta_id)


def get_parsed_extra(
    extra: Annotated[
        str,
        Path(
            ..., description="Kiegészítő szűrési paraméterek (pl. search=film&skip=20)"
        ),
    ],
) -> ParsedExtra:
    return parse_extra(extra)
