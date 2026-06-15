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
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.schemas.internal import ImdbInfo
from app.modules.auth.dependencies import ApiKeyGuard
from app.modules.playback_histories.dependencies import get_playback_histories_service
from app.modules.playback_histories.schemas.internal import (
    PlaybackHistoryClientInfo,
    PlaybackHistoryCreate,
)
from app.modules.playback_histories.service import PlaybackHistoriesService
from app.modules.playbacks.dependencies import get_playbacks_service
from app.modules.playbacks.service import PlaybacksService
from app.modules.stream.dependencies import get_parsed_stream_token, get_stream_service
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import StreamService
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/{api_key}/stream",
    tags=["Stream"],
)


@router.get(
    "/{stream_token}",
    openapi_extra={"x-external": True},
)
@router.head(
    "/{stream_token}",
    openapi_extra={"x-external": True},
)
async def stream(
    request: Request,
    stream_token: Annotated[StreamToken, Depends(get_parsed_stream_token)],
    stream_service: Annotated[StreamService, Depends(get_stream_service)],
    playback_histories_service: Annotated[
        PlaybackHistoriesService,
        Depends(
            get_playback_histories_service,
        ),
    ],
    playbacks_service: Annotated[PlaybacksService, Depends(get_playbacks_service)],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
    db: Annotated[Session, Depends(get_db)],
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    client_info = PlaybackHistoryClientInfo(
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    playbacks_service.check_playback_limit(
        user=user,
        current_playback_id=stream_token.playback_id,
    )

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

    playback_histories_service.get_or_create(
        PlaybackHistoryCreate(
            client=client_info,
            indexer_id=stream_token.indexer_id,
            playback_id=stream_token.playback_id,
            user_id=user.id,
            torrent_id=stream_token.torrent_id,
            file_index=stream_token.file_index,
            imdb_info=imdb_info,
            torrent_name=file.torrent.name,
            file_name=file.name,
        )
    )

    db.commit()

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
        return Response(
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )

    iterator = await file.stream(
        playback_id=stream_token.playback_id,
        user_id=user.id,
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
