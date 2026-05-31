from common.database import get_db
from fastapi import Depends
from modules.network.ddns.dependencies import create_ddns_service
from modules.network.service import NetworkService
from modules.network.ssl.dependencies import create_ssl_service
from modules.settings.dependencies import create_settings_service
from modules.system.dependencies import create_system_service
from sqlalchemy.orm import Session


def create_network_service(db: Session) -> NetworkService:
    """Létrehozza a NetworkService példányát."""
    settings_service = create_settings_service(db)
    ddns_service = create_ddns_service()
    ssl_service = create_ssl_service()
    system_service = create_system_service()

    return NetworkService(
        settings_service=settings_service,
        ddns_service=ddns_service,
        ssl_service=ssl_service,
        system_service=system_service,
    )


def get_network_service(
    db: Session = Depends(get_db),
) -> NetworkService:
    """FastAPI függőség-injektáló provider a NetworkService példányosításához."""
    return create_network_service(db)
