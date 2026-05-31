from functools import lru_cache

from modules.network.ddns.dependencies import create_ddns_service
from modules.network.ssl.service import SslService


@lru_cache(maxsize=1)
def create_ssl_service() -> SslService:
    """Létrehozza a SslService példányát (Singleton)."""
    ddns_service = create_ddns_service()
    return SslService(
        ddns_service=ddns_service,
    )


def get_ssl_service() -> SslService:
    """FastAPI függőség-injektáló provider a SslService példányosításához."""
    return create_ssl_service()
