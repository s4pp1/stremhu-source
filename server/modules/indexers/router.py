from fastapi import APIRouter, Depends, status
from modules.auth.dependencies import SessionGuard
from modules.indexer_accounts.dependencies import get_indexer_accounts_service
from modules.indexer_accounts.service import IndexerAccountsService
from modules.indexers.dependencies import get_indexers_service
from modules.indexers.schemas.api import (
    IndexerLoginRequest,
    IndexerResponse,
    IndexerUpdateRequest,
)
from modules.indexers.service import IndexersService
from modules.roles.enums import UserRole
from modules.users.models import UserModel

router = APIRouter(
    prefix="/indexers",
    tags=["Indexers"],
)


@router.get(
    "/",
    response_model=list[IndexerResponse],
)
async def get_list(
    indexer_accounts_service: IndexerAccountsService = Depends(
        get_indexer_accounts_service
    ),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    """Bejelentkezett indexerek listájának lekérése."""
    return indexer_accounts_service.find_list()


@router.post(
    "/login",
    status_code=status.HTTP_201_CREATED,
    response_model=IndexerResponse,
)
async def login(
    payload: IndexerLoginRequest,
    indexers_service: IndexersService = Depends(get_indexers_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    """Bejelentkezés egy új indexerre."""
    indexer_account = await indexers_service.login(payload)

    return IndexerResponse(
        id=indexer_account.indexer_id,
        username=indexer_account.username,
        download_full_torrent=indexer_account.download_full_torrent,
        hit_and_run=indexer_account.hit_and_run,
        keep_seed_seconds=indexer_account.keep_seed_seconds,
        updated_at=indexer_account.updated_at,
        created_at=indexer_account.created_at,
    )


@router.post(
    "/cleanup",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cleanup(
    indexers_service: IndexersService = Depends(get_indexers_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
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
    indexers_service: IndexersService = Depends(get_indexers_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    """Egy indexer beállításainak módosítása."""
    return await indexers_service.update(indexer_id, payload)


@router.delete(
    "/{indexer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete(
    indexer_id: str,
    indexers_service: IndexersService = Depends(get_indexers_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    """Indexer törlése/kijelentkeztetése."""
    await indexers_service.delete(indexer_id)
