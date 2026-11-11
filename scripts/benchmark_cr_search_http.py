"""Real Stremio/provider/repository HTTP path with synthetic cached torrents.

The tracker/metadata transport and native download-status lookup are fixed
stubs. File-DB reads, source mapping, filtering/sorting, token construction,
serialization, auth and cache/singleflight are real. No native media payload is
downloaded. A distinct smoke validates wiring before a registered measurement.
"""

import asyncio
import datetime
import hashlib
import json
import resource
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated

import httpx
import libtorrent
from fastapi import Depends
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.common import async_utils
from app.common.database import get_db
from app.main import app
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.preferences.dependencies import create_preferences_service
from app.modules.roles.models import RoleModel
from app.modules.stremio import service as streams
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.torrent_files import models as torrent_models
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_files.repository import TorrentFilesRepository
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.torrent_source_provider.service import TorrentSourceProviderService
from app.modules.torrent_streams.service import TorrentStreamsService
from app.modules.users.dependencies import get_users_service
from app.modules.users.models import UserModel

SMOKE = '--fixture-smoke' in sys.argv
SAMPLES = 4 if SMOKE else 100


async def drain_background_tasks():
    close = getattr(async_utils, 'drain_background_tasks', None)
    if close is not None:
        await close()
    else:
        # Same old background registry, without assuming the new close API.
        pending = getattr(async_utils, '_background_tasks', set())
        while pending:
            await asyncio.gather(*tuple(pending), return_exceptions=True)
            # gather(done tasks) may finish synchronously. Let the registry
            # discard callbacks run before testing it again.
            await asyncio.sleep(0)


def invalidate_results():
    invalidate = getattr(streams, 'invalidate_stream_cache', None)
    if invalidate is not None:
        invalidate()


def percentile(values, fraction):
    return sorted(values)[int((len(values)-1)*fraction)]


def memory():
    stat = dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
    return dict(anon_bytes=int(stat['anon']),file_bytes=int(stat['file']),current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()),peak_bytes=int(Path('/sys/fs/cgroup/memory.peak').read_text()),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


async def main():
    rows, cold = [], []
    attempted_external = 0
    original_send = httpx.AsyncClient.send

    async def offline_send(client, request, *args, **kwargs):
        nonlocal attempted_external
        if request.url.host != 'fixture.invalid':
            attempted_external += 1
            raise RuntimeError('Offline search fixture blocked external HTTP')
        return await original_send(client, request, *args, **kwargs)

    httpx.AsyncClient.send = offline_send
    with tempfile.TemporaryDirectory() as directory:
        for count in ([20] if SMOKE else [20, 100]):
            engine = create_engine(f"sqlite:///{Path(directory)/str(count)}.db", connect_args={'check_same_thread':False}, hide_parameters=True)
            database.Base.metadata.create_all(engine)
            database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
            accounts, users = [], []
            now = datetime.datetime.now()
            with Session(engine, expire_on_commit=False) as db:
                role = RoleModel(id='user',name='Synthetic')
                db.add(role)
                for index in range(2):
                    definition = IndexerDefinitionModel(id=f'fixture-{index}',name=f'Synthetic {index}',url='https://fixture.invalid',details_path='/details/{torrent_id}')
                    account = IndexerAccountModel(indexer_id=definition.id,username='synthetic',password='synthetic')
                    account.indexer_definition = definition
                    db.add_all([definition,account])
                    accounts.append(account)
                    user = UserModel(id=f'fixture-user-{index}',username=f'synthetic-{index}',torrent_seed=25 if index else None)
                    user.role = role
                    user.preference_definitions, user.attribute_exclusions = [], []
                    db.add(user)
                    users.append(user)
                db.flush()
                records = []
                for index in range(count):
                    encoded = libtorrent.bencode({b'info':{b'name':f'Fixture.Movie.{index:04d}.2024.1080p.mkv'.encode(),b'length':104857600,b'piece length':1048576,b'pieces':bytes(2000)}})
                    records.append(dict(indexer_id=accounts[index%2].indexer_id,torrent_id=str(index),info_hash=str(libtorrent.torrent_info(encoded).info_hash()),torrent_bytes=encoded,last_used_at=now,created_at=now))
                db.execute(insert(torrent_models.TorrentFileModel.__table__), records)
                db.commit()

            class Metadata:
                async def get_torrents_by_imdb_id(self, imdb_id):
                    await asyncio.sleep(.001)
                    return [IndexerTorrent(indexer_account=accounts[index%2],torrent_id=str(index),download_url='https://fixture.invalid/download',imdb_id=imdb_id,seeders=20+index%11,media_attributes=[]) for index in range(count)], []

            class Resolver:
                async def get_alternate_imdb_ids(self, *args, **kwargs):
                    return []

                async def get_title_by_imdb(self, *args, **kwargs):
                    raise RuntimeError('Unexpected fallback: the fixture must yield playable files')

            settings = SimpleNamespace(get_app_url=lambda:'https://fixture.invalid')
            # Upstream asks for the whole inventory; the fork uses targeted
            # file status. Both see the same fixed empty native inventory.
            inventory = SimpleNamespace(_relay_service=None,get_torrents=lambda:[],is_file_downloaded=lambda **kwargs:False)
            user_lookup = SimpleNamespace(find_by_api_key=lambda key:next((user for user in users if user.api_key==key),None),find_by_id=lambda key:next((user for user in users if user.id==key),None))

            def service(db: Annotated[Session, Depends(get_db, scope='function')]):
                provider = TorrentSourceProviderService(Metadata(),TorrentFilesService(TorrentFilesRepository(db)),IsolatedTorrentFilesService())
                search = TorrentStreamsService(db,provider,inventory,settings,create_preferences_service(db))
                result = streams.StremioService(search,settings)
                result._tvdb_resolver = Resolver()
                return result

            app.dependency_overrides[get_stremio_service] = service
            app.dependency_overrides[get_auth_service] = lambda:AuthService(user_lookup)
            app.dependency_overrides[get_users_service] = lambda:user_lookup
            statements = 0

            def sql(*args):
                nonlocal statements
                statements += 1

            event.listen(engine,'before_cursor_execute',sql)
            metadata_cache = getattr(torrent_models, '_TORRENT_INFO_CACHE', None)
            if metadata_cache is not None:
                metadata_cache.clear()
            invalidate_results()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://fixture.invalid') as client:
                async def request(index, imdb):
                    user = users[index%2]
                    began = time.perf_counter_ns()
                    response = await client.get(f'/api/{user.api_key}/stremio/stream/movie/{imdb}.json')
                    milliseconds = (time.perf_counter_ns()-began)/1e6
                    if response.status_code != 200:
                        raise RuntimeError(f'Synthetic search status {response.status_code}')
                    body = response.json()
                    expected = count if index%2==0 else sum(20+number%11>25 for number in range(count))
                    if len(body['streams']) != expected:
                        raise RuntimeError('Synthetic search result count mismatch')

                    def normalize(value):
                        if isinstance(value,dict):
                            output = {}
                            for key,item in value.items():
                                if key=='url':
                                    if not item.startswith(f'https://fixture.invalid/api/{user.api_key}/'):
                                        raise RuntimeError('Search URL crossed the synthetic user boundary')
                                    output[key]='TEST_BASE_URL/STREMHU_API_KEY/opaque-playback'
                                else:
                                    output[key]=normalize(item)
                            return output
                        if isinstance(value,list):
                            return [normalize(item) for item in value]
                        return value

                    digest = hashlib.sha256(json.dumps(normalize(body),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                    return milliseconds,digest,expected

                for user_index in [0,1]:
                    began = time.perf_counter()
                    _,digest,total = await request(user_index,'tt1000001')
                    await drain_background_tasks()
                    cold.append(dict(count=count,user=user_index,wall_seconds=time.perf_counter()-began,result_count=total,payload_hash=digest))
                for kind in ['same-result-key','unique-result-key-warm-metadata']:
                    for concurrency in ([1] if SMOKE else [1,4,8]):
                        invalidate_results()
                        for user_index in [0,1]:
                            await request(user_index,'tt1000001')
                        await drain_background_tasks()
                        semaphore = asyncio.Semaphore(concurrency)
                        sql_before,cpu_before = statements,time.process_time()

                        async def measured(index):
                            async with semaphore:
                                return await request(index,'tt1000001' if kind=='same-result-key' else f'tt{2000000+index}')

                        values = await asyncio.gather(*(measured(index) for index in range(SAMPLES)))
                        await drain_background_tasks()
                        latencies = [value[0] for value in values]
                        rows.append(dict(count=count,kind=kind,concurrency=concurrency,samples_ms=latencies,p50_ms=percentile(latencies,.5),p95_ms=percentile(latencies,.95),p99_ms=percentile(latencies,.99),cpu_seconds=time.process_time()-cpu_before,sql_statements=statements-sql_before,payload_hashes=sorted({value[1] for value in values}),result_counts=sorted({value[2] for value in values}),memory=memory()))
            await drain_background_tasks()
            if engine.pool.checkedout():
                raise RuntimeError('Synthetic search fixture left a checked-out connection')
            invalidate_results()
            engine.dispose()
    httpx.AsyncClient.send = original_send
    print(json.dumps(dict(fixture='cr17-search-http-fixture-smoke-v2' if SMOKE else 'cr17-search-http-file-db-v2',is_measurement=not SMOKE,rows=rows,cold=cold,external_http_attempts=attempted_external,scope='Real API/provider/fileDB/filter/sort/serialization; fixed1ms metadata stub, no native payload/real tracker. Cold initial request separate; cold-key cells retain the normal parsed-metadata cache. Two synthetic users and URL boundary assertions.')))


asyncio.run(main())
