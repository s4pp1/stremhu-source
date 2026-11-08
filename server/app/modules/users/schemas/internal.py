from pydantic import BaseModel, Field

from app.modules.roles.constants import UserRoleKey


class BaseUser(BaseModel):
    username: str

    torrent_seed: int | None = None

    enable_smart_filter: bool = Field(
        default=False,
    )

    enable_stream_deduplication: bool = Field(
        default=True,
    )

    smart_filter_grouping_preference_id: str | None = None

    smart_filter_limit: int = Field(
        default=1,
        ge=1,
    )

    enable_fallback_subtitles: bool = Field(
        default=False,
    )

    enable_catalog_search: bool = Field(
        default=True,
    )

    enable_downloaded_marker: bool = Field(
        default=True,
    )

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

    enable_smart_filter: bool | None = None

    enable_stream_deduplication: bool | None = None

    smart_filter_grouping_preference_id: str | None = None

    smart_filter_limit: int | None = Field(
        default=None,
        ge=1,
    )

    enable_fallback_subtitles: bool | None = None

    enable_catalog_search: bool | None = None

    enable_downloaded_marker: bool | None = None

    max_concurrent_streams: int | None = Field(
        default=None,
        gt=0,
    )
