from modules.roles.constants import UserRoleKey
from pydantic import BaseModel


class BaseUser(BaseModel):
    username: str
    torrent_seed: int | None = None
    only_best_torrent: bool = False


class UserCreate(BaseUser):
    password: str | None = None
    role_id: str = UserRoleKey.USER


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role_id: str | None = None
    torrent_seed: int | None = None
    only_best_torrent: bool | None = None
