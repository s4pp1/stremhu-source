from enum import Enum


class AuthenticationErrorEnum(str, Enum):
    """A NestJS AuthenticationErrorEnum portolása."""

    CREDENTIAL_ERROR = "credentials-error"
    SESSION_ERROR = "session-error"
