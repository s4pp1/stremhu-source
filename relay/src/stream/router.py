from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import AsyncIterator, Tuple
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from torrents.router import torrents_service
from torrents.schemas import PrioritizeAndWaitRequest

CHUNK_SIZE = 1024 * 1024

router = APIRouter(
    prefix="/stream",
    tags=["Stream"],
)


def _parse_range_header(
    range_header: str | None,
    file_size: int,
) -> Tuple[int, int, bool]:
    if file_size <= 0:
        raise HTTPException(404, "A fájl üres vagy nem elérhető.")

    if not range_header:
        return 0, file_size - 1, False

    if not range_header.startswith("bytes="):
        raise HTTPException(416, "Érvénytelen range header.")

    range_value = range_header.replace("bytes=", "", 1).strip()
    if "," in range_value:
        raise HTTPException(416, "A több tartomány nem támogatott.")

    start_str, end_str = range_value.split("-", 1)

    if start_str == "":
        if not end_str:
            raise HTTPException(416, "Érvénytelen range header.")
        suffix_length = int(end_str)
        if suffix_length <= 0:
            raise HTTPException(416, "Érvénytelen range header.")
        start = max(file_size - suffix_length, 0)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

    if start < 0 or end < 0 or start > end or end >= file_size:
        raise HTTPException(416, "A kért tartomány kívül esik a fájlon.")

    return start, end, True


async def _file_chunk_iterator(
    file_path: Path,
    start: int,
    end: int,
    request: Request,
) -> AsyncIterator[bytes]:
    with file_path.open("rb") as file_handle:
        file_handle.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            if await request.is_disconnected():
                return
            chunk = file_handle.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                return
            remaining -= len(chunk)
            yield chunk


async def _stream_with_priorities(
    info_hash: str,
    file_index: int,
    file_path: Path,
    start: int,
    end: int,
    request: Request,
) -> AsyncIterator[bytes]:
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    stream_id = uuid4().hex
    current_byte = start

    try:
        while current_byte <= end:
            if await request.is_disconnected():
                return

            end_byte = None

            while end_byte is None:
                if await request.is_disconnected():
                    return

                response = torrents_service.prioritize_and_wait(
                    parsed_info_hash,
                    stream_id,
                    file_index,
                    PrioritizeAndWaitRequest(
                        start_byte=current_byte,
                        end_byte=end,
                    ),
                )

                end_byte = response.end_byte

                if end_byte is None:
                    await asyncio.sleep(0.25)

            if end_byte < current_byte:
                return

            async for chunk in _file_chunk_iterator(
                file_path=file_path,
                start=current_byte,
                end=end_byte,
                request=request,
            ):
                yield chunk

            current_byte = end_byte + 1
    finally:
        torrents_service.reset_pieces_priorities(
            parsed_info_hash,
            file_index,
            stream_id,
        )


@router.get(
    "/{info_hash}/{file_index}",
    operation_id="stream_file",
)
async def stream_file(
    info_hash: str,
    file_index: int,
    request: Request,
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    torrent_handle = torrents_service.get_torrent_handle_or_raise(parsed_info_hash)
    file_details = torrents_service.get_torrent_file(parsed_info_hash, file_index)

    base_path = Path(torrent_handle.save_path())
    file_path = base_path / file_details.path

    if not file_path.exists():
        raise HTTPException(404, "A fájl nem található a lemezen.")

    start, end, is_range = _parse_range_header(
        request.headers.get("range"),
        file_details.size,
    )

    content_type, _ = mimetypes.guess_type(file_path.name)
    media_type = content_type or "application/octet-stream"

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
    }

    if is_range:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_details.size}"

    if file_details.is_available:
        iterator = _file_chunk_iterator(
            file_path=file_path,
            start=start,
            end=end,
            request=request,
        )
    else:
        iterator = _stream_with_priorities(
            info_hash=info_hash,
            file_index=file_index,
            file_path=file_path,
            start=start,
            end=end,
            request=request,
        )

    return StreamingResponse(
        content=iterator,
        media_type=media_type,
        status_code=206 if is_range else 200,
        headers=headers,
    )
