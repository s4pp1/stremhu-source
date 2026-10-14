from pydantic import BaseModel, ConfigDict

from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.torrent_files.models import TorrentFileModel


class TorrentSource(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    indexer_torrent: IndexerTorrent
    torrent_file: TorrentFileModel
