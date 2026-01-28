from __future__ import annotations

import content_types
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
    stream = await stream_service.prepare_for_stream(
        info_hash=info_hash,
        file_index=file_index,
        range_header=range_header,
    )

    content_type = content_types.get_content_type(stream.file.name)
    media_type = content_type or "application/octet-stream"

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store, no-transform",
    }

    if range_header is None:
        status_code = 200
        headers["Content-Length"] = str(stream.file.size)
    else:
        status_code = 206
        headers["Content-Length"] = str(stream.end_byte - stream.start_byte + 1)
        headers["Content-Range"] = (
            f"bytes {stream.start_byte}-{stream.end_byte}/{stream.file.size}"
        )

    if request.method == "HEAD":
        return Response(
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )

    iterator = await stream_service.stream(
        stream=stream,
        request=request,
    )

    return StreamingResponse(
        content=iterator,
        media_type=media_type,
        status_code=status_code,
        headers=headers,
    )
