import asyncio
import itertools
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

_PLAYBACK_TTL_SECONDS = 7200.0
_record_ids = itertools.count(1)


@dataclass(frozen=True)
class PlaybackRecord:
    group: str
    timestamp: float
    nonce: int


class ActivePlaybackRegistry:
    """Loop-owned authenticated playback intents with independent bounded waiters."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic, ttl: float = _PLAYBACK_TTL_SECONDS, max_users: int = 1024, max_waiters: int = 4096):
        if ttl <= 0 or max_users <= 0 or max_waiters < 0:
            raise ValueError("Invalid playback registry bounds")
        self.clock, self.ttl = clock, ttl
        self.max_users, self.max_waiters = max_users, max_waiters
        self._history: OrderedDict[str, list[PlaybackRecord]] = OrderedDict()
        self._waiters: dict[str, set[asyncio.Event]] = {}
        self._waiter_count = 0
        self._closed = False

    @property
    def user_count(self) -> int:
        return len(self._history)

    @property
    def waiter_count(self) -> int:
        return self._waiter_count

    def prune(self, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        for user_id, history in list(self._history.items()):
            kept = [r for r in history if now - r.timestamp < self.ttl]
            if kept:
                self._history[user_id] = kept
            else:
                del self._history[user_id]

    def record(self, user_id: str, group: str) -> int | None:
        if self._closed:
            return None
        now = self.clock()
        self.prune(now)
        if user_id not in self._history and len(self._history) >= self.max_users:
            self._history.popitem(last=False)
        record = PlaybackRecord(group, now, next(_record_ids))
        history = [r for r in self._history.get(user_id, []) if r.group != group]
        self._history[user_id] = [record, *history[:19]]
        self._history.move_to_end(user_id)
        for event in self._waiters.get(user_id, ()):
            event.set()
        return record.nonce

    def find(self, user_id: str, valid_groups: set[str], max_age: float = _PLAYBACK_TTL_SECONDS) -> str | None:
        now = self.clock()
        self.prune(now)
        if self._closed:
            return None
        return next((r.group for r in self._history.get(user_id, []) if r.group in valid_groups and now - r.timestamp <= max_age), None)

    def remove_if_matches(self, user_id: str, group: str, nonce: int | None) -> None:
        history = self._history.get(user_id)
        if history is not None:
            kept = [r for r in history if (r.group, r.nonce) != (group, nonce)]
            if kept:
                self._history[user_id] = kept
            else:
                del self._history[user_id]

    async def wait(self, user_id: str, valid_groups: set[str], timeout: float = 2.0) -> str | None:
        recent = self.find(user_id, valid_groups, 30.0)
        if recent or not valid_groups or self._closed or self._waiter_count >= self.max_waiters:
            return recent
        event = asyncio.Event()
        self._waiters.setdefault(user_id, set()).add(event)
        self._waiter_count += 1
        try:
            await asyncio.wait_for(event.wait(), timeout)
        except TimeoutError:
            pass
        finally:
            events = self._waiters.get(user_id)
            if events is not None and event in events:
                events.remove(event)
                self._waiter_count -= 1
                if not events:
                    del self._waiters[user_id]
        return self.find(user_id, valid_groups)

    def close(self) -> None:
        self._closed = True
        self._history.clear()
        for events in self._waiters.values():
            for event in events:
                event.set()
        self._waiters.clear()
        self._waiter_count = 0


_registry = ActivePlaybackRegistry()


def record_active_playback(user_id: str, indexer_id: str, torrent_id: str) -> int | None:
    return _registry.record(user_id, f"{indexer_id}-{torrent_id}")


def remove_active_playback_if_matches(user_id: str, indexer_id: str, torrent_id: str, nonce: int | None) -> None:
    _registry.remove_if_matches(user_id, f"{indexer_id}-{torrent_id}", nonce)


def find_active_binge_group(user_id: str, valid_binge_groups: set[str], max_age_seconds: float = _PLAYBACK_TTL_SECONDS) -> str | None:
    return _registry.find(user_id, valid_binge_groups, max_age_seconds)


async def wait_for_active_binge_group(user_id: str, valid_binge_groups: set[str], timeout: float = 2.0) -> str | None:
    return await _registry.wait(user_id, valid_binge_groups, timeout)


def clear_active_playbacks() -> None:
    global _registry
    _registry.close()
    _registry = ActivePlaybackRegistry()
