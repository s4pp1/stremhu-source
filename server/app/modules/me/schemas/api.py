from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class MeUpdateRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    username: str | None = None

    password: str | None = None

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
