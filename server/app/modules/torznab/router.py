import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.modules.torznab.constants import (
    FEED_MEDIA_TYPE,
    TORRENT_MEDIA_TYPE,
    XML_MEDIA_TYPE,
)
from app.modules.torznab.dependencies import (
    get_torznab_service,
    require_torznab_path_user,
    require_torznab_user,
)
from app.modules.torznab.enums import TorznabFunction
from app.modules.torznab.query import parse_torznab_query
from app.modules.torznab.service import TorznabService
from app.modules.torznab.utils import xml_response
from app.modules.users.models import UserModel

router = APIRouter(tags=["Torznab"])


# Prowlarr és társai szeretik a /api postfixet hozzáfűzni valamiért.
@router.get("/torznab", include_in_schema=False)
@router.get("/torznab/api", include_in_schema=False)
async def torznab_api(
    request: Request,
    torznab_service: Annotated[TorznabService, Depends(get_torznab_service)],
    user: Annotated[UserModel, Depends(require_torznab_user)],
) -> Response:
    query = parse_torznab_query(request)

    if query.function is TorznabFunction.CAPS:
        return xml_response(torznab_service.capabilities(), XML_MEDIA_TYPE)

    link = await asyncio.to_thread(
        torznab_service.feed_link,
        request.url.path,
        request.url.query,
    )
    items, total = await torznab_service.search(query, user.api_key)

    return xml_response(
        torznab_service.feed(
            link=link,
            items=items,
            offset=query.offset,
            total=total,
        ),
        FEED_MEDIA_TYPE,
    )


@router.get("/{api_key}/torznab/download/{token}", include_in_schema=False)
async def torznab_download(
    token: str,
    torznab_service: Annotated[TorznabService, Depends(get_torznab_service)],
    _: Annotated[UserModel, Depends(require_torznab_path_user)],
) -> Response:
    torrent_bytes = await torznab_service.torrent_bytes(token)

    if torrent_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return Response(content=torrent_bytes, media_type=TORRENT_MEDIA_TYPE)
