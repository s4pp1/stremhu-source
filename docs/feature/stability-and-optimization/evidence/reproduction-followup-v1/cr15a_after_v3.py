"""CR15a after-gate controller (v3; v1 and v2 FAILED, v3 = same protocol, after source 0864a87). Same private tracker fixture and normal probe as G15 normal-transport v2.
Normal: two series x five before/after pairs, pair order alternating (ABBA), before = frozen aaa9ee5 server/app,
after = frozen CR15a 0864a87 server/app, both on the pinned C image. Giant: chunked-large/gzip-large control,
after twice (one per series) and before once (expected OOM, recorded as outcome). argv: [--smoke]"""
import hashlib
import json
import os
import pathlib
import secrets
import subprocess
import sys
import time

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'cr15a-after-v3-fixture'
SMOKE = '--smoke' in sys.argv
protocol = json.loads((e / 'cr15a-after-v3-protocol.json').read_text(encoding='utf-8')) if not SMOKE else None
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
SOURCES = {'before': (r / 'g02-post-cr17-v2-source/server/app', e / 'g02-post-cr17-v2-source-manifest.json'),
           'after': (r / 'cr15a-after-v3-source/server/app', e / 'cr15a-after-v3-source-manifest.json')}
if protocol:
    for name, digest in protocol['fixture_sha256'].items():
        if hashlib.sha256((fx / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Fixture drift: ' + name)
for label, (src, man) in SOURCES.items():
    for name, digest in json.loads(man.read_text(encoding='utf-8'))['files'].items():
        if hashlib.sha256((src / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Frozen {label} source drift: {name}')


def call(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], check=True, **kw)


context = json.loads(call('context', 'inspect', 'desktop-linux', capture_output=True, text=True).stdout)[0]
if not context['Endpoints']['docker']['Host'].startswith('npipe://'):
    raise RuntimeError('Not local Docker Desktop')
env = os.environ.copy()
env.update(HOST_IP=(pathlib.Path.cwd() / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false',
           TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1')
if SMOKE:
    cases = [('smoke', 'before', 'normal'), ('smoke', 'after', 'normal'), ('smoke', 'after', 'giant'), ('smoke', 'before', 'giant')]
else:
    cases = []
    for s in ('s1', 's2'):
        for i in range(5):
            pair = ['before', 'after'] if i % 2 == 0 else ['after', 'before']
            cases += [(f'{s}-{i}', side, 'normal') for side in pair]
        cases.append((f'{s}-giant', 'after', 'giant'))
    cases.append(('confirm-giant', 'before', 'giant'))
network = 'cr-cr15a-after-v3-obva7te6'
call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', network, capture_output=True)
server = None
try:
    server = call('run', '--detach', '--rm', '--name', network + '-server', '--label', 'stremhu.task=obva7te6', '--network', network,
                  '--network-alias', 'tracker.fixture.invalid', '--network-alias', 'cdn.other.invalid', '--read-only', '--cpus', '1', '--cpuset-cpus', '10',
                  '--memory', '512m', '--tmpfs', '/tmp', '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--entrypoint', 'python', IMAGE,
                  '/fixture/server.py', capture_output=True, text=True).stdout.strip()
    deadline = time.monotonic() + 45
    while subprocess.run(['docker', '--context', 'desktop-linux', 'exec', server, 'python', '-c',
                          "import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/ready',timeout=1))['ready']"],
                         capture_output=True).returncode != 0:
        if time.monotonic() > deadline:
            raise RuntimeError('Private tracker readiness failed')
        time.sleep(.1)
    for tag, side, probe in cases:
        stem = f'cr15a-after-v3-{probe}-{side}-{tag}'
        target = e / (stem + '.json')
        if target.exists():
            raise RuntimeError('Refusing evidence overwrite')
        out = r / 'cr15a-after-v3-output' / stem
        out.mkdir(parents=True, exist_ok=False)
        name = stem + '-obva7te6'
        cmd = ['run', '--name', name, '--label', 'stremhu.task=obva7te6', '--network', network, '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9',
               '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
               '--mount', f'type=bind,source={out},target=/fixture-output', '--mount', f'type=bind,source={SOURCES[side][0]},target=/app/app,readonly']
        for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE']:
            cmd += ['--env', key]
        cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, f'/fixture/{"probe" if probe == "normal" else "giant"}.py']
        if SMOKE:
            cmd.append('--fixture-smoke')
        print(stem, 'starting', flush=True)
        with (e / (stem + '.stdout')).open('w', encoding='utf-8') as so, (e / (stem + '.stderr')).open('w', encoding='utf-8') as se:
            result = subprocess.run(['docker', '--context', 'desktop-linux', *cmd], env=env, stdout=so, stderr=se)
        state = json.loads(call('inspect', name, capture_output=True, text=True).stdout)[0]['State']
        rows_file = out / 'rows.jsonl'
        st = dict(exit_code=state['ExitCode'], oom_killed=state['OOMKilled'],
                  completed_rows=sum(1 for _ in rows_file.open()) if rows_file.exists() else 0)
        (e / (stem + '-state.json')).write_text(json.dumps(st), encoding='utf-8')
        call('rm', name, capture_output=True)
        expected_fail = probe == 'giant' and side == 'before'
        if result.returncode and not expected_fail:
            raise RuntimeError('Run failed; raw and completed rows retained; no gate completion')
        if result.returncode == 0:
            d = json.loads((e / (stem + '.stdout')).read_text(encoding='utf-8'))
            d.update(side=side, tag=tag, probe=probe, image=IMAGE, state=st)
            target.write_text(json.dumps(d), encoding='utf-8')
        print(stem, 'saved' if result.returncode == 0 else f'ended exit={st["exit_code"]} oom={st["oom_killed"]}', flush=True)
finally:
    if server is not None:
        subprocess.run(['docker', '--context', 'desktop-linux', 'stop', '--time', '5', server], capture_output=True)
    subprocess.run(['docker', '--context', 'desktop-linux', 'network', 'rm', network], capture_output=True)
if not SMOKE:
    (e / 'cr15a-after-v3-complete.json').write_text(json.dumps(dict(cases=cases, complete=True)), encoding='utf-8')
print('CR15a after-gate controller finished', flush=True)
