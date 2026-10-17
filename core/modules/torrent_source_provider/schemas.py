from pydantic import BaseModel, ConfigDict

from core.modules.indexers.schemas.internal import IndexerTorrent
from core.modules.torrent_files.models import TorrentFileModel


class TorrentSource(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    indexer_torrent: IndexerTorrent
    torrent_file: TorrentFileModel
