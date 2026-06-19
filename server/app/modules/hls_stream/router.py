from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.auth.dependencies import ApiKeyGuard
from app.modules.hls_stream.hls_manifest_generator import HlsManifestGenerator
from app.modules.hls_stream.service import HlsStreamService, get_hls_stream_service
from app.modules.hls_stream.transcode_manager import transcode_manager
from app.modules.playbacks.dependencies import get_playbacks_service
from app.modules.playbacks.service import PlaybacksService
from app.modules.stream.dependencies import get_parsed_stream_token, get_stream_service
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import StreamService
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/{api_key}/hls_stream",
    tags=["HLS Stream"],
)


@router.get(
    "/{stream_token}/master.m3u8",
    openapi_extra={"x-external": True},
)
async def get_master_playlist(
    api_key: str,
    stream_token: str,
    parsed_stream_token: Annotated[StreamToken, Depends(get_parsed_stream_token)],
    stream_service: Annotated[StreamService, Depends(get_stream_service)],
    hls_service: Annotated[HlsStreamService, Depends(get_hls_stream_service)],
    playbacks_service: Annotated[PlaybacksService, Depends(get_playbacks_service)],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
    db: Annotated[Session, Depends(get_db)],
):
    # Check limit and history if necessary
    playbacks_service.check_playback_limit(
        user=user,
        current_playback_id=parsed_stream_token.playback_id,
    )

    # prepare_for_stream triggers torrent download logic
    _, relay_file = await stream_service.prepare_for_stream(
        range_header=None,
        indexer_id=parsed_stream_token.indexer_id,
        torrent_id=parsed_stream_token.torrent_id,
        file_index=parsed_stream_token.file_index,
    )

    # Release the database lock so that the internal ffprobe request can touch the file
    db.commit()

    metadata, _ = await hls_service.get_or_probe_stream(
        stream_token, parsed_stream_token, user, api_key, relay_file
    )

    master_m3u8 = HlsManifestGenerator.generate_master_playlist(stream_token, metadata)

    return Response(content=master_m3u8, media_type="application/vnd.apple.mpegurl")


@router.get(
    "/{stream_token}/variant/{profile_id}/index.m3u8",
    openapi_extra={"x-external": True},
)
async def get_media_playlist(
    api_key: str,
    stream_token: str,
    profile_id: str,
    parsed_stream_token: Annotated[StreamToken, Depends(get_parsed_stream_token)],
    stream_service: Annotated[StreamService, Depends(get_stream_service)],
    hls_service: Annotated[HlsStreamService, Depends(get_hls_stream_service)],
    user: Annotated[UserModel, Depends(ApiKeyGuard())],
    db: Annotated[Session, Depends(get_db)],
):
    _, relay_file = await stream_service.prepare_for_stream(
        range_header=None,
        indexer_id=parsed_stream_token.indexer_id,
        torrent_id=parsed_stream_token.torrent_id,
        file_index=parsed_stream_token.file_index,
    )

    # Release the database lock
    db.commit()

    metadata, keyframes = await hls_service.get_or_probe_stream(
        stream_token, parsed_stream_token, user, api_key, relay_file
    )

    media_m3u8 = HlsManifestGenerator.generate_media_playlist(
        keyframes, metadata.duration
    )

    return Response(content=media_m3u8, media_type="application/vnd.apple.mpegurl")


@router.get(
    "/{stream_token}/variant/{profile_id}/chunk_{chunk_id}.ts",
    openapi_extra={"x-external": True},
)
async def get_chunk(
    request: Request,
    api_key: str,
    stream_token: str,
    profile_id: str,
    chunk_id: int,
    hls_service: Annotated[HlsStreamService, Depends(get_hls_stream_service)],
):
    chunk_info = hls_service.get_chunk_info(stream_token, chunk_id)
    if not chunk_info:
        raise HTTPException(status_code=404, detail="Chunk not found")

    start_time, duration = chunk_info

    base_url = str(request.base_url).rstrip("/")
    local_stream_url = f"{base_url}/api/{api_key}/stream/{stream_token}"

    chunk_file_path = await transcode_manager.get_chunk(
        stream_token=stream_token,
        profile_id=profile_id,
        stream_url=local_stream_url,
        chunk_id=chunk_id,
        chunk_duration=duration,
    )

    if not chunk_file_path or not chunk_file_path.exists():
        raise HTTPException(status_code=500, detail="Failed to generate chunk")

    return FileResponse(
        path=chunk_file_path,
        media_type="video/MP2T",
        headers={
            "Cache-Control": "no-store, no-transform",
        },
    )
