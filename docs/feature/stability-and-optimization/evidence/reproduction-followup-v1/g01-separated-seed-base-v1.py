"""Bounded loopback-only BitTorrent v1 seed for disposable native fixtures.

Every byte is synthetic zero data. There is no tracker, DNS, webseed or outbound
connection. Distinct peer IDs permit exercising native per-torrent peer caps
without hundreds of native seeder processes. This is not a production peer.
"""

import asyncio
import itertools
import struct


class LocalSeed:
    def __init__(self, torrents: dict[bytes, tuple[int, int]], max_connections=512):
        self.torrents = torrents
        self.max_connections = max_connections
        self.servers = []
        self.tasks = set()
        self.writers = set()
        self.sequence = itertools.count(1)
        self.handshakes = 0
        self.requests = 0
        self.bytes_sent = 0
        self.peak_connections = 0
        self.errors = []
        self.endpoints = []
        self.block_delay = 0

    async def start(self, peers: int):
        if not 1 <= peers <= self.max_connections:
            raise ValueError("Fixture peer count outside bounded contract")
        for _ in range(peers):
            server = await asyncio.start_server(self._serve, "0.0.0.0", 0)
            self.servers.append(server)
            self.endpoints.append(server.sockets[0].getsockname()[:2])
        return self

    async def _serve(self, reader, writer):
        task = asyncio.current_task()
        if len(self.tasks) >= self.max_connections:
            writer.close()
            await writer.wait_closed()
            return
        self.tasks.add(task)
        self.writers.add(writer)
        self.peak_connections = max(self.peak_connections, len(self.tasks))
        try:
            handshake = await asyncio.wait_for(reader.readexactly(68), 10)
            if handshake[:20] != b"\x13BitTorrent protocol":
                raise ValueError("Fixture accepts plain BitTorrent v1 only")
            info_hash = handshake[28:48]
            piece_size, total_size = self.torrents[info_hash]
            piece_count = (total_size + piece_size - 1) // piece_size
            bitfield = bytearray(b"\xff" * ((piece_count + 7) // 8))
            if piece_count % 8:
                bitfield[-1] = (255 << (8 - piece_count % 8)) & 255
            peer_id = b"-CR0001-" + f"{next(self.sequence):012d}".encode()
            writer.write(b"\x13BitTorrent protocol" + b"\0" * 8 + info_hash + peer_id)
            writer.write(struct.pack("!I", len(bitfield) + 1) + b"\x05" + bitfield)
            writer.write(b"\0\0\0\x01\x01")  # unchoke
            await writer.drain()
            self.handshakes += 1
            while True:
                size = struct.unpack("!I", await reader.readexactly(4))[0]
                if size == 0:
                    continue
                if size > 65536:
                    raise ValueError("Oversized fixture peer message")
                message = await reader.readexactly(size)
                if message[0] != 6:
                    continue
                if len(message) != 13:
                    raise ValueError("Invalid fixture block request")
                index, offset, length = struct.unpack("!III", message[1:])
                remaining = min(piece_size, total_size - index * piece_size)
                if index >= piece_count or not 0 < length <= 16384 or offset + length > remaining:
                    raise ValueError("Block request outside synthetic torrent")
                if self.block_delay:
                    await asyncio.sleep(self.block_delay)
                writer.write(struct.pack("!IBII", length + 9, 7, index, offset) + b"\0" * length)
                await writer.drain()
                self.requests += 1
                self.bytes_sent += length
        except (asyncio.IncompleteReadError, ConnectionError, asyncio.CancelledError):
            pass
        except Exception as error:
            self.errors.append(type(error).__name__)
        finally:
            self.tasks.discard(task)
            self.writers.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def close(self):
        for server in self.servers:
            server.close()
        await asyncio.gather(*(server.wait_closed() for server in self.servers))
        for writer in tuple(self.writers):
            writer.close()
        for task in tuple(self.tasks):
            task.cancel()
        await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
