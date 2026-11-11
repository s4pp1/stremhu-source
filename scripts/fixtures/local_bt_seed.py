"""Bounded BitTorrent v1 seed for disposable native fixtures.

Every byte is synthetic zero data. There is no DNS, webseed or outbound
connection; peers are found either by direct injection or by the separate
``local_tracker`` fixture. Distinct peer IDs permit exercising native
per-torrent peer caps without hundreds of native seeder processes. This is not
a production peer.

Without ``profiles`` every endpoint answers immediately (the original loopback
behaviour). With ``profiles`` each endpoint gets a deterministic network model:
a per-connection upload rate, a one-way request latency with jitter (pipelined,
so it is paid once per request, not serialised), or a stalled peer that accepts
requests and never answers. Cancelled block requests are not sent.
"""

import asyncio
import itertools
import random
import struct
from dataclasses import dataclass
from functools import partial

_ZERO_BLOCK = bytes(16384)


class _UtpRefuser(asyncio.DatagramProtocol):
    """Answers a uTP SYN (BEP 29) with ST_RESET so the connecting client falls back to TCP at once."""

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if len(data) < 20 or data[0] != 0x41:  # type ST_SYN (4), version 1
            return
        connection_id = data[2:4]
        seq_nr = data[16:18]
        reset = bytes([0x31, 0]) + connection_id + bytes(12) + b"\0\0" + seq_nr
        self.transport.sendto(reset, addr)


@dataclass(frozen=True)
class PeerProfile:
    rate_bytes_per_s: float | None = None
    latency_s: float = 0.0
    jitter_s: float = 0.0
    stall: bool = False


class LocalSeed:
    def __init__(
        self,
        torrents: dict[bytes, tuple[int, int]],
        max_connections=512,
        profiles: list[PeerProfile] | None = None,
        seed: int = 0,
    ):
        self.torrents = torrents
        self.max_connections = max_connections
        self.profiles = profiles
        self.seed = seed
        self.servers = []
        self.tasks = set()
        self.writers = set()
        self.sequence = itertools.count(1)
        self.handshakes = 0
        self.requests = 0
        self.requests_ignored = 0
        self.cancels = 0
        self.bytes_sent = 0
        self.peak_connections = 0
        self.errors = []
        self.endpoints = []
        self.udp_transports = []
        # info hash (hex) -> event-loop time (CLOCK_MONOTONIC, shared by containers on one host).
        self.first_handshake: dict[str, float] = {}

    async def start(self, peers: int, host: str = "127.0.0.1", ports: list[int] | None = None):
        if not 1 <= peers <= self.max_connections:
            raise ValueError("Fixture peer count outside bounded contract")
        if ports is not None and len(ports) != peers:
            raise ValueError("One port per fixture peer")
        loop = asyncio.get_running_loop()
        for index in range(peers):
            profile = self.profiles[index % len(self.profiles)] if self.profiles else None
            handler = partial(self._serve, profile, random.Random(self.seed * 1000 + index))
            server = await asyncio.start_server(handler, host, ports[index] if ports else 0)
            self.servers.append(server)
            endpoint = server.sockets[0].getsockname()[:2]
            self.endpoints.append(endpoint)
            # The fixture speaks TCP only. A real swarm mostly speaks uTP too, so an unanswered uTP
            # attempt (and its multi-second fallback) would be a harness artefact: refuse it at once.
            transport, _ = await loop.create_datagram_endpoint(_UtpRefuser, local_addr=endpoint)
            self.udp_transports.append(transport)
        return self

    async def _serve(self, profile: PeerProfile | None, rng: random.Random, reader, writer):
        task = asyncio.current_task()
        if len(self.tasks) >= self.max_connections:
            writer.close()
            await writer.wait_closed()
            return
        self.tasks.add(task)
        self.writers.add(writer)
        self.peak_connections = max(self.peak_connections, len(self.tasks))
        sender: asyncio.Task | None = None
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
            self.first_handshake.setdefault(info_hash.hex(), asyncio.get_running_loop().time())
            queue: asyncio.Queue[tuple[float, int, int, int]] | None = None
            cancelled: set[tuple[int, int, int]] = set()
            if profile is not None and not profile.stall:
                queue = asyncio.Queue()
                sender = asyncio.create_task(self._send_loop(writer, queue, cancelled, profile, rng))
            loop = asyncio.get_running_loop()
            while True:
                size = struct.unpack("!I", await reader.readexactly(4))[0]
                if size == 0:
                    continue
                if size > 65536:
                    raise ValueError("Oversized fixture peer message")
                message = await reader.readexactly(size)
                if message[0] == 8 and len(message) == 13:
                    cancelled.add(struct.unpack("!III", message[1:]))
                    self.cancels += 1
                    continue
                if message[0] != 6:
                    continue
                if len(message) != 13:
                    raise ValueError("Invalid fixture block request")
                index, offset, length = struct.unpack("!III", message[1:])
                remaining = min(piece_size, total_size - index * piece_size)
                if index >= piece_count or not 0 < length <= 16384 or offset + length > remaining:
                    raise ValueError("Block request outside synthetic torrent")
                if profile is None:
                    writer.write(struct.pack("!IBII", length + 9, 7, index, offset) + _ZERO_BLOCK[:length])
                    await writer.drain()
                    self.requests += 1
                    self.bytes_sent += length
                elif queue is None:
                    self.requests_ignored += 1
                else:
                    queue.put_nowait((loop.time(), index, offset, length))
        except (asyncio.IncompleteReadError, ConnectionError, asyncio.CancelledError):
            pass
        except Exception as error:
            self.errors.append(type(error).__name__)
        finally:
            if sender is not None:
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)
            self.tasks.discard(task)
            self.writers.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def _send_loop(self, writer, queue, cancelled, profile: PeerProfile, rng: random.Random):
        loop = asyncio.get_running_loop()
        next_free = loop.time()
        while True:
            received, index, offset, length = await queue.get()
            if (index, offset, length) in cancelled:
                cancelled.discard((index, offset, length))
                continue
            due = received + profile.latency_s + (rng.uniform(0, profile.jitter_s) if profile.jitter_s else 0.0)
            delay = due - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            if profile.rate_bytes_per_s:
                # Token bucket with a small burst allowance: timer overshoot is not lost, so the
                # long-run rate matches the profile instead of drifting below it.
                next_free = max(loop.time() - 0.05, next_free) + length / profile.rate_bytes_per_s
                delay = next_free - loop.time()
                if delay > 0:
                    await asyncio.sleep(delay)
            writer.write(struct.pack("!IBII", length + 9, 7, index, offset) + _ZERO_BLOCK[:length])
            await writer.drain()
            self.requests += 1
            self.bytes_sent += length

    async def close(self):
        for transport in self.udp_transports:
            transport.close()
        for server in self.servers:
            server.close()
        # Close the open peer connections first: on Python 3.12+ Server.wait_closed() waits for
        # every active connection, so waiting before closing them would hang while a client
        # (the product) keeps its peer connections open.
        for writer in tuple(self.writers):
            writer.close()
        for task in tuple(self.tasks):
            task.cancel()
        await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
        await asyncio.gather(*(server.wait_closed() for server in self.servers))
