from typing import Annotated

from fastapi import APIRouter, Depends

from server.modules.auth.dependencies import SessionGuard
from server.modules.filesystem.dependencies import get_filesystem_service
from server.modules.filesystem.schemas.api import (
    BrowseDirectoriesResponse,
    CreateDirectoryRequest,
    CreateDirectoryResponse,
)
from server.modules.filesystem.service import FilesystemService
from server.modules.roles.constants import UserRoleKey
from server.modules.users.models import UserModel

router = APIRouter(
    prefix="/filesystem",
    tags=["filesystem"],
)


@router.get(
    "/directories",
    response_model=BrowseDirectoriesResponse,
)
def browse_directories(
    filesystem_service: Annotated[FilesystemService, Depends(get_filesystem_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
    path: str | None = None,
):
    return filesystem_service.browse_directories(path=path)


@router.post(
    "/directories",
    response_model=CreateDirectoryResponse,
)
def create_directory(
    payload: CreateDirectoryRequest,
    filesystem_service: Annotated[FilesystemService, Depends(get_filesystem_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    created_path = filesystem_service.create_directory(
        parent_path=payload.parent_path,
        name=payload.name,
    )
    return CreateDirectoryResponse(path=str(created_path))
