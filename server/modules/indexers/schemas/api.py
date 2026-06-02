import datetime

from modules.indexer_accounts.schemas import IndexerAccountUpdate
from modules.indexers.schemas.internal import IndexerLogin
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class IndexerResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: str
    username: str
    download_full_torrent: bool
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None
    updated_at: datetime.datetime
    created_at: datetime.datetime


class IndexerLoginRequest(IndexerLogin):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class IndexerUpdateRequest(IndexerAccountUpdate):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
