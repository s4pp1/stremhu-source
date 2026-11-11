"""Actual Relay/Torrent policy with a synthetic native handle, no networking."""

import json
import threading
from types import SimpleNamespace

import libtorrent

from app.common.torrent_info import TorrentInfo
from app.modules.relay.entities import Torrent
from app.modules.relay.schemas import RelaySettingsUpdate
from app.modules.relay.service import RelayService


class Handle:
    def __init__(self):
        self.limit = 20

    def is_valid(self):
        return True

    def set_max_connections(self, value):
        self.limit = value


failures = 0
for _ in range(100):
    handle = Handle()
    service = object.__new__(RelayService)
    service._torrent_connections_limit = 20
    service._connection_policy_lock = threading.RLock()
    service._libtorrent_session = SimpleNamespace(get_torrents=lambda:[handle], apply_settings=lambda settings:None)
    torrent = Torrent(handle, TorrentInfo(info_hash="a"*40, name="fixture", size=1, piece_size=1024, files=[]), service, 0)
    torrent.files = {0:SimpleNamespace(has_active_streams=True)}
    torrent.get_deadlines = lambda:{}
    service._torrents = {libtorrent.sha1_hash(bytes.fromhex("a"*40)):torrent}
    torrent.priority_manager()
    service.update_settings(RelaySettingsUpdate(torrent_connections_limit=10))
    torrent.priority_manager()
    failures += handle.limit != 50
print(json.dumps(dict(fixture="active-20-to-10-native-tracked-drift-v1", cycles=100, incorrect_effective_limits=failures, policy="legacy active minimum 50 retained")))
