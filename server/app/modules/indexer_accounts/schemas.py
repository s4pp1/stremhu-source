import datetime

from pydantic import BaseModel

from app.modules.indexer_definitions.schemas.internal import IndexerDefinition


class IndexerAccountBase(BaseModel):
    username: str
    download_full_torrent: bool
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None


class IndexerAccountCreate(IndexerAccountBase):
    indexer_id: str
    password: str
    cookies: dict[str, str] | None = None


class IndexerAccount(IndexerAccountBase):
    indexer_definition: IndexerDefinition
    updated_at: datetime.datetime
    created_at: datetime.datetime


class IndexerAccountUpdate(BaseModel):
    download_full_torrent: bool | None = None
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None
