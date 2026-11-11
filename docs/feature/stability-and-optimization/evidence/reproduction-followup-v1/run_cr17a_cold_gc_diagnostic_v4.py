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
fixture=r/'cr17a-cold-gc-diagnostic-fixture-v4.py'
s=(r/'cr17b-policy-fixture-v2.py').read_text()
s=s.replace('    rows, cold = [], []', """    rows, cold = [], []
    gc_events=[]
    gc_phase={'name':'initialization','started':0.0}
    def observe_gc(phase,info):
        if phase=='start':gc_phase['started']=time.perf_counter()
        else:gc_events.append(dict(phase=gc_phase['name'],generation=info['generation'],seconds=time.perf_counter()-gc_phase['started'],collected=info['collected'],uncollectable=info['uncollectable']))
    gc.callbacks.append(observe_gc)""")
s=s.replace('                    cold_sql = statements', "                    gc_phase['name']='cold-'+str(user_index)\n                    cold_sql = statements")
needle='                if PROFILE:\n                    output=Path'
assert s.count(needle)==1
injection="""                if PROFILE:
                    gc.callbacks.remove(observe_gc)
                    print(json.dumps(dict(fixture='cr17a-cold-GC-diagnostic-v4',is_measurement=False,cold=cold,gc_events=gc_events,default_gc_enabled=gc.isenabled(),scope='Observe default GC only, no forced collect/threshold changes. Actual original two cold calls,not timing acceptance or a heap run.')))
                    event.remove(engine,'before_cursor_execute',sql)
                    app.dependency_overrides.clear()
                    engine.dispose()
                    httpx.AsyncClient.send=original_send
                    return
                if PROFILE:
                    output=Path"""
assert not fixture.exists()
fixture.write_text(s.replace(needle,injection),encoding='utf-8')
protocol=dict(id='cr17a-cold-GC-diagnostic-v4',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='V3 colduser0+29.5ms/user1-32.5ms distribution: investigate cause before any next change. Default GC enabled,callbacks observe generation/time per actual user call.5paired freshprocesses/source,2CPU6,7/1GiB,networknone,frozen sources unchanged. NO acceptance,budget relaxation or production GC change.',fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
(e/'cr17a-cold-GC-diagnostic-v4-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
env=os.environ.copy()
env.update(HOST_IP=(repo/'.git/cr-test-host').read_text().strip(),SESSION_SECRET=secrets.token_urlsafe(48),STREMHU_LOAD_DOTENV='false',PYTHONDONTWRITEBYTECODE='1')
for i in range(5):
    for label in (['before','after'] if i%2==0 else ['after','before']):
        source=r/('cr17a-after-v7-source' if label=='before' else 'cr17a-drain-fix-v2-source')/'server/app'
        stem=f'cr17a-cold-GC-diagnostic-v4-{label}-{i}'
        cmd=['docker','--context','desktop-linux','run','--rm','--name',stem.lower()+'-obva7te6','--network','none','--read-only','--cpus','2','--cpuset-cpus','6,7','--memory','1g','--tmpfs','/tmp','--tmpfs','/app/data','--tmpfs','/fixture-output']
        for key in ['HOST_IP','SESSION_SECRET','STREMHU_LOAD_DOTENV','PYTHONDONTWRITEBYTECODE']:cmd+=['--env',key]
        cmd+=['--env','PYTHONPATH=/app','--mount',f'type=bind,source={fixture},target=/fixture/probe.py,readonly','--mount',f'type=bind,source={source},target=/app/app,readonly','--entrypoint','python',image,'/fixture/probe.py','--heap-profile']
        result=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8')
        for suffix,value in [('stdout',result.stdout),('stderr',result.stderr)]: (e/(stem+'.'+suffix)).write_text(value,encoding='utf-8')
        if result.returncode:raise RuntimeError('ColdGC diagnostic failed;raw retained')
        d=json.loads(result.stdout)
        assert not d['is_measurement'] and d['default_gc_enabled'] and len(d['cold'])==2
        d.update(protocol=protocol['id'],label=label,repetition=i,image=image)
        (e/(stem+'.json')).write_text(json.dumps(d,indent=2),encoding='utf-8')
        print(label,i,dict(cold_ms=[row['wall_seconds']*1000 for row in d['cold']],gc2=[(row['phase'],row['seconds']*1000) for row in d['gc_events'] if row['generation']==2]),flush=True)
