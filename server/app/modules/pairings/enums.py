from enum import Enum


class PairingStatusEnum(str, Enum):
    PENDING = "pending"
    LINKED = "linked"
    EXPIRED = "expired"


class LinkResult(str, Enum):
    LINKED_NOW = "linked_now"
    ALREADY_LINKED_TO_SAME_USER = "already_linked_to_same_user"
    CONFLICT = "conflict"
    EXPIRED_OR_MISSING = "expired_or_missing"
