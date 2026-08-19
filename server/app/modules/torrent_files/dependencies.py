from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_files.repository import TorrentFilesRepository
from app.modules.torrent_files.service import TorrentFilesService


def create_torrent_files_service(db: Session) -> TorrentFilesService:
    torrent_files_repository = TorrentFilesRepository(db)
    return TorrentFilesService(torrent_files_repository)


def get_torrent_files_service(
    db: Annotated[Session, Depends(get_db)],
) -> TorrentFilesService:
    return create_torrent_files_service(db)


def create_isolated_torrent_files_service() -> IsolatedTorrentFilesService:
    return IsolatedTorrentFilesService()


def get_isolated_torrent_files_service() -> IsolatedTorrentFilesService:
    return create_isolated_torrent_files_service()
