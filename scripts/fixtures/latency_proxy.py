"""H3 (stream-performance): TCP proxy that adds a fixed one-way latency in both directions.

Models a remote viewer (e.g. over a VPN/Tailscale link) between the player emulator and the
product, without `tc netem` or NET_ADMIN. Each direction is a pipelined FIFO: a chunk read at
time t is written at t + delay, so the delay is paid once per round trip, not per chunk.

Usage (own container on the internal measurement network):
  python latency_proxy.py --listen 0.0.0.0:7070 --target <app address>:7070 --one-way-ms 10
Prints one ready line; runs until SIGTERM. Carries opaque bytes (TLS stays end-to-end).
"""

import argparse
import asyncio
import contextlib
import json
import signal


async def pump(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, delay: float) -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[float, bytes]] = asyncio.Queue()

    async def sender() -> None:
        while True:
            due, chunk = await queue.get()
            if not chunk:
                break
            wait = due - loop.time()
            if wait > 0:
                await asyncio.sleep(wait)
            writer.write(chunk)
            await writer.drain()

    task = asyncio.create_task(sender())
    try:
        while True:
            chunk = await reader.read(65536)
            queue.put_nowait((loop.time() + delay, chunk))
            if not chunk:
                break
        await task
    except (ConnectionError, asyncio.CancelledError):
        task.cancel()
    finally:
        with contextlib.suppress(Exception):  # best effort close of a proxied socket
            writer.close()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--one-way-ms", type=float, required=True)
    args = parser.parse_args()
    listen_host, listen_port = args.listen.rsplit(":", 1)
    target_host, target_port = args.target.rsplit(":", 1)
    delay = args.one_way_ms / 1000.0

    async def handle(client_reader, client_writer):
        try:
            upstream_reader, upstream_writer = await asyncio.open_connection(target_host, int(target_port))
        except OSError:
            client_writer.close()
            return
        await asyncio.gather(pump(client_reader, upstream_writer, delay), pump(upstream_reader, client_writer, delay),
                             return_exceptions=True)

    server = await asyncio.start_server(handle, listen_host, int(listen_port))
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    print(json.dumps({"ready": True, "one_way_ms": args.one_way_ms}), flush=True)
    await stop.wait()
    server.close()
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
