from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.relay_settings.dependencies import get_relay_settings_service
from modules.relay_settings.service import RelaySettingsService
from modules.roles.enums import UserRole
from modules.settings.schemas.api import (
    RelaySettingsResponse,
    RelaySettingsUpdateRequest,
)
from modules.users.models import UserModel

router = APIRouter(
    prefix="/relay",
    tags=["Relay"],
)


@router.get(
    "/settings",
    response_model=RelaySettingsResponse,
)
def get_settings(
    relay_settings_service: RelaySettingsService = Depends(get_relay_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> RelaySettingsResponse:
    return relay_settings_service.get_settings()


@router.put(
    "/settings",
    response_model=RelaySettingsResponse,
)
def update_settings(
    payload: RelaySettingsUpdateRequest,
    relay_settings_service: RelaySettingsService = Depends(get_relay_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> RelaySettingsResponse:
    return relay_settings_service.update_settings(payload)
