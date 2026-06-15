class TrackerException(Exception):
    """Általános tracker hiba."""

    pass


class CredentialsRequiredException(TrackerException):
    """Hiányzó hitelesítési adatok."""

    pass


class AuthenticationException(TrackerException):
    """Hibás felhasználónév vagy jelszó."""

    pass
