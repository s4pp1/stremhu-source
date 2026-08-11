from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.roles.schemas.api import RoleResponse
from app.modules.users.schemas.internal import (
    UserCreate,
    UserUpdate,
)


class UserCreateRequest(UserCreate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class UserUpdateRequest(UserUpdate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: str
    username: str
    role: RoleResponse
    api_key: str
    updated_at: datetime
    created_at: datetime
    torrent_seed: int | None
    enable_smart_filter: bool
    smart_filter_grouping_preference_id: str | None
    smart_filter_limit: int
    max_concurrent_streams: int | None
