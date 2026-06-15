from pydantic import BaseModel, Field

from app.modules.roles.constants import UserRoleKey


class BaseUser(BaseModel):
    username: str

    torrent_seed: int | None = None

    only_best_torrent: bool = False

    max_concurrent_streams: int | None = Field(
        default=None,
        gt=0,
    )


class UserCreate(BaseUser):
    password: str | None = None

    role_id: str = UserRoleKey.USER


class UserUpdate(BaseModel):
    username: str | None = None

    password: str | None = None

    role_id: str | None = None

    torrent_seed: int | None = None

    only_best_torrent: bool | None = None

    max_concurrent_streams: int | None = Field(
        default=None,
        gt=0,
    )
