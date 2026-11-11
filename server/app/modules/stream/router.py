from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import content_types
from fastapi import (
    APIRouter,
    Depends,
    Header,
    Request,
    Response,
)
from fastapi.responses import StreamingResponse

from app.common.async_utils import owned_to_thread
from app.common.database import isolated_db_session
from app.common.keyed_lock import KeyedLock
from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.common.schemas.internal import ImdbInfo
from app.config import config
from app.modules.auth.dependencies import create_auth_service
from app.modules.playback_histories.dependencies import (
    create_playback_histories_service,
)
from app.modules.playback_histories.schemas.internal import (
    PlaybackHistoryClientInfo,
)
from app.modules.playbacks.dependencies import create_playbacks_service
from app.modules.relay.dependencies import get_relay_service
from app.modules.stream.active_playback import (
    record_active_playback,
    remove_active_playback_if_matches,
)
from app.modules.stream.dependencies import (
    create_stream_service,
    get_parsed_stream_token,
)
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import parse_range_header
from app.modules.stream.utils.subtitles import (
    ass_to_vtt_cooperative,
    decode_subtitle_text,
    decode_subtitle_text_cooperative,
)

router = APIRouter(
    prefix="/{api_key}/stream",
    tags=["Stream"],
)

subtitles_router = APIRouter(
    prefix="/{api_key}/subtitles",
    tags=["Subtitles"],
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
        user = await owned_to_thread(
            auth_service.verify_api_key,
            api_key=api_key,
        )

        playbacks_service = create_playbacks_service(
            relay_service=get_relay_service(),
            playback_histories_service=create_playback_histories_service(local_db),
        )
        playbacks_service.check_playback_limit(
            user=user,
            current_playback_id=stream_token.playback_id,
        )
        stream_service = create_stream_service(local_db)

        record_id = record_active_playback(
            user_id=user.id,
            indexer_id=stream_token.indexer_id,
            torrent_id=stream_token.torrent_id,
        )
        try:
            parsed_range_header, file = await stream_service.prepare_for_stream(
                range_header=range_header,
                indexer_id=stream_token.indexer_id,
                torrent_id=stream_token.torrent_id,
                file_index=stream_token.file_index,
            )
        except BaseException:
            remove_active_playback_if_matches(user.id, stream_token.indexer_id, stream_token.torrent_id, record_id)
            raise

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


_SUBTITLE_CACHE_MAX_ENTRIES = 128
_SUBTITLE_CACHE_TTL_SECONDS = 3600.0
# Ennél kisebb nyers feliratot teljes egészében memóriába gyűjtünk és cache-elünk;
# a nagyobb nyers fájl cache nélkül, Range-támogatással streamelődik.
_SUBTITLE_INLINE_RAW_MAX_BYTES = 2 * 1024 * 1024

# Kulcs: (indexer_id, torrent_id, file_index, is_vtt_converted) -> a TÉNYLEGES reprezentáció.
# Érték: (timestamp, media_type, disp_name, content_bytes)
SubtitleCacheKey = tuple[str, str, int, bool]
_subtitle_content_cache: dict[SubtitleCacheKey, tuple[float, str, str, bytes]] = {}
_subtitle_cache_bytes = 0
# Kérés szerinti kulcs (a kért kiterjesztés alapján) -> tényleges reprezentáció kulcsa.
# Így ugyanazok a bájtok nem tárolódnak többször eltérő alias-kulcsokkal.
_subtitle_cache_alias: dict[SubtitleCacheKey, SubtitleCacheKey] = {}
_subtitle_locks = KeyedLock()


class SubtitleIncompleteError(Exception):
    """A felirat adatgyűjtése nem a teljes fájlt adta vissza."""


def _cache_pop(cache_key: SubtitleCacheKey) -> None:
    global _subtitle_cache_bytes
    entry = _subtitle_content_cache.pop(cache_key, None)
    if entry is not None:
        _subtitle_cache_bytes -= len(entry[3])


def _get_cached_subtitle(
    cache_key: SubtitleCacheKey,
) -> tuple[str, str, bytes] | None:
    final_key = _subtitle_cache_alias.get(cache_key, cache_key)
    entry = _subtitle_content_cache.get(final_key)
    if entry is None:
        return None
    ts, media_type, disp_name, content_bytes = entry
    if time.monotonic() - ts > _SUBTITLE_CACHE_TTL_SECONDS:
        _cache_pop(final_key)
        return None
    return media_type, disp_name, content_bytes


def _put_cached_subtitle(
    cache_key: SubtitleCacheKey,
    media_type: str,
    disp_name: str,
    content_bytes: bytes,
) -> bool:
    """Cache-be írás összesített bájtkerettel. Visszatér: bekerült-e."""
    global _subtitle_cache_bytes
    size = len(content_bytes)
    max_bytes = config.subtitle_cache_max_bytes
    # Egyetlen bejegyzés legfeljebb a keret negyedét foglalhatja.
    if size > max_bytes // 4:
        return False

    _cache_pop(cache_key)
    while _subtitle_content_cache and (
        len(_subtitle_content_cache) >= _SUBTITLE_CACHE_MAX_ENTRIES
        or _subtitle_cache_bytes + size > max_bytes
    ):
        _cache_pop(next(iter(_subtitle_content_cache)))

    _subtitle_content_cache[cache_key] = (
        time.monotonic(),
        media_type,
        disp_name,
        content_bytes,
    )
    _subtitle_cache_bytes += size
    return True


def _register_subtitle_alias(
    request_key: SubtitleCacheKey, final_key: SubtitleCacheKey
) -> None:
    if request_key == final_key:
        return
    if len(_subtitle_cache_alias) >= _SUBTITLE_CACHE_MAX_ENTRIES * 4:
        _subtitle_cache_alias.pop(next(iter(_subtitle_cache_alias)), None)
    _subtitle_cache_alias[request_key] = final_key


def _content_disposition(filename: str) -> str:
    """RFC 6266 / 5987: ASCII fallback + UTF-8 `filename*` (ékezetes fájlnevekhez).

    A Starlette latin-1 kódolással írja a fejlécet; nem latin-1 karakter (pl. „ő”)
    nyers beírása kezeletlen hibát okozna.
    """
    fallback = "".join(
        ch for ch in filename if 32 <= ord(ch) < 127 and ch not in '"\\'
    ).strip()
    if not fallback:
        fallback = "subtitle" + Path(filename).suffix.encode("ascii", "ignore").decode()
    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


def _decode_subtitle_text(raw_bytes: bytes) -> str:
    """Explicit dekódolási szabály, lásd ``decode_subtitle_text``."""
    return decode_subtitle_text(raw_bytes)


async def _collect_subtitle_bytes(
    file,
    stream_token: StreamToken,
    user_id: str,
    request: Request,
) -> bytes:
    """A teljes feliratfájl összegyűjtése. Részleges tartalom esetén kivételt dob."""
    iterator = await file.stream(
        playback_id=stream_token.playback_id,
        user_id=user_id,
        request=request,
        stream_start_byte=0,
        stream_end_byte=file.size - 1,
        raise_errors=True,
    )
    chunks: list[bytes] = []
    total = 0
    async for chunk in iterator:
        total += len(chunk)
        if total > file.size:
            raise SubtitleIncompleteError("A felirat hosszabb a vártnál.")
        chunks.append(chunk)
    if total != file.size:
        raise SubtitleIncompleteError(
            f"A felirat nem teljes ({total}/{file.size} bájt)."
        )
    return b"".join(chunks)


def _subtitle_unavailable() -> Response:
    return Response(
        status_code=503,
        content="A felirat jelenleg nem érhető el teljes egészében.",
        headers={"Retry-After": "5", "Cache-Control": "no-store"},
        media_type="text/plain; charset=utf-8",
    )


def subtitle_response_headers(disp_name: str) -> dict[str, str]:
    return {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Content-Disposition": _content_disposition(disp_name),
    }


def _build_cached_subtitle_response(
    request_method: str,
    media_type: str,
    disp_name: str,
    content_bytes: bytes,
    range_header: str | None,
    convert_to_vtt: bool,
    stream_service=None,
) -> Response:
    _ = stream_service
    headers = subtitle_response_headers(disp_name)
    total_size = len(content_bytes)
    if range_header is None or convert_to_vtt or total_size == 0:
        status_code = 200
        body = content_bytes
        headers["Content-Length"] = str(total_size)
    else:
        parsed_range = parse_range_header(
            file_size=total_size,
            range_header=range_header,
        )
        status_code = 206
        body = content_bytes[parsed_range.start_byte : parsed_range.end_byte + 1]
        headers["Content-Length"] = str(len(body))
        headers["Content-Range"] = (
            f"bytes {parsed_range.start_byte}-{parsed_range.end_byte}/{total_size}"
        )

    if request_method == "HEAD":
        return _apply_capitalized_headers(
            Response(
                status_code=status_code,
                headers=headers,
                media_type=media_type,
            )
        )
    return _apply_capitalized_headers(
        Response(
            content=body,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )
    )


@subtitles_router.get("/{stream_token}")
@subtitles_router.get("/{stream_token}/{filename}")
@subtitles_router.head("/{stream_token}")
@subtitles_router.head("/{stream_token}/{filename}")
async def stream_subtitle(
    request: Request,
    api_key: str,
    stream_token: Annotated[StreamToken, Depends(get_parsed_stream_token)],
    filename: str | None = None,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    req_ext_hint = Path(filename).suffix.lower() if filename else ""
    want_vtt_hint = req_ext_hint == ".vtt"
    request_key: SubtitleCacheKey = (
        stream_token.indexer_id,
        stream_token.torrent_id,
        stream_token.file_index,
        want_vtt_hint,
    )
    lock_key = ":".join(str(part) for part in request_key)

    # A KeyedLock referenciaszámlált: a lock a várakozókat is túléli, így
    # egymásra váró kérések sem indítanak párhuzamos letöltést.
    async with _subtitle_locks(lock_key):
        with isolated_db_session() as local_db:
            # Cache-hit előtt is hitelesítünk: a közös fájlcache nem jogosultságcache.
            auth_service = create_auth_service(local_db)
            user = await owned_to_thread(
                auth_service.verify_api_key,
                api_key=api_key,
            )

            cached = _get_cached_subtitle(request_key)
            if cached is not None:
                cached_media_type, cached_disp_name, cached_bytes = cached
                return _build_cached_subtitle_response(
                    request_method=request.method,
                    media_type=cached_media_type,
                    disp_name=cached_disp_name,
                    content_bytes=cached_bytes,
                    range_header=range_header,
                    convert_to_vtt=want_vtt_hint,
                )

            stream_service = create_stream_service(local_db)
            parsed_range_header, file = await stream_service.prepare_for_stream(
                range_header=range_header,
                indexer_id=stream_token.indexer_id,
                torrent_id=stream_token.torrent_id,
                file_index=stream_token.file_index,
                require_subtitle=True,
            )

        req_ext = req_ext_hint or Path(file.name).suffix.lower()
        file_ext = Path(file.name).suffix.lower()

        convert_to_vtt = req_ext == ".vtt" and file_ext in (".ass", ".ssa")
        final_key: SubtitleCacheKey = (
            stream_token.indexer_id,
            stream_token.torrent_id,
            stream_token.file_index,
            convert_to_vtt,
        )

        if convert_to_vtt:
            media_type = "text/vtt; charset=utf-8"
            disp_name = Path(file.name).stem + ".vtt"
        elif file_ext in (".ass", ".ssa"):
            media_type = "text/x-ssa; charset=utf-8"
            disp_name = file.name
        elif file_ext == ".vtt":
            media_type = "text/vtt; charset=utf-8"
            disp_name = file.name
        elif file_ext == ".srt":
            media_type = "text/plain; charset=utf-8"
            disp_name = file.name
        else:
            media_type = (
                content_types.get_content_type(file.name)
                or "text/plain; charset=utf-8"
            )
            disp_name = file.name

        headers = subtitle_response_headers(disp_name)

        if convert_to_vtt:
            if file.size > config.subtitle_max_source_bytes:
                return Response(
                    status_code=422,
                    content="A felirat túl nagy a konverzióhoz.",
                    media_type="text/plain; charset=utf-8",
                )

            if request.method == "HEAD":
                return _apply_capitalized_headers(
                    Response(
                        status_code=200,
                        headers=headers,
                        media_type=media_type,
                    )
                )

            try:
                raw_bytes = await _collect_subtitle_bytes(
                    file, stream_token, user.id, request
                )
            except Exception as e:
                logger.warning("operation=subtitle-collect %s", network_error_fields(e))
                return _subtitle_unavailable()

            try:
                vtt_output = await ass_to_vtt_cooperative(
                    await decode_subtitle_text_cooperative(raw_bytes)
                )
            except Exception as e:
                logger.warning("operation=subtitle-convert %s", network_error_fields(e))
                return Response(
                    status_code=422,
                    content="A felirat nem konvertálható.",
                    media_type="text/plain; charset=utf-8",
                )

            vtt_bytes = vtt_output.encode("utf-8")
            # Üres konverziós eredményt (nem üres forrásnál) nem tárolunk sikerként.
            has_cues = "-->" in vtt_output
            if has_cues or not raw_bytes.strip():
                if _put_cached_subtitle(final_key, media_type, disp_name, vtt_bytes):
                    _register_subtitle_alias(request_key, final_key)
            headers["Content-Length"] = str(len(vtt_bytes))
            return _apply_capitalized_headers(
                Response(
                    content=vtt_bytes,
                    status_code=200,
                    headers=headers,
                    media_type=media_type,
                )
            )

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

        if file.size <= _SUBTITLE_INLINE_RAW_MAX_BYTES:
            try:
                raw_bytes = await _collect_subtitle_bytes(
                    file, stream_token, user.id, request
                )
            except Exception as e:
                logger.warning("operation=subtitle-collect %s", network_error_fields(e))
                return _subtitle_unavailable()

            if _put_cached_subtitle(final_key, media_type, disp_name, raw_bytes):
                _register_subtitle_alias(request_key, final_key)
            return _build_cached_subtitle_response(
                request_method=request.method,
                media_type=media_type,
                disp_name=disp_name,
                content_bytes=raw_bytes,
                range_header=range_header,
                convert_to_vtt=False,
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
        b"connection": b"Connection",
    }
    headers = []
    for key, value in response.raw_headers:
        headers.append((overrides.get(key, key), value))
    response.raw_headers = headers
    return response
