from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.stremio.schemas import StremioStream

Revision = tuple[int, int]


class StreamCacheState:
    """Single-process cache; revision comparison and insertion share one lock."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic, ttl: float = 60.0, max_entries: int = 500, max_user_revisions: int = 1024):
        if ttl <= 0 or max_entries <= 0 or max_user_revisions <= 0:
            raise ValueError("Invalid stream cache bounds")
        self._clock, self._ttl = clock, ttl
        self._max_entries, self._max_user_revisions = max_entries, max_user_revisions
        self._lock = threading.RLock()
        self._global_epoch = 0
        self._user_epochs: dict[str, int] = {}
        self._entries: dict[str, tuple[str, float, list[StremioStream]]] = {}

    def revision(self, user_id: str) -> Revision:
        with self._lock:
            return self._global_epoch, self._user_epochs.get(user_id, 0)

    @property
    def global_epoch(self) -> int:
        with self._lock:
            return self._global_epoch

    def get(self, key: str) -> list[StremioStream] | None:
        with self._lock:
            cached = self._entries.get(key)
            if cached is None:
                return None
            _, timestamp, streams = cached
            if self._clock() - timestamp >= self._ttl:
                del self._entries[key]
                return None
            return streams

    def put_if_revision(self, user_id: str, key: str, revision: Revision, streams: list[StremioStream]) -> bool:
        with self._lock:
            if self.revision(user_id) != revision:
                return False
            if len(self._entries) >= self._max_entries:
                for old_key in list(self._entries)[:min(100, self._max_entries)]:
                    del self._entries[old_key]
            self._entries[key] = (user_id, self._clock(), streams)
            return True

    def invalidate_user(self, user_id: str) -> None:
        with self._lock:
            if user_id not in self._user_epochs and len(self._user_epochs) >= self._max_user_revisions:
                self.invalidate_all()
            self._user_epochs[user_id] = self._user_epochs.get(user_id, 0) + 1
            for key, (owner, _, _) in list(self._entries.items()):
                if owner == user_id:
                    del self._entries[key]

    def invalidate_all(self) -> None:
        with self._lock:
            self._global_epoch += 1
            self._user_epochs.clear()
            self._entries.clear()


stream_cache_state = StreamCacheState()
