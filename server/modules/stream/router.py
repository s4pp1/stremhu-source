from __future__ import annotations

import logging

import content_types
from fastapi import APIRouter, Depends, Header, Path, Request, Response
from fastapi.responses import StreamingResponse
from modules.auth.dependencies import ApiKeyGuard
from modules.stream.dependencies import get_stream_service
from modules.stream.service import StreamService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/{api_key}/stream",
    tags=["Stream"],
)

logger = logging.getLogger(__name__)


@router.get(
    "/{indexer_id}/{torrent_id}/{file_index}/{session_id}",
    operation_id="get_stream_file",
)
@router.head(
    "/{indexer_id}/{torrent_id}/{file_index}/{session_id}",
    operation_id="head_stream_file",
)
async def stream(
    request: Request,
    indexer_id: str = Path(..., description="Az indexelő azonosítója"),
    torrent_id: str = Path(..., description="A torrent azonosítója"),
    file_index: int = Path(..., description="A fájl indexe"),
    session_id: str = Path(..., description="A session azonosítója"),
    range_header: str | None = Header(None, alias="Range"),
    stream_service: StreamService = Depends(get_stream_service),
    current_user: UserModel = Depends(ApiKeyGuard()),
) -> Response:

    parsed_range_header, file = await stream_service.prepare_for_stream(
        range_header=range_header,
        indexer_id=indexer_id,
        torrent_id=torrent_id,
        file_index=file_index,
    )

    content_type = content_types.get_content_type(file.name)
    media_type = content_type or "application/octet-stream"

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store, no-transform",
        "Connection": "close",
    }

    if range_header is None:
        status_code = 200
        headers["Content-Length"] = str(file.size)
    else:
        status_code = 206
        headers["Content-Length"] = str(parsed_range_header.content_length)
        headers["Content-Range"] = (
            f"bytes {parsed_range_header.start_byte}-{parsed_range_header.end_byte}/{file.size}"
        )

    if request.method == "HEAD":
        return Response(
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )

    iterator = await file.stream(
        request=request,
        stream_start_byte=parsed_range_header.start_byte,
        stream_end_byte=parsed_range_header.end_byte,
    )

    return StreamingResponse(
        content=iterator,
        media_type=media_type,
        status_code=status_code,
        headers=headers,
    )
