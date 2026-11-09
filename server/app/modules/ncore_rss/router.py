from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import SessionGuard
from app.modules.ncore_rss.dependencies import get_ncore_rss_service
from app.modules.ncore_rss.schemas import (
    NcoreRssFeedUpdate,
    NcoreRssItemResponse,
    NcoreRssItemUpdate,
    NcoreRssManualItemCreate,
    NcoreRssStatusResponse,
)
from app.modules.ncore_rss.service import NcoreRssService
from app.modules.roles.constants import UserRoleKey
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/indexers/ncore/rss",
    tags=["nCore RSS"],
)


@router.get("/", response_model=NcoreRssStatusResponse)
def get_status(
    service: Annotated[NcoreRssService, Depends(get_ncore_rss_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return service.get_status()


@router.get("/items", response_model=list[NcoreRssItemResponse])
def get_items(
    service: Annotated[NcoreRssService, Depends(get_ncore_rss_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return service.get_items()


@router.put("/feed", response_model=NcoreRssStatusResponse)
async def configure_feed(
    payload: NcoreRssFeedUpdate,
    service: Annotated[NcoreRssService, Depends(get_ncore_rss_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return await service.configure_feed(payload)


@router.delete("/feed", response_model=NcoreRssStatusResponse)
def clear_feed(
    service: Annotated[NcoreRssService, Depends(get_ncore_rss_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return service.clear_feed()


@router.post("/sync", response_model=NcoreRssStatusResponse)
async def sync_feed(
    service: Annotated[NcoreRssService, Depends(get_ncore_rss_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return await service.sync()


@router.post(
    "/items",
    response_model=NcoreRssItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_manual_item(
    payload: NcoreRssManualItemCreate,
    service: Annotated[NcoreRssService, Depends(get_ncore_rss_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return await service.add_manual_item(payload)


@router.patch("/items/{torrent_id}", response_model=NcoreRssItemResponse)
async def update_item(
    torrent_id: str,
    payload: NcoreRssItemUpdate,
    service: Annotated[NcoreRssService, Depends(get_ncore_rss_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return await service.update_item(
        torrent_id=torrent_id,
        payload=payload,
        update_imdb_id="imdb_id" in payload.model_fields_set,
        update_download_url="download_url" in payload.model_fields_set,
    )
