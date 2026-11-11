"""Repeated real lifespan closure, synthetic fileDB and no network.

OS-thread counts complement the separate full30min heap profiles. This finite
functional probe is not a shortened heap measurement or a production leak claim.
"""

import asyncio
import gc
import json
import tempfile
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main as application
from app.boot.settings import ensure_default_settings
from app.common import database
from app.config import config
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.relay.dependencies import get_relay_service


def threads():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('Threads:'):
            return int(line.split()[1])
    raise RuntimeError('Native OS thread counter unavailable')


async def main():
    async def offline_send(*args, **kwargs):
        raise RuntimeError('External HTTP prohibited in lifecycle thread fixture')

    httpx.AsyncClient.send = offline_send
    config.reverse_proxy_domain = 'fixture.invalid'
    application.restore_torrents = lambda: None
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory)/'fixture.db'}", connect_args={'check_same_thread': False}, hide_parameters=True)
        database.Base.metadata.create_all(engine)
        database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
        ensure_default_settings()
        initial_threads = threads()
        for cycle in range(20):
            async with application.lifespan(application.app):
                active_threads = threads()
                relay = get_relay_service()
                definitions = get_indexer_definitions_service()
            report = getattr(application.app.state, 'shutdown_result', None)
            rows.append(dict(cycle=cycle,active_threads=active_threads,closed_threads=threads(),tasks=len(asyncio.all_tasks()),checkouts=engine.pool.checkedout(),callbacks=len(relay.on_save_resume),shutdown_result=report))
            del relay, definitions, report
            gc.collect()
        # This explicit fixture-only final cleanup also works on the old
        # baseline; before rows above are observed before this intervention.
        if get_indexer_definitions_service.cache_info().currsize:
            await get_indexer_definitions_service().close_all()
        if get_relay_service.cache_info().currsize:
            native = getattr(get_relay_service(), '_libtorrent_session', None)
            if native is not None:
                native.set_alert_notify(lambda: None)
                native.pause()
            del native
        get_relay_service.cache_clear()
        get_indexer_definitions_service.cache_clear()
        gc.collect()
        final_checkouts = engine.pool.checkedout()
        engine.dispose()
    print(json.dumps(dict(fixture='cr17-repeated-lifespan-os-threads-v1',is_measurement=False,initial_threads=initial_threads,rows=rows,final_checkouts=final_checkouts,scope='20 real synthetic lifespans, no restored/native torrents or HTTP. OS-thread functional closure only; no heap or leak claim.')))


asyncio.run(main())
