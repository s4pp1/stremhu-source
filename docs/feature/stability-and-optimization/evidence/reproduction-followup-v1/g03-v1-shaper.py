"""G03 v1 link shaper: TCP relay emulating one shared bottleneck link.
Downstream (server->client) bytes are serialized at RATE bytes/s over a single shared link (all connections queue on it),
in segments of max(1460 B, 1 ms of link time), then delivered after a one-way propagation DELAY. Upstream gets DELAY only.
Order is preserved per connection; EOF propagates after queued data. argv: listen_port target_host target_port rate_Bps delay_ms"""
import asyncio
import sys
import time

LISTEN, HOST, PORT = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
RATE, DELAY = float(sys.argv[4]), float(sys.argv[5]) / 1000
SEG = max(1460, int(RATE / 1000))
link_free = 0.0


async def pump(reader, writer, shaped):
    global link_free
    q = asyncio.Queue()

    async def sender():
        while True:
            item = await q.get()
            if item is None:
                try:
                    writer.write_eof()
                except (OSError, RuntimeError):
                    pass
                return
            at, data = item
            d = at - time.monotonic()
            if d > 0:
                await asyncio.sleep(d)
            writer.write(data)
            await writer.drain()

    task = asyncio.create_task(sender())
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            now = time.monotonic()
            for i in range(0, len(data), SEG if shaped else len(data)):
                part = data[i:i + SEG] if shaped else data
                if shaped:
                    link_free = max(link_free, now) + len(part) / RATE
                    q.put_nowait((link_free + DELAY, part))
                else:
                    q.put_nowait((now + DELAY, part))
    except (ConnectionError, OSError):
        pass
    q.put_nowait(None)
    try:
        await task
    except (ConnectionError, OSError):
        pass


async def handle(cr, cw):
    try:
        sr, sw = await asyncio.open_connection(HOST, PORT)
    except OSError:
        cw.close()
        return
    await asyncio.gather(pump(cr, sw, False), pump(sr, cw, True), return_exceptions=True)
    for w in (sw, cw):
        w.close()


async def main():
    server = await asyncio.start_server(handle, '0.0.0.0', LISTEN, backlog=256)
    async with server:
        await server.serve_forever()

asyncio.run(main())
