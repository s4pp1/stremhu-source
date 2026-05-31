from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.relay_settings.dependencies import get_relay_settings_service
from modules.relay_settings.schemas import RelaySettingsUpdateRequest
from modules.relay_settings.service import RelaySettingsService
from modules.roles.enums import UserRole
from modules.settings.schemas import (
    RelaySettings,
)
from modules.users.models import UserModel

router = APIRouter(
    prefix="/setting/relay",
    tags=["Setting"],
)


@router.get(
    "/",
    response_model=RelaySettings,
)
def get_relay_settings(
    relay_settings_service: RelaySettingsService = Depends(get_relay_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> RelaySettings:
    return relay_settings_service.get_settings()


@router.put(
    "/",
    response_model=RelaySettings,
)
def update_relay_settings(
    payload: RelaySettingsUpdateRequest,
    relay_settings_service: RelaySettingsService = Depends(get_relay_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> RelaySettings:
    return relay_settings_service.update_settings(payload)
