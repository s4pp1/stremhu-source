from pydantic import BaseModel, ConfigDict

from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.torrent_files.schemas import TorrentFileSnapshot


class TorrentSource(BaseModel):
    """Megosztott keresési eredmény: csak Session nélküli, módosíthatatlan értéket tartalmaz."""

    model_config = ConfigDict(frozen=True)

    indexer_torrent: IndexerTorrent
    torrent_file: TorrentFileSnapshot
