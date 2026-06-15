from enum import Enum


class SettingsKeyEnum(str, Enum):
    SYSTEM = "system"
    RELAY = "relay"
    NETWORK = "network"


class NetworkModeEnum(str, Enum):
    LOCAL = "local"
    AUTO = "auto"
    MANUAL = "manual"


class NetworkConnectionEnum(str, Enum):
    LOCAL = "local"
    PUBLIC = "public"
