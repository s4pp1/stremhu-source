from modules.indexer_accounts.models import IndexerAccountModel
from modules.indexer_definitions.schemas import (
    IndexerDefinitionLogin,
    IndexerDefinitionTorrent,
)
from pydantic import BaseModel


class IndexerLogin(IndexerDefinitionLogin):
    indexer_id: str


class IndexerTorrent(IndexerDefinitionTorrent):
    indexer_account: IndexerAccountModel
    torrent_id: str


class DownloadedTorrentFile(BaseModel):
    indexer_account: IndexerAccountModel
    torrent_id: str
    torrent_bytes: bytes


class IndexerFindTorrentsResult(BaseModel):
    torrents: list[IndexerTorrent] = []
    next_page: int | None = None


class IndexerCleanupInfo(BaseModel):
    id: str
    keep_seed_seconds: int | None = None
    not_completed_torrent_ids: list[str] | None = None
