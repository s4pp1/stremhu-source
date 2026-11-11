"""Reproduce cache-state SQL variation without changing production clocks."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import secrets
import subprocess

r=Path(__file__).parent
repo=Path.cwd()
e=r/'evidence'
original=r/'cr17b-policy-fixture-v2.py'
fixture=r/'cr17a-sql-cache-fixture-v5.py'
text=original.read_text()
text=text.replace('            statements = 0','            statements = 0\n            touch_updates = 0')
text=text.replace('                nonlocal statements','                nonlocal statements, touch_updates')
text=text.replace('                statements += 1','                statements += 1\n                if args[2].lower().lstrip().startswith("update torrent_files"): touch_updates += 1')

needle='                if PROFILE:\n                    output=Path'
assert text.count(needle)==1 and not fixture.exists()
injection='''                if PROFILE:
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
                    output=Path'''
fixture.write_text(text.replace(needle,injection),encoding='utf-8')
image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
protocol=dict(id='cr17a-cache-SQL-state-diagnostic-v5',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Original V2 exact SQL invariant failed on baseline itself. Controlled real cache warm/expired/crossing states prove cause;no acceptance threshold change.9states x100requests/source,2frozenC sources. Own clock only,not timing.',fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),resources='2CPU8,9/1GiB,networknone,readonlysource,tmpfssyntheticDB. DifferentCPU from coldcontrol;not a timing dataset.')
(e/'cr17a-cache-SQL-state-diagnostic-v5-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
env=os.environ.copy()
env.update(HOST_IP=(repo/'.git/cr-test-host').read_text().strip(),SESSION_SECRET=secrets.token_urlsafe(48),STREMHU_LOAD_DOTENV='false',PYTHONDONTWRITEBYTECODE='1')
for label,folder in [('before','cr17a-after-v7-source'),('after','cr17a-drain-fix-v2-source')]:
    stem='cr17a-cache-SQL-state-diagnostic-v5-'+label
    cmd=['docker','--context','desktop-linux','run','--rm','--name',stem.lower()+'-obva7te6','--network','none','--read-only','--cpus','2','--cpuset-cpus','8,9','--memory','1g','--tmpfs','/tmp','--tmpfs','/app/data','--tmpfs','/fixture-output']
    for key in ['HOST_IP','SESSION_SECRET','STREMHU_LOAD_DOTENV','PYTHONDONTWRITEBYTECODE']:cmd+=['--env',key]
    cmd+=['--env','PYTHONPATH=/app','--mount',f'type=bind,source={fixture},target=/fixture/probe.py,readonly','--mount',f'type=bind,source={r/folder/"server/app"},target=/app/app,readonly','--entrypoint','python',image,'/fixture/probe.py','--heap-profile']
    result=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8')
    (e/(stem+'.stdout')).write_text(result.stdout,encoding='utf-8')
    (e/(stem+'.stderr')).write_text(result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('SQL-cache diagnostic failed;raw retained')
    d=json.loads(result.stdout)
    assert not d['is_measurement'] and len(d['rows'])==9
    d.update(protocol=protocol['id'],image=image,source=folder)
    (e/(stem+'.json')).write_text(json.dumps(d,indent=2),encoding='utf-8')
    print(label,'9real API/cache-state cases saved',flush=True)
