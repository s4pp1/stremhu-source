from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import StreamingResponse
from stream.dependencies import get_stream_service
from stream.service import StreamService

router = APIRouter(
    prefix="/stream",
    tags=["Stream"],
)


@router.get(
    "/{info_hash}/{file_index}",
    operation_id="get_stream_file",
)
@router.head(
    "/{info_hash}/{file_index}",
    operation_id="head_stream_file",
)
async def stream(
    info_hash: str,
    file_index: int,
    request: Request,
    range_header: str | None = Header(None, alias="Range"),
    stream_service: StreamService = Depends(get_stream_service),
):
    playback = await stream_service.stream(
        info_hash=info_hash,
        file_index=file_index,
        request=request,
        range_header=range_header,
    )

    content_type, _ = mimetypes.guess_type(playback.file_name)
    media_type = content_type or "application/octet-stream"

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store, no-transform",
    }

    if range_header is None:
        status_code = 200
        headers["Content-Length"] = str(playback.file_size)
    else:
        status_code = 206
        headers["Content-Length"] = str(playback.content_length)
        headers["Content-Range"] = (
            f"bytes {playback.start_byte}-{playback.end_byte}/{playback.file_size}"
        )

    if request.method == "HEAD":
        return Response(
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )

    return StreamingResponse(
        content=playback.iterator,
        media_type=media_type,
        status_code=status_code,
        headers=headers,
    )
