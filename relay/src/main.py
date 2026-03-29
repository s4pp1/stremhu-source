from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from config import config
from fastapi import FastAPI
from libtorrent_client.background_tasks import alert_loop, resume_save_loop
from libtorrent_client.dependencies import get_libtorrent_client_service
from monitoring.router import router as monitoring_router
from setting.router import router as setting_router
from stream.router import router as stream_router
from torrents.router import router as torrents_router


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health HTTP" not in record.getMessage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("RELAY_AUTO_START") == "true":
        logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir.parent / "openapi"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "openapi.json").open("w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)

    # Könyvtárstruktúra biztosítása
    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    config.resume_data_dir.mkdir(parents=True, exist_ok=True)

    # Háttérfeladatok indítása
    alert_task = asyncio.create_task(alert_loop())
    save_task = asyncio.create_task(resume_save_loop())

    yield

    save_task.cancel()
    alert_task.cancel()

    libtorrent_client_service = get_libtorrent_client_service()
    libtorrent_client_service.trigger_save_resume_data()

    await asyncio.sleep(1)
    libtorrent_client_service.process_alerts()


app = FastAPI(
    title="StremHU Relay",
    lifespan=lifespan,
)


app.include_router(monitoring_router)
app.include_router(setting_router)
app.include_router(torrents_router)
app.include_router(stream_router)
