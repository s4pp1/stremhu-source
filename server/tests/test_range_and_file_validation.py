from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.stream import router as stream_router
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import (
    StreamService,
    parse_range_header,
    validate_file_type,
)
from app.modules.stream.utils.stream_token import generate_stream_token
from app.modules.users.models import UserModel


def test_parse_range_header_rfc9110_matrix():
    n = 1000

    # 1. nincs Range -> teljes fájl
    r = parse_range_header(file_size=n, range_header=None)
    assert r.start_byte == 0
    assert r.end_byte == 999
    assert r.content_length == 1000

    # 2. bytes=0-99 -> 100 bájt
    r = parse_range_header(file_size=n, range_header="bytes=0-99")
    assert r.start_byte == 0
    assert r.end_byte == 99
    assert r.content_length == 100

    # 3. bytes=900- -> utolsó 100 bájt
    r = parse_range_header(file_size=n, range_header="bytes=900-")
    assert r.start_byte == 900
    assert r.end_byte == 999
    assert r.content_length == 100

    # 4. bytes=-100 -> utolsó 100 bájt (suffix)
    r = parse_range_header(file_size=n, range_header="bytes=-100")
    assert r.start_byte == 900
    assert r.end_byte == 999
    assert r.content_length == 100

    # 5. bytes=900-5000 -> végpont levágása 999-re
    r = parse_range_header(file_size=n, range_header="bytes=900-5000")
    assert r.start_byte == 900
    assert r.end_byte == 999
    assert r.content_length == 100

    # 6. bytes=1000- -> 416 nem kielégíthető tartomány
    with pytest.raises(HTTPException) as exc_info:
        parse_range_header(file_size=n, range_header="bytes=1000-")
    assert exc_info.value.status_code == 416
    assert exc_info.value.headers == {"Content-Range": "bytes */1000"}

    # 7. Szintaktikailag hibás range-ek -> szabályozott 416 (nem 500)
    for invalid in ["bytes=abc-def", "bytes=", "bytes=invalid", "invalid", "bytes=50-20"]:
        with pytest.raises(HTTPException) as exc_info:
            parse_range_header(file_size=n, range_header=invalid)
        assert exc_info.value.status_code == 416
        assert exc_info.value.headers == {"Content-Range": "bytes */1000"}

    # 8. Több tartomány (multipart) elutasítása -> szabályozott 416
    with pytest.raises(HTTPException) as exc_info:
        parse_range_header(file_size=n, range_header="bytes=0-50, 100-150")
    assert exc_info.value.status_code == 416
    assert exc_info.value.headers == {"Content-Range": "bytes */1000"}


def test_validate_file_type():
    # Videófájl stream végpontra: engedélyezett
    validate_file_type(is_video=True)

    # Nem videófájl (pl. .nfo, .txt, .exe): elutasítva 400-zal
    with pytest.raises(HTTPException) as exc:
        validate_file_type(is_video=False)
    assert exc.value.status_code == 400
    assert exc.value.detail == "A megadott fájl nem videó."


@pytest.mark.parametrize(
    "header",
    [
        "bytes=²-",
        "bytes=١-",
        "bytes=０-9",
        "bytes=0-²",
        "bytes=" + "9" * 5000 + "-",
        "bytes=-" + "0" * 5000,
    ],
)
def test_range_malformed_or_unsatisfiable_numbers_are_controlled(header):
    with pytest.raises(HTTPException) as error:
        parse_range_header(1000, header)
    assert error.value.status_code == 416
    assert error.value.headers == {"Content-Range": "bytes */1000"}


@pytest.mark.parametrize(
    "header,start,end",
    [
        ("bytes=0-" + "9" * 5000, 0, 999),
        ("bytes=-" + "9" * 5000, 0, 999),
        ("bytes=" + "0" * 5000 + "10-99", 10, 99),
    ],
)
def test_long_meaningful_range_numbers_saturate(header, start, end):
    result = parse_range_header(1000, header)
    assert (result.start_byte, result.end_byte, result.content_length) == (
        start,
        end,
        end - start + 1,
    )


@pytest.mark.parametrize("size", [0, 1])
def test_range_zero_and_one_byte_files(size):
    if size == 0:
        assert parse_range_header(size).content_length == 0
        with pytest.raises(HTTPException) as error:
            parse_range_header(size, "bytes=0-0")
        assert error.value.status_code == 416
        assert error.value.headers == {"Content-Range": "bytes */0"}
    else:
        assert parse_range_header(size, "bytes=-" + "9" * 5000).content_length == 1


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_stream_router_get_and_head_range_headers_and_existing_torrent_validation(
    monkeypatch, method
):
    raw = b"0123456789"
    video_file = Mock()
    video_file.name = "movie.mkv"
    video_file.size = len(raw)
    video_file.is_video = True
    video_file.torrent = SimpleNamespace(name="movie")

    async def read(**kwargs):
        async def chunks():
            yield raw[kwargs["stream_start_byte"] : kwargs["stream_end_byte"] + 1]

        return chunks()

    video_file.stream = AsyncMock(side_effect=read)

    torrents_service = Mock()
    torrents_service.find_by_id.return_value = SimpleNamespace(info_hash="a" * 40)
    relay_service = Mock()
    relay_service.get_torrent_file.return_value = video_file
    isolated_files = Mock()

    service = StreamService(
        torrents_service=cast(Any, torrents_service),
        torrent_files_service=cast(Any, Mock()),
        indexers_service=cast(Any, Mock()),
        relay_service=cast(Any, relay_service),
        isolated_torrent_files_service=cast(Any, isolated_files),
    )
    monkeypatch.setattr(service, "save_playback_history", AsyncMock())

    auth = Mock()
    auth.verify_api_key.return_value = UserModel(id="fixture-user", username="fixture")
    playbacks = Mock()

    @contextmanager
    def fixture_db():
        yield None

    monkeypatch.setattr(stream_router, "isolated_db_session", fixture_db)
    monkeypatch.setattr(stream_router, "create_auth_service", lambda db: auth)
    monkeypatch.setattr(stream_router, "create_playbacks_service", lambda **kw: playbacks)
    monkeypatch.setattr(stream_router, "create_stream_service", lambda db: service)

    token = generate_stream_token(
        StreamToken(
            indexer_id="fixture", torrent_id="1", file_index=0, playback_id="p1"
        )
    )
    url = f"/api/fixture-key/stream/{token}"
    client = TestClient(app)

    # 1. Range nélkül -> 200 OK
    resp_full = client.request(method, url)
    assert resp_full.status_code == 200
    assert resp_full.headers["Accept-Ranges"] == "bytes"
    assert resp_full.headers["Content-Length"] == "10"
    assert resp_full.content == (b"" if method == "HEAD" else raw)
    if method == "HEAD":
        video_file.stream.assert_not_called()

    # 2. Túlmutató Range (bytes=2-999999) -> 206 Partial Content, fájlvégre vágva
    video_file.stream.reset_mock()
    resp_range = client.request(method, url, headers={"Range": "bytes=2-999999"})
    assert resp_range.status_code == 206
    assert resp_range.headers["Content-Range"] == "bytes 2-9/10"
    assert resp_range.headers["Content-Length"] == "8"
    assert resp_range.content == (b"" if method == "HEAD" else raw[2:10])
    if method == "HEAD":
        video_file.stream.assert_not_called()

    # 3. Érvénytelen / nem kielégíthető Range -> 416 + Content-Range: bytes */10
    for bad_range in ["bytes=abc-def", "bytes=10-"]:
        resp_bad = client.request(method, url, headers={"Range": bad_range})
        assert resp_bad.status_code == 416
        assert resp_bad.headers["Content-Range"] == "bytes */10"

    # 4. Már relayben lévő torrent nem-videó fájlja -> 400 Bad Request
    video_file.is_video = False
    resp_non_video = client.request(method, url)
    assert resp_non_video.status_code == 400
    if method == "HEAD":
        assert resp_non_video.content == b""
    else:
        assert resp_non_video.json()["detail"] == "A megadott fájl nem videó."
