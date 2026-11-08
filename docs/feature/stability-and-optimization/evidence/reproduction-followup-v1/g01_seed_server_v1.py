"""Private synthetic seed only; no tracker, credentials or outbound traffic."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from local_bt_seed import LocalSeed

seed = None
control = asyncio.Lock()


@asynccontextmanager
async def lifespan(app):
    try:
        yield
    finally:
        if seed is not None:
            await seed.close()


app = FastAPI(lifespan=lifespan)


class Torrent(BaseModel):
    info_hash: str = Field(pattern=r"^[0-9a-f]{40}$")
    piece_bytes: int = Field(ge=256 << 10, le=4 << 20)
    total_bytes: int = Field(ge=256 << 10, le=32 << 20)


class Case(BaseModel):
    torrents: list[Torrent] = Field(min_length=1, max_length=8)
    peers: int = Field(ge=1, le=100)
    block_delay_ms: int = Field(ge=0, le=50)


@app.get('/control/ready')
async def ready():
    return dict(ready=True)


@app.post('/control/case')
async def configure(case: Case):
    global seed
    async with control:
        if seed is not None:
            await seed.close()
        seed = LocalSeed({bytes.fromhex(item.info_hash): (item.piece_bytes,item.total_bytes) for item in case.torrents})
        seed.block_delay = case.block_delay_ms / 1000
        await seed.start(case.peers)
        return dict(ports=[port for _,port in seed.endpoints])


@app.get('/control/stats')
async def stats():
    if seed is None:
        return dict(active=False)
    return dict(active=True,handshakes=seed.handshakes,requests=seed.requests,bytes_sent=seed.bytes_sent,peak_connections=seed.peak_connections,active_connections=len(seed.writers),errors=seed.errors)


@app.post('/control/close')
async def close():
    global seed
    async with control:
        if seed is not None:
            await seed.close()
            seed = None
    return dict(closed=True)
