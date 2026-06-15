from enum import Enum


class PairingStatusEnum(str, Enum):
    PENDING = "pending"
    LINKED = "linked"
    EXPIRED = "expired"
