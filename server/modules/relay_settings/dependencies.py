from common.database import get_db
from fastapi import Depends
from modules.relay.dependencies import get_relay_service
from modules.relay_settings.service import RelaySettingsService
from modules.settings.dependencies import create_settings_service
from sqlalchemy.orm import Session


def create_relay_settings_service(
    db: Session,
) -> RelaySettingsService:
    settings_service = create_settings_service(db)
    relay_service = get_relay_service()
    return RelaySettingsService(settings_service, relay_service)


def get_relay_settings_service(
    db: Session = Depends(get_db),
) -> RelaySettingsService:
    return create_relay_settings_service(db)
