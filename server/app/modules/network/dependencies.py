from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.network.ddns.dependencies import create_ddns_service
from app.modules.network.service import NetworkService
from app.modules.network.ssl.dependencies import create_ssl_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.system.dependencies import create_system_service


def create_network_service(db: Session) -> NetworkService:
    """Létrehozza a NetworkService példányát."""
    settings_service = create_settings_service(db)
    ddns_service = create_ddns_service()
    ssl_service = create_ssl_service()
    system_service = create_system_service(db)

    return NetworkService(
        settings_service=settings_service,
        ddns_service=ddns_service,
        ssl_service=ssl_service,
        system_service=system_service,
    )


def get_network_service(
    db: Annotated[Session, Depends(get_db)],
) -> NetworkService:
    """FastAPI függőség-injektáló provider a NetworkService példányosításához."""
    return create_network_service(db)
