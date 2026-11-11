"""Synthetic app loaded by Hypercorn's real one-worker supervisor.

The controller sends Docker SIGTERM. Private fixture routes and a fileDB are
only reachable in a task-owned --internal Docker network. No tracker or real
credentials enter the process; the torrent has no announce URL or payload.
"""

import asyncio
import hashlib
import json
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import httpx
import libtorrent
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.responses import JSONResponse
from starlette.routing import Route

from app import main as application
from app.boot.settings import ensure_default_settings
from app.common import database
from app.common.async_utils import owned_to_thread
from app.config import config
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.relay.dependencies import get_relay_service
from app.modules.roles.models import RoleModel
from app.modules.settings.models import SettingModel
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrents.models import TorrentModel

SECONDS = int(os.environ['CR_RUNTIME_WORK_SECONDS'])
if SECONDS not in {4, 15, 32}:
    raise RuntimeError('Unregistered runtime fixture duration')
OUTPUT = Path('/fixture-output')
if not OUTPUT.is_dir():
    raise RuntimeError('Task-owned fixture output directory required')
entered, finished = threading.Event(), threading.Event()
outbound_attempts = 0
relay = None


async def offline_send(*args, **kwargs):
    global outbound_attempts
    outbound_attempts += 1
    raise RuntimeError('External HTTP prohibited by runtime fixture')


httpx.AsyncClient.send = offline_send
config.reverse_proxy_domain = 'fixture.invalid'
config.downloads_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine('sqlite:////tmp/runtime-fixture.db',connect_args={'check_same_thread':False},hide_parameters=True)
database.Base.metadata.create_all(engine)
database.SessionLocal = sessionmaker(bind=engine,autoflush=False)
ensure_default_settings()
encoded = libtorrent.bencode({b'info':{b'name':b'fixture.bin',b'length':16384,b'piece length':16384,b'pieces':hashlib.sha1(bytes(16384)).digest()}})
with Session(engine) as db:
    definition = IndexerDefinitionModel(id='ncore',name='Synthetic',url='https://fixture.invalid',details_path='/details')
    db.add(definition)
    db.flush()
    db.add(IndexerAccountModel(indexer_id='ncore',username='synthetic',password='synthetic'))
    db.flush()
    torrent = TorrentFileModel(indexer_id='ncore',torrent_id='fixture',torrent_bytes=encoded)
    db.add(torrent)
    db.flush()
    db.add(TorrentModel(info_hash=torrent.info_hash,indexer_id='ncore',torrent_id='fixture',is_persisted=True,full_download=False))
    db.execute(text('CREATE TABLE fixture_work (value INTEGER NOT NULL)'))
    db.execute(text('INSERT INTO fixture_work VALUES (0)'))
    db.commit()


def ready_state():
    with Session(engine) as db:
        roles = set(db.scalars(select(RoleModel.id)))
        settings = set(db.scalars(select(SettingModel.key)))
    return {'admin','user'}.issubset(roles) and {'system','relay'}.issubset(settings)


async def ready(request):
    initialized = await owned_to_thread(ready_state)
    restored = len(get_relay_service()._get_torrents()) == 1
    return JSONResponse({'ready':initialized and restored and not getattr(application.app.state,'stopping',True)})


def worker():
    try:
        # The Session is born, used, committed and closed on this one worker.
        with Session(engine) as db:
            db.execute(text('SELECT value FROM fixture_work')).scalar_one()
            entered.set()
            threading.Event().wait(SECONDS)
            db.execute(text('UPDATE fixture_work SET value=1'))
            db.commit()
    finally:
        finished.set()


async def start(request):
    global relay
    if relay is not None:
        return JSONResponse({'started':False},status_code=409)
    relay = get_relay_service()
    identity = 'e'*40
    relay._torrents[libtorrent.sha1_hash(bytes.fromhex(identity))] = SimpleNamespace(priority_manager=worker)
    relay.priority_update_queue.put_nowait(identity)
    active = await owned_to_thread(entered.wait,3)
    return JSONResponse({'started':active and not finished.is_set()},status_code=200 if active else 503)


def durable_state():
    with Session(engine) as db:
        torrent = db.scalars(select(TorrentModel)).one()
        counter = db.execute(text('SELECT value FROM fixture_work')).scalar_one()
        resume = torrent.resume_bytes
        info_hash = torrent.info_hash
    roundtrip = bool(resume) and str(libtorrent.read_resume_data(resume).info_hashes.v1) == info_hash
    return dict(counter=counter,native_resume_saved=bool(resume),native_resume_roundtrip=roundtrip,native_resume_bytes=len(resume or b''),native_resume_sha256=hashlib.sha256(resume).hexdigest() if resume else None)


app = application.app
app.router.routes.insert(0,Route('/fixture/ready',ready))
app.router.routes.insert(0,Route('/fixture/start',start,methods=['POST']))
original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def observed_lifespan(owner):
    try:
        async with original_lifespan(owner):
            yield
    finally:
        durable = await owned_to_thread(durable_state)
        result = dict(fixture='cr17-real-hypercorn-supervisor-sigterm-v1',is_measurement=False,worker_seconds=SECONDS,worker_finished=finished.is_set(),shutdown=getattr(owner.state,'shutdown_result',None),native_reference_released=relay is not None and not hasattr(relay,'_libtorrent_session'),pool_checked_out=engine.pool.checkedout(),outbound_http_attempts=outbound_attempts,**durable)
        (OUTPUT/'report.json').write_text(json.dumps(result),encoding='utf-8')


app.router.lifespan_context = observed_lifespan
