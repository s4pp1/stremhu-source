from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.roles.enums import UserRole
from modules.settings.dependencies import get_settings_service
from modules.settings.schemas.api import (
    SystemSettingsResponse,
    SystemSettingsUpdateRequest,
)
from modules.settings.service import SettingsService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get(
    "/settings",
    response_model=SystemSettingsResponse,
)
def get_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> SystemSettingsResponse:
    return settings_service.get_system()


@router.put(
    "/settings",
    response_model=SystemSettingsResponse,
)
def update_settings(
    payload: SystemSettingsUpdateRequest,
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> SystemSettingsResponse:
    return settings_service.save_system(payload)
