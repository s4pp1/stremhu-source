"""SP03: playback history recording in both ``playback_history_background`` states.

Off is the earlier path: every GET/HEAD request awaits the locked, threaded
write before its headers. On (SP03, the default since gsp03-v1): one write per
playback, off the response path; a failed write is retried by the next request,
a full pending set falls back to a synchronous write, the recorded set is
bounded, and shutdown drains pending writes (see test_lifespan_cleanup).

The DB write is a thread-safe double except in the real-SQLite one-row test;
scheduling, locking, the router order and the background-task drain are the
product's.
"""

import asyncio
import logging
import threading
from collections.abc import AsyncIterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.async_utils import drain_background_tasks
from app.config import config
from app.main import app
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.playback_histories.models import PlaybackHistoryModel
from app.modules.playback_histories.schemas.internal import PlaybackHistoryClientInfo
from app.modules.playbacks.service import PlaybacksService
from app.modules.stream import active_playback, router, service as stream_service
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import (
    StreamService,
    clear_playback_history_state,
    parse_range_header,
)
from app.modules.stream.utils.stream_token import generate_stream_token
from app.modules.users.models import UserModel

pytestmark = pytest.mark.anyio

SECRET_MARKER = "fixture-sensitive-write-marker"
FILE_SIZE = 4096


class _Writes:
    def __init__(self, fail_first: int = 0, gate: threading.Event | None = None):
        self.calls: list[str] = []
        self.fail_first = fail_first
        self.gate = gate
        self.lock = threading.Lock()

    def __call__(self, payload) -> None:
        if self.gate is not None:
            assert self.gate.wait(5)
        with self.lock:
            self.calls.append(payload.playback_id)
            if len(self.calls) <= self.fail_first:
                raise RuntimeError(f"synthetic write failure {SECRET_MARKER}")


@pytest.fixture(params=[False, True], ids=["legacy", "background"])
def background(request, monkeypatch) -> bool:
    monkeypatch.setattr(config, "playback_history_background", request.param)
    return request.param


@pytest.fixture
def background_on(monkeypatch) -> None:
    monkeypatch.setattr(config, "playback_history_background", True)


@pytest.fixture
def history(monkeypatch):
    clear_playback_history_state()

    def install(writes: _Writes) -> _Writes:
        monkeypatch.setattr(stream_service, "_persist_playback_history", writes)
        return writes

    yield install
    clear_playback_history_state()


def _save(playback_id: str, user_id: str = "user"):
    service = object.__new__(StreamService)
    token = StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id=playback_id)
    file = cast(Any, SimpleNamespace(name="movie.mkv", torrent=SimpleNamespace(name="movie")))
    return service.save_playback_history(token, PlaybackHistoryClientInfo(user_agent=None, ip=None), user_id, file)


async def test_first_request_waits_for_the_write_only_in_legacy_mode(history, background):
    gate = threading.Event()
    writes = history(_Writes(gate=gate))
    call = asyncio.create_task(_save("p1"))
    try:
        if background:
            await asyncio.wait_for(call, 1)  # returns although the write is blocked
            assert writes.calls == []
        else:
            await asyncio.sleep(0.05)
            assert not call.done()  # today's path: the response waits for the write
    finally:
        gate.set()
    await call
    await drain_background_tasks()
    assert writes.calls == ["p1"]


async def test_repeated_requests_write_once_only_in_background_mode(history, background):
    writes = history(_Writes())
    for _ in range(10):
        await _save("p2")
    await drain_background_tasks()
    for _ in range(10):
        await _save("p2")
    await drain_background_tasks()
    assert writes.calls == (["p2"] if background else ["p2"] * 20)


async def test_failed_write_keeps_the_request_and_logs_without_its_text(history, background, caplog):
    caplog.set_level(logging.WARNING, logger="app.common.logger")
    writes = history(_Writes(fail_first=1))
    for _ in range(3):
        await _save("p3")  # never raises into the stream response
        await drain_background_tasks()
    # Background: the failure is not marked recorded, so the next request retries once.
    assert writes.calls == (["p3", "p3"] if background else ["p3"] * 3)
    assert "playback-history-write" in caplog.text
    assert "synthetic write failure" not in caplog.text
    assert SECRET_MARKER not in caplog.text


async def test_full_pending_set_falls_back_to_a_synchronous_write(history, background_on, monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger="app.common.logger")
    writes = history(_Writes(fail_first=1))
    monkeypatch.setattr(stream_service, "_HISTORY_PENDING_MAX", 0)
    await _save("p4")
    assert writes.calls == ["p4"]  # attempted before the call returned; it failed
    await _save("p4")
    assert writes.calls == ["p4", "p4"]  # the failure is not lost: retried synchronously
    await _save("p4")
    await drain_background_tasks()
    assert writes.calls == ["p4", "p4"]
    assert SECRET_MARKER not in caplog.text


async def test_distinct_playbacks_are_each_written(history, background):
    writes = history(_Writes())
    await asyncio.gather(*(_save(f"p5-{i}") for i in range(5)))
    await drain_background_tasks()
    assert sorted(writes.calls) == [f"p5-{i}" for i in range(5)]


async def test_recorded_set_is_bounded_by_capacity_and_age(history, background_on, monkeypatch):
    writes = history(_Writes())
    now = [1000.0]
    monkeypatch.setattr(stream_service, "time", SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(stream_service, "_HISTORY_RECORDED_MAX", 2)
    for playback_id in ("a", "b", "c"):
        await _save(playback_id)
        await drain_background_tasks()
    await _save("c")
    await _save("a")  # evicted by capacity: written again (get_or_create reads the row)
    await drain_background_tasks()
    assert writes.calls == ["a", "b", "c", "a"]
    now[0] += stream_service._HISTORY_RECORDED_TTL_SECONDS
    await _save("c")  # expired by age
    await drain_background_tasks()
    assert writes.calls == ["a", "b", "c", "a", "c"]


async def test_one_history_row_per_playback_on_a_real_database(pairing_engine, background):
    clear_playback_history_state()
    with Session(pairing_engine) as db:
        db.add(IndexerDefinitionModel(id="fixture", name="fixture", url="https://fixture.invalid", details_path="/d"))
        db.commit()
    try:
        await asyncio.gather(*(_save("db-1", user_id="one") for _ in range(10)))
        await drain_background_tasks()
        for _ in range(5):
            await _save("db-1", user_id="one")
        await drain_background_tasks()
    finally:
        clear_playback_history_state()
    with Session(pairing_engine) as db:
        assert db.scalars(select(PlaybackHistoryModel.playback_id)).all() == ["db-1"]


@contextmanager
def _fixture_db():
    yield None


class _Endpoint:
    """The real stream endpoint with a real StreamService.save_playback_history; storage is faked."""

    def __init__(self, monkeypatch, user: UserModel, relay_streams: list[Any] | None = None):
        self.user = user
        self.auth = Mock()
        self.auth.verify_api_key.return_value = user
        self.relay = Mock()
        self.relay.get_active_streams.return_value = relay_streams or []
        self.file = cast(
            Any,
            SimpleNamespace(
                name="movie.mkv",
                size=FILE_SIZE,
                torrent=SimpleNamespace(name="movie"),
                stream=AsyncMock(side_effect=self._body),
            ),
        )
        self.service = object.__new__(StreamService)
        self.prepare = AsyncMock(side_effect=self._prepare)
        cast(Any, self.service).prepare_for_stream = self.prepare
        monkeypatch.setattr(router, "isolated_db_session", _fixture_db)
        monkeypatch.setattr(router, "create_auth_service", lambda db: self.auth)
        monkeypatch.setattr(router, "get_relay_service", lambda: self.relay)
        monkeypatch.setattr(router, "create_playback_histories_service", lambda db: None)
        monkeypatch.setattr(
            router,
            "create_playbacks_service",
            lambda **kwargs: PlaybacksService(
                relay_service=kwargs["relay_service"],
                playback_histories_service=kwargs["playback_histories_service"],
            ),
        )
        monkeypatch.setattr(router, "create_stream_service", lambda db: self.service)

    async def _prepare(self, range_header, **kwargs):
        return parse_range_header(FILE_SIZE, range_header), self.file

    async def _body(self, stream_start_byte: int, stream_end_byte: int, **kwargs) -> AsyncIterator[bytes]:
        async def chunks() -> AsyncIterator[bytes]:
            yield b"\0" * (stream_end_byte - stream_start_byte + 1)

        return chunks()

    def url(self, playback_id: str) -> str:
        token = generate_stream_token(
            StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id=playback_id)
        )
        return f"/api/{SECRET_MARKER}/stream/{token}"


@pytest.fixture
def endpoint_client():
    active_playback.clear_active_playbacks()
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    yield client
    active_playback.clear_active_playbacks()


@pytest.mark.parametrize("fail_first", [0, 1], ids=["ok", "first-write-fails"])
async def test_get_and_head_ranges_through_the_endpoint(
    monkeypatch, history, background, endpoint_client, fail_first, caplog
):
    caplog.set_level(logging.WARNING, logger="app.common.logger")
    writes = history(_Writes(fail_first=fail_first))
    endpoint = _Endpoint(monkeypatch, UserModel(id="router-user", username="fixture"))
    url = endpoint.url("router-p")
    async with endpoint_client as client:
        for index in range(10):
            method = "GET" if index % 2 == 0 else "HEAD"
            start = index * 100
            response = await client.request(method, url, headers={"Range": f"bytes={start}-"})
            assert response.status_code == 206
            assert response.headers["Content-Range"] == f"bytes {start}-{FILE_SIZE - 1}/{FILE_SIZE}"
            assert len(response.content) == (FILE_SIZE - start if method == "GET" else 0)
            await drain_background_tasks()
    expected = ["router-p"] * (1 + fail_first) if background else ["router-p"] * 10
    assert writes.calls == expected
    assert SECRET_MARKER not in caplog.text


@pytest.mark.parametrize("denial", ["api-key", "playback-limit"])
async def test_rejected_requests_never_write_history(monkeypatch, history, background, endpoint_client, denial):
    writes = history(_Writes())
    user = UserModel(id="limited-user", username="fixture", max_concurrent_streams=1)
    other = SimpleNamespace(user_id=user.id, playback_id="another-playback")
    endpoint = _Endpoint(monkeypatch, user, relay_streams=[other])
    if denial == "api-key":
        endpoint.auth.verify_api_key.side_effect = HTTPException(401, "fixture rejected key")
    async with endpoint_client as client:
        for method in ("GET", "HEAD"):
            response = await client.request(method, endpoint.url("denied-p"), headers={"Range": "bytes=0-"})
            assert response.status_code == (401 if denial == "api-key" else 403)
    await drain_background_tasks()
    assert writes.calls == []
    endpoint.prepare.assert_not_called()


async def test_playback_limit_counts_relay_streams_not_history(monkeypatch, history, background, endpoint_client):
    """The limit reads the relay's active streams; the history write path does not change it."""
    writes = history(_Writes())
    user = UserModel(id="limit-user", username="fixture", max_concurrent_streams=1)
    endpoint = _Endpoint(monkeypatch, user, relay_streams=[SimpleNamespace(user_id=user.id, playback_id="same-p")])
    async with endpoint_client as client:
        same = await client.head(endpoint.url("same-p"), headers={"Range": "bytes=0-"})
        other = await client.head(endpoint.url("new-p"), headers={"Range": "bytes=0-"})
    await drain_background_tasks()
    assert same.status_code == 206
    assert other.status_code == 403
    assert writes.calls == ["same-p"]


def test_default_is_the_gate_passed_background_write():
    from app.config import Config

    assert Config.model_fields["playback_history_background"].default is True
    assert Config.model_validate({"playback_history_background": "false"}).playback_history_background is False
