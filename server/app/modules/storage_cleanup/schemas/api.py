from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.storage_cleanup.enums import (
    StorageCleanupProtectedReasonEnum,
    StorageCleanupScoreComponentKeyEnum,
)


class StorageCleanupScoreComponent(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    key: StorageCleanupScoreComponentKeyEnum
    points: float
    max_points: float


class StorageCleanupQueueItem(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    info_hash: str
    name: str
    score: int
    components: list[StorageCleanupScoreComponent]
    protected_reason: StorageCleanupProtectedReasonEnum | None
    would_delete: bool
    downloaded_bytes: int


class StorageCleanupQueueResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    free_bytes: int
    total_bytes: int
    threshold_bytes: int
    below_threshold: bool
    min_score: int
    hnr_known: bool
    items: list[StorageCleanupQueueItem]
