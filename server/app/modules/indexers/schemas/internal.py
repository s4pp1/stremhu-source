from pydantic import BaseModel

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.schemas.internal import (
    IndexerDefinitionLogin,
)
from app.modules.media_attributes.models import MediaAttributeModel


class IndexerLogin(IndexerDefinitionLogin):
    indexer_id: str


class IndexerTorrent(BaseModel):
    indexer_account: IndexerAccountModel
    torrent_id: str
    download_url: str
    imdb_id: str | None = None
    seeders: int = 0
    media_attributes: list[MediaAttributeModel] = []


class DownloadedTorrentFile(BaseModel):
    indexer_id: str
    torrent_id: str
    torrent_bytes: bytes


class IndexerFindTorrentsResult(BaseModel):
    torrents: list[IndexerTorrent] = []
    next_page: int | None = None


class IndexerCleanupInfo(BaseModel):
    id: str
    keep_seed_seconds: int | None = None
    not_completed_torrent_ids: list[str] | None = None
