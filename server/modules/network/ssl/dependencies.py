from modules.network.ddns.dependencies import create_ddns_service
from modules.network.ssl.service import SslService


def create_ssl_service() -> SslService:
    """Létrehozza a SslService példányát."""
    ddns_service = create_ddns_service()
    return SslService(
        ddns_service=ddns_service,
    )


def get_ssl_service() -> SslService:
    """FastAPI függőség-injektáló provider a SslService példányosításához."""
    return create_ssl_service()
