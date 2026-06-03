import libtorrent as libtorrent
from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.roles.enums import UserRole
from modules.torrents.dependencies import get_torrents_service
from modules.torrents.schemas.api import TorrentResponse, TorrentUpdateRequest
from modules.torrents.service import TorrentsService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/torrents",
    tags=["Torrents"],
)


@router.get(
    "/",
    response_model=list[TorrentResponse],
)
def get_list(
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    torrent_pairs = torrents_service.get_torrents()
    return [
        TorrentResponse.from_torrent_pair(torrent_pair)
        for torrent_pair in torrent_pairs
    ]


@router.get(
    "/{info_hash}",
    response_model=TorrentResponse,
)
def get_one(
    info_hash: str,
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    torrent_pair = torrents_service.get_by_info_hash(info_hash)
    return TorrentResponse.from_torrent_pair(torrent_pair)


@router.put(
    "/{info_hash}",
    response_model=TorrentResponse,
)
def update(
    info_hash: str,
    req: TorrentUpdateRequest,
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    torrent_pair = torrents_service.update(
        info_hash=info_hash,
        payload=req,
    )
    return TorrentResponse.from_torrent_pair(torrent_pair)


@router.delete(
    "/{info_hash}",
    status_code=204,
)
def delete(
    info_hash: str,
    torrents_service: TorrentsService = Depends(get_torrents_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    torrents_service.delete(
        info_hash=info_hash,
    )
