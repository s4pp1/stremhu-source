import asyncio
from typing import cast

import libtorrent
import pytest

from app.config import config
from app.modules.relay.service import PieceReadAbortedError, RelayService

INFO_HASH = "a" * 40
PIECE_INDEX = 7
KEY = (INFO_HASH, PIECE_INDEX)


def test_missing_read_alert_times_out_and_cleans_up(monkeypatch):
    monkeypatch.setattr(config, "relay_read_timeout_seconds", 0.01)

    async def scenario():
        service = make_service(asyncio.get_running_loop())
        with pytest.raises(TimeoutError):
            await service.get_piece_data(cast(libtorrent.torrent_handle, FakeHandle()), PIECE_INDEX)
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}

    asyncio.run(scenario())


def test_torrent_cancellation_and_shutdown_clean_up_waiters():
    async def scenario():
        service = make_service(asyncio.get_running_loop())
        request = asyncio.create_task(service.get_piece_data(
            cast(libtorrent.torrent_handle, FakeHandle()), PIECE_INDEX
        ))
        while KEY not in service._pending_piece_reads:
            await asyncio.sleep(0)
        service.cancel_piece_requests(INFO_HASH)
        # Felismerhető hibát kap, nem vár örökké és nem csendes CancelledError-t
        with pytest.raises(PieceReadAbortedError):
            await request
        await service.close_piece_requests()
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}

    asyncio.run(scenario())


def test_cancel_other_torrent_does_not_affect_waiter():
    async def scenario():
        service = make_service(asyncio.get_running_loop())
        request = asyncio.create_task(service.get_piece_data(
            cast(libtorrent.torrent_handle, FakeHandle()), PIECE_INDEX
        ))
        while KEY not in service._pending_piece_reads:
            await asyncio.sleep(0)
        service.cancel_piece_requests("b" * 40)
        await deliver_read_piece(service, b"ok")
        assert await request == b"ok"

    asyncio.run(scenario())


def test_late_alert_after_abort_is_harmless():
    async def scenario():
        service = make_service(asyncio.get_running_loop())
        request = asyncio.create_task(service.get_piece_data(
            cast(libtorrent.torrent_handle, FakeHandle()), PIECE_INDEX
        ))
        while KEY not in service._pending_piece_reads:
            await asyncio.sleep(0)
        future = service._pending_piece_reads[KEY]
        service.cancel_piece_requests(INFO_HASH)
        with pytest.raises(PieceReadAbortedError):
            await request
        # A process_alerts mintája: a már lezárt future-re nem hív set_result-ot
        assert future.done()
        assert service._pending_piece_reads.pop(KEY, None) is None

    asyncio.run(scenario())


def test_retry_series_has_total_deadline(monkeypatch):
    monkeypatch.setattr(config, "relay_piece_timeout_seconds", 0.05)
    monkeypatch.setattr(config, "relay_read_timeout_seconds", 10.0)

    async def scenario():
        service = make_service(asyncio.get_running_loop())
        with pytest.raises(TimeoutError):
            await service.get_piece_data(
                cast(libtorrent.torrent_handle, FakeHandle()), PIECE_INDEX
            )
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}

    asyncio.run(scenario())


class FakeHandle:
    """Minimális torrent_handle: a darab megvan, a read_piece csak számolja a hívásokat."""

    def __init__(self) -> None:
        self.read_calls = 0

    def info_hash(self) -> str:
        return INFO_HASH

    def have_piece(self, piece_index: int) -> bool:
        _ = piece_index
        return True

    def read_piece(self, piece_index: int) -> None:
        _ = piece_index
        self.read_calls += 1


def make_service(loop: asyncio.AbstractEventLoop) -> RelayService:
    # A teljes konstruktor libtorrent sessiont indítana, a get_piece_data-hoz
    # viszont csak ezek a mezők kellenek.
    service = object.__new__(RelayService)
    service._loop = loop
    service._piece_fetch_tasks = {}
    service._pending_piece_reads = {}
    return service


async def deliver_read_piece(
    service: RelayService,
    data: bytes | None = None,
    error: Exception | None = None,
) -> None:
    """A process_alerts read_piece_alert ágát utánozza."""
    while KEY not in service._pending_piece_reads:
        await asyncio.sleep(0)
    future = service._pending_piece_reads.pop(KEY, None)
    if future and not future.done():
        if error:
            service._loop.call_soon_threadsafe(future.set_exception, error)
        else:
            service._loop.call_soon_threadsafe(future.set_result, data or b"")


def test_concurrent_waiters_share_same_task_and_deduplicate():
    """Ha egyszerre több kérés érkezik ugyanarra a darabra, ugyanahhoz a Taskhoz
    csatlakoznak (Singleflight), így csak egyetlen libtorrent read hívás történik,
    és mindkét kérés megkapja az eredményt."""

    async def scenario() -> None:
        service = make_service(asyncio.get_running_loop())
        fake_handle = FakeHandle()
        handle = cast(libtorrent.torrent_handle, fake_handle)

        # Két kérés indul párhuzamosan ugyanarra a darabra
        first = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        second = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))

        # Megérkezik az adat
        await deliver_read_piece(service, b"piece_data")

        # Csak 1-szer hívódott meg a libtorrent.read_piece (nincs felesleges disk-I/O)
        assert fake_handle.read_calls == 1

        # Mindkét kérés sikeresen megkapja ugyanazt az adatot
        assert await first == b"piece_data"
        assert await second == b"piece_data"

        # A Task lezárultával a belső állapotok kitisztulnak
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}

    asyncio.run(scenario())


def test_subsequent_request_starts_new_task_after_first_finishes():
    """Miután az első kérés lezárult és a Task kitakarította magát, egy későbbi
    új kérés tiszta lappal új Taskot és új olvasást indít."""

    async def scenario() -> None:
        service = make_service(asyncio.get_running_loop())
        fake_handle = FakeHandle()
        handle = cast(libtorrent.torrent_handle, fake_handle)

        # Első kérés lefut
        first = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        await deliver_read_piece(service, b"first")
        assert await first == b"first"
        assert service._piece_fetch_tasks == {}

        # Második kérés érkezik később: új Task indul
        second = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        await deliver_read_piece(service, b"second")
        assert fake_handle.read_calls == 2
        assert await second == b"second"
        assert service._piece_fetch_tasks == {}

    asyncio.run(scenario())


def test_cancellation_of_one_waiter_does_not_cancel_task_for_others():
    """Ha az egyik kliens bontja a kapcsolatot (CancelledError), a háttérben
    futó Task az asyncio.shield miatt nem szakad meg, és a másik kliens megkapja az adatot."""

    async def scenario() -> None:
        service = make_service(asyncio.get_running_loop())
        fake_handle = FakeHandle()
        handle = cast(libtorrent.torrent_handle, fake_handle)

        first = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        second = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))

        # Várjuk meg, amíg a Task elindul és regisztrálja a kérést
        while KEY not in service._pending_piece_reads:
            await asyncio.sleep(0)

        # Az első kérés lemondása (pl. kliens disconnect)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first

        # A háttértask még mindig él és várja a darabot
        await deliver_read_piece(service, b"data_for_second")
        assert await second == b"data_for_second"
        assert service._piece_fetch_tasks == {}

    asyncio.run(scenario())


def test_retry_on_file_not_found_error():
    """Ha a libtorrent FileNotFoundError hibát ad, a service újrapróbálkozik
    és a sikeres próbálkozás adatát adja vissza."""

    async def scenario() -> None:
        service = make_service(asyncio.get_running_loop())
        fake_handle = FakeHandle()
        handle = cast(libtorrent.torrent_handle, fake_handle)

        req = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))

        # 1. próbálkozás: FileNotFoundError
        await deliver_read_piece(service, error=FileNotFoundError("not ready"))

        # 2. próbálkozás: sikeres olvasás az újrapóbálkozás után
        await deliver_read_piece(service, data=b"recovered_data")
        assert await req == b"recovered_data"
        assert service._piece_fetch_tasks == {}

    asyncio.run(scenario())
