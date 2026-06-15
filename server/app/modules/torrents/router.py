from typing import Annotated

import libtorrent as libtorrent
from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import SessionGuard
from app.modules.roles.constants import UserRoleKey
from app.modules.torrents.dependencies import get_torrents_service
from app.modules.torrents.schemas.api import TorrentResponse, TorrentUpdateRequest
from app.modules.torrents.schemas.internal import TorrentUpdate
from app.modules.torrents.service import TorrentsService
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/torrents",
    tags=["Torrents"],
)


@router.get(
    "/",
    response_model=list[TorrentResponse],
)
def get_list(
    torrents_service: Annotated[TorrentsService, Depends(get_torrents_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    torrent_pairs = torrents_service.get_torrents()
    return [
        TorrentResponse.from_torrent_with_relay(torrent_pair)
        for torrent_pair in torrent_pairs
    ]


@router.get(
    "/{info_hash}",
    response_model=TorrentResponse,
)
def get_one(
    info_hash: str,
    torrents_service: Annotated[TorrentsService, Depends(get_torrents_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    torrent_pair = torrents_service.get_by_info_hash(info_hash)
    return TorrentResponse.from_torrent_with_relay(torrent_pair)


@router.put(
    "/{info_hash}",
    response_model=TorrentResponse,
)
def update(
    info_hash: str,
    payload: TorrentUpdateRequest,
    torrents_service: Annotated[TorrentsService, Depends(get_torrents_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    torrent_pair = torrents_service.update(
        info_hash=info_hash,
        payload=TorrentUpdate.model_validate(
            payload.model_dump(exclude_unset=True),
        ),
    )
    return TorrentResponse.from_torrent_with_relay(torrent_pair)


@router.delete(
    "/{info_hash}",
    status_code=204,
)
def delete(
    info_hash: str,
    torrents_service: Annotated[TorrentsService, Depends(get_torrents_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    torrents_service.delete(
        info_hash=info_hash,
    )
