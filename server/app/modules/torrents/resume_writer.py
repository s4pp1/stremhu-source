"""Bounded, loop-owned admission with worker-owned database transactions."""

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

from app.common.database import isolated_db_session
from app.common.logger import logger
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.schemas.internal import TorrentUpdate


@dataclass(frozen=True, slots=True)
class ResumeEnvelope:
    info_hash: str = field(repr=False)
    data: bytes = field(repr=False)
    sequence: int


@dataclass(frozen=True, slots=True)
class ResumeWriterStats:
    accepted: int
    coalesced: int
    rejected: int
    completed: int
    failed: int
    retry_batches: int
    superseded_retries: int
    pending: int
    in_flight: int
    distinct_hashes: int
    leased_bytes: int
    peak_bytes: int
    peak_hashes: int


def save_resume_batch(batch: tuple[ResumeEnvelope, ...]) -> None:
    # No request Session, ORM object, Relay or HTTP client enters the worker.
    with isolated_db_session() as db:
        repository = TorrentRepository(db)
        for item in batch:
            # Preserve the existing first-matching-row behavior. A torrent
            # deleted while queued must not be recreated by a resume alert.
            repository.update(item.info_hash, TorrentUpdate(resume_bytes=item.data))


class ResumeWriter:
    def __init__(
        self,
        save_batch: Callable[[tuple[ResumeEnvelope, ...]], None] = save_resume_batch,
        *,
        max_bytes: int = 8 * 1024 * 1024,
        max_hashes: int = 1024,
        batch_size: int = 64,
        retry_delay: float = 0.1,
    ):
        if min(max_bytes, max_hashes, batch_size) < 1 or retry_delay < 0:
            raise ValueError("Invalid resume writer bounds")
        self._save_batch = save_batch
        self._max_bytes = max_bytes
        self._max_hashes = max_hashes
        self._batch_size = batch_size
        self._retry_delay = retry_delay
        self._pending: OrderedDict[str, ResumeEnvelope] = OrderedDict()
        self._in_flight: tuple[ResumeEnvelope, ...] = ()
        # At most one pending and one in-flight lease per distinct hash.
        self._hash_leases: dict[str, int] = {}
        self._pending_bytes = 0
        self._in_flight_bytes = 0
        self._sequence = 0
        self._accepted = self._coalesced = self._rejected = 0
        self._completed = self._failed = self._retry_batches = 0
        self._superseded_retries = self._peak_bytes = self._peak_hashes = 0
        self._wake = asyncio.Event()
        self._owner_loop: asyncio.AbstractEventLoop | None = None
        self._worker: asyncio.Task[None] | None = None
        self._closing: asyncio.Task[bool] | None = None
        self._accepting = False

    @property
    def stats(self) -> ResumeWriterStats:
        return ResumeWriterStats(
            accepted=self._accepted,
            coalesced=self._coalesced,
            rejected=self._rejected,
            completed=self._completed,
            failed=self._failed,
            retry_batches=self._retry_batches,
            superseded_retries=self._superseded_retries,
            pending=len(self._pending),
            in_flight=len(self._in_flight),
            distinct_hashes=len(self._hash_leases),
            leased_bytes=self._pending_bytes + self._in_flight_bytes,
            peak_bytes=self._peak_bytes,
            peak_hashes=self._peak_hashes,
        )

    def start(self) -> None:
        if self._closing is not None:
            raise RuntimeError("Resume writer is closed")
        loop = asyncio.get_running_loop()
        if self._worker is not None:
            if loop is not self._owner_loop or self._worker.done():
                raise RuntimeError("Resume writer cannot be restarted")
            return
        self._owner_loop = loop
        self._accepting = True
        self._worker = asyncio.create_task(self._run(), name="resume-writer")

    def _reject(self, reason: str) -> bool:
        self._rejected += 1
        # Every rejection is counted; logarithmic warnings cannot flood logs.
        if self._rejected & (self._rejected - 1) == 0:
            logger.warning("Resume admission rejected: reason=%s count=%s", reason, self._rejected)
        return False

    def submit(self, info_hash: str, data: bytes) -> bool:
        if not self._accepting:
            return self._reject("closed-or-not-started")
        if asyncio.get_running_loop() is not self._owner_loop:
            raise RuntimeError("Resume admission must run on its owner loop")
        if not isinstance(data, bytes):
            raise TypeError("Resume data must be immutable bytes")
        previous = self._pending.get(info_hash)
        replaced_bytes = len(previous.data) if previous is not None else 0
        size = self._pending_bytes + self._in_flight_bytes - replaced_bytes + len(data)
        if size > self._max_bytes:
            return self._reject("byte-capacity")
        if info_hash not in self._hash_leases and len(self._hash_leases) >= self._max_hashes:
            return self._reject("hash-capacity")
        self._sequence += 1
        self._accepted += 1
        if previous is None:
            self._hash_leases[info_hash] = self._hash_leases.get(info_hash, 0) + 1
        else:
            self._coalesced += 1
        self._pending[info_hash] = ResumeEnvelope(info_hash, data, self._sequence)
        self._pending_bytes += len(data) - replaced_bytes
        self._peak_bytes = max(self._peak_bytes, size)
        self._peak_hashes = max(self._peak_hashes, len(self._hash_leases))
        self._wake.set()
        return True

    def _take_batch(self) -> tuple[ResumeEnvelope, ...]:
        items = []
        for _ in range(min(self._batch_size, len(self._pending))):
            _, item = self._pending.popitem(last=False)
            items.append(item)
            self._pending_bytes -= len(item.data)
            self._in_flight_bytes += len(item.data)
        self._in_flight = tuple(items)
        return self._in_flight

    def _release(self, item: ResumeEnvelope) -> None:
        self._in_flight_bytes -= len(item.data)
        leases = self._hash_leases[item.info_hash] - 1
        if leases:
            self._hash_leases[item.info_hash] = leases
        else:
            del self._hash_leases[item.info_hash]

    def _discard_superseded_retries(self) -> tuple[ResumeEnvelope, ...]:
        remaining = []
        for item in self._in_flight:
            newer = self._pending.get(item.info_hash)
            if newer is not None and newer.sequence > item.sequence:
                self._release(item)
                self._superseded_retries += 1
            else:
                remaining.append(item)
        self._in_flight = tuple(remaining)
        return self._in_flight

    def _release_batch(self, batch: tuple[ResumeEnvelope, ...]) -> None:
        for item in batch:
            self._release(item)

    async def _run(self) -> None:
        while True:
            if not self._pending:
                if not self._accepting:
                    return
                self._wake.clear()
                await self._wake.wait()
                continue
            batch = self._take_batch()
            for attempt in range(2):
                if attempt:
                    # Keep the in-flight byte lease during backoff. Newer
                    # pending data must not be replaced by an older retry.
                    await asyncio.sleep(self._retry_delay)
                    batch = self._discard_superseded_retries()
                    if not batch:
                        break
                    self._retry_batches += 1
                try:
                    await asyncio.to_thread(self._save_batch, batch)
                except Exception as error:
                    logger.warning("Resume batch failed: kind=%s attempt=%s", type(error).__name__, attempt + 1)
                    if attempt:
                        self._failed += len(batch)
                else:
                    self._completed += len(batch)
                    break
            self._release_batch(batch)
            self._in_flight = ()
            # An idle coroutine frame must not retain the completed payloads
            # after releasing their byte/hash leases.
            batch = ()

    async def _finish(self) -> bool:
        if self._worker is not None:
            await self._worker
        return self._failed == 0 and self._rejected == 0

    async def flush_and_close(self) -> bool:
        if self._closing is None:
            self._accepting = False
            self._wake.set()
            self._closing = asyncio.create_task(self._finish(), name="resume-writer-close")
        cancelled = False
        while True:
            try:
                result = await asyncio.shield(self._closing)
                break
            except asyncio.CancelledError:
                if self._closing.cancelled():
                    raise
                cancelled = True
        # Cancellation does not stop to_thread. Return it to the caller only
        # after the owned worker has finished its real writes and drained.
        if cancelled:
            raise asyncio.CancelledError
        return result
