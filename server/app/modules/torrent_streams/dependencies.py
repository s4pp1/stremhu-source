from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.settings.dependencies import create_settings_service
from app.modules.torrent_source_provider.dependencies import (
    create_torrent_source_provider_service,
)
from app.modules.torrent_streams.service import TorrentStreamsService
from app.modules.torrents.dependencies import create_torrents_service


def create_torrent_streams_service(
    db: Session,
) -> TorrentStreamsService:
    torrent_source_provider_service = create_torrent_source_provider_service(db)
    torrents_service = create_torrents_service(db)
    settings_service = create_settings_service(db)

    return TorrentStreamsService(
        db=db,
        torrent_source_provider_service=torrent_source_provider_service,
        torrents_service=torrents_service,
        settings_service=settings_service,
    )


def get_torrent_streams_service(
    db: Annotated[Session, Depends(get_db)],
) -> TorrentStreamsService:
    return create_torrent_streams_service(db)
