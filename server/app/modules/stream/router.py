from __future__ import annotations

from typing import Annotated

import content_types
from fastapi import (
    APIRouter,
    Depends,
    Header,
    Request,
    Response,
)
from fastapi.responses import StreamingResponse

from app.common.database import isolated_db_session
from app.common.schemas.internal import ImdbInfo
from app.modules.auth.dependencies import create_auth_service
from app.modules.playback_histories.dependencies import (
    create_playback_histories_service,
)
from app.modules.playback_histories.schemas.internal import (
    PlaybackHistoryClientInfo,
)
from app.modules.playbacks.dependencies import create_playbacks_service
from app.modules.relay.dependencies import get_relay_service
from app.modules.stream.dependencies import (
    create_stream_service,
    get_parsed_stream_token,
)
from app.modules.stream.schemas import StreamToken

router = APIRouter(
    prefix="/{api_key}/stream",
    tags=["Stream"],
)


@router.get(
    "/{stream_token}",
)
@router.head(
    "/{stream_token}",
)
async def stream(
    request: Request,
    api_key: str,
    stream_token: Annotated[StreamToken, Depends(get_parsed_stream_token)],
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    client_info = PlaybackHistoryClientInfo(
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    with isolated_db_session() as local_db:
        auth_service = create_auth_service(local_db)
        user = auth_service.verify_api_key(api_key=api_key)

        playbacks_service = create_playbacks_service(
            relay_service=get_relay_service(),
            playback_histories_service=create_playback_histories_service(local_db),
        )
        playbacks_service.check_playback_limit(
            user=user,
            current_playback_id=stream_token.playback_id,
        )
        stream_service = create_stream_service(local_db)

        parsed_range_header, file = await stream_service.prepare_for_stream(
            range_header=range_header,
            indexer_id=stream_token.indexer_id,
            torrent_id=stream_token.torrent_id,
            file_index=stream_token.file_index,
        )

        imdb_info: ImdbInfo | None = None
        if stream_token.imdb_id is not None:
            imdb_info = ImdbInfo(
                imdb_id=stream_token.imdb_id,
                series_info=stream_token.series_info,
            )

        await stream_service.save_playback_history(
            stream_token=stream_token,
            client_info=client_info,
            user_id=user.id,
            file=file,
            imdb_info=imdb_info,
        )

    content_type = content_types.get_content_type(file.name)
    media_type = content_type or "application/octet-stream"

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store, no-transform",
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
        return _apply_capitalized_headers(
            Response(
                status_code=status_code,
                headers=headers,
                media_type=media_type,
            )
        )

    iterator = await file.stream(
        playback_id=stream_token.playback_id,
        user_id=user.id,
        request=request,
        stream_start_byte=parsed_range_header.start_byte,
        stream_end_byte=parsed_range_header.end_byte,
    )

    return _apply_capitalized_headers(
        StreamingResponse(
            content=iterator,
            media_type=media_type,
            status_code=status_code,
            headers=headers,
        )
    )


def _apply_capitalized_headers(response: Response) -> Response:
    overrides = {
        b"content-length": b"Content-Length",
        b"content-range": b"Content-Range",
        b"accept-ranges": b"Accept-Ranges",
        b"cache-control": b"Cache-Control",
        b"content-type": b"Content-Type",
    }
    headers = []
    for key, value in response.raw_headers:
        headers.append((overrides.get(key, key), value))
    response.raw_headers = headers
    return response
