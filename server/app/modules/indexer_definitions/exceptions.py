class IndexerDefinitionException(Exception):
    """Általános indexer hiba."""

    pass


class CredentialsRequiredException(IndexerDefinitionException):
    """Hiányzó hitelesítési adatok."""

    pass


class AuthenticationException(IndexerDefinitionException):
    """Hibás felhasználónév vagy jelszó."""

    pass


class AuthenticationOtherException(IndexerDefinitionException):
    """Egyéb hitelesítési probléma (pl. Cloudflare, karbantartás, IP tiltás)."""

    pass


class IndexerResponseTooLargeException(IndexerDefinitionException):
    """A válasz dekódolt törzse meghaladta a megengedett méretet."""

    pass


class IndexerDownloadHostNotAllowedException(IndexerDefinitionException):
    """A letöltés (vagy egy átirányítása) nem a tracker saját domainjére mutat."""

    pass


class TechInfoUnavailableException(IndexerDefinitionException):
    """A Tech Info lekérése nem sikerült (hálózati vagy szerverhiba); nem azonos a „nincs adat” esettel."""

    pass
