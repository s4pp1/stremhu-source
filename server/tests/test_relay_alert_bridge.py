import asyncio

import pytest

from app.modules.relay import service as relay_module

pytestmark = pytest.mark.anyio


async def test_native_alert_bridge_never_calls_python_notify(monkeypatch):
    native_class = relay_module.libtorrent.session
    descriptors = []

    class NativeProxy:
        def __init__(self):
            self.native = native_class()

        def __getattr__(self, name):
            return getattr(self.native, name)

        def set_alert_notify(self, callback):
            raise AssertionError('Python native callback must not be installed')

        def set_alert_fd(self, descriptor):
            descriptors.append(descriptor)
            self.native.set_alert_fd(descriptor)

    monkeypatch.setattr(relay_module.libtorrent, 'session', NativeProxy)
    relay = relay_module.RelayService()
    observed = asyncio.Event()
    process = relay.process_alerts

    def inspect_alerts():
        process()
        observed.set()

    relay.process_alerts = inspect_alerts
    try:
        assert descriptors and descriptors[0] >= 0
        relay._libtorrent_session.post_session_stats()
        await asyncio.wait_for(observed.wait(), 2)
        assert relay._alert_task is not None and not relay._alert_task.done()
        assert not relay._alert_failed
        await relay.close_piece_requests()
        await relay.close_native()
        assert descriptors[-1] == -1
        assert relay._alert_task.done()
        assert relay._alert_reader.fileno() == relay._alert_writer.fileno() == -1
        await relay.close_native()
    finally:
        if hasattr(relay, '_libtorrent_session'):
            await relay.close_piece_requests()
            await relay.close_native()


async def test_alert_channel_failure_aborts_waiters_and_still_releases_native(monkeypatch, caplog):
    relay = relay_module.RelayService()
    loop = asyncio.get_running_loop()
    marker = 'synthetic-sensitive-alert-channel-error'

    async def broken_receive(*args):
        raise OSError(marker)

    monkeypatch.setattr(loop, 'sock_recv', broken_receive)
    piece = loop.create_future()
    resume = loop.create_future()
    relay._pending_piece_reads[('fixture',0)] = piece
    relay._resume_pending['fixture'] = resume
    try:
        deadline = loop.time()+2
        while not relay._alert_failed:
            if loop.time() > deadline:
                pytest.fail('Alert pump failure was not observed')
            await asyncio.sleep(0)
        assert not relay._accepting
        with pytest.raises(relay_module.PieceReadAbortedError):
            await piece
        assert await resume is False
        result = await relay.save_final_resume()
        assert not result.complete
        with pytest.raises(RuntimeError, match='Native alert channel failed'):
            await relay.close_native()
        assert not hasattr(relay, '_libtorrent_session')
        assert relay._alert_reader.fileno() == relay._alert_writer.fileno() == -1
        assert marker not in caplog.text
        assert 'OSError' in caplog.text
    finally:
        if hasattr(relay, '_libtorrent_session'):
            await relay.close_native()
