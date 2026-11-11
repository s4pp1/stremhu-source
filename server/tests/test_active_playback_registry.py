import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.service import AuthService
from app.modules.stream import active_playback, router
from app.modules.stream.active_playback import ActivePlaybackRegistry
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import parse_range_header
from app.modules.stream.utils.stream_token import generate_stream_token
from app.modules.users.models import UserModel
from app.modules.users.service import UsersService


def test_registry_global_ttl_cap_history_and_nonce():
    now = [0.0]
    registry = ActivePlaybackRegistry(clock=lambda: now[0])
    for index in range(1025):
        registry.record(str(index), "group")
    assert registry.user_count == 1024
    assert registry.find("0", {"group"}) is None
    old = registry.record("user", "latest")
    newer = registry.record("user", "latest")
    registry.remove_if_matches("user", "latest", old)
    assert registry.find("user", {"latest"}) == "latest"
    registry.remove_if_matches("user", "latest", newer)
    assert registry.find("user", {"latest"}) is None
    for index in range(21):
        registry.record("history", str(index))
    assert registry.find("history", {"0"}) is None
    assert registry.find("history", {"1"}) == "1"
    now[0] = 7200
    assert registry.find("unrelated", {"group"}) is None
    assert registry.user_count == 0


@pytest.mark.anyio
async def test_waiter_lifecycle_capacity_cancel_timeout_and_close():
    registry = ActivePlaybackRegistry(max_waiters=1)
    waiting = asyncio.create_task(registry.wait("user", {"group"}, 100))
    await asyncio.sleep(0)
    assert registry.waiter_count == 1
    assert await asyncio.wait_for(registry.wait("another", {"group"}, 100), 0.1) is None
    waiting.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiting
    assert registry.waiter_count == 0
    assert await registry.wait("user", {"group"}, 0) is None
    assert registry.waiter_count == 0
    waiting = asyncio.create_task(registry.wait("user", {"group"}, 100))
    await asyncio.sleep(0)
    registry.close()
    assert await asyncio.wait_for(waiting, 0.1) is None
    assert registry.waiter_count == 0
    assert registry.record("user", "group") is None


@pytest.mark.anyio
async def test_history_eviction_does_not_discard_live_waiters():
    registry = ActivePlaybackRegistry(max_users=1)
    registry.record("user", "old")
    waiting = asyncio.create_task(registry.wait("user", {"new"}, 1))
    await asyncio.sleep(0)
    registry.record("other", "group")
    assert registry.waiter_count == 1
    registry.record("user", "new")
    assert await waiting == "new"
    assert registry.waiter_count == 0
    assert await registry.wait("user", {"new"}) == "new"


@contextmanager
def fixture_db():
    yield None


def test_signed_stream_with_rejected_key_does_not_register_intent(monkeypatch):
    active_playback.clear_active_playbacks()
    users = Mock(spec=UsersService)
    users.find_by_api_key.return_value = None
    monkeypatch.setattr(router, "isolated_db_session", fixture_db)
    monkeypatch.setattr(router, "create_auth_service", lambda db: AuthService(users))
    token = generate_stream_token(StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id="fixture"))
    client = TestClient(app)
    for index in range(100):
        assert client.get(f"/api/invalid-fixture-{index}/stream/{token}").status_code == 401
    assert active_playback._registry.user_count == 0
    active_playback.clear_active_playbacks()


@pytest.mark.parametrize("newer_intent", [False, True])
def test_prepare_failure_withdraws_only_its_own_intent(monkeypatch, newer_intent):
    active_playback.clear_active_playbacks()


    user = UserModel(id="fixture-user", username="fixture")
    auth = Mock()
    auth.verify_api_key.return_value = user

    async def fail_prepare(**kwargs):
        assert active_playback.find_active_binge_group(user.id, {"fixture-1"}) == "fixture-1"
        if newer_intent:
            active_playback.record_active_playback(user.id, "fixture", "1")
        raise HTTPException(400, "fixture preparation failure")

    stream = Mock()
    stream.prepare_for_stream = AsyncMock(side_effect=fail_prepare)
    monkeypatch.setattr(router, "isolated_db_session", fixture_db)
    monkeypatch.setattr(router, "create_auth_service", lambda db: auth)
    monkeypatch.setattr(router, "get_relay_service", lambda: None)
    monkeypatch.setattr(router, "create_playback_histories_service", lambda db: None)
    monkeypatch.setattr(router, "create_playbacks_service", lambda **kwargs: Mock())
    monkeypatch.setattr(router, "create_stream_service", lambda db: stream)
    token = generate_stream_token(StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id="fixture"))
    response = TestClient(app).get(f"/api/fixture/stream/{token}")
    assert response.status_code == 400
    assert active_playback.find_active_binge_group(user.id, {"fixture-1"}) == ("fixture-1" if newer_intent else None)
    active_playback.clear_active_playbacks()


@pytest.mark.parametrize("denied", [False, True])
def test_head_intent_is_recorded_after_playback_limit_check(monkeypatch, denied):
    active_playback.clear_active_playbacks()
    user = UserModel(id="head-fixture-user", username="fixture")
    auth = Mock()
    auth.verify_api_key.return_value = user
    playbacks = Mock()
    if denied:
        playbacks.check_playback_limit.side_effect = HTTPException(429, "fixture limit")
    file = Mock(size=10)
    file.name = "fixture.mkv"
    stream = Mock()
    stream.prepare_for_stream = AsyncMock(return_value=(parse_range_header(10), file))
    stream.save_playback_history = AsyncMock()
    monkeypatch.setattr(router, "isolated_db_session", fixture_db)
    monkeypatch.setattr(router, "create_auth_service", lambda db: auth)
    monkeypatch.setattr(router, "get_relay_service", lambda: None)
    monkeypatch.setattr(router, "create_playback_histories_service", lambda db: None)
    monkeypatch.setattr(router, "create_playbacks_service", lambda **kwargs: playbacks)
    monkeypatch.setattr(router, "create_stream_service", lambda db: stream)
    token = generate_stream_token(StreamToken(indexer_id="head-fixture", torrent_id="1", file_index=0, playback_id="fixture"))
    response = TestClient(app).head(f"/api/fixture/stream/{token}")
    assert response.status_code == (429 if denied else 200)
    assert response.content == b""
    assert active_playback.find_active_binge_group(user.id, {"head-fixture-1"}) == (None if denied else "head-fixture-1")
    file.stream.assert_not_called()
    active_playback.clear_active_playbacks()
