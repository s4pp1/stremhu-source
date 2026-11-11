import concurrent.futures
import threading
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import libtorrent
import pytest

from app.common.torrent_info import TorrentInfo
from app.modules.relay.entities import File, Torrent
from app.modules.relay.schemas import RelaySettingsUpdate, RelayTorrent
from app.modules.relay.service import RelayService

HASH = "a" * 40
KEY = libtorrent.sha1_hash(bytes.fromhex(HASH))


class Handle:
    def __init__(self):
        self.limit = 20
        self.valid = True
        self.fail = False
        self.values = []
        self.entered = threading.Event()
        self.release = threading.Event()
        self.pause = False

    def is_valid(self):
        return self.valid

    def set_max_connections(self, value):
        if self.pause:
            self.entered.set()
            if not self.release.wait(2):
                raise RuntimeError("fixture policy barrier timeout")
        self.limit = value
        self.values.append(value)
        if self.fail:
            self.fail = False
            raise RuntimeError("fixture partial native failure")

    def unset_flags(self, flags):
        pass

    def piece_priorities(self):
        return [0]

    def prioritize_pieces(self, priorities):
        pass


@pytest.fixture
def policy_fixture(monkeypatch):
    def create(base=20, active=True):
        service = object.__new__(RelayService)
        service._connection_policy_lock = threading.RLock()
        service._torrent_connections_limit = base
        service._libtorrent_session = Mock()
        handle = Handle()
        torrent = Torrent(cast(libtorrent.torrent_handle, handle), TorrentInfo(info_hash=HASH, name="fixture", size=1, piece_size=1024, files=[]), service, 0)
        flag = SimpleNamespace(has_active_streams=active)
        torrent.files = {0:cast(File, flag)}
        monkeypatch.setattr(torrent, "get_deadlines", lambda:{})
        service._torrents = {KEY:torrent}
        return service, torrent, handle, flag

    return create


@pytest.mark.parametrize("active,values,expected", [(True, [10, 80, 20], [50, 80, 50]), (False, [10, 80, 20], [10, 80, 20]), (True, [80, 20, 10], [80, 50, 50])])
def test_settings_and_priority_use_same_effective_legacy_policy(policy_fixture, active, values, expected):
    service, torrent, handle, flag = policy_fixture(active=active)
    for value, effective in zip(values, expected, strict=True):
        service.update_settings(RelaySettingsUpdate(torrent_connections_limit=value))
        assert handle.limit == effective
        torrent.priority_manager()
        assert handle.limit == effective == torrent._last_applied_limit
    flag.has_active_streams = not active
    torrent.priority_manager()
    assert handle.limit == (max(values[-1], 50) if flag.has_active_streams else values[-1])


def test_invalid_removed_and_replacement_handle_do_not_reuse_applied_state(policy_fixture):
    service, torrent, handle, _ = policy_fixture()
    service.apply_torrent_connection_policy(torrent)
    assert handle.limit == 50
    handle.valid = False
    service.apply_torrent_connection_policy(torrent)
    assert torrent._last_applied_limit is None
    replacement = Handle()
    torrent.torrent_handle = cast(libtorrent.torrent_handle, replacement)
    service.apply_torrent_connection_policy(torrent)
    assert replacement.limit == 50
    assert replacement.values == [50]
    service._torrents.pop(KEY)
    service.apply_torrent_connection_policy(torrent)
    assert torrent._last_applied_limit is None
    assert replacement.values == [50]


def test_partial_native_failure_invalidates_tracking_and_can_return_to_old_target(policy_fixture):
    service, torrent, handle, _ = policy_fixture()
    service.apply_torrent_connection_policy(torrent)
    handle.fail = True
    with pytest.raises(RuntimeError, match="partial native failure"):
        service.update_settings(RelaySettingsUpdate(torrent_connections_limit=80))
    assert handle.limit == 80
    assert torrent._last_applied_limit is None
    service.update_settings(RelaySettingsUpdate(torrent_connections_limit=20))
    assert handle.limit == 50 == torrent._last_applied_limit


def test_concurrent_priority_snapshot_cannot_overwrite_newer_settings(policy_fixture):
    service, torrent, handle, _ = policy_fixture()
    handle.pause = True
    settings_started = threading.Event()
    settings_finished = threading.Event()

    def settings():
        settings_started.set()
        service.update_settings(RelaySettingsUpdate(torrent_connections_limit=80))
        settings_finished.set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        priority = executor.submit(torrent.priority_manager)
        try:
            assert handle.entered.wait(1)
            updated = executor.submit(settings)
            assert settings_started.wait(1)
            assert not settings_finished.wait(0.05)
        finally:
            handle.release.set()
        priority.result(timeout=2)
        updated.result(timeout=2)
    assert handle.limit == 80 == torrent._last_applied_limit


def test_new_native_handle_uses_current_policy_after_add_race(policy_fixture, monkeypatch):
    service, _, handle, _ = policy_fixture(active=False)
    service._torrents.clear()
    native = cast(Mock, service._libtorrent_session)

    def added(params):
        service.update_settings(RelaySettingsUpdate(torrent_connections_limit=80))
        return handle

    native.add_torrent.side_effect = added
    response = RelayTorrent(info_hash=HASH, name="fixture", download_speed=0, upload_speed=0, downloaded=0, uploaded=0, total=1, max_connections=80, connections=0)
    monkeypatch.setattr(RelayTorrent, "from_libtorrent_handle", lambda native_handle:response)
    torrent_bytes = libtorrent.bencode({b"info":{b"name":b"fixture.mkv", b"length":1, b"piece length":16384, b"pieces":b"\0"*20}})
    assert service.add_torrent(torrent_bytes).max_connections == 80
    assert handle.values == [80]
    owned = next(iter(service._torrents.values()))
    assert owned._last_applied_limit == 80
