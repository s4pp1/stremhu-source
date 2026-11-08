from pathlib import Path
import datetime
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import time

r = Path(__file__).parent
repo = Path.cwd()
e = r / 'evidence'
fixture = r / 'g15-deadline-fixture-v1'
assert not fixture.exists()
fixture.mkdir()
for source, target in [(r/'g15_deadline_server_v1.py', fixture/'server.py'), (r/'g15_deadline_probe_v1.py', fixture/'probe.py'), (repo/'scripts/probe_cr_torrent_metadata_sizes.py', fixture/'metadata_sizes.py')]:
    shutil.copy2(source, target)
images = {'A':'s4pp1/stremhu-source@sha256:a3a2012893d689795f958ccec666fef6277f8677f24efebe9568cb44ec7a0621', 'B':'stremhu-source@sha256:6ca708d99b8698e6cf116a6183c283922ebd2e53940c366a93a421b4ca974a38', 'C':'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'}


def call(*args, **kwargs):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], check=True, **kwargs)


assert json.loads(call('context', 'inspect', 'desktop-linux', capture_output=True, text=True).stdout)[0]['Endpoints']['docker']['Host'].startswith('npipe://')
protocol = dict(id='g15-slow-body-cancel-functional-v1', registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope='Independent G15 before-state preparation.25s drip at0.5s intervals with20s HTTPX read timeout;caller cancel,external1s fixture timeout,queued semaphore waiter cancel.Each A/B/C functional only,not repeated timing or tuning.', resource='Client2CPU0,1/1GiB,serverCPU15/256MiB,private internal network,no publishedports or outbound.', fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.iterdir()})
(e/'g15-deadline-v1-protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
for label, image in images.items():
    network = 'cr-g15-deadline-v1-' + label.lower() + '-obva7te6'
    call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', network, capture_output=True)
    server = None
    env = os.environ.copy()
    env.update(HOST_IP=(repo/'.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false', TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1')
    try:
        server = call('run', '--detach', '--rm', '--name', network+'-server', '--network', network, '--network-alias', 'tracker.fixture.invalid', '--read-only', '--cpus', '1', '--cpuset-cpus', '15', '--memory', '256m', '--tmpfs', '/tmp', '--mount', f'type=bind,source={fixture},target=/fixture,readonly', '--entrypoint', 'python', images['C'], '/fixture/server.py', capture_output=True, text=True).stdout.strip()
        deadline = time.monotonic() + 30
        while True:
            ready = subprocess.run(['docker','--context','desktop-linux','exec',server,'python','-c',"import urllib.request;assert len(urllib.request.urlopen('http://127.0.0.1:8080/small',timeout=1).read())==82073"], capture_output=True)
            if ready.returncode == 0:
                break
            if time.monotonic() > deadline:
                raise RuntimeError('Slow-body fixture readiness failed')
            time.sleep(.1)
        cmd = ['docker','--context','desktop-linux','run','--rm','--name',network+'-client','--network',network,'--read-only','--cpus','2','--cpuset-cpus','0,1','--memory','1g','--tmpfs','/tmp','--tmpfs','/app/data','--mount',f'type=bind,source={fixture},target=/fixture,readonly']
        for key in ['HOST_IP','SESSION_SECRET','STREMHU_LOAD_DOTENV','TEST_BASE_URL','PYTHONDONTWRITEBYTECODE']:
            cmd += ['--env', key]
        cmd += ['--env', 'PYTHONPATH=/app']
        if label in ['B','C']:
            source = r / ('baseline' if label=='B' else 'cr17a-drain-fix-v2-source') / 'server/app'
            cmd += ['--mount', f'type=bind,source={source},target=/app/app,readonly']
        cmd += ['--entrypoint','python',image,'/fixture/probe.py']
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8')
        name = 'g15-deadline-v1-' + label
        for suffix, value in [('stdout',result.stdout),('stderr',result.stderr)]:
            (e/(name+'.'+suffix)).write_text(value, encoding='utf-8')
        if result.returncode:
            raise RuntimeError('Slow-body functional observation failed;raw retained')
        data = json.loads(result.stdout)
        assert not data['is_measurement'] and len(data['rows']) == 4 and data['client_closed']
        data.update(image=image, protocol=protocol['id'])
        (e/(name+'.json')).write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(label, '4functional slow/cancel observations saved', flush=True)
    finally:
        if server is not None:
            call('stop', '--time','5',server,capture_output=True)
        call('network','rm',network,capture_output=True)
