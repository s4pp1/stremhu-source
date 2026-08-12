from typing import NamedTuple

from pydantic import BaseModel

from app.modules.relay.schemas import RelayTorrent
from app.modules.torrents.models import TorrentModel


class TorrentWithRelay(NamedTuple):
    torrent: TorrentModel
    relay: RelayTorrent

    @property
    def info_hash(self) -> str:
        return self.torrent.info_hash


class TorrentKey(NamedTuple):
    indexer_id: str
    torrent_id: str


class StorageUsage(BaseModel):
    used_bytes: int
    free_bytes: int
    total_bytes: int


class TorrentCreate(BaseModel):
    indexer_id: str
    torrent_id: str


class TorrentUpdate(BaseModel):
    is_persisted: bool | None = None
    full_download: bool | None = None
    resume_bytes: bytes | None = None
