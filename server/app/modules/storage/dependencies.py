from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.relay.dependencies import get_relay_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.storage.service import StorageService
from app.modules.torrents.dependencies import create_torrents_service
from app.modules.torrents.repository import TorrentRepository


def create_storage_service(db: Session) -> StorageService:
    return StorageService(
        torrent_repository=TorrentRepository(db),
        torrents_service=create_torrents_service(db),
        settings_service=create_settings_service(db),
        relay_service=get_relay_service(),
    )


def get_storage_service(
    db: Annotated[Session, Depends(get_db)],
) -> StorageService:
    return create_storage_service(db)
