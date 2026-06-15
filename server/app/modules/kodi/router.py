from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.modules.auth.dependencies import ApiKeyGuard
from app.modules.kodi.dependencies import get_kodi_service
from app.modules.kodi.schemas import (
    KodiImdbStreams,
    KodiImdbStreamsParams,
)
from app.modules.kodi.service import KodiService
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/{api_key}/kodi",
    tags=["Kodi"],
)


@router.get(
    "/imdb/{imdb_id}/streams",
    response_model=KodiImdbStreams,
)
async def get_streams(
    imdb_id: Annotated[str, Path(..., description="IMDb azonosító")],
    query: Annotated[KodiImdbStreamsParams, Depends()],
    kodi_service: Annotated[KodiService, Depends(get_kodi_service)],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> KodiImdbStreams:
    """Lekéri a Kodi-kompatibilis streameket IMDb ID (és opcionális évad/epizód) alapján."""
    torrent_streams, errors = await kodi_service.imdb_streams(
        user=user,
        imdb_id=imdb_id,
        payload=query,
    )

    return KodiImdbStreams.from_torrent_streams_pair(
        torrent_streams=torrent_streams,
        errors=errors,
    )
