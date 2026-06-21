class IndexerDefinitionException(Exception):
    """Általános indexer hiba."""

    pass


class CredentialsRequiredException(IndexerDefinitionException):
    """Hiányzó hitelesítési adatok."""

    pass


class AuthenticationException(IndexerDefinitionException):
    """Hibás felhasználónév vagy jelszó."""

    pass
