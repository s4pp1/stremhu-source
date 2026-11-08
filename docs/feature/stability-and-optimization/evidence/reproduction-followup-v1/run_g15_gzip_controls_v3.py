from pathlib import Path
import datetime
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import time

r=Path(__file__).parent
repo=Path.cwd()
e=r/'evidence'
fixture=r/'g15-gzip-reference-fixture-v3'
assert not fixture.exists()
fixture.mkdir()
for source,target in [(r/'g15_gzip_probe_v3.py',fixture/'probe.py'),(repo/'scripts/fixtures/g15_http_server.py',fixture/'server.py'),(repo/'scripts/probe_cr_torrent_metadata_sizes.py',fixture/'metadata_sizes.py')]:shutil.copy2(source,target)
wire=json.loads((e/'g15-real-http-wiring-v1.json').read_text())
expected={row['kind']:row for row in wire['rows']}
(fixture/'expected.json').write_text(json.dumps(expected),encoding='utf-8')
images={'A':'s4pp1/stremhu-source@sha256:a3a2012893d689795f958ccec666fef6277f8677f24efebe9568cb44ec7a0621','B':'stremhu-source@sha256:6ca708d99b8698e6cf116a6183c283922ebd2e53940c366a93a421b4ca974a38','C':'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'}
protocol=dict(id='g15-gzip-reference-v3',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Independent G15 focused reproduction after original controlledOOM. Exact checkedC transport component and new narrowed workload; no application change. A/B/C execute identical narrowed workload,sequential androtated.',sampling='128MiBdecoded gzip: two unchanged5-run C cohorts then5rotatedABC,concurrency1/4/8 eachfreshprocess,100configured measuredrequests plus distinctcold+warmup. Failed/OOM cases are outcomes,not100actual completions or successful timing samples. Earlier64MiBchunked/full24cell failures retained. Invalid native body deliberately tests decoding envelope,not representative valid metadata. DefaultGC unchanged,no prodlimit selected.',resources='Client2CPU2,3/1GiB;privateHTTPserver1CPU4/512MiB;internalDocker network,no hostports/outbound/realcredentials;row artifacts on owned bind output;memory sampler bounded100recent snapshots plus permetric peak/count.',source_C='cr17a-drain-fix-v2-source,328Python checked604/64;actual download modules unchanged from Source7;provider retention is separate G15c/CR17 work',images=images,fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.iterdir()})
protocol['source_B_app_sha256']={p.relative_to(r/'baseline/server/app').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (r/'baseline/server/app').rglob('*.py') if '__pycache__' not in p.parts}
(e/'g15-gzip-reference-v3-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
def call(*args,**kwargs):return subprocess.run(['docker','--context','desktop-linux',*args],check=True,**kwargs)
context=json.loads(call('context','inspect','desktop-linux',capture_output=True,text=True).stdout)[0]
assert context['Endpoints']['docker']['Host'].startswith('npipe://')
for image in images.values():
    call('run','--rm','--network','none','--read-only','--cpus','1','--cpuset-cpus','2','--memory','128m','--entrypoint','python',image,'-c',"from pathlib import Path;assert not any(Path(p).exists() for p in ['/app/.env','/app/server/.env','/.env'])",capture_output=True)
network='cr-g15-gzip-reference-v3-obva7te6'
call('network','create','--internal','--label','stremhu.task=obva7te6',network,capture_output=True)
server=None
env=os.environ.copy()
env.update(HOST_IP=(repo/'.git/cr-test-host').read_text().strip(),SESSION_SECRET=secrets.token_urlsafe(48),STREMHU_LOAD_DOTENV='false',TEST_BASE_URL='http://tracker.fixture.invalid:8080',PYTHONDONTWRITEBYTECODE='1')
try:
    server=call('run','--detach','--rm','--name',network+'-server','--label','stremhu.task=obva7te6','--network',network,'--network-alias','tracker.fixture.invalid','--network-alias','cdn.other.invalid','--read-only','--cpus','1','--cpuset-cpus','4','--memory','512m','--tmpfs','/tmp','--mount',f'type=bind,source={fixture},target=/fixture,readonly','--entrypoint','python',images['C'],'/fixture/server.py',capture_output=True,text=True).stdout.strip()
    deadline=time.monotonic()+45
    while True:
        check=subprocess.run(['docker','--context','desktop-linux','exec',server,'python','-c',"import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/ready',timeout=1))['ready']"],capture_output=True)
        if check.returncode==0:break
        if time.monotonic()>deadline:raise RuntimeError('Private tracker readiness failed')
        time.sleep(.1)
    cases=[('C',series,i,c) for series in ['a','b'] for i in range(5) for c in [1,4,8]]+[(label,'ref',i,c) for i in range(5) for label in [['A','B','C'],['B','C','A'],['C','A','B']][i%3] for c in [1,4,8]]
    for label,series,repetition,concurrency in cases:
        env['G15_CONCURRENCY']=str(concurrency)
        assert all(hashlib.sha256((fixture/name).read_bytes()).hexdigest()==digest for name,digest in protocol['fixture_sha256'].items())
        stem=f'g15-gzip-reference-v3-{label}-{series}-{repetition}-c{concurrency}'
        output=r/(stem+'-output')
        assert not output.exists()
        output.mkdir()
        cmd=['docker','--context','desktop-linux','run','--name',stem+'-obva7te6','--label','stremhu.task=obva7te6','--network',network,'--read-only','--cpus','2','--cpuset-cpus','2,3','--memory','1g','--tmpfs','/tmp','--tmpfs','/app/data','--mount',f'type=bind,source={fixture},target=/fixture,readonly','--mount',f'type=bind,source={output},target=/fixture-output']
        for key in ['HOST_IP','SESSION_SECRET','STREMHU_LOAD_DOTENV','TEST_BASE_URL','PYTHONDONTWRITEBYTECODE','G15_CONCURRENCY']:cmd+=['--env',key]
        cmd+=['--env','PYTHONPATH=/app']
        if label in ['B','C']:
            source=r/('baseline' if label=='B' else 'cr17a-drain-fix-v2-source')/'server/app'
            manifest=json.loads((e/('cr17a-drain-checked-v2-manifest.json' if label=='C' else 'g0-baseline-manifest.json')).read_text()) if label=='C' else None
            if manifest is not None:assert all(hashlib.sha256((source/Path(name).relative_to('app')).read_bytes()).hexdigest()==digest for name,digest in manifest['files'].items() if name.startswith('app/'))
            else:assert all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in protocol['source_B_app_sha256'].items())
            cmd+=['--mount',f'type=bind,source={source},target=/app/app,readonly']
        cmd+=['--entrypoint','python',images[label],'/fixture/probe.py']+(['--fixture-smoke'] if series=='smoke' else [])
        stats_code="import json,urllib.request;print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/stats',timeout=2))))"
        before_stats=json.loads(call('exec',server,'python','-c',stats_code,capture_output=True,text=True).stdout)
        print(stem,'starting distinctsmoke' if series=='smoke' else 'starting1x100request cell',flush=True)
        with (e/(stem+'.stdout')).open('w',encoding='utf-8') as out,(e/(stem+'.stderr')).open('w',encoding='utf-8') as err:result=subprocess.run(cmd,env=env,stdout=out,stderr=err)
        state=json.loads(call('inspect',stem+'-obva7te6',capture_output=True,text=True).stdout)[0]['State']
        after_stats=json.loads(call('exec',server,'python','-c',stats_code,capture_output=True,text=True).stdout)
        actual_received=after_stats.get('gzip-large',0)-before_stats.get('gzip-large',0)
        (e/(stem+'-state.json')).write_text(json.dumps(dict(exit_code=state['ExitCode'],oom_killed=state['OOMKilled'],completed_rows=sum(1 for _ in (output/'rows.jsonl').open()) if (output/'rows.jsonl').exists() else 0,configured_measured_requests=100,actual_server_received_including_cold_warmup=actual_received,decoded_bytes_per_fullbody=128<<20,concurrency=concurrency,scope='Received requests are not necessarily completed responses;failedattempt is not successfultiming')),encoding='utf-8')
        call('rm',stem+'-obva7te6',capture_output=True)
        if result.returncode:
            print(stem,'incomplete',result.returncode,'oom',state['OOMKilled'],flush=True)
            continue
        data=json.loads((e/(stem+'.stdout')).read_text())
        assert data['is_measurement']==(series!='smoke') and len(data['rows'])==1
        assert all(len(row['samples_ms'])==(4 if series=='smoke' else 100) for row in data['rows'])
        data.update(protocol=protocol['id'],image=images[label],source=protocol['source_C'] if label=='C' else 'baseline2615596 source overlay' if label=='B' else 'pinnedimage revision8c99c7d',resources=protocol['resources'],fixture_sha256=protocol['fixture_sha256'])
        (e/(stem+'.json')).write_text(json.dumps(data),encoding='utf-8')
        print(stem,'saved',flush=True)
finally:
    if server is not None:call('stop','--time','5',server,capture_output=True)
    call('network','rm',network,capture_output=True)

(e/'g15-gzip-reference-v3-complete.json').write_text(json.dumps(dict(status='Reference attempts complete; outcomes must be assessed,no automatic acceptance')),encoding='utf-8')
