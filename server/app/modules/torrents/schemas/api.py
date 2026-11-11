from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.indexer_definitions.schemas.api import IndexerDefinitionResponse
from app.modules.relay.schemas import RelayTorrent
from app.modules.torrents.schemas.internal import TorrentListRecord, TorrentWithRelay


class TorrentResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    info_hash: str
    indexer_definition: IndexerDefinitionResponse
    torrent_id: str
    name: str
    download_speed: int
    upload_speed: int
    downloaded: int
    uploaded: int
    total: int
    is_persisted: bool
    full_download: bool | None
    updated_at: datetime
    created_at: datetime

    @classmethod
    def from_list_record(cls, record: TorrentListRecord, relay: RelayTorrent) -> "TorrentResponse":
        return cls(
            info_hash=record.torrent_info_hash,
            indexer_definition=IndexerDefinitionResponse(
                id=record.indexer_id,
                name=record.indexer_name,
                url=record.indexer_url,
                details_path=record.indexer_details_path,
                requires_full_download=record.indexer_requires_full_download,
                supports_totp=record.indexer_supports_totp,
            ),
            torrent_id=record.torrent_id,
            name=relay.name,
            download_speed=relay.download_speed,
            upload_speed=relay.upload_speed,
            downloaded=relay.downloaded,
            uploaded=relay.uploaded,
            total=relay.total,
            is_persisted=record.is_persisted,
            full_download=record.full_download,
            updated_at=record.updated_at,
            created_at=record.created_at,
        )

    @classmethod
    def from_torrent_with_relay(
        cls,
        torrent_with_relay: TorrentWithRelay,
    ) -> "TorrentResponse":
        return cls(
            info_hash=torrent_with_relay.info_hash,
            indexer_definition=IndexerDefinitionResponse.model_validate(
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
            updated_at=torrent_with_relay.torrent.updated_at,
            created_at=torrent_with_relay.torrent.created_at,
        )


class TorrentUpdateRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    is_persisted: bool | None = None
    full_download: bool | None = None
