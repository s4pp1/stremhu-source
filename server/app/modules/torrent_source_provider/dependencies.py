from sqlalchemy.orm import Session

from app.modules.indexers.dependencies import create_indexers_service
from app.modules.torrent_files.dependencies import create_torrent_files_service
from app.modules.torrent_source_provider.service import TorrentSourceProviderService


def create_torrent_source_provider_service(db: Session) -> TorrentSourceProviderService:
    indexers_service = create_indexers_service(db)
    torrent_files_service = create_torrent_files_service(db)

    return TorrentSourceProviderService(
        indexers_service=indexers_service,
        torrent_files_service=torrent_files_service,
    )
