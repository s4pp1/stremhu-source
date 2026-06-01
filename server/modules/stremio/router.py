from common.logger import logger
from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import RedirectResponse
from modules.auth.dependencies import ApiKeyGuard
from modules.stremio.constants import SEARCH_ID
from modules.stremio.dependencies import (
    get_parsed_catalog_id,
    get_parsed_extra,
    get_parsed_stream_id,
    get_stremio_service,
)
from modules.stremio.enums import MediaType
from modules.stremio.schemas import (
    Manifest,
    MetaResponse,
    ParsedCatalogId,
    ParsedExtra,
    ParsedStreamId,
    StremioCatalogResponse,
    StremioStreams,
)
from modules.stremio.service import StremioService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/{api_key}/stremio",
    tags=["Stremio"],
)


# ──────────────────────────────────────────────
# Manifest & Configure
# ──────────────────────────────────────────────


@router.get(
    "/manifest.json",
    response_model=Manifest,
    response_model_exclude_none=True,
    openapi_extra={"x-external": True},
)
def manifest(
    stremio_service: StremioService = Depends(get_stremio_service),
    user: UserModel = Depends(ApiKeyGuard()),
) -> Manifest:
    return stremio_service.manifest()


@router.get(
    "/configure",
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
    openapi_extra={"x-external": True},
)
def configure(
    _: UserModel = Depends(ApiKeyGuard()),
) -> RedirectResponse:
    return RedirectResponse(url="/", status_code=status.HTTP_308_PERMANENT_REDIRECT)


# ──────────────────────────────────────────────
# Streams
# ──────────────────────────────────────────────


@router.get(
    "/stream/{media_type}/{stream_id}.json",
    response_model=StremioStreams,
    openapi_extra={"x-external": True},
)
async def streams(
    media_type: MediaType = Path(..., description="A média típusa"),
    parsed_id: ParsedStreamId = Depends(get_parsed_stream_id),
    stremio_service: StremioService = Depends(get_stremio_service),
    user: UserModel = Depends(ApiKeyGuard()),
) -> StremioStreams:
    streams = await stremio_service.get_streams(user, parsed_id)
    return StremioStreams(streams=streams)


# ──────────────────────────────────────────────
# Catalogs
# ──────────────────────────────────────────────


@router.get(
    "/catalog/{media_type}/{catalog_id}.json",
    response_model=StremioCatalogResponse,
    openapi_extra={"x-external": True},
)
async def catalog(
    media_type: MediaType,
    catalog_id: str,
    stremio_service: StremioService = Depends(get_stremio_service),
    current_user: UserModel = Depends(ApiKeyGuard()),
) -> StremioCatalogResponse:
    return await _get_catalog(stremio_service, media_type, catalog_id)


@router.get(
    "/catalog/{media_type}/{catalog_id}/{extra}.json",
    response_model=StremioCatalogResponse,
    openapi_extra={"x-external": True},
)
async def catalog_with_extra(
    media_type: MediaType = Path(..., description="A média típusa"),
    catalog_id: str = Path(..., description="A katalógus azonosítója"),
    parsed_extra: ParsedExtra = Depends(get_parsed_extra),
    stremio_service: StremioService = Depends(get_stremio_service),
    current_user: UserModel = Depends(ApiKeyGuard()),
) -> StremioCatalogResponse:
    return await _get_catalog(stremio_service, media_type, catalog_id, parsed_extra)


async def _get_catalog(
    stremio_service: StremioService,
    media_type: MediaType,
    catalog_id: str,
    extra: ParsedExtra | None = None,
) -> StremioCatalogResponse:
    """Közös katalógus logika – a NestJS getCatalog() privát metódus portolása."""
    if extra is None:
        extra = ParsedExtra()

    search = extra.search

    if media_type != MediaType.MOVIE or catalog_id != SEARCH_ID or not search:
        return StremioCatalogResponse(metas=[])

    parts = search.split("-", 1)
    if len(parts) < 2 or parts[0] != "t":
        return StremioCatalogResponse(metas=[])

    torrent_id = parts[1]

    try:
        meta_previews = await stremio_service.get_metas(torrent_id)
    except Exception as e:
        logger.error("A lista lekérésénél hiba történt: %s", e)
        meta_previews = []

    return StremioCatalogResponse(metas=meta_previews)


# ──────────────────────────────────────────────
# Meta
# ──────────────────────────────────────────────


@router.get(
    "/meta/{media_type}/{meta_id}.json",
    response_model=MetaResponse,
    openapi_extra={"x-external": True},
)
async def meta(
    media_type: MediaType = Path(..., description="A média típusa"),
    parsed_id: ParsedCatalogId | None = Depends(get_parsed_catalog_id),
    stremio_service: StremioService = Depends(get_stremio_service),
    _: UserModel = Depends(ApiKeyGuard()),
) -> MetaResponse:
    if media_type != MediaType.MOVIE or parsed_id is None:
        return MetaResponse(meta={})

    result = await stremio_service.get_meta(parsed_id.tracker_id, parsed_id.torrent_id)

    if not result:
        return MetaResponse(meta={})

    return MetaResponse(meta=result)
