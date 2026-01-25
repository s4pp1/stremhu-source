from fastapi import APIRouter, Depends
from libtorrent_client.dependencies import get_libtorrent_client_service
from libtorrent_client.schemas import UpdateSettings
from libtorrent_client.service import LibtorrentClientService

router = APIRouter(
    prefix="/setting",
    tags=["Setting"],
)


@router.put(
    "/",
    response_model=None,
    operation_id="update",
)
async def update(
    req: UpdateSettings,
    libtorrent_client_service: LibtorrentClientService = Depends(
        get_libtorrent_client_service
    ),
):
    libtorrent_client_service.update_settings(req)
