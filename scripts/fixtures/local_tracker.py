"""Minimal HTTP announce tracker for disposable native fixtures.

Answers every ``GET /announce`` with the configured IPv4 peer endpoints in the
compact format, so the product finds the synthetic seed through its normal
announce path, without test hooks. It never contacts anything itself.
"""

import asyncio
import socket
import struct


def _bencode(value) -> bytes:
    if isinstance(value, int):
        return b"i%de" % value
    if isinstance(value, bytes):
        return b"%d:%s" % (len(value), value)
    if isinstance(value, str):
        return _bencode(value.encode())
    if isinstance(value, dict):
        items = sorted((k.encode() if isinstance(k, str) else k, v) for k, v in value.items())
        return b"d" + b"".join(_bencode(k) + _bencode(v) for k, v in items) + b"e"
    raise TypeError(type(value).__name__)


class LocalTracker:
    def __init__(self, peers: list[tuple[str, int]], interval: int = 900):
        self.peers = peers
        self.interval = interval
        self.announces = 0
        self.errors: list[str] = []
        self._server: asyncio.base_events.Server | None = None

    def _body(self) -> bytes:
        compact = b"".join(socket.inet_aton(host) + struct.pack("!H", port) for host, port in self.peers)
        return _bencode({"interval": self.interval, "min interval": self.interval, "peers": compact})

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        self._server = await asyncio.start_server(self._serve, host, port)
        return self._server.sockets[0].getsockname()[1]

    async def _serve(self, reader, writer):
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            request_line = head.split(b"\r\n", 1)[0]
            if request_line.startswith(b"GET /announce"):
                body, status = self._body(), b"200 OK"
                self.announces += 1
            else:
                body, status = b"", b"404 Not Found"
            writer.write(
                b"HTTP/1.1 " + status + b"\r\nContent-Type: text/plain\r\nContent-Length: "
                + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
            )
            await writer.drain()
        except Exception as error:  # fixture accounting only
            self.errors.append(type(error).__name__)
        finally:
            writer.close()

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
