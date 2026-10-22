from typing import Annotated

from fastapi import APIRouter, Depends, Path

from server.modules.auth.dependencies import ApiKeyGuard
from server.modules.kodi.dependencies import get_kodi_service
from server.modules.kodi.schemas.api import (
    KodiImdbStreamsRequest,
    KodiImdbStreamsResponse,
)
from server.modules.kodi.service import KodiService
from server.modules.users.models import UserModel

router = APIRouter(
    prefix="/{api_key}/kodi",
    tags=["Kodi"],
)


@router.get(
    "/imdb/{imdb_id}/streams",
    response_model=KodiImdbStreamsResponse,
)
async def find_streams(
    imdb_id: Annotated[str, Path(..., description="IMDb azonosító")],
    query: Annotated[KodiImdbStreamsRequest, Depends()],
    kodi_service: Annotated[KodiService, Depends(get_kodi_service)],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> KodiImdbStreamsResponse:
    torrent_streams, errors = await kodi_service.imdb_streams(
        user=user,
        imdb_id=imdb_id,
        payload=query,
    )

    return KodiImdbStreamsResponse.from_torrent_streams_pair(
        torrent_streams=torrent_streams,
        errors=errors,
    )
