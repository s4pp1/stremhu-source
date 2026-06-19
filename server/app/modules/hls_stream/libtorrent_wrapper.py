import asyncio
import os
from typing import BinaryIO

from app.modules.relay.entities import File


class DummyRequest:
    async def is_disconnected(self):
        return False


class LibtorrentFileWrapper(BinaryIO):
    """
    Synchronous file-like object that wraps a libtorrent File by utilizing
    the existing file.stream() async method in a background thread.
    """

    def __init__(
        self,
        relay_file: File,
        playback_id: str,
        user_id: str,
        loop: asyncio.AbstractEventLoop,
    ):
        self.file = relay_file
        self.playback_id = playback_id
        self.user_id = user_id
        self.loop = loop
        self._pos = 0
        self._size = relay_file.size
        self._dummy_request = DummyRequest()

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            # If a library tries to read the entire file (e.g. read()), we MUST NOT download gigabytes!
            # We return up to a maximum of 5MB.
            size = min(self._size - self._pos, 5 * 1024 * 1024)

        if size == 0 or self._pos >= self._size:
            return b""

        # Absolute safeguard to prevent downloading more than 10MB in a single read call
        if size > 10 * 1024 * 1024:
            size = 10 * 1024 * 1024

        read_size = min(size, self._size - self._pos)
        end_pos = self._pos + read_size - 1

        async def fetch_chunk():
            iterator = await self.file.stream(
                playback_id=self.playback_id,
                user_id=self.user_id,
                stream_start_byte=self._pos,
                stream_end_byte=end_pos,
                request=self._dummy_request,  # type: ignore
            )
            data = bytearray()
            async for chunk in iterator:
                data.extend(chunk)
                # Break early if we exceeded the requested read size somehow
                if len(data) >= read_size:
                    break
            return bytes(data[:read_size])

        # Run the async stream fetch thread-safely from this background thread
        future = asyncio.run_coroutine_threadsafe(fetch_chunk(), self.loop)
        data = future.result()

        self._pos += len(data)
        return data

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence == os.SEEK_SET:
            self._pos = offset
        elif whence == os.SEEK_CUR:
            self._pos += offset
        elif whence == os.SEEK_END:
            self._pos = self._size + offset

        self._pos = max(0, min(self._pos, self._size))
        return self._pos

    def tell(self) -> int:
        return self._pos

    def close(self):
        pass

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def write(self, s) -> int:
        raise NotImplementedError()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
