import asyncio
import threading
import weakref
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.modules.relay import service as relay_module
from app.modules.relay.service import RelayService

pytestmark = pytest.mark.anyio


@pytest.fixture
async def resume_rig(monkeypatch):
    class Success:
        def __init__(self, handle):
            self.handle = handle
            self.params = object()

    class Failure:
        def __init__(self, handle):
            self.handle = handle

    monkeypatch.setattr(relay_module.libtorrent, "save_resume_data_alert", Success)
    monkeypatch.setattr(relay_module.libtorrent, "save_resume_data_failed_alert", Failure)
    monkeypatch.setattr(relay_module.libtorrent, "write_resume_data", lambda _: {b"fixture": 1})

    class Handle:
        requests = 0

        def is_valid(self):
            return True

        def info_hash(self):
            return "a"*40

        def save_resume_data(self, flags):
            self.requests += 1

    class Native:
        def __init__(self):
            self.alerts = []

        def get_torrents(self):
            return [handle]

        def pop_alerts(self):
            alerts, self.alerts = self.alerts, []
            return alerts

        def set_alert_notify(self, callback):
            self.callback = callback

        def set_alert_fd(self, descriptor):
            self.descriptor = descriptor

        def pause(self):
            pass

    handle = Handle()
    native = Native()
    relay = object.__new__(RelayService)
    relay._libtorrent_session = cast(Any, native)
    relay._loop = asyncio.get_running_loop()
    relay._accepting, relay._closed = True, False
    relay._native_close_task = None
    relay._resume_pending = {}
    relay._pending_piece_reads, relay._piece_fetch_tasks = {}, {}
    relay._torrents = {}
    relay.priority_update_queue = asyncio.Queue()
    relay.on_save_resume = []

    def deliver(success=True):
        native.alerts.append(Success(handle) if success else Failure(handle))
        relay.process_alerts()

    return SimpleNamespace(relay=relay, handle=handle, deliver=deliver)


@pytest.mark.parametrize("accepted", [True, False])
async def test_final_snapshot_is_acknowledged_only_after_callback_acceptance(resume_rig, accepted):
    rig = resume_rig
    received = []

    def callback(key, data):
        received.append((key, data))
        assert not closing.done()
        return accepted

    rig.relay.on_save_resume.append(callback)
    closing = asyncio.create_task(rig.relay.save_final_resume())
    await asyncio.sleep(0)
    assert rig.handle.requests == 1
    rig.deliver()
    result = await closing
    assert result.requested == 1
    assert result.accepted == int(accepted)
    assert result.failed == int(not accepted)
    assert result.complete is accepted
    assert received == [("a"*40, b"d7:fixturei1ee")]


async def test_final_snapshot_drains_previous_request_then_requires_a_new_ack(resume_rig):
    rig = resume_rig
    rig.relay.trigger_save_resume_data()
    rig.relay.trigger_save_resume_data()
    assert rig.handle.requests == 1
    closing = asyncio.create_task(rig.relay.save_final_resume())
    await asyncio.sleep(0)
    assert rig.handle.requests == 1
    rig.deliver()
    while rig.handle.requests < 2:
        await asyncio.sleep(0)
    assert not closing.done()
    rig.deliver()
    assert (await closing).complete
    assert rig.relay._resume_pending == {}


async def test_old_alert_deadline_cannot_be_mistaken_for_final_ack(resume_rig):
    rig = resume_rig
    rig.relay.trigger_save_resume_data()
    result = await rig.relay.save_final_resume(timeout=.01)
    assert not result.complete and result.timed_out == 1
    assert rig.handle.requests == 1
    rig.deliver()
    closing = asyncio.create_task(rig.relay.save_final_resume())
    await asyncio.sleep(0)
    assert rig.handle.requests == 2
    assert not closing.done()
    rig.deliver()
    assert (await closing).complete


@pytest.mark.parametrize("fault", ["native", "callback", "serialization", "deadline"])
async def test_final_snapshot_failure_is_explicit_and_never_logs_sensitive_text(resume_rig, monkeypatch, caplog, fault):
    rig = resume_rig
    marker = "synthetic-resume-sensitive-marker"

    def fail(*args):
        raise RuntimeError(marker)

    if fault == "callback":
        rig.relay.on_save_resume.append(fail)
    elif fault == "serialization":
        monkeypatch.setattr(relay_module.libtorrent, "write_resume_data", fail)
    closing = asyncio.create_task(rig.relay.save_final_resume(timeout=.02))
    await asyncio.sleep(0)
    if fault != "deadline":
        rig.deliver(success=fault != "native")
    result = await closing
    assert not result.complete
    assert result.failed + result.timed_out == 1
    assert marker not in caplog.text


async def test_native_release_is_idempotent_detaches_notify_and_runs_final_reference_off_loop(resume_rig):
    relay = resume_rig.relay
    released = []
    finalizer = weakref.finalize(relay._libtorrent_session, lambda:released.append(threading.get_ident()))
    loop_thread = threading.get_ident()
    relay.trigger_save_resume_data()
    pending = next(iter(relay._resume_pending.values()))
    # The fixture deliver closure holds native; release it so Relay owns the
    # last reference, as production does after final-snapshot processing.
    del resume_rig.deliver
    await relay.close_native()
    await relay.close_native()
    assert pending.result() is False
    assert relay._closed and not relay._accepting
    assert not hasattr(relay, "_libtorrent_session")
    assert relay.on_save_resume == []
    assert not finalizer.alive
    assert released and released[0] != loop_thread
    relay.process_alerts()  # An already queued callback cannot access native.
    with pytest.raises(relay_module.PieceReadAbortedError):
        await relay.get_piece_data(resume_rig.handle, 0)


async def test_pinned_native_final_alert_reaches_writer_before_native_is_released(tmp_path):
    import hashlib

    from app.modules.torrents.resume_writer import ResumeWriter

    native = relay_module.libtorrent
    torrent = native.torrent_info(native.bencode({b"info": {
        b"name": b"fixture.bin", b"length": 16384, b"piece length": 16384,
        b"pieces": hashlib.sha1(bytes(16384)).digest(),
    }}))
    relay = RelayService()
    saved = {}
    writer = ResumeWriter(lambda batch:saved.update((item.info_hash,item.data) for item in batch))
    writer.start()
    relay.on_save_resume.append(writer.submit)
    try:
        params = native.add_torrent_params()
        params.ti, params.save_path = torrent, str(tmp_path)
        params.flags |= native.torrent_flags.paused
        relay._libtorrent_session.add_torrent(params)
        # An earlier periodic request crosses the final-save boundary.
        relay.trigger_save_resume_data()
        relay.stop_admission()
        result = await relay.save_final_resume(timeout=5)
        assert result.complete and result.requested == result.accepted == 1
        assert await writer.flush_and_close()
        assert len(saved) == 1
        encoded = next(iter(saved.values()))
        assert native.read_resume_data(encoded).info_hashes.v1 == torrent.info_hash()
        assert writer.stats.leased_bytes == 0
    finally:
        await writer.flush_and_close()
        await relay.close_piece_requests()
        await relay.close_native()
