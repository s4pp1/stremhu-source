"""Functional G01 native/loopback-seed wiring; never a policy measurement."""

import asyncio
import hashlib
import json

import libtorrent

from app.common.async_utils import drain_background_tasks
from app.config import config
from app.modules.relay.schemas import RelaySettingsUpdate
from app.modules.relay.service import RelayService
from local_bt_seed import LocalSeed


class ConnectedRequest:
    async def is_disconnected(self):
        return False


async def main():
    piece_size = 256 * 1024
    total_size = 8 * piece_size
    info = {b"name": b"synthetic-seeder.mkv", b"piece length": piece_size,
            b"length": total_size, b"pieces": hashlib.sha1(b"\0" * piece_size).digest() * 8,
            b"private": 1}
    info_hash = hashlib.sha1(libtorrent.bencode(info)).digest()
    seed = await LocalSeed({info_hash: (piece_size, total_size)}).start(16)
    relay = RelayService()
    priority = None
    data = bytearray()
    observations = {}
    try:
        config.downloads_dir.mkdir(parents=True, exist_ok=True)
        settings = relay._libtorrent_session.get_settings()
        required = {"listen_interfaces", "allow_multiple_connections_per_ip", "enable_upnp",
                    "enable_natpmp", "enable_dht", "enable_lsd", "out_enc_policy", "in_enc_policy"}
        if not required <= settings.keys():
            raise RuntimeError("Pinned native settings surface differs")
        relay._libtorrent_session.apply_settings({
            "listen_interfaces": "127.0.0.1:0", "allow_multiple_connections_per_ip": True,
            "enable_upnp": False, "enable_natpmp": False, "enable_dht": False, "enable_lsd": False,
            "out_enc_policy": int(libtorrent.enc_policy.disabled),
            "in_enc_policy": int(libtorrent.enc_policy.disabled),
        })
        relay.update_settings(RelaySettingsUpdate(connections_limit=200, torrent_connections_limit=20))
        relay.add_torrent(libtorrent.bencode({b"info": info}))
        torrent = relay._torrents[libtorrent.sha1_hash(info_hash)]
        handle = torrent.torrent_handle
        handle.unset_flags(libtorrent.torrent_flags.paused | libtorrent.torrent_flags.auto_managed)
        priority = asyncio.create_task(relay.priority_manager_loop())
        file = relay.get_torrent_file(info_hash.hex(), 0)
        stream = await file.stream("synthetic-playback", "synthetic-user", 0, 65535, ConnectedRequest(), raise_errors=True)
        relay.apply_torrent_connection_policy(torrent)
        for endpoint in seed.endpoints:
            handle.connect_peer(endpoint)
        async with asyncio.timeout(30):
            async for chunk in stream:
                data.extend(chunk)
        observations = dict(native_connections=handle.status().num_connections,
                            native_limit=handle.status().connections_limit,
                            tracked_limit=torrent._last_applied_limit,
                            verified_first_piece=handle.have_piece(0))
        if bytes(data) != b"\0" * 65536 or not seed.handshakes or not seed.requests or not observations["verified_first_piece"]:
            raise RuntimeError("Native seed/verified stream wiring failed")
        if observations["native_limit"] != 50 or observations["tracked_limit"] != 50:
            raise RuntimeError("Legacy active50 state changed")
        await drain_background_tasks()
    finally:
        if priority is not None:
            priority.cancel()
            await asyncio.gather(priority, return_exceptions=True)
        await relay.close_piece_requests()
        await relay.close_native()
        await seed.close()
    print(json.dumps(dict(fixture="g01-native-loopback-seed-wiring-v1", is_measurement=False,
                          native_version=libtorrent.version, stream_bytes=len(data),
                          stream_sha256=hashlib.sha256(data).hexdigest(), **observations,
                          seed_handshakes=seed.handshakes, seed_requests=seed.requests,
                          seed_bytes=seed.bytes_sent, peak_seed_connections=seed.peak_connections,
                          seed_errors=seed.errors, remaining_seed_tasks=len(seed.tasks),
                          scope="Synthetic zero bytes, actual native hash verification/Relay stream; networknone loopback seed only. No G01 policy or latency/memory result.")))


asyncio.run(main())
