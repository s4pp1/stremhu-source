import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, Generic, TypeVar

from app.common.async_utils import await_owned_task

T = TypeVar("T")


class SearchStoppingError(Exception):
    """No new shared search may start after its lifecycle owner stops."""


class SearchOverloadedError(Exception):
    """The process-wide admission limit is full; no new unique shared search starts."""

    def __init__(self) -> None:
        super().__init__("A keresési szolgáltatás túlterhelt, a keresés nem indult el.")


class AdmissionGate:
    """Folyamatszintű, várakozósor nélküli keret egyedi megosztott munkákhoz.

    Csak az event loopból használható. A slotot a tulajdonolt task foglalja, és a task
    tényleges befejezésekor szabadul fel; egy várakozó lecsatlakozása nem engedi el.
    """

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("admission limit must be positive")
        self._limit = limit
        self._active = 0

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def active(self) -> int:
        return self._active

    def try_acquire(self) -> bool:
        if self._active >= self._limit:
            return False
        self._active += 1
        return True

    def release(self) -> None:
        if self._active <= 0:
            raise RuntimeError("admission released without a lease")
        self._active -= 1


class _Lease:
    """Egyetlen admission-slot; a felszabadítás idempotens."""

    def __init__(self, gate: AdmissionGate | None) -> None:
        self._gate = gate

    def release(self) -> None:
        gate, self._gate = self._gate, None
        if gate is not None:
            gate.release()


async def _release_after(work: Coroutine[Any, Any, T], lease: _Lease) -> T:
    # A slot a munka tényleges végén szabadul, még a task done-callbackjei előtt,
    # így egy közben érkező új kulcs nem kap hamis túlterhelést.
    try:
        return await work
    finally:
        lease.release()


class Singleflight(Generic[T]):
    """
    Több azonos kulcsú párhuzamos kérés egyetlen közös háttértaskot vár meg.
    Megszakításbiztos: ha egy vagy több várakozó lecsatlakozik (kliens megszakítás),
    a háttértask az asyncio.shield védelem miatt nem szakad meg, így a többi várakozó
    sikeresen megkapja az eredményt. A regiszter takarítása a task saját befejezéséhez
    kötött, nem a várakozók finally ágához.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[T]] = {}
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None

    @property
    def closed(self) -> bool:
        return self._closed

    async def run(
        self,
        key: str,
        coro_fn: Callable[[], Coroutine[Any, Any, T]],
        admission: AdmissionGate | None = None,
    ) -> T:
        if self._closed:
            raise SearchStoppingError()
        task = self._tasks.get(key)
        if task is None or task.done():
            # Csak új egyedi munka kér slotot; a csatlakozó várakozó nem.
            if admission is not None and not admission.try_acquire():
                raise SearchOverloadedError()
            lease = _Lease(admission)
            try:
                task = asyncio.create_task(_release_after(coro_fn(), lease))
            except BaseException:
                lease.release()
                raise
            self._tasks[key] = task

            def _on_done(t: asyncio.Task[T]) -> None:
                # Tartalék: indulás előtt megszakított task coroutine-ja nem fut le.
                lease.release()
                if not t.cancelled():
                    t.exception()
                if self._tasks.get(key) is t:
                    self._tasks.pop(key, None)

            task.add_done_callback(_on_done)

        return await asyncio.shield(task)

    def is_running(self, key: str) -> bool:
        task = self._tasks.get(key)
        return task is not None and not task.done()

    def cancel(self, key: str) -> bool:
        task = self._tasks.pop(key, None)
        if task is not None and not task.done():
            task.cancel()
            return True
        return False

    async def cancel_all(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def aclose(self) -> None:
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self.cancel_all(), name="singleflight-close")
        await await_owned_task(self._close_task)

