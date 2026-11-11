"""H1 player emulator (stream-performance): one playback session against a real server.

Runs in its own container on the internal measurement network. Requests go over
real HTTP(S) to the product's stream endpoint, like a player would:

1. ``Range: bytes=0-``: time to response headers and to the first body byte.
2. After the first ``probe_after`` bytes, a parallel tail probe of the last
   ``tail_bytes`` (MP4 ``moov`` / MKV cues): its total time.
3. Playback model at ``bitrate``: starts when ``start_buffer_s`` is buffered and the
   tail probe is done; stalls when the playhead reaches the received data and
   resumes after ``rebuffer_s``; reading pauses at ``max_buffer_s`` ahead
   (TCP back-pressure, as real players do).
4. Seek: the first request is closed, a new ``Range`` starts at ``seek_fraction`` of
   the file; time to first byte and to ``rebuffer_s`` buffered, then playback again.

Output: one JSON object (times in seconds, CLOCK_MONOTONIC anchors included so the
controller can relate them to the seed's first handshake). The API key and the
stream token are read from ``--targets`` and never printed.
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx

TICK = 0.05


class Playback:
    """Byte-based playback clock fed by a reader task."""

    def __init__(self, bytes_per_s: float, start_buffer_s: float, rebuffer_s: float, max_buffer_s: float):
        self.rate = bytes_per_s
        self.start_bytes = start_buffer_s * bytes_per_s
        self.rebuffer_bytes = rebuffer_s * bytes_per_s
        self.max_buffer_bytes = max_buffer_s * bytes_per_s
        self.received = 0
        self.position = 0.0
        self.playing = False
        self.stalls = 0
        self.stall_s = 0.0
        self.stalled_since: float | None = None
        self.started_at: float | None = None
        self.played_s = 0.0
        self.buffer_samples: list[float] = []
        self.full_buffer_at: float | None = None

    def ahead(self) -> float:
        return self.received - self.position

    def tick(self, now: float, dt: float, may_start: bool) -> None:
        if not self.playing:
            if self.started_at is None and not may_start:
                return
            needed = self.start_bytes if self.started_at is None else self.rebuffer_bytes
            if self.ahead() >= needed:
                self.playing = True
                if self.started_at is None:
                    self.started_at = now
                if self.stalled_since is not None:
                    self.stall_s += now - self.stalled_since
                    self.stalled_since = None
            return
        advance = self.rate * dt
        if self.position + advance > self.received:
            self.played_s += max(0.0, (self.received - self.position) / self.rate)
            self.position = float(self.received)
            self.playing = False
            self.stalls += 1
            self.stalled_since = now
            return
        self.position += advance
        self.played_s += dt
        self.buffer_samples.append(self.ahead() / self.rate)
        if self.full_buffer_at is None and self.ahead() >= 0.9 * self.max_buffer_bytes:
            self.full_buffer_at = now

    def summary(self, t_start: float) -> dict:
        samples = sorted(self.buffer_samples)
        return {
            "time_to_start_s": None if self.started_at is None else round(self.started_at - t_start, 3),
            "stalls": self.stalls, "stall_s": round(self.stall_s, 3), "played_s": round(self.played_s, 2),
            "buffer_s_min": round(samples[0], 2) if samples else None,
            "buffer_s_p10": round(samples[len(samples) // 10], 2) if samples else None,
            "buffer_s_median": round(samples[len(samples) // 2], 2) if samples else None,
            "time_to_full_buffer_s": None if self.full_buffer_at is None else round(self.full_buffer_at - t_start, 3),
            "bytes_received": self.received,
        }


async def read_stream(client, url, headers, playback: Playback | None, marks: dict, stop: asyncio.Event,
                      limit: int | None = None):
    async with client.stream("GET", url, headers=headers) as response:
        marks["headers"] = time.monotonic()
        marks["status"] = response.status_code
        marks["content_range"] = response.headers.get("content-range")
        total = 0
        async for chunk in response.aiter_raw(65536):
            if "first_byte" not in marks:
                marks["first_byte"] = time.monotonic()
            total += len(chunk)
            if playback is not None:
                playback.received += len(chunk)
                while playback.ahead() >= playback.max_buffer_bytes and not stop.is_set():
                    await asyncio.sleep(TICK)
            if "probe_bytes" in marks and total >= marks["probe_bytes"] and "probe_reached" not in marks:
                marks["probe_reached"] = time.monotonic()
            if stop.is_set() or (limit is not None and total >= limit):
                break
        marks["done"] = time.monotonic()
        marks["bytes"] = total


async def run_phase(playback: Playback, play_seconds: float, wall_cap: float, may_start) -> None:
    last = time.monotonic()
    deadline = last + wall_cap
    while playback.played_s < play_seconds and time.monotonic() < deadline:
        await asyncio.sleep(TICK)
        now = time.monotonic()
        playback.tick(now, now - last, may_start())
        last = now
    if playback.stalled_since is not None:
        playback.stall_s += time.monotonic() - playback.stalled_since
        playback.stalled_since = None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--bitrate-mbit", type=float, default=30.0)
    parser.add_argument("--start-buffer-s", type=float, default=2.0)
    parser.add_argument("--rebuffer-s", type=float, default=1.0)
    parser.add_argument("--max-buffer-s", type=float, default=30.0)
    parser.add_argument("--play-s", type=float, default=45.0)
    parser.add_argument("--seek-play-s", type=float, default=15.0)
    parser.add_argument("--seek-fraction", type=float, default=0.5)
    parser.add_argument("--probe-after", type=int, default=1 << 20)
    parser.add_argument("--tail-bytes", type=int, default=1 << 20)
    args = parser.parse_args()

    data = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    target = next(t for t in data["targets"] if t["id"] == args.target_id)
    url = f"{args.base}/api/{data['api_key']}/stream/{target['token']}"
    rate = args.bitrate_mbit * 1e6 / 8
    result: dict = {"target": args.target_id, "bitrate_mbit": args.bitrate_mbit, "errors": []}
    timeout = httpx.Timeout(120.0, connect=30.0)
    async with httpx.AsyncClient(verify=False, trust_env=False, timeout=timeout, http2=False) as client:
        # Phase 1: start + tail probe + playback.
        playback = Playback(rate, args.start_buffer_s, args.rebuffer_s, args.max_buffer_s)
        main_marks: dict = {"probe_bytes": args.probe_after}
        stop = asyncio.Event()
        t_start = time.monotonic()
        result["t_start_monotonic"] = t_start
        reader = asyncio.create_task(read_stream(client, url, {"Range": "bytes=0-"}, playback, main_marks, stop))
        tail_marks: dict = {}
        tail_task: asyncio.Task | None = None

        def may_start() -> bool:
            nonlocal tail_task
            if tail_task is None and "probe_reached" in main_marks and main_marks.get("content_range"):
                size = int(main_marks["content_range"].rsplit("/", 1)[1])
                result["file_size"] = size
                tail_marks["requested"] = time.monotonic()
                tail_task = asyncio.create_task(read_stream(
                    client, url, {"Range": f"bytes={size - args.tail_bytes}-{size - 1}"}, None, tail_marks,
                    asyncio.Event()))
            return tail_task is not None and tail_task.done()

        try:
            await run_phase(playback, args.play_s, args.play_s * 4 + 90, may_start)
        except Exception as error:  # noqa: BLE001 - recorded; the controller marks the run failed
            result["errors"].append(f"phase1:{type(error).__name__}")
        stop_at = time.monotonic()
        stop.set()
        for task in (reader, tail_task):
            if task is not None:
                try:
                    await asyncio.wait_for(task, 10)
                except Exception as error:  # noqa: BLE001 - recorded in the result
                    result["errors"].append(f"reader:{type(error).__name__}")
        result["start"] = {
            "status": main_marks.get("status"),
            "headers_s": round(main_marks["headers"] - t_start, 3) if "headers" in main_marks else None,
            "ttfb_s": round(main_marks["first_byte"] - t_start, 3) if "first_byte" in main_marks else None,
            "tail_probe_s": round(tail_marks["done"] - tail_marks["requested"], 3)
            if "done" in tail_marks and "requested" in tail_marks else None,
            "tail_status": tail_marks.get("status"),
            **playback.summary(t_start),
        }
        result["first_byte_monotonic"] = main_marks.get("first_byte")
        result["phase1_stop_monotonic"] = stop_at
        result["phase1_closed_monotonic"] = main_marks.get("done")

        # Phase 2: seek.
        size = result.get("file_size")
        if size:
            seek_at = int(size * args.seek_fraction) // 65536 * 65536
            seek = Playback(rate, args.rebuffer_s, args.rebuffer_s, args.max_buffer_s)
            seek_marks: dict = {}
            seek_stop = asyncio.Event()
            t_seek = time.monotonic()
            result["seek_request_monotonic"] = t_seek
            seek_reader = asyncio.create_task(read_stream(client, url, {"Range": f"bytes={seek_at}-"}, seek,
                                                          seek_marks, seek_stop))
            try:
                await run_phase(seek, args.seek_play_s, args.seek_play_s * 4 + 60, lambda: True)
            except Exception as error:  # noqa: BLE001 - recorded in the result
                result["errors"].append(f"phase2:{type(error).__name__}")
            seek_stop.set()
            try:
                await asyncio.wait_for(seek_reader, 10)
            except Exception as error:  # noqa: BLE001 - recorded in the result
                result["errors"].append(f"seek-reader:{type(error).__name__}")
            result["seek"] = {
                "status": seek_marks.get("status"),
                "ttfb_s": round(seek_marks["first_byte"] - t_seek, 3) if "first_byte" in seek_marks else None,
                **{k: v for k, v in seek.summary(t_seek).items() if k != "time_to_full_buffer_s"},
                "resume_s": seek.summary(t_seek)["time_to_start_s"],
            }
    result["t_end_monotonic"] = time.monotonic()
    Path(args.out).write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps({"target": args.target_id, "errors": result["errors"],
                      "ttfb_s": result["start"]["ttfb_s"], "stalls": result["start"]["stalls"]}))


if __name__ == "__main__":
    asyncio.run(main())
