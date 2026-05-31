from datetime import datetime

from modules.preferences.enums import PreferenceEnum
from modules.roles.enums import UserRole
from modules.roles.schemas import Role
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseUser(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    username: str
    torrent_seed: int | None = None
    only_best_torrent: bool = False


class UserCreateRequest(BaseUser):
    password: str
    role_id: UserRole = UserRole.USER


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    username: str | None = None
    password: str | None = None
    role_id: UserRole | None = None
    torrent_seed: int | None = None
    only_best_torrent: bool | None = None


class User(BaseUser):
    id: str
    role: Role
    token: str
    updated_at: datetime
    created_at: datetime


class UserPreferenceCreateRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    preference: PreferenceEnum
    preferred: list[str]


class UserPreferenceUpdateRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    preferred: list[str]


class UserPreferencesReorderRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    preferences: list[PreferenceEnum]
