from enum import Enum


class StorageCleanupProtectedReasonEnum(str, Enum):
    PINNED = "pinned"
    ACTIVE_STREAM = "active_stream"
    HNR_PENDING = "hnr_pending"
    HNR_UNKNOWN = "hnr_unknown"
    KEEP_SEED = "keep_seed"


class StorageCleanupScoreComponentKeyEnum(str, Enum):
    FIRST_PLAYED = "first_played"
    LAST_PLAYED = "last_played"
    DOWNLOADED = "downloaded"
    SEEDERS = "seeders"
    LEECHERS = "leechers"
    UPLOADED = "uploaded"
