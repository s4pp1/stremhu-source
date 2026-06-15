from pydantic import BaseModel

from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.torrent_files.models import TorrentFileModel


class TorrentSource(BaseModel):
    indexer_torrent: IndexerTorrent
    torrent_file: TorrentFileModel
