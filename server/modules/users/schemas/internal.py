from datetime import datetime

from modules.roles.enums import UserRole
from modules.roles.schemas import Role
from pydantic import BaseModel


class BaseUser(BaseModel):
    username: str
    torrent_seed: int | None = None
    only_best_torrent: bool = False


class UserCreate(BaseUser):
    password: str
    role_id: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role_id: UserRole | None = None
    torrent_seed: int | None = None
    only_best_torrent: bool | None = None


class User(BaseUser):
    id: str
    role: Role
    api_key: str
    updated_at: datetime
    created_at: datetime


class UserPreferenceCreate(BaseModel):
    preference_id: str
    attribute_ids: list[str]


class UserPreferenceUpdate(BaseModel):
    attribute_ids: list[str]


class UserPreferencesReorder(BaseModel):
    preference_ids: list[str]
