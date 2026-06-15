from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.indexer_definitions.schemas.api import IndexerDefinitionResponse
from app.modules.users.schemas.api import UserResponse


class PlaybackHistoryResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    playback_id: str

    user: UserResponse

    indexer_definition: IndexerDefinitionResponse

    torrent_name: str | None

    file_name: str | None

    created_at: datetime
