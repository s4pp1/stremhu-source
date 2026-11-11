from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status
from fastapi.responses import RedirectResponse

from app.common.logger import logger
from app.modules.auth.dependencies import ApiKeyGuard
from app.modules.stremio.catalogs_service import StremioCatalogsService
from app.modules.stremio.dependencies import (
    get_parsed_catalog_id,
    get_parsed_extra,
    get_parsed_stream_id,
    get_stremio_catalogs_service,
    get_stremio_service,
)
from app.modules.stremio.enums import MediaType
from app.modules.stremio.schemas import (
    Manifest,
    MetaResponse,
    ParsedCatalogId,
    ParsedExtra,
    StreamId,
    StremioCatalogResponse,
    StremioStreams,
    StremioSubtitles,
)
from app.modules.stremio.service import StremioService
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/{api_key}/stremio",
    tags=["Stremio"],
)


@router.get(
    "/manifest.json",
    response_model=Manifest,
    response_model_exclude_none=True,
)
def manifest(
    stremio_service: Annotated[StremioService, Depends(get_stremio_service)],
    _: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> Manifest:
    # Az API-kulcs csak hitelesít: a manifest tartalma szándékosan felhasználófüggetlen.
    return stremio_service.manifest()


@router.get(
    "/configure",
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
def configure(
    _: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> RedirectResponse:
    return RedirectResponse(
        url="/",
        status_code=status.HTTP_308_PERMANENT_REDIRECT,
    )


@router.get(
    "/stream/{media_type}/{stream_id}.json",
    response_model=StremioStreams,
)
async def streams(
    media_type: Annotated[MediaType, Path(..., description="A média típusa")],
    parsed_id: Annotated[StreamId, Depends(get_parsed_stream_id)],
    stremio_service: Annotated[StremioService, Depends(get_stremio_service)],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> StremioStreams:
    logger.info(f"[StremioRouter] Stream kérés érkezett: {media_type=}, {parsed_id=}")
    streams = await stremio_service.get_streams(user, parsed_id)
    return StremioStreams(streams=streams)


@router.get(
    "/subtitles/{media_type}/{stream_id}.json",
    response_model=StremioSubtitles,
    response_model_exclude_none=True,
)
@router.get(
    "/subtitles/{media_type}/{stream_id}/{extra}.json",
    response_model=StremioSubtitles,
    response_model_exclude_none=True,
)
async def subtitles(
    request: Request,
    media_type: Annotated[MediaType, Path(..., description="A média típusa")],
    parsed_id: Annotated[StreamId, Depends(get_parsed_stream_id)],
    stremio_service: Annotated[StremioService, Depends(get_stremio_service)],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
    extra: str | None = None,
) -> StremioSubtitles:
    stremio_subs = await stremio_service.get_subtitles(
        user=user,
        parsed_id=parsed_id,
        extra=extra,
        query_params=dict(request.query_params),
    )
    return StremioSubtitles(subtitles=stremio_subs)



@router.get(
    "/catalog/{media_type}/{catalog_id}.json",
    response_model=StremioCatalogResponse,
)
async def catalog(
    media_type: MediaType,
    catalog_id: str,
    stremio_catalogs_service: Annotated[
        StremioCatalogsService, Depends(get_stremio_catalogs_service)
    ],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> StremioCatalogResponse:
    return await stremio_catalogs_service.get_catalog(
        media_type,
        catalog_id,
        user=user,
    )


@router.get(
    "/catalog/{media_type}/{catalog_id}/{extra}.json",
    response_model=StremioCatalogResponse,
)
async def catalog_with_extra(
    media_type: Annotated[MediaType, Path(..., description="A média típusa")],
    catalog_id: Annotated[str, Path(..., description="A katalógus azonosítója")],
    parsed_extra: Annotated[ParsedExtra, Depends(get_parsed_extra)],
    stremio_catalogs_service: Annotated[
        StremioCatalogsService, Depends(get_stremio_catalogs_service)
    ],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> StremioCatalogResponse:
    return await stremio_catalogs_service.get_catalog(
        media_type,
        catalog_id,
        parsed_extra,
        user=user,
    )


@router.get(
    "/meta/{media_type}/{meta_id}.json",
    response_model=MetaResponse,
)
async def meta(
    media_type: Annotated[MediaType, Path(..., description="A média típusa")],
    parsed_id: Annotated[ParsedCatalogId | None, Depends(get_parsed_catalog_id)],
    stremio_catalogs_service: Annotated[
        StremioCatalogsService, Depends(get_stremio_catalogs_service)
    ],
    _: Annotated[UserModel, Depends(ApiKeyGuard())],
) -> MetaResponse:
    if media_type not in (MediaType.MOVIE, MediaType.SERIES) or parsed_id is None:
        return MetaResponse(meta={})

    result = await stremio_catalogs_service.get_meta(
        indexer_id=parsed_id.indexer_id,
        torrent_id=parsed_id.torrent_id,
        media_type=media_type,
    )

    if not result:
        return MetaResponse(meta={})

    return MetaResponse(meta=result)
