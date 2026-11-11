import datetime

from pydantic import BaseModel, ConfigDict

from app.common.torrent_info import TorrentInfo
from app.modules.torrent_files.models import TorrentFileModel


class TorrentFileSnapshot(BaseModel):
    """Session nélküli .torrent-leíró; a torrent_bytes nem része, a TorrentInfo materializált."""

    model_config = ConfigDict(frozen=True)

    indexer_id: str
    torrent_id: str
    info_hash: str
    created_at: datetime.datetime
    info: TorrentInfo

    @classmethod
    def from_model(cls, model: TorrentFileModel) -> "TorrentFileSnapshot":
        return cls(
            indexer_id=model.indexer_id,
            torrent_id=model.torrent_id,
            info_hash=model.info_hash,
            created_at=model.created_at,
            info=model.info,
        )


class TorrentFileIdentifier(BaseModel):
    indexer_id: str
    torrent_id: str


class TorrentFilesFilter(BaseModel):
    indexer_id: str | None = None
    torrent_id: str | None = None
    identifiers: list[TorrentFileIdentifier] | None = None
    exclude_persisted: bool | None = None
