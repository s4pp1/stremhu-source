import secrets

from server.common.logger import logger
from server.config import config

_cached_secret: str | None = None


def get_session_secret() -> str:
    """Visszaadja a munkamenet titkosítási kulcsát a system_dir/session.key fájlból.

    Ha a kulcsfájl nem létezik, automatikusan generál egy új véletlenszerű kulcsot,
    és elmenti a fájlba. Környezeti változóból vagy CLI-ből nem bírálható felül;
    a perzisztencia a fájlrendszeren keresztül (system_dir) történik.
    """
    global _cached_secret
    if _cached_secret:
        return _cached_secret

    key_file = config.system_dir / "session.key"
    if key_file.exists():
        try:
            secret = key_file.read_text(encoding="utf-8").strip()
            if secret:
                _cached_secret = secret
                return secret
        except Exception:
            logger.warning(
                "Nem sikerült beolvasni a session.key fájlt, új kulcs generálása..."
            )

    secret = secrets.token_urlsafe(32)
    try:
        config.system_dir.mkdir(parents=True, exist_ok=True)
        key_file.write_text(secret, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Nem sikerült elmenteni a session.key fájlt: {e}")

    _cached_secret = secret
    return secret


def ensure_session_secret() -> str:
    """Gondoskodik a session.key kulcsfájl létrehozásáról az alkalmazás indításakor."""
    return get_session_secret()
