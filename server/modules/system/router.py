from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.roles.constants import UserRoleKey
from modules.settings.dependencies import get_settings_service
from modules.settings.schemas.api import (
    SystemSettingsResponse,
    SystemSettingsUpdateRequest,
)
from modules.settings.service import SettingsService
from modules.system.dependencies import get_system_service
from modules.system.schemas.api import SystemStatusResponse
from modules.system.service import SystemService
from modules.torrent_files.dependencies import get_torrent_files_service
from modules.torrent_files.service import TorrentFilesService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get(
    "/status",
    response_model=SystemStatusResponse,
)
def get_status(
    system_service: SystemService = Depends(get_system_service),
):
    return system_service.status()


@router.get(
    "/settings",
    response_model=SystemSettingsResponse,
)
def get_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    return settings_service.get_system()


@router.put(
    "/settings",
    response_model=SystemSettingsResponse,
)
def update_settings(
    payload: SystemSettingsUpdateRequest,
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    return settings_service.save_system(payload)


@router.post(
    "/cleanup",
)
def cleanup(
    torrent_files_service: TorrentFilesService = Depends(get_torrent_files_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    torrent_files_service.run_retention_cleanup(retention_seconds=0)
