from datetime import datetime

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.roles.schemas.api import RoleResponse
from app.modules.users.schemas.internal import (
    BaseUser,
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


class UserResponse(BaseUser):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: str
    role: RoleResponse
    api_key: str
    updated_at: datetime
    created_at: datetime
