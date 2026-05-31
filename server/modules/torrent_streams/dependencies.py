from common.database import get_db
from fastapi import Depends
from modules.attributes.repository import AttributesRepository
from modules.attributes.service import AttributesService
from modules.indexers.dependencies import create_indexers_service
from modules.network.dependencies import create_network_service
from modules.torrent_files.dependencies import create_torrent_files_service
from modules.torrent_streams.service import TorrentStreamsService
from modules.torrents.dependencies import create_torrents_service
from sqlalchemy.orm import Session


def create_torrent_streams_service(db: Session) -> TorrentStreamsService:
    attributes_service = AttributesService(AttributesRepository(db))
    indexers_service = create_indexers_service(db)
    torrent_files_service = create_torrent_files_service(db)
    torrents_service = create_torrents_service(db)
    network_service = create_network_service(db)

    return TorrentStreamsService(
        db=db,
        indexers_service=indexers_service,
        torrent_files_service=torrent_files_service,
        torrents_service=torrents_service,
        attributes_service=attributes_service,
        network_service=network_service,
    )


def get_torrent_streams_service(
    db: Session = Depends(get_db),
) -> TorrentStreamsService:
    """FastAPI függőség-injektáló provider a TorrentStreamsService példányosításához."""
    return create_torrent_streams_service(db)
