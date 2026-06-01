from modules.indexers.dependencies import create_indexers_service
from modules.torrent_files.dependencies import create_torrent_files_service
from modules.torrent_source_provider.service import TorrentSourceProviderService
from sqlalchemy.orm import Session


def create_torrent_source_provider_service(db: Session) -> TorrentSourceProviderService:
    indexers_service = create_indexers_service(db)
    torrent_files_service = create_torrent_files_service(db)

    return TorrentSourceProviderService(
        indexers_service=indexers_service,
        torrent_files_service=torrent_files_service,
    )
