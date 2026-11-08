from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.common.sensitive_responses import SensitiveResponsePolicy
from app.main import app
from app.modules.auth.service import AuthService
from app.modules.stream import router as stream_module
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import parse_range_header
from app.modules.stream.utils.stream_token import generate_stream_token
from app.modules.users.models import UserModel
from app.modules.users.service import UsersService


class SharedCache:
    """A local cache fixture in front of the real app, including its auth guard."""

    def __init__(self, application: ASGIApp):
        self.application = application
        self.entries: dict[tuple[str, str], list[Message]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.application(scope, receive, send)
        key = (scope["method"], scope["path"])
        if key in self.entries:
            for message in self.entries[key]:
                await send(message)
            return
        messages: list[Message] = []

        async def capture(message: Message):
            messages.append(dict(message))
            await send(message)

        await self.application(scope, receive, capture)
        start = next(message for message in messages if message["type"] == "http.response.start")
        policy = dict(start.get("headers", [])).get(b"cache-control", b"")
        if b"public" in policy and b"no-store" not in policy and start["status"] in {200, 206}:
            self.entries[key] = messages


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/pair/status/fixture", "/api/me/", "/api/users/", "/api/playbacks/", "/api/fixture/subtitles/token", "/api/fixture/stremio/subtitles/movie/tt1234567.json"])
@pytest.mark.parametrize("status", [200, 401, 403, 422, 500])
def test_response_start_policy_including_unhandled_errors(path, status):
    application = FastAPI()
    application.add_middleware(SensitiveResponsePolicy)

    @application.get(path)
    def endpoint():
        if status == 500:
            raise RuntimeError("fixture fault")
        if status != 200:
            raise HTTPException(status)
        return Response(b"fixture", headers={"Cache-Control": "public, max-age=1"})

    response = TestClient(application, raise_server_exceptions=False).get(path)
    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"


def test_policy_leaves_other_responses_unchanged():
    application = FastAPI()
    application.add_middleware(SensitiveResponsePolicy)

    @application.get("/api/fixture/stremio/manifest.json")
    def endpoint():
        return Response(b"fixture", headers={"Cache-Control": "max-age=60"})

    response = TestClient(application).get("/api/fixture/stremio/manifest.json")
    assert response.content == b"fixture"
    assert response.headers["cache-control"] == "max-age=60"


@pytest.mark.parametrize("method,range_header,expected_status,expected_body", [("GET", None, 200, b"0123456789"), ("HEAD", None, 200, b""), ("GET", "bytes=2-4", 206, b"234"), ("HEAD", "bytes=2-4", 206, b""), ("GET", "bytes=99-", 416, None), pytest.param("GET", b"bytes=\xb2-", 416, None, id="latin1-range-http"), pytest.param("GET", "bytes=0-" + "9" * 5000, 206, b"0123456789", id="long-end-clamped-http")])
def test_real_subtitle_cache_hit_reauthenticates_after_key_rotation(monkeypatch, method, range_header, expected_status, expected_body):
    user = UserModel(id="fixture-user", username="fixture", api_key="fixture-key")
    users = Mock(spec=UsersService)
    users.find_by_api_key.side_effect = lambda key: user if key == user.api_key else None
    auth = AuthService(users)

    @contextmanager
    def fixture_db():
        yield None

    monkeypatch.setattr(stream_module, "isolated_db_session", fixture_db)
    monkeypatch.setattr(stream_module, "create_auth_service", lambda db: auth)
    stream_module._subtitle_content_cache.clear()
    stream_module._put_cached_subtitle(("fixture", "1", 0, False), "text/plain", "fixture.srt", b"0123456789")
    payload = StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id="fixture")
    path = "/api/fixture-key/subtitles/" + generate_stream_token(payload)
    shared_cache = SharedCache(app)
    client = TestClient(shared_cache)
    try:
        response = client.request(method, path, headers={"Range": range_header} if range_header else {})
        assert response.status_code == expected_status
        assert response.headers["cache-control"] == "no-store"
        if expected_body is not None:
            assert response.content == expected_body
        if expected_status == 206:
            if range_header == "bytes=2-4":
                assert response.headers["content-range"] == "bytes 2-4/10"
                assert response.headers["content-length"] == "3"
            else:
                assert response.headers["content-range"] == "bytes 0-9/10"
                assert response.headers["content-length"] == "10"
        assert shared_cache.entries == {}
        user.api_key = "rotated-fixture-key"
        revoked = client.get(path)
        assert revoked.status_code == 401
        assert revoked.headers["cache-control"] == "no-store"
        assert users.find_by_api_key.call_count == 2
    finally:
        stream_module._subtitle_content_cache.clear()


def test_real_sensitive_router_errors_have_policy():
    client = TestClient(app)
    for method, path in [("POST", "/api/auth/login"), ("POST", "/api/auth/pair/verify"), ("GET", "/api/fixture/subtitles/not-a-token")]:
        response = client.request(method, path, json={})
        assert response.status_code >= 400
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("kind", ["inline", "streamed", "converted"])
@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize("range_value", [None, "bytes=2-4"])
def test_cold_subtitle_paths_preserve_body_range_head_and_policy(monkeypatch, kind, method, range_value):
    raw = b"0123456789"
    if kind == "converted":
        raw = b"[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Fixture\n"
    if kind == "streamed":
        monkeypatch.setattr(stream_module, "_SUBTITLE_INLINE_RAW_MAX_BYTES", 5)
    file = Mock()
    file.name = "fixture.ass" if kind == "converted" else "fixture.srt"
    file.size = len(raw)

    async def read(**kwargs):
        async def chunks():
            yield raw[kwargs["stream_start_byte"]:kwargs["stream_end_byte"] + 1]
        return chunks()

    file.stream = AsyncMock(side_effect=read)

    async def prepare(**kwargs):
        return parse_range_header(len(raw), kwargs.get("range_header")), file

    service = Mock()
    service.prepare_for_stream = AsyncMock(side_effect=prepare)
    auth = Mock()
    auth.verify_api_key.return_value = UserModel(id="fixture", username="fixture")

    @contextmanager
    def fixture_db():
        yield None

    monkeypatch.setattr(stream_module, "isolated_db_session", fixture_db)
    monkeypatch.setattr(stream_module, "create_auth_service", lambda db: auth)
    monkeypatch.setattr(stream_module, "create_stream_service", lambda db: service)
    stream_module._subtitle_content_cache.clear()
    token = generate_stream_token(StreamToken(indexer_id="cold-fixture", torrent_id="1", file_index=0, playback_id="fixture"))
    filename = "/fixture.vtt" if kind == "converted" else "/fixture.srt"
    try:
        response = TestClient(app).request(method, "/api/fixture/subtitles/" + token + filename, headers={"Range": range_value} if range_value else {})
        assert response.headers["cache-control"] == "no-store"
        assert response.status_code == (206 if range_value and kind != "converted" else 200)
        if method == "HEAD":
            assert response.content == b""
            file.stream.assert_not_called()
        elif kind == "converted":
            assert response.content.startswith(b"WEBVTT")
            assert b"Fixture" in response.content
        else:
            assert response.content == (raw[2:5] if range_value else raw)
            assert response.headers["content-length"] == str(len(response.content))
        if range_value and kind != "converted":
            assert response.headers["content-range"] == "bytes 2-4/10"
    finally:
        stream_module._subtitle_content_cache.clear()


def test_subtitle_collection_failure_has_safe_log_and_no_store(monkeypatch, caplog):
    marker = "synthetic-subtitle-error-marker"
    auth = Mock()
    auth.verify_api_key.return_value = UserModel(id="fixture", username="fixture")
    file = Mock(name="fixture.srt", size=10)
    file.name = "fixture.srt"
    service = Mock()
    service.prepare_for_stream = AsyncMock(return_value=(parse_range_header(10), file))
    @contextmanager
    def fixture_db():
        yield None
    monkeypatch.setattr(stream_module, "isolated_db_session", fixture_db)
    monkeypatch.setattr(stream_module, "create_auth_service", lambda db: auth)
    monkeypatch.setattr(stream_module, "create_stream_service", lambda db: service)
    monkeypatch.setattr(stream_module, "_collect_subtitle_bytes", AsyncMock(side_effect=httpx.ReadTimeout(marker)))
    stream_module._subtitle_content_cache.clear()
    token = generate_stream_token(StreamToken(indexer_id="error-fixture", torrent_id="1", file_index=0, playback_id="fixture"))
    response = TestClient(app).get("/api/fixture/subtitles/" + token)
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert marker not in caplog.text
    assert marker not in response.text
