"""Real Stremio/provider/repository HTTP path with synthetic cached torrents.

The tracker/metadata transport and native download-status lookup are fixed
stubs. File-DB reads, source mapping, filtering/sorting, token construction,
serialization, auth and cache/singleflight are real. No native media payload is
downloaded. A distinct smoke validates wiring before a registered measurement.
"""

import asyncio
import gc
import tracemalloc
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
from app.modules.preferences.models import PreferenceModel
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.preference_definitions.models import PreferenceDefinitionModel, PreferenceDefinitionAttributeModel
from app.modules.user_preference_definitions.models import UserPreferenceDefinitionModel
from app.modules.attribute_exclusions.models import AttributeExclusionModel

SMOKE = '--fixture-smoke' in sys.argv
PROFILE_SMOKE = '--profile-smoke' in sys.argv
PROFILE = '--heap-profile' in sys.argv or PROFILE_SMOKE
if SMOKE and PROFILE:raise RuntimeError('Distinct wiring/profile modes required')
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
    golden = {}
    profile_summary = None
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
        for count in ([100] if PROFILE else [20] if SMOKE else [20, 100]):
            engine = create_engine(f"sqlite:///{Path(directory)/str(count)}.db", connect_args={'check_same_thread':False}, hide_parameters=True)
            database.Base.metadata.create_all(engine)
            database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
            accounts, users = [], []
            now = datetime.datetime.now()
            with Session(engine, expire_on_commit=False) as db:
                role = RoleModel(id='user',name='Synthetic')
                db.add(role)
                fixture_attributes = {}
                category_ids = {'a':'video-codec','b':'source'}
                for category in ['a','b']:
                    preference = PreferenceModel(id=category_ids[category],name=f'Synthetic {category}',description='Synthetic policy',multiple=category=='b',strict_exclusion=category=='b')
                    db.add(preference)
                    for position in range(3):
                        attribute = MediaAttributeModel(id=f'fixture-{category}-{position}',preference_id=preference.id,name=f'Synthetic {category}{position}')
                        db.add(attribute)
                        fixture_attributes[category,position] = attribute
                db.flush()
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
                    for category in ['a','b']:
                        definition = PreferenceDefinitionModel(id=f'fixture-definition-{index}-{category}',preference_id=category_ids[category])
                        db.add(definition)
                        db.flush()
                        positions = [0,1,2] if (index==0)==(category=='a') else [2,1,0]
                        for order,position in enumerate(positions):
                            db.add(PreferenceDefinitionAttributeModel(definition_id=definition.id,attribute_id=f'fixture-{category}-{position}',order=order))
                        category_order = (0 if category=='a' else 1) if index==0 else (1 if category=='a' else 0)
                        db.add(UserPreferenceDefinitionModel(user_id=user.id,definition_id=definition.id,order=category_order))
                    if index==1:
                        db.add(AttributeExclusionModel(user_id=user.id,attribute_id='fixture-a-0'))
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
                    return [IndexerTorrent(indexer_account=accounts[index%2],torrent_id=str(index),download_url='https://fixture.invalid/download',imdb_id=imdb_id,seeders=20+index%11,media_attributes=[fixture_attributes['a',index%3],fixture_attributes['b',index%3]]) for index in range(count)], []

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
            statements = 0
            touch_updates = 0

            def sql(*args):
                nonlocal statements, touch_updates
                statements += 1
                if args[2].lower().lstrip().startswith("update torrent_files"): touch_updates += 1

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
                    expected = count if index%2==0 else sum(20+number%11>25 and number%3!=0 for number in range(count))
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
                    key=(count,index%2)
                    if key in golden and golden[key]!=digest:raise RuntimeError('Ranked policy golden payload/order drift')
                    golden[key]=digest
                    return milliseconds,digest,expected

                if PROFILE:tracemalloc.start()
                for user_index in [0,1]:
                    cold_sql = statements
                    began = time.perf_counter()
                    _,digest,total = await request(user_index,'tt1000001')
                    await drain_background_tasks()
                    cold.append(dict(sql_statements=statements-cold_sql,count=count,user=user_index,wall_seconds=time.perf_counter()-began,result_count=total,payload_hash=digest))
                if PROFILE:
                    from app.modules.stremio.cache import stream_cache_state
                    clock=[0.0]
                    stream_cache_state._clock=lambda:clock[0]
                    original_get=stream_cache_state.get
                    original_put=stream_cache_state.put_if_revision
                    observations={'hit':0,'miss':0,'put':0,'provider':0}
                    def observed_get(key):
                        value=original_get(key)
                        observations['miss' if value is None else 'hit']+=1
                        return value
                    def observed_put(*args,**kwargs):
                        result=original_put(*args,**kwargs)
                        if result:observations['put']+=1
                        return result
                    stream_cache_state.get=observed_get
                    stream_cache_state.put_if_revision=observed_put
                    original_provider=TorrentSourceProviderService._find_by_imdb_id
                    async def observed_provider(self,*args,**kwargs):
                        observations['provider']+=1
                        return await original_provider(self,*args,**kwargs)
                    TorrentSourceProviderService._find_by_imdb_id=observed_provider
                    diagnostics=[]
                    for state in ['warm','expired','crossing']:
                        for concurrency in [1,4,8]:
                            invalidate_results()
                            clock[0]=0.0
                            for user_index in [0,1]:await request(user_index,'tt1000001')
                            await drain_background_tasks()
                            clock[0]=0.0 if state=='warm' else 61.0 if state=='expired' else 59.0
                            observations.update(hit=0,miss=0,put=0,provider=0)
                            sql_before=statements
                            touch_before=touch_updates
                            gate=asyncio.Semaphore(concurrency)
                            async def measured(index):
                                async with gate:
                                    if state=='crossing' and index>=20:clock[0]=61.0
                                    return await request(index,'tt1000001')
                            values=await asyncio.gather(*(measured(index) for index in range(100)))
                            await drain_background_tasks()
                            count_sql=statements-sql_before
                            assert observations['hit']+observations['miss']==100
                            assert observations['put']==(0 if state=='warm' else 2)
                            touch_count=touch_updates-touch_before
                            residual=count_sql-(100+7*observations['put']+2*observations['provider']+touch_count)
                            diagnostics.append(dict(state=state,concurrency=concurrency,sql_statements=count_sql,stage_formula_residual=residual,touch_updates=touch_count,cache_observations=observations.copy(),payload_hashes=sorted({value[1] for value in values}),result_counts=sorted({value[2] for value in values})))
                    assert attempted_external==0
                    print(json.dumps(dict(fixture='cr17a-cache-SQL-state-diagnostic-v5',is_measurement=False,rows=diagnostics,scope='Actual API-key auth/provider/fileDB/filter/sort. Only stream-cache clock is fixture-controlled: TTL60 retained,other clocks untouched. SQL diagnostic counts actual cache refills and shared provider factory starts separately; also stale-touch UPDATE. Candidate accounting100auth+7per-user-refill+2per-provider-execution+touch; residual recorded,not assumed. Semantic diagnostic,not performance measurement or production cachepolicy change.')))
                    event.remove(engine,'before_cursor_execute',sql)
                    app.dependency_overrides.clear()
                    engine.dispose()
                    httpx.AsyncClient.send=original_send
                    return
                if PROFILE:
                    output=Path('/fixture-output/policy-heap-rows.jsonl')
                    if not output.parent.is_dir():raise RuntimeError('Owned profile output required')
                    duration=60 if PROFILE_SMOKE else 1800
                    interval=20 if PROFILE_SMOKE else 30
                    for user_index in [0,1]:await request(user_index,'tt1000001')
                    await drain_background_tasks()
                    gc.collect()
                    started=time.monotonic();cycle=0
                    with output.open('x',encoding='utf-8') as stream:
                        while time.monotonic()-started<duration:
                            kind='same-result-key' if cycle%2==0 else 'unique-result-key-warm-metadata'
                            concurrency=[1,4,8][cycle%3]
                            if kind=='same-result-key':
                                for user_index in [0,1]:await request(user_index,'tt1000001')
                                await drain_background_tasks()
                            gate=asyncio.Semaphore(concurrency)
                            sql_before,cpu_before=statements,time.process_time()
                            lag=[];done=asyncio.Event()
                            async def monitor():
                                due=asyncio.get_running_loop().time()+.01
                                while not done.is_set():
                                    await asyncio.sleep(max(0,due-asyncio.get_running_loop().time()))
                                    lag.append(max(0,asyncio.get_running_loop().time()-due)*1000)
                                    due=asyncio.get_running_loop().time()+.01
                            ticker=asyncio.create_task(monitor())
                            async def measured(index):
                                async with gate:
                                    return await request(index,'tt1000001' if kind=='same-result-key' else f'tt{3000000+cycle*1000+index}')
                            try:
                                values=await asyncio.gather(*(measured(index) for index in range(100)))
                                await drain_background_tasks()
                            finally:
                                done.set();await ticker
                            samples=[value[0] for value in values]
                            row=dict(cycle=cycle,count=count,kind=kind,concurrency=concurrency,samples_ms=samples,p50_ms=percentile(samples,.5),p95_ms=percentile(samples,.95),p99_ms=percentile(samples,.99),cpu_seconds=time.process_time()-cpu_before,sql_statements=statements-sql_before,payload_hashes=sorted({value[1] for value in values}),result_counts=sorted({value[2] for value in values}),loop_lag_samples_ms=lag,loop_lag_p99_ms=percentile(lag,.99),elapsed_seconds=time.monotonic()-started)
                            del values,ticker
                            await asyncio.sleep(0)
                            gc.collect()
                            row.update(heap_bytes_after_gc=tracemalloc.get_traced_memory()[0],memory=memory(),tasks_quiescent=len(asyncio.all_tasks()),pool_checked_out=engine.pool.checkedout(),background_tasks=len(getattr(async_utils,'_background_tasks',())))
                            if row['pool_checked_out'] or row['tasks_quiescent']!=1 or row['background_tasks']:raise RuntimeError('Policy heap fixture not quiescent')
                            stream.write(json.dumps(row)+'\n');stream.flush()
                            print(json.dumps(dict(cycle=cycle,elapsed_seconds=row['elapsed_seconds'],kind=kind,concurrency=concurrency,pool=row['pool_checked_out'],heap=row['heap_bytes_after_gc'])),file=sys.stderr,flush=True)
                            del row,samples,lag,done,gate
                            cycle+=1
                            remaining=min(started+cycle*interval,started+duration)-time.monotonic()
                            if remaining>0:await asyncio.sleep(remaining)
                    measured_seconds=time.monotonic()-started
                    tracemalloc.stop()
                    rows=[json.loads(line) for line in output.read_text().splitlines()]
                    profile_summary=dict(measured_seconds=measured_seconds,required_seconds=None if PROFILE_SMOKE else 1800,required_cycles=3 if PROFILE_SMOKE else 60,profile_mode='smoke' if PROFILE_SMOKE else 'full',golden_policy_users=2)
                else:
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
    print(json.dumps(dict(fixture='cr17-policy-heap-smoke-v1' if PROFILE_SMOKE else 'cr17-policy-real-auth-ranked-heap-30min-v1' if PROFILE else 'cr17-policy-http-real-auth-smoke-v2' if SMOKE else 'cr17-policy-http-real-auth-ranked-v2',is_measurement=not SMOKE and not PROFILE_SMOKE,profile=profile_summary,rows=rows,cold=cold,external_http_attempts=attempted_external,scope='Real API/provider/fileDB/filter/sort/serialization; fixed1ms metadata stub, no native payload/real tracker. Cold initial request separate; real API-key/DB auth and two synthetic ranked preference/exclusion graphs. Normal parsed-metadata cache retained. No authentication stub.')))


asyncio.run(main())
