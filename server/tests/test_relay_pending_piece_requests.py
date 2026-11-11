import asyncio
from typing import cast

import libtorrent
import pytest

from app.modules.relay import service as relay_service_module
from app.modules.relay.service import RelayService

INFO_HASH = "a" * 40
PIECE_INDEX = 7
KEY = (INFO_HASH, PIECE_INDEX)


class FakeHandle:
    """Minimális torrent_handle: a read_piece csak számolja a hívásokat."""

    def __init__(self, have: bool = True) -> None:
        self.read_calls = 0
        self.have = have
        self.removed = False

    def info_hash(self) -> str:
        return INFO_HASH

    def have_piece(self, piece_index: int) -> bool:
        _ = piece_index
        if self.removed:
            raise RuntimeError("invalid torrent handle used")
        return self.have

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
    service._piece_fetch_waiters = {}
    return service


async def deliver_read_piece(
    service: RelayService,
    data: bytes | None = None,
    error: Exception | None = None,
) -> None:
    """A process_alerts read_piece_alert ágát utánozza."""
    while KEY not in service._pending_piece_reads:
        await asyncio.sleep(0)
    service._resolve_piece_read(KEY, data=data, error=error)


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


def test_fetch_cancelled_after_alert_does_not_raise_invalid_state():
    """Ha a darab olvasása megérkezik, de a fetch task közben megszakad (pl. leállás),
    nem keletkezhet "Exception in callback Future.set_result ... InvalidStateError"."""

    async def scenario() -> None:
        loop = asyncio.get_running_loop()
        loop_errors: list[dict[str, object]] = []
        loop.set_exception_handler(lambda _loop, context: loop_errors.append(context))

        service = make_service(loop)
        handle = cast(libtorrent.torrent_handle, FakeHandle())

        waiter = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        while KEY not in service._pending_piece_reads:
            await asyncio.sleep(0)

        fetch_task = service._piece_fetch_tasks[KEY]
        fetch_task.cancel()
        service._resolve_piece_read(KEY, data=b"late")

        with pytest.raises(asyncio.CancelledError):
            await waiter
        await asyncio.sleep(0)

        assert loop_errors == []
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}

    asyncio.run(scenario())


def test_fetch_task_is_cancelled_when_last_waiter_leaves():
    """Ha az utolsó várakozó is bont, a háttértask nem marad árván futva."""

    async def scenario() -> None:
        service = make_service(asyncio.get_running_loop())
        handle = cast(libtorrent.torrent_handle, FakeHandle(have=False))

        waiter = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        while KEY not in service._pending_piece_reads:
            await asyncio.sleep(0)
        fetch_task = service._piece_fetch_tasks[KEY]

        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        await asyncio.sleep(0)

        assert fetch_task.cancelled()
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}
        assert service._piece_fetch_waiters == {}

    asyncio.run(scenario())


def test_lost_piece_finished_alert_is_recovered_by_recheck(monkeypatch):
    """Ha a darab letöltődik, de a piece_finished_alert elveszik, a kérés nem lóg
    örökké: az időszakos újraellenőrzés elindítja az olvasást."""

    monkeypatch.setattr(relay_service_module, "PIECE_READ_RECHECK_INTERVAL", 0.01)

    async def scenario() -> None:
        service = make_service(asyncio.get_running_loop())
        fake_handle = FakeHandle(have=False)
        handle = cast(libtorrent.torrent_handle, fake_handle)

        request = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        await asyncio.sleep(0.03)
        assert fake_handle.read_calls == 0

        # A darab megérkezett, de erről nem jött alert
        fake_handle.have = True

        async def wait_for_read() -> None:
            while fake_handle.read_calls == 0:
                await asyncio.sleep(0.005)

        await asyncio.wait_for(wait_for_read(), 1)

        await deliver_read_piece(service, b"recovered")
        assert await asyncio.wait_for(request, 1) == b"recovered"
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}

    asyncio.run(scenario())


def test_removed_torrent_fails_waiter_instead_of_hanging(monkeypatch):
    """Ha a torrentet törlik, miközben egy kérés a darabra vár, a kérés hibával
    lezárul, és nem marad beragadt task, amihez a későbbi kérések csatlakoznának."""

    monkeypatch.setattr(relay_service_module, "PIECE_READ_RECHECK_INTERVAL", 0.01)

    async def scenario() -> None:
        service = make_service(asyncio.get_running_loop())
        fake_handle = FakeHandle(have=False)
        handle = cast(libtorrent.torrent_handle, fake_handle)

        request = asyncio.create_task(service.get_piece_data(handle, PIECE_INDEX))
        await asyncio.sleep(0.03)

        fake_handle.removed = True

        with pytest.raises(RuntimeError):
            await asyncio.wait_for(request, 1)
        assert service._piece_fetch_tasks == {}
        assert service._pending_piece_reads == {}

    asyncio.run(scenario())
