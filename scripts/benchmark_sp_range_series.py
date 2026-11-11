"""H1 range-series client (stream-performance, GSP03): repeated Range requests on a warm torrent.

Runs in its own container on the internal measurement network, like
``benchmark_sp_playback.py``, against the product's real stream endpoint:

1. Warm-up (not a sample): one playback token reads the whole file with
   ``Range: bytes=0-``, so every piece is downloaded before the series.
2. After ``--settle-s``, a second, fresh playback token sends ``--requests``
   sequential bounded Range requests (``--read-bytes`` each, ``--gap-ms`` apart):
   request 1 starts at 0, request 2 is the tail probe, the rest are spread over the
   file (fixed golden-ratio sequence, 64 KiB aligned), as a player's start, tail
   probe and seeks. Every stream response carries ``Connection: close``, so every
   request opens a new connection, as players see it.

Per request: time to response headers and to the first body byte, from the request
start (connection setup included). Per series: p50/p95 (median / nearest rank) of
all requests, of the repeats (2..N) and the first request alone, plus the count of
non-206 responses and errors. The API key and the tokens are read from ``--targets``
(``sp_app_fixture.py --playbacks 2``) and never printed.
"""

import argparse
import asyncio
import json
import math
import time
from pathlib import Path

import httpx

ALIGN = 65536
GOLDEN = (math.sqrt(5) - 1) / 2


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]


def rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def offsets(size: int, count: int, read_bytes: int) -> list[int]:
    """Request 1 at 0, request 2 the tail probe, the rest spread over the file."""
    last = max(0, size - read_bytes)
    result = [0, last]
    for index in range(1, max(0, count - 2) + 1):
        fraction = (index * GOLDEN) % 1.0
        result.append(min(last, int(fraction * last) // ALIGN * ALIGN))
    return result[:count]


async def timed_get(client: httpx.AsyncClient, url: str, start: int, end: int | None) -> dict:
    header = f"bytes={start}-" if end is None else f"bytes={start}-{end}"
    mark: dict = {"start": start}
    t0 = time.monotonic()
    async with client.stream("GET", url, headers={"Range": header}) as response:
        mark["headers_s"] = time.monotonic() - t0
        mark["status"] = response.status_code
        mark["content_range"] = response.headers.get("content-range")
        total = 0
        async for chunk in response.aiter_raw(65536):
            if "ttfb_s" not in mark:
                mark["ttfb_s"] = time.monotonic() - t0
            total += len(chunk)
    mark["total_s"] = time.monotonic() - t0
    mark["bytes"] = total
    return mark


async def run(client: httpx.AsyncClient, warm_url: str, series_url: str, requests: int, read_bytes: int,
              gap_s: float, settle_s: float) -> dict:
    result: dict = {"mode": "range-series", "errors": []}
    t_warm = time.monotonic()
    try:
        warm = await timed_get(client, warm_url, 0, None)
    except Exception as error:  # noqa: BLE001 - recorded; the series cannot run without a size
        result["errors"].append(f"warm:{type(error).__name__}")
        result["series"] = {"n": 0, "ok": 0, "non_206": 0, "error_count": len(result["errors"])}
        result["bytes_received_total"] = 0
        return result
    size = int(warm["content_range"].rsplit("/", 1)[1]) if warm.get("content_range") else None
    result["file_size"] = size
    result["warm"] = {"status": warm["status"], "bytes": warm["bytes"], "seconds": round(time.monotonic() - t_warm, 3),
                      "complete": size is not None and warm["bytes"] == size}
    if not size or warm["status"] != 206 or warm["bytes"] != size:
        result["errors"].append("warm:incomplete")
    await asyncio.sleep(settle_s)
    marks = []
    for index, start in enumerate(offsets(size or 0, requests, read_bytes)):
        if index:
            await asyncio.sleep(gap_s)
        end = min(start + read_bytes, size or start + read_bytes) - 1
        try:
            mark = await timed_get(client, series_url, start, end)
        except Exception as error:  # noqa: BLE001 - recorded; counted in error_count
            result["errors"].append(f"series{index}:{type(error).__name__}")
            mark = {"start": start, "error": type(error).__name__}
        if mark.get("status") is not None and (mark["status"] != 206 or mark["bytes"] != end - start + 1):
            mark["unexpected"] = True
        marks.append(mark)
    ttfb = [m["ttfb_s"] for m in marks if "ttfb_s" in m]
    headers = [m["headers_s"] for m in marks if "headers_s" in m]
    repeats = [m["ttfb_s"] for m in marks[1:] if "ttfb_s" in m]
    result["series"] = {
        "n": len(marks),
        "ok": sum(1 for m in marks if m.get("status") == 206 and not m.get("unexpected")),
        "non_206": sum(1 for m in marks if m.get("status") != 206),
        "error_count": len(result["errors"]),
        "first_ttfb_s": rounded(marks[0].get("ttfb_s")) if marks else None,
        "ttfb_s_p50": rounded(median(ttfb)), "ttfb_s_p95": rounded(p95(ttfb)),
        "repeat_ttfb_s_p50": rounded(median(repeats)), "repeat_ttfb_s_p95": rounded(p95(repeats)),
        "headers_s_p50": rounded(median(headers)), "headers_s_p95": rounded(p95(headers)),
        "requests": [{k: rounded(v) if k.endswith("_s") else v for k, v in m.items() if k != "content_range"}
                     for m in marks],
    }
    result["bytes_received_total"] = warm["bytes"] + sum(m.get("bytes", 0) for m in marks)
    return result


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--read-bytes", type=int, default=1 << 20)
    parser.add_argument("--gap-ms", type=float, default=200.0)
    parser.add_argument("--settle-s", type=float, default=2.0)
    parser.add_argument("--warm-playback", type=int, default=0)
    parser.add_argument("--series-playback", type=int, default=1)
    args = parser.parse_args()

    data = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    target = next(t for t in data["targets"] if t["id"] == args.target_id)
    playbacks = target["playbacks"]

    def url(index: int) -> str:
        return f"{args.base}/api/{data['api_key']}/stream/{playbacks[index]['token']}"

    timeout = httpx.Timeout(120.0, connect=30.0)
    t_start = time.monotonic()
    async with httpx.AsyncClient(verify=False, trust_env=False, timeout=timeout, http2=False) as client:
        result = await run(client, url(args.warm_playback), url(args.series_playback), args.requests,
                           args.read_bytes, args.gap_ms / 1000.0, args.settle_s)
    result = {"target": args.target_id, **result, "t_start_monotonic": t_start, "t_end_monotonic": time.monotonic()}
    Path(args.out).write_text(json.dumps(result), encoding="utf-8")
    series = result["series"]
    print(json.dumps({"target": args.target_id, "errors": result["errors"], "ttfb_s_p50": series.get("ttfb_s_p50"),
                      "first_ttfb_s": series.get("first_ttfb_s"), "non_206": series.get("non_206")}))


if __name__ == "__main__":
    asyncio.run(main())
