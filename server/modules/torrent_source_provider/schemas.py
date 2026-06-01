from modules.indexers.schemas import IndexerTorrent
from modules.torrent_files.models import TorrentFileModel
from pydantic import BaseModel


class TorrentSource(BaseModel):
    indexer_torrent: IndexerTorrent
    torrent_file: TorrentFileModel
