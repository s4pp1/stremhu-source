"""G0 (stream-performance): native libtorrent piece-priority/deadline semantics.

Functional probe, not a gate measurement. Runs in a network-disabled container.
The rate-limited synthetic seed runs in a child process (sp_seed_service.py) so
it never shares the probe's event loop; piece state is read with one bitfield
query per check. Questions answered for SP01/SP02/SP04:

A. Is a priority-0 piece downloaded once it gets a deadline? Its reported priority?
B. Which priority remains after reset_piece_deadline on an unfinished piece?
C. Deadline pieces with the rest of the torrent at priority 1 versus 0 (current policy).
D. Rough per-call cost of the native calls the priority manager issues.
E. Do concurrent read_piece calls all complete?
F. Plain throughput with every piece wanted (harness ceiling).
G. The product's sliding deadline window (rest at priority 0) with 4/16/64-piece windows.

Usage (inside the image): python probe_sp_libtorrent_priorities.py [rate_bytes_per_s] [latency_s]
"""

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

import libtorrent

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "fixtures"))
from synthetic_torrent import build

PIECE = 256 * 1024
PIECES = 200
PEERS = 4
RATE = float(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000.0  # bytes/s per seed connection
LATENCY = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02
NAMES = ("a", "c1", "c0", "f", "g4", "g16", "g64")


def session() -> libtorrent.session:
    ses = libtorrent.session()
    ses.apply_settings({
        "listen_interfaces": "127.0.0.1:0",
        "enable_dht": False, "enable_lsd": False, "enable_upnp": False, "enable_natpmp": False,
        "allow_multiple_connections_per_ip": True,
        "out_enc_policy": int(libtorrent.enc_policy.disabled),
        "in_enc_policy": int(libtorrent.enc_policy.disabled),
        "alert_mask": int(libtorrent.alert_category.error | libtorrent.alert_category.storage
                          | libtorrent.alert_category.status | libtorrent.alert_category.piece_progress),
        # The relay's own picker-relevant settings (relay/service.py), so picking matches the product.
        "auto_sequential": False, "piece_extent_affinity": True, "piece_timeout": 10,
        "request_timeout": 30, "strict_end_game_mode": False, "connections_limit": 300,
    })
    return ses


def add(ses, torrent, save_dir: str, priority: int):
    params = libtorrent.add_torrent_params()
    params.ti = libtorrent.torrent_info(torrent.torrent_bytes)
    params.save_path = save_dir
    params.flags &= ~(libtorrent.torrent_flags.auto_managed | libtorrent.torrent_flags.paused)
    handle = ses.add_torrent(params)
    handle.prioritize_pieces([priority] * torrent.piece_count)
    return handle


def pieces(handle) -> list[bool]:
    return list(handle.status(libtorrent.status_flags_t.query_pieces).pieces)


def priority_of(handle, piece: int) -> int:
    return handle.get_piece_priorities()[piece]


class Alerts:
    def __init__(self, ses):
        self.ses = ses
        self.finished: list[tuple[float, str, int]] = []
        self.reads: list[tuple[int, int]] = []

    def pump(self):
        for alert in self.ses.pop_alerts():
            if isinstance(alert, libtorrent.piece_finished_alert):
                self.finished.append((time.monotonic(), str(alert.handle.info_hash()), alert.piece_index))
            elif isinstance(alert, libtorrent.read_piece_alert):
                self.reads.append((alert.piece, alert.error.value() if alert.error else 0))

    async def until(self, predicate, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump()
            if predicate():
                return True
            await asyncio.sleep(0.02)
        self.pump()
        return predicate()


async def start_seed(work: Path):
    spec = {"peers": PEERS, "seed": 7, "host": "127.0.0.1",
            "profiles": [{"rate_bytes_per_s": RATE, "latency_s": LATENCY}],
            "torrents": [{"id": n, "name": f"sp-g0-{n}.mkv", "piece_size": PIECE, "total_size": PIECE * PIECES}
                         for n in NAMES]}
    (work / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(HERE / "sp_seed_service.py"), "--spec", str(work / "spec.json"),
        "--stats", str(work / "stats.json"), stdout=asyncio.subprocess.PIPE)
    ready = json.loads(await asyncio.wait_for(proc.stdout.readline(), 30))
    return proc, [tuple(e) for e in ready["endpoints"]]


async def main():
    torrents = {n: build(f"sp-g0-{n}.mkv", PIECE, PIECE * PIECES) for n in NAMES}
    result: dict = {"fixture": "sp-g0-libtorrent-priorities-v2", "is_measurement": False,
                    "native_version": libtorrent.__version__, "piece_size": PIECE, "pieces": PIECES,
                    "seed": {"peers": PEERS, "rate_bytes_per_s_per_peer": RATE, "latency_s": LATENCY,
                             "process": "separate child process"}}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        seed_proc, endpoints = await start_seed(work)
        save_dir = str(work / "data")
        ses = session()
        alerts = Alerts(ses)

        def connect(handle):
            for endpoint in endpoints:
                handle.connect_peer(endpoint)

        # A: deadline on a priority-0 piece (peers connected first, nothing wanted).
        ha = add(ses, torrents["a"], save_dir, 0)
        connect(ha)
        await asyncio.sleep(2)
        before = ha.status().num_pieces
        ha.set_piece_deadline(100, 0)
        prio_after_deadline = priority_of(ha, 100)
        started = time.monotonic()
        got = await alerts.until(lambda: ha.have_piece(100), 15)
        result["A_deadline_on_prio0"] = {
            "pieces_before_deadline": before, "priority_after_set_deadline": prio_after_deadline,
            "downloaded": got, "seconds": round(time.monotonic() - started, 3),
            "priority_after_finish": priority_of(ha, 100),
            "other_pieces_downloaded": ha.status().num_pieces - (1 if got else 0),
        }

        # B: reset_piece_deadline on an unfinished priority-0 piece; is it downloaded afterwards?
        ha.set_piece_deadline(150, 5000)
        prio_set = priority_of(ha, 150)
        ha.reset_piece_deadline(150)
        prio_reset = priority_of(ha, 150)
        downloaded_after_reset = await alerts.until(lambda: ha.have_piece(150), 10)
        result["B_reset_deadline"] = {"priority_after_set": prio_set, "priority_after_reset": prio_reset,
                                      "downloaded_within_10s_after_reset": downloaded_after_reset}

        # F: plain throughput with every piece wanted (harness ceiling).
        hf = add(ses, torrents["f"], save_dir, 4)
        started = time.monotonic()
        connect(hf)
        await alerts.until(lambda: all(pieces(hf)[:64]), 60)
        first64 = time.monotonic() - started
        result["F_full_priority_first_64_pieces"] = {
            "seconds": round(first64, 3), "mb_per_s": round(64 * PIECE / first64 / 1e6, 2),
            "ceiling_mb_per_s": round(PEERS * RATE / 1e6, 2)}

        # E: concurrent read_piece on finished pieces.
        have = [p for p, ok in enumerate(pieces(hf)) if ok][:8]
        alerts.reads.clear()
        for piece in have:
            hf.read_piece(piece)
        await alerts.until(lambda: len(alerts.reads) >= len(have), 5)
        result["E_concurrent_read_piece"] = {"requested": len(have), "completed": len(alerts.reads),
                                             "errors": sum(1 for _, code in alerts.reads if code)}
        ses.remove_torrent(hf)

        # G: the product's sliding deadline window (rest at priority 0).
        for window in (4, 16, 64):
            handle = add(ses, torrents[f"g{window}"], save_dir, 0)
            state = {"cursor": 0, "applied": set(), "updates": 0, "update_s": 0.0}

            def refresh(handle=handle, state=state, window=window):
                t0 = time.perf_counter()
                have_map = pieces(handle)
                while state["cursor"] < 64 and have_map[state["cursor"]]:
                    state["cursor"] += 1
                missing = [p for p in range(state["cursor"], PIECES) if not have_map[p]][:window]
                for d, piece in enumerate(missing):
                    handle.set_piece_deadline(piece, 0 if d == 0 else 300 if d == 1 else 1000 + 500 * d)
                for piece in state["applied"] - set(missing):
                    handle.reset_piece_deadline(piece)
                state["applied"] = set(missing)
                state["updates"] += 1
                state["update_s"] += time.perf_counter() - t0

            refresh()
            started = time.monotonic()
            connect(handle)
            seen = 0
            while state["cursor"] < 64 and time.monotonic() - started < 90:
                alerts.pump()
                if len(alerts.finished) != seen:
                    seen = len(alerts.finished)
                    refresh()
                await asyncio.sleep(0.005)
            elapsed = time.monotonic() - started
            result[f"G_sliding_window_{window}_pieces"] = {
                "window_bytes": window * PIECE, "first_64_pieces_done": state["cursor"] >= 64,
                "seconds": round(elapsed, 3), "mb_per_s": round(64 * PIECE / elapsed / 1e6, 2),
                "mean_update_ms": round(state["update_s"] / max(1, state["updates"]) * 1000, 3)}
            ses.remove_torrent(handle)
            await asyncio.sleep(0.5)

        # C: 8 deadline pieces with the rest at priority 1 (c1) vs 0 (c0, current policy).
        for key, background in (("c1", 1), ("c0", 0)):
            handle = add(ses, torrents[key], save_dir, background)
            targets = list(range(120, 128))
            for distance, piece in enumerate(targets):
                handle.set_piece_deadline(piece, 0 if distance == 0 else 300 if distance == 1 else 1000 + 500 * distance)
            started = time.monotonic()
            connect(handle)
            done = await alerts.until(lambda handle=handle: all(pieces(handle)[120:128]), 30)
            elapsed = time.monotonic() - started
            info_hash = str(handle.info_hash())
            order = [p for _, h, p in alerts.finished if h == info_hash]
            ranks = sorted(order.index(p) for p in targets if p in order)
            result[f"C_deadlines_background_prio{background}"] = {
                "all_deadline_pieces_done": done, "seconds_until_all_deadline_pieces": round(elapsed, 3),
                "non_deadline_pieces_finished_before_last_deadline_piece": (ranks[-1] + 1 - len(ranks)) if ranks else None,
                "completion_rank_of_deadline_pieces": ranks,
            }
            ses.remove_torrent(handle)
            await asyncio.sleep(0.5)

        # D: per-call cost on a 4000-piece torrent without peers.
        big = build("sp-g0-big.mkv", 16384, 16384 * 4000)
        hb = add(ses, big, save_dir, 0)

        def per_call(fn, n):
            t0 = time.perf_counter()
            for i in range(n):
                fn(i)
            return round((time.perf_counter() - t0) / n * 1e6, 2)

        result["D_call_cost_us_4000_pieces"] = {
            "have_piece": per_call(lambda i: hb.have_piece(i % 4000), 5000),
            "status_query_pieces": per_call(lambda i: hb.status(libtorrent.status_flags_t.query_pieces), 200),
            "get_piece_priorities": per_call(lambda i: hb.get_piece_priorities(), 200),
            "set_piece_deadline": per_call(lambda i: hb.set_piece_deadline(i % 4000, 1000), 4000),
            "reset_piece_deadline": per_call(lambda i: hb.reset_piece_deadline(i % 4000), 4000),
            "prioritize_pieces_full_list": per_call(lambda i: hb.prioritize_pieces([0] * 4000), 50),
            "note": "Wall-clock on the probe container; order of magnitude only, not a gate metric.",
        }
        ses.remove_torrent(hb)
        ses.remove_torrent(ha)
        del ses
        seed_proc.terminate()
        await seed_proc.wait()
        stats_file = work / "stats.json"
        result["seed_stats"] = json.loads(stats_file.read_text()) if stats_file.exists() else None
    print(json.dumps(result, indent=1))


asyncio.run(main())
