from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from server.modules.auth.dependencies import SessionGuard
from server.modules.indexers.dependencies import get_indexers_service
from server.modules.indexers.service import IndexersService
from server.modules.roles.constants import UserRoleKey
from server.modules.roles.schemas.api import RoleResponse
from server.modules.settings.dependencies import get_settings_service
from server.modules.settings.schemas.api import (
    SystemSettingsResponse,
    SystemSettingsUpdateRequest,
)
from server.modules.settings.service import SettingsService
from server.modules.system.dependencies import get_system_service
from server.modules.system.schemas.api import SystemStatusResponse
from server.modules.system.service import SystemService
from server.modules.torrent_files.dependencies import get_torrent_files_service
from server.modules.torrent_files.service import TorrentFilesService
from server.modules.users.models import UserModel

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
)
async def indexers_cleanup(
    indexers_service: Annotated[IndexersService, Depends(get_indexers_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    await indexers_service.cleanup_torrents_by_rules()


@router.post(
    "/restart",
)
def restart(
    background_tasks: BackgroundTasks,
    system_service: Annotated[SystemService, Depends(get_system_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    background_tasks.add_task(system_service.restart)
