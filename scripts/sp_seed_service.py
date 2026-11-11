"""H1 seed service (stream-performance): synthetic swarm + optional local tracker.

Runs in its own process/container so the seeder never shares an event loop with
the measured client or product. Reads a JSON spec, writes the synthetic .torrent
files (announce -> the local tracker when enabled), prints one ready line as JSON
and serves until SIGTERM/SIGINT, then writes its statistics.

Spec:
  {"peers": 8, "seed": 1, "host": "0.0.0.0", "port_base": 6900,
   "tracker": {"port": 6969, "advertise": "<container address>"} | null,
   "profiles": [{"rate_bytes_per_s": 2000000, "latency_s": 0.03, "jitter_s": 0.01, "stall": false}],
   "torrents": [{"id": "p4m", "name": "sp-p4m.mkv", "piece_size": 4194304, "total_size": 2147483648}]}

Synthetic zero data only; no outbound connection.
"""

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from local_bt_seed import LocalSeed, PeerProfile
from local_tracker import LocalTracker
from synthetic_torrent import build


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--torrent-dir")
    parser.add_argument("--stats")
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    tracker_spec = spec.get("tracker")
    announce = f"http://{tracker_spec['advertise']}:{tracker_spec['port']}/announce" if tracker_spec else None
    torrents = [build(t["name"], t["piece_size"], t["total_size"], announce) for t in spec["torrents"]]
    if args.torrent_dir:
        out = Path(args.torrent_dir)
        out.mkdir(parents=True, exist_ok=True)
        for item, torrent in zip(spec["torrents"], torrents, strict=True):
            (out / f"{item['id']}.torrent").write_bytes(torrent.torrent_bytes)
    profiles = [PeerProfile(**p) for p in spec.get("profiles", [])] or None
    host = spec.get("host", "127.0.0.1")
    peers = spec["peers"]
    ports = [spec["port_base"] + i for i in range(peers)] if spec.get("port_base") else None
    seed = await LocalSeed({t.info_hash: (t.piece_size, t.total_size) for t in torrents},
                           profiles=profiles, seed=spec.get("seed", 0)).start(peers, host=host, ports=ports)
    tracker = None
    if tracker_spec:
        # Real swarms have one address per peer (the product allows one connection per IP), so the
        # controller may run one peer per container and advertise all of them here.
        advertised = [tuple(p) for p in tracker_spec["peers"]] if tracker_spec.get("peers") else [
            (tracker_spec["advertise"], port) for _, port in seed.endpoints]
        tracker = LocalTracker(advertised)
        await tracker.start(host, tracker_spec["port"])
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    print(json.dumps({"ready": True, "endpoints": seed.endpoints,
                      "info_hashes": {t["id"]: tr.info_hash.hex() for t, tr in zip(spec["torrents"], torrents, strict=True)}}),
          flush=True)
    await stop.wait()
    stats = {"handshakes": seed.handshakes, "requests": seed.requests, "requests_ignored": seed.requests_ignored,
             "cancels": seed.cancels, "bytes_sent": seed.bytes_sent, "peak_connections": seed.peak_connections,
             "errors": seed.errors, "first_handshake_monotonic": seed.first_handshake,
             "tracker_announces": tracker.announces if tracker else None,
             "tracker_errors": tracker.errors if tracker else None}
    # Write the statistics before closing, so a slow close can never lose them.
    if args.stats:
        Path(args.stats).write_text(json.dumps(stats), encoding="utf-8")
    else:
        print(json.dumps({"stats": stats}), flush=True)
    if tracker:
        await tracker.close()
    await seed.close()


if __name__ == "__main__":
    asyncio.run(main())
