import asyncio
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException, Request

from app.common.constants import CHUNK_SIZE, STALLED_STREAM_TIMEOUT_SECONDS
from app.modules.playback_histories.service import PlaybackHistoriesService
from app.modules.playbacks.service import PlaybacksService
from app.modules.relay.entities import File, Stream, Torrent
from app.modules.relay.service import RelayService
from app.modules.users.models import UserModel

USER_ID = "user-1"
CURRENT_PLAYBACK_ID = "playback-new"


class FakeStream:
    """A limitellenőrzéshez csak ez a három mező kell a Streamből."""

    def __init__(self, user_id: str, playback_id: str, stalled: bool) -> None:
        self.user_id = user_id
        self.playback_id = playback_id
        self._stalled = stalled
        self.timeouts: list[float] = []

    def is_client_stalled(self, timeout_seconds: float) -> bool:
        self.timeouts.append(timeout_seconds)
        return self._stalled


def make_playbacks_service(streams: list[FakeStream]) -> PlaybacksService:
    relay_service = SimpleNamespace(get_active_streams=lambda: streams)
    return PlaybacksService(
        relay_service=cast(RelayService, relay_service),
        playback_histories_service=cast(PlaybackHistoriesService, object()),
    )


def make_user(max_concurrent_streams: int | None) -> UserModel:
    return cast(
        UserModel,
        SimpleNamespace(id=USER_ID, max_concurrent_streams=max_concurrent_streams),
    )


def test_active_stream_of_other_playback_blocks_new_playback():
    """Egy másik lejátszás aktív streamje (a kliens olvas belőle) továbbra is
    elfoglalja a helyet, a limit 1."""
    streams = [FakeStream(USER_ID, "playback-old", stalled=False)]
    service = make_playbacks_service(streams)

    with pytest.raises(HTTPException) as exc_info:
        service.check_playback_limit(make_user(1), CURRENT_PLAYBACK_ID)

    assert exc_info.value.status_code == 403


def test_stalled_stream_does_not_block_new_playback():
    """A megállt (nyitva maradt, de nem olvasott) stream nem foglal helyet, az új
    lejátszás elindulhat, és a küszöbérték a konstansból jön."""
    stalled = FakeStream(USER_ID, "playback-old", stalled=True)
    service = make_playbacks_service([stalled])

    service.check_playback_limit(make_user(1), CURRENT_PLAYBACK_ID)

    assert stalled.timeouts == [STALLED_STREAM_TIMEOUT_SECONDS]


def test_stalled_stream_does_not_hide_an_active_one():
    """Ha a megállt stream mellett van aktív is, az továbbra is számít."""
    streams = [
        FakeStream(USER_ID, "playback-stalled", stalled=True),
        FakeStream(USER_ID, "playback-active", stalled=False),
    ]
    service = make_playbacks_service(streams)

    with pytest.raises(HTTPException) as exc_info:
        service.check_playback_limit(make_user(1), CURRENT_PLAYBACK_ID)

    assert exc_info.value.status_code == 403


def test_limit_of_two_counts_only_active_playbacks():
    """Limit 2 mellett egy aktív és egy megállt lejátszás mellé indulhat újabb."""
    streams = [
        FakeStream(USER_ID, "playback-stalled", stalled=True),
        FakeStream(USER_ID, "playback-active", stalled=False),
    ]
    service = make_playbacks_service(streams)

    service.check_playback_limit(make_user(2), CURRENT_PLAYBACK_ID)


def test_streams_of_same_playback_and_other_users_are_ignored():
    """A saját lejátszás további kéréseit és más felhasználók streamjeit a limit
    nem számolja (a korábbi viselkedés változatlan)."""
    streams = [
        FakeStream(USER_ID, CURRENT_PLAYBACK_ID, stalled=False),
        FakeStream("user-2", "playback-other", stalled=False),
    ]
    service = make_playbacks_service(streams)

    service.check_playback_limit(make_user(1), CURRENT_PLAYBACK_ID)


def test_no_limit_means_no_check():
    """Ha nincs beállítva limit, a stream állapotát sem vizsgáljuk."""
    streams = [FakeStream(USER_ID, "playback-old", stalled=False)]
    service = make_playbacks_service(streams)

    service.check_playback_limit(make_user(None), CURRENT_PLAYBACK_ID)

    assert streams[0].timeouts == []


class FakeTorrentService:
    """A Stream generátorhoz csak a prioritásfrissítés és a darab olvasás kell."""

    def __init__(self, piece: bytes, gate: asyncio.Event | None = None) -> None:
        self._piece = piece
        self._gate = gate

    def trigger_priority_update(self, info_hash: str) -> None:
        _ = info_hash

    async def get_piece_data(self, torrent_handle: object, piece_index: int) -> bytes:
        _ = (torrent_handle, piece_index)
        if self._gate is not None:
            await self._gate.wait()
        return self._piece


class FakeRequest:
    async def is_disconnected(self) -> bool:
        return False


def make_stream(service: FakeTorrentService) -> tuple[Stream, File]:
    piece_size = 2 * CHUNK_SIZE
    torrent = SimpleNamespace(
        torrent_handle=object(),
        info_hash="a" * 40,
        piece_size=piece_size,
        service=service,
    )
    file = SimpleNamespace(offset=0, streams={})
    stream = Stream(
        stream_id="stream-1",
        playback_id="playback-1",
        user_id=USER_ID,
        torrent=cast(Torrent, torrent),
        file=cast(File, file),
        stream_start_byte=0,
        stream_end_byte=piece_size - 1,
    )
    return stream, cast(File, file)


def fake_clock(monkeypatch: pytest.MonkeyPatch, now: list[float]) -> None:
    # Csak az entities modul órája, az asyncio saját időzítése érintetlen marad.
    monkeypatch.setattr(
        "app.modules.relay.entities.time",
        SimpleNamespace(monotonic=lambda: now[0]),
    )


def test_stream_is_stalled_only_while_client_does_not_take_the_chunk(
    monkeypatch: pytest.MonkeyPatch,
):
    """Amíg a generátor az átadott chunk mellett vár, a stream a küszöb után
    megállt; ha a kliens átvette a chunkot és jön a következő, az idő újraindul."""

    async def scenario() -> None:
        now = [1000.0]
        fake_clock(monkeypatch, now)
        stream, file = make_stream(FakeTorrentService(bytes(2 * CHUNK_SIZE)))
        request = cast(Request, FakeRequest())

        assert not stream.is_client_stalled(0)

        generator = stream._stream_inner(request)
        await anext(generator)

        # A generátor az első chunk átadásánál áll, a kliens még nem vette át.
        now[0] = 1000.0 + STALLED_STREAM_TIMEOUT_SECONDS - 1
        assert not stream.is_client_stalled(STALLED_STREAM_TIMEOUT_SECONDS)
        now[0] = 1000.0 + STALLED_STREAM_TIMEOUT_SECONDS
        assert stream.is_client_stalled(STALLED_STREAM_TIMEOUT_SECONDS)

        # A kliens átveszi az elsőt, a második chunknál az idő újraindul.
        await anext(generator)
        assert not stream.is_client_stalled(STALLED_STREAM_TIMEOUT_SECONDS)
        now[0] += STALLED_STREAM_TIMEOUT_SECONDS
        assert stream.is_client_stalled(STALLED_STREAM_TIMEOUT_SECONDS)

        # A stream végén már nincs mire várni.
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
        assert not stream.is_client_stalled(0)

        # A destroy() kitakarítja a streamet a fájlból.
        await asyncio.sleep(0.5)
        assert file.streams == {}

    asyncio.run(scenario())


def test_waiting_for_torrent_data_is_not_a_stalled_client(
    monkeypatch: pytest.MonkeyPatch,
):
    """Ha a stream a torrent darabjára vár (lassú letöltés), az nem a kliens hibája,
    ezért nem számít megállt streamnek."""

    async def scenario() -> None:
        now = [1000.0]
        fake_clock(monkeypatch, now)
        gate = asyncio.Event()
        stream, _ = make_stream(FakeTorrentService(bytes(2 * CHUNK_SIZE), gate))
        request = cast(Request, FakeRequest())

        generator = cast(AsyncGenerator[bytes, None], stream._stream_inner(request))
        first_chunk = asyncio.ensure_future(anext(generator))
        await asyncio.sleep(0)

        now[0] += 10 * STALLED_STREAM_TIMEOUT_SECONDS
        assert not stream.is_client_stalled(STALLED_STREAM_TIMEOUT_SECONDS)

        gate.set()
        await first_chunk
        await generator.aclose()
        await asyncio.sleep(0.5)

    asyncio.run(scenario())
