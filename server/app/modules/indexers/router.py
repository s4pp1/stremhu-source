from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import SessionGuard
from app.modules.indexer_accounts.dependencies import get_indexer_accounts_service
from app.modules.indexer_accounts.service import IndexerAccountsService
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.indexer_definitions.schemas.api import IndexerDefinitionResponse
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.indexers.dependencies import get_indexers_service
from app.modules.indexers.schemas.api import (
    IndexerLoginRequest,
    IndexerResponse,
    IndexerUpdateRequest,
)
from app.modules.indexers.schemas.internal import IndexerLogin
from app.modules.indexers.service import IndexersService
from app.modules.roles.constants import UserRoleKey
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/indexers",
    tags=["Indexers"],
)


@router.get(
    "/",
    response_model=list[IndexerResponse],
)
async def get_list(
    indexer_accounts_service: Annotated[
        IndexerAccountsService, Depends(get_indexer_accounts_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    """Bejelentkezett indexerek listájának lekérése."""
    return indexer_accounts_service.find_list()


@router.get(
    "/definitions",
    response_model=list[IndexerDefinitionResponse],
)
async def get_definition_list(
    indexer_definitions_service: Annotated[
        IndexerDefinitionsService, Depends(get_indexer_definitions_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return indexer_definitions_service.get_list()


@router.post(
    "/login",
    status_code=status.HTTP_201_CREATED,
    response_model=IndexerResponse,
)
async def login(
    payload: IndexerLoginRequest,
    indexers_service: Annotated[IndexersService, Depends(get_indexers_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    indexer_account = await indexers_service.login(
        IndexerLogin(
            indexer_id=payload.indexer_id,
            username=payload.username,
            password=payload.password,
        )
    )
    return indexer_account


@router.post(
    "/cleanup",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cleanup(
    indexers_service: Annotated[IndexersService, Depends(get_indexers_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    """Karbantartási takarítás manuális futtatása."""
    await indexers_service.cleanup_torrents_by_rules()


@router.put(
    "/{indexer_id}",
    response_model=IndexerResponse,
)
async def update(
    indexer_id: str,
    payload: IndexerUpdateRequest,
    indexers_service: Annotated[IndexersService, Depends(get_indexers_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return await indexers_service.update(indexer_id, payload)


@router.delete(
    "/{indexer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete(
    indexer_id: str,
    indexers_service: Annotated[IndexersService, Depends(get_indexers_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    """Indexer törlése/kijelentkeztetése."""
    await indexers_service.delete(indexer_id)
