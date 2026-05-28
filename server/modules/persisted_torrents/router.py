import libtorrent as libtorrent
from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.persisted_torrents.dependencies import get_torrents_service
from modules.persisted_torrents.schemas import (
    RelayTorrent,
    TorrentUpdate,
)
from modules.persisted_torrents.service import TorrentsService
from modules.roles.enums import UserRole
from modules.users.models import UserModel

router = APIRouter(
    prefix="/torrents",
    tags=["Torrents"],
)


@router.get(
    "/",
    response_model=list[RelayTorrent],
)
def get_list(
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    return torrents_service.get_torrents()


@router.get(
    "/{info_hash}",
    response_model=RelayTorrent,
)
def get_one(
    info_hash: str,
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    return torrents_service.get_or_raise(info_hash)


@router.put(
    "/{info_hash}",
    response_model=RelayTorrent,
    operation_id="update_torrent",
)
def update(
    info_hash: str,
    req: TorrentUpdate,
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    return torrents_service.update(
        info_hash=info_hash,
        payload=req,
    )


@router.delete(
    "/{info_hash}",
    response_model=RelayTorrent,
    operation_id="delete_torrent",
)
def delete(
    info_hash: str,
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    return torrents_service.delete(
        info_hash=info_hash,
    )
