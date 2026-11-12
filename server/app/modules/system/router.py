from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.modules.auth.dependencies import SessionGuard
from app.modules.indexers.dependencies import get_indexers_service
from app.modules.indexers.service import IndexersService
from app.modules.roles.constants import UserRoleKey
from app.modules.roles.schemas.api import RoleResponse
from app.modules.settings.dependencies import get_settings_service
from app.modules.settings.enums import StorageCleanupTriggerEnum
from app.modules.settings.schemas.api import (
    SystemSettingsResponse,
    SystemSettingsUpdateRequest,
)
from app.modules.settings.schemas.internal import (
    StorageCleanupLastRun,
    SystemSettings,
)
from app.modules.settings.service import SettingsService
from app.modules.storage_cleanup.dependencies import get_storage_cleanup_service
from app.modules.storage_cleanup.service import StorageCleanupService
from app.modules.system.dependencies import get_system_service
from app.modules.system.schemas.api import SystemStatusResponse
from app.modules.system.service import SystemService
from app.modules.torrent_files.dependencies import get_torrent_files_service
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get(
    "/roles",
    response_model=list[RoleResponse],
)
def get_roles(
    system_service: Annotated[SystemService, Depends(get_system_service)],
):
    return system_service.get_roles()


@router.get(
    "/status",
    response_model=SystemStatusResponse,
)
def get_status(
    system_service: Annotated[SystemService, Depends(get_system_service)],
):
    return system_service.status()


@router.get(
    "/settings",
    response_model=SystemSettingsResponse,
)
def get_settings(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return settings_service.get_system()


@router.put(
    "/settings",
    response_model=SystemSettingsResponse,
)
def update_settings(
    payload: SystemSettingsUpdateRequest,
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return settings_service.save_system(payload)


@router.post(
    "/torrent-files/cleanup",
)
def torrent_files_cleanup(
    torrent_files_service: Annotated[
        TorrentFilesService, Depends(get_torrent_files_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    torrent_files_service.run_retention_cleanup(retention_seconds=0)


@router.post(
    "/indexers/cleanup",
    response_model=StorageCleanupLastRun | None,
)
async def indexers_cleanup(
    indexers_service: Annotated[IndexersService, Depends(get_indexers_service)],
    storage_cleanup_service: Annotated[
        StorageCleanupService, Depends(get_storage_cleanup_service)
    ],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    """A karbantartás manuális futtatása: Hit'n'Run takarítás, majd tárhely alapú törlés, ha be van kapcsolva."""
    await indexers_service.cleanup_torrents_by_rules()

    system_settings = settings_service.find_system() or SystemSettings()
    if not system_settings.storage_cleanup_enabled:
        return None

    return await storage_cleanup_service.run(StorageCleanupTriggerEnum.MANUAL)


@router.post(
    "/restart",
)
def restart(
    background_tasks: BackgroundTasks,
    system_service: Annotated[SystemService, Depends(get_system_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    background_tasks.add_task(system_service.restart)
