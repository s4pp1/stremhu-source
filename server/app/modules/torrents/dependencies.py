from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.relay.dependencies import get_relay_service
from app.modules.torrent_files.dependencies import create_torrent_files_service
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.service import TorrentsService


def create_torrents_service(
    db: Session,
) -> TorrentsService:
    torrent_repository = TorrentRepository(db)
    relay_service = get_relay_service()
    torrent_files_service = create_torrent_files_service(db)
    indexer_accounts_service = create_indexer_accounts_service(db)

    return TorrentsService(
        torrent_repository=torrent_repository,
        relay_service=relay_service,
        torrent_files_service=torrent_files_service,
        indexer_accounts_service=indexer_accounts_service,
    )


def get_torrents_service(
    db: Annotated[Session, Depends(get_db)],
) -> TorrentsService:
    return create_torrents_service(db)
