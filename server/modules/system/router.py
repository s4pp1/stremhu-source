from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.roles.enums import UserRole
from modules.settings.dependencies import get_settings_service
from modules.settings.schemas import (
    SystemSettings,
    SystemSettingsSave,
)
from modules.settings.service import SettingsService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get(
    "/settings",
    response_model=SystemSettings,
)
def get_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> SystemSettings:
    return settings_service.get_system_or_raise()


@router.put(
    "/settings",
    response_model=SystemSettings,
)
def update_settings(
    payload: SystemSettingsSave,
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> SystemSettings:
    return settings_service.save_system(payload)
