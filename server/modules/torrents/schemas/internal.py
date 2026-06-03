from typing import NamedTuple

from modules.relay.schemas import RelayTorrent
from modules.torrents.models import TorrentModel
from pydantic import BaseModel


class TorrentWithRelay(NamedTuple):
    torrent: TorrentModel
    relay: RelayTorrent

    @property
    def info_hash(self) -> str:
        return self.torrent.info_hash


class TorrentCreate(BaseModel):
    indexer_id: str
    torrent_id: str


class TorrentUpdate(BaseModel):
    is_persisted: bool | None = None
    download_full_torrent: bool | None = None
