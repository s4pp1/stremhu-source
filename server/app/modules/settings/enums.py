from enum import Enum


class SettingsKeyEnum(str, Enum):
    SYSTEM = "system"
    RELAY = "relay"
    NETWORK = "network"


class NetworkModeEnum(str, Enum):
    LOCAL = "local"
    AUTO = "auto"
    MANUAL = "manual"


class RelayEncryptionEnum(str, Enum):
    ENABLED = "enabled"
    FORCED = "forced"
    DISABLED = "disabled"


class NetworkConnectionEnum(str, Enum):
    LOCAL = "local"
    PUBLIC = "public"


class StorageCleanupThresholdUnitEnum(str, Enum):
    PERCENT = "percent"
    GB = "gb"


class StorageCleanupTriggerEnum(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
