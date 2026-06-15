from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.indexer_accounts.schemas import IndexerAccountUpdate
from app.modules.indexer_definitions.schemas.api import IndexerDefinitionResponse


class IndexerResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    indexer_id: str
    indexer_definition: IndexerDefinitionResponse
    username: str
    download_full_torrent: bool
    hit_and_run: bool | None
    keep_seed_seconds: int | None
    updated_at: datetime
    created_at: datetime


class IndexerLoginRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    indexer_id: str
    username: str
    password: str


class IndexerUpdateRequest(IndexerAccountUpdate):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
