from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from config import config
from fastapi import FastAPI
from monitoring.router import router as monitoring_router
from torrents.router import router as torrents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir.parent / "openapi"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "openapi.json").open("w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
    yield


app = FastAPI(
    title="Torrent Engine",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(monitoring_router)
app.include_router(torrents_router)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=config.port,
    )
