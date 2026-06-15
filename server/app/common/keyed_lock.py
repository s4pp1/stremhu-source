import asyncio
from contextlib import asynccontextmanager


class KeyedLock:
    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}
        self._ref_counts: dict[str, int] = {}

    @asynccontextmanager
    async def __call__(self, key: str):
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
            self._ref_counts[key] = 0

        self._ref_counts[key] += 1
        try:
            async with self._locks[key]:
                yield
        finally:
            self._ref_counts[key] -= 1
            if self._ref_counts[key] == 0:
                self._locks.pop(key, None)
                self._ref_counts.pop(key, None)
