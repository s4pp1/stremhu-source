from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.relay.dependencies import get_relay_service
from app.modules.relay_settings.service import RelaySettingsService
from app.modules.settings.dependencies import create_settings_service


def create_relay_settings_service(
    db: Session,
) -> RelaySettingsService:
    settings_service = create_settings_service(db)
    relay_service = get_relay_service()
    return RelaySettingsService(settings_service, relay_service)


def get_relay_settings_service(
    db: Annotated[Session, Depends(get_db)],
) -> RelaySettingsService:
    return create_relay_settings_service(db)
