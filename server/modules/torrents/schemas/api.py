from datetime import datetime

from modules.indexer_definitions.schemas import IndexerDefinition
from modules.torrents.schemas.internal import TorrentUpdate, TorrentWithRelay
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TorrentResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    info_hash: str
    indexer_definition: IndexerDefinition
    torrent_id: str
    name: str
    download_speed: int
    upload_speed: int
    downloaded: int
    uploaded: int
    total: int
    is_persisted: bool
    full_download: bool | None
    last_played_at: datetime
    updated_at: datetime
    created_at: datetime

    @classmethod
    def from_torrent_pair(
        cls,
        torrent_with_relay: TorrentWithRelay,
    ) -> "TorrentResponse":
        return cls(
            info_hash=torrent_with_relay.info_hash,
            indexer_definition=IndexerDefinition.model_validate(
                torrent_with_relay.torrent.indexer_account.indexer_definition
            ),
            torrent_id=torrent_with_relay.torrent.torrent_id,
            name=torrent_with_relay.relay.name,
            download_speed=torrent_with_relay.relay.download_speed,
            upload_speed=torrent_with_relay.relay.upload_speed,
            downloaded=torrent_with_relay.relay.downloaded,
            uploaded=torrent_with_relay.relay.uploaded,
            total=torrent_with_relay.relay.total,
            is_persisted=torrent_with_relay.torrent.is_persisted,
            full_download=torrent_with_relay.torrent.full_download,
            last_played_at=torrent_with_relay.torrent.last_played_at,
            updated_at=torrent_with_relay.torrent.updated_at,
            created_at=torrent_with_relay.torrent.created_at,
        )


class TorrentUpdateRequest(TorrentUpdate):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
