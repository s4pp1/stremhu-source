from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True)
class TorrentListRecord:
    torrent_info_hash: str
    file_info_hash: str
    indexer_id: str
    torrent_id: str
    is_persisted: bool
    full_download: bool | None
    updated_at: datetime
    created_at: datetime
    indexer_name: str
    indexer_url: str
    indexer_details_path: str
    indexer_requires_full_download: bool
    indexer_supports_totp: bool


class TorrentCreate(BaseModel):
    indexer_id: str
    torrent_id: str


class TorrentUpdate(BaseModel):
    is_persisted: bool | None = None
    full_download: bool | None = None
    resume_bytes: bytes | None = None
