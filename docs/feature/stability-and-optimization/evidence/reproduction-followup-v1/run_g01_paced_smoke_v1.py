from pathlib import Path
import hashlib
import json
import os
import secrets
import subprocess
import time

repo=Path.cwd()
r=Path(__file__).parent
e=r/'evidence'
image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
network='cr-g01-paced-smoke-obva7te6'
volume=network+'-data'
server=network+'-seed'
client=network+'-client'

def call(*args,**kwargs):
    return subprocess.run(['docker','--context','desktop-linux',*args],check=True,**kwargs)

context=json.loads(call('context','inspect','desktop-linux',capture_output=True,text=True).stdout)[0]
assert context['Endpoints']['docker']['Host'].startswith('npipe://')
s=(repo/'scripts/fixtures/local_bt_seed.py').read_text(encoding='utf-8')
s=s.replace('self.endpoints = []','self.endpoints = []\n        self.block_delay = 0',1)
s=s.replace('self._serve, "127.0.0.1", 0','self._serve, "0.0.0.0", 0',1)
needle='                writer.write(struct.pack("!IBII", length + 9, 7, index, offset) + b"\\0" * length)'
assert needle in s
s=s.replace(needle,'                if self.block_delay:\n                    await asyncio.sleep(self.block_delay)\n'+needle,1)
seed=r/'g01-separated-seed-base-v1.py'
seed.write_text(s,encoding='utf-8')
env=os.environ.copy()
env.update(HOST_IP=(repo/'.git/cr-test-host').read_text().strip(),SESSION_SECRET=secrets.token_urlsafe(48),STREMHU_LOAD_DOTENV='false',PYTHONDONTWRITEBYTECODE='1',TEST_BASE_URL='http://seeder.fixture.invalid:8080',G01_VARIANT='legacy',G01_BLOCK_DELAY_MS='50')
call('network','create','--internal','--label','stremhu.task=obva7te6',network,capture_output=True)
call('volume','create','--driver','local','--label','stremhu.task=obva7te6','--label','stremhu.disposable=true',volume,capture_output=True)
details=json.loads(call('volume','inspect',volume,capture_output=True,text=True).stdout)[0]
assert details['Driver']=='local' and details['Labels']['stremhu.task']=='obva7te6'
started=False
try:
    cmd=['run','--detach','--rm','--name',server,'--label','stremhu.task=obva7te6','--network',network,'--network-alias','seeder.fixture.invalid','--read-only','--cpus','1','--cpuset-cpus','15','--memory','256m','--tmpfs','/tmp','--env','PYTHONDONTWRITEBYTECODE','--env','PYTHONPATH=/fixture','--mount',f'type=bind,source={seed},target=/fixture/local_bt_seed.py,readonly','--mount',f'type=bind,source={r/"g01_seed_server_v1.py"},target=/fixture/server.py,readonly','--entrypoint','python',image,'-c',"import asyncio;from hypercorn.asyncio import serve;from hypercorn.config import Config;from server import app;c=Config();c.bind=['0.0.0.0:8080'];asyncio.run(serve(app,c))"]
    call(*cmd,env=env,capture_output=True)
    started=True
    deadline=time.monotonic()+45
    while True:
        check=subprocess.run(['docker','--context','desktop-linux','exec',server,'python','-c',"import urllib.request,json;print(json.load(urllib.request.urlopen('http://127.0.0.1:8080/control/ready',timeout=1))['ready'])"],capture_output=True,text=True)
        if check.returncode==0 and check.stdout.strip()=='True':break
        if time.monotonic()>deadline:raise RuntimeError('Private seed readiness failed')
        time.sleep(.1)
    cmd=['run','--rm','--name',client,'--label','stremhu.task=obva7te6','--network',network,'--read-only','--cpus','2','--cpuset-cpus','0,1','--memory','1g','--tmpfs','/tmp','--env','HOST_IP','--env','SESSION_SECRET','--env','STREMHU_LOAD_DOTENV','--env','PYTHONDONTWRITEBYTECODE','--env','TEST_BASE_URL','--env','G01_VARIANT','--env','G01_BLOCK_DELAY_MS','--env','PYTHONPATH=/app','--mount',f'type=volume,source={volume},target=/app/data','--mount',f'type=bind,source={r/"cr17a-drain-fix-v1-source/server/app"},target=/app/app,readonly','--mount',f'type=bind,source={r/"g01_paced_native_v1.py"},target=/fixture/probe.py,readonly','--entrypoint','python',image,'/fixture/probe.py','--fixture-smoke']
    with (e/'g01-paced-smoke-v1.stdout').open('w',encoding='utf-8') as out,(e/'g01-paced-smoke-v1.stderr').open('w',encoding='utf-8') as err:
        result=subprocess.run(['docker','--context','desktop-linux',*cmd],env=env,stdout=out,stderr=err)
    if result.returncode:raise RuntimeError('Separated native seed wiring failed;raw retained')
    data=json.loads((e/'g01-paced-smoke-v1.stdout').read_text())
    assert not data['is_measurement'] and len(data['rows'])==8 and not data['seed_stats']['errors']
    data.update(image=image,client_resource='2CPU0,1/1GiB',server_resource='1CPU15/256MiB',storage='Own labelled local Docker volume, retained;native data is reclaimable file cache,not tmpfs',fixture_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [seed,r/'g01_seed_server_v1.py',r/'g01_paced_native_v1.py']})
    (e/'g01-paced-smoke-v1.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('Paced native profile wiring PASS; not fullG01 matrix or measurement.',flush=True)
finally:
    if started:call('stop','--time','10',server,capture_output=True)
    call('network','rm',network,capture_output=True)
