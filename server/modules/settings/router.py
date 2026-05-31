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
    prefix="/setting",
    tags=["Setting"],
)


@router.get(
    "/",
    response_model=SystemSettings,
    operation_id="get_app_settings",
)
def get_app_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> SystemSettings:
    return settings_service.get_system_or_raise()


@router.put(
    "/",
    response_model=SystemSettings,
    operation_id="update_app_settings",
)
def update_app_settings(
    payload: SystemSettingsSave,
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> SystemSettings:
    return settings_service.save_system(payload)
