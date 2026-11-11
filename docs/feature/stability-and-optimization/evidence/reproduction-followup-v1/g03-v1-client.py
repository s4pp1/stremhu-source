"""G03 v1 client: runs one (repetition, profile) batch of cells and writes raw per-request rows.
Timing covers request start -> last raw body byte; raw bodies are kept and decoded/verified only after the cell, so
client-side decompression is measured separately and never inside the timed window. Server CPU/memory come from the
server's own /__stats endpoint, fetched directly (not through the shaper) before and after each cell.
argv: config.json output.json"""
import asyncio
import hashlib
import json
import sys
import time
import zlib

import httpx

cfg = json.load(open(sys.argv[1]))
SMOKE = cfg.get('smoke', False)


async def one(client, url):
    t0 = time.perf_counter()
    async with client.stream('GET', url, headers={'Accept-Encoding': 'gzip'}) as r:
        th = time.perf_counter() - t0
        raw, ttfb = bytearray(), None
        async for chunk in r.aiter_raw():
            if ttfb is None:
                ttfb = time.perf_counter() - t0
            raw += chunk
        total = time.perf_counter() - t0
    return dict(status=r.status_code, encoding=r.headers.get('content-encoding'), vary=r.headers.get('vary'),
                ctype=r.headers.get('content-type'), headers_ms=th * 1000, ttfb_ms=(ttfb if ttfb is not None else total) * 1000,
                total_ms=total * 1000), bytes(raw)


async def stats(direct):
    r = await direct.get(cfg['stats_url'])
    return r.json()


async def run_cell(direct, cell):
    url = f"{cfg['base_url']}/{cell['variant_path']}/{cell['payload']}"
    mode, n, warm = cell['mode'], cell['n'], cfg['warmup']
    rows, bodies = [], []
    if mode == 'fresh':
        async def fresh_one():
            async with httpx.AsyncClient(timeout=120) as c:
                return await one(c, url)
        for _ in range(warm):
            await fresh_one()
        s0 = await stats(direct)
        for _ in range(n):
            row, body = await fresh_one()
            rows.append(row)
            bodies.append(body)
        s1 = await stats(direct)
    else:
        conc = int(mode[1:])
        limits = httpx.Limits(max_connections=conc, max_keepalive_connections=conc)
        async with httpx.AsyncClient(timeout=120, limits=limits) as c:
            await asyncio.gather(*[one(c, url) for _ in range(conc)])
            for _ in range(warm):
                await one(c, url)
            s0 = await stats(direct)
            left = [n]

            async def worker():
                while left[0] > 0:
                    left[0] -= 1
                    row, body = await one(c, url)
                    rows.append(row)
                    bodies.append(body)
            t0 = time.perf_counter()
            await asyncio.gather(*[worker() for _ in range(conc)])
            wall = time.perf_counter() - t0
            s1 = await stats(direct)
    for row, body in zip(rows, bodies):
        row['wire_bytes'] = len(body)
        td = time.perf_counter()
        decoded = zlib.decompress(body, 31) if row['encoding'] == 'gzip' else body
        row['decode_ms'] = (time.perf_counter() - td) * 1000
        row['decoded_bytes'] = len(decoded)
        row['decoded_sha256'] = hashlib.sha256(decoded).hexdigest()
    out = dict(cell, rows=rows, server_before=s0, server_after=s1, server_cpu_ms=(s1['cpu_s'] - s0['cpu_s']) * 1000,
               same_server_pid=s0['pid'] == s1['pid'])
    if mode != 'fresh':
        out['wall_s'] = wall
    return out


async def main():
    results = []
    async with httpx.AsyncClient(timeout=30) as direct:
        start = await stats(direct)
        for cell in cfg['cells']:
            results.append(await run_cell(direct, cell))
            print(cell['payload'], cell['variant'], cell['mode'], 'done', flush=True)
        end = await stats(direct)
    json.dump(dict(profile=cfg['profile'], repetition=cfg['repetition'], smoke=SMOKE, server_start=start, server_end=end, cells=results),
              open(sys.argv[2], 'w'))

asyncio.run(main())
