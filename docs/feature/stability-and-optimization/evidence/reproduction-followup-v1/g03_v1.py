"""G03 v1 controller: sequential, rotated (repetition x link profile) batches of the identity/gzip cell matrix.
Each batch: fresh internal network, fresh server process (C image + frozen aaa9ee5 overlay), optional shaper, one client.
Refuses evidence overwrite; verifies fixture and frozen source hashes against the registered protocol."""
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
fx = r / 'g03-v1'
out_root = r / 'g03-v1-output'
SMOKE = '--smoke' in sys.argv
if not SMOKE:
    registered = json.loads((e / 'g03-v1-protocol.json').read_text(encoding='utf-8'))
    for name, digest in registered['fixture_sha256'].items():
        if hashlib.sha256((fx / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Fixture drift: ' + name)
protocol = json.loads((fx / 'params.json').read_text(encoding='utf-8'))
protocol['fixture_sha256'] = {n: hashlib.sha256((fx / n).read_bytes()).hexdigest() for n in ['server.py', 'shaper.py', 'client.py', 'params.json']}
manifest = json.loads((e / 'g02-post-cr17-v2-source-manifest.json').read_text(encoding='utf-8'))
src = r / 'g02-post-cr17-v2-source/server/app'
for name, digest in manifest['files'].items():
    if hashlib.sha256((src / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError('Frozen source drift: ' + name)


def call(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], check=True, **kw)


context = json.loads(call('context', 'inspect', 'desktop-linux', capture_output=True, text=True).stdout)[0]
if not context['Endpoints']['docker']['Host'].startswith('npipe://'):
    raise RuntimeError('Not local Docker Desktop')
repo = pathlib.Path.cwd()
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false')
IMAGE = protocol['image']
PROFILES = protocol['profiles']
PAYLOADS = protocol['payloads']
VARIANTS = protocol['variants']
MODES = protocol['modes']


def cells_for(rep):
    cells = []
    for pi, payload in enumerate(PAYLOADS):
        k = (rep + pi) % len(VARIANTS)
        for v in VARIANTS[k:] + VARIANTS[:k]:
            for mode in MODES:
                n = protocol['n_fresh'] if mode == 'fresh' else protocol['n_keepalive']
                cells.append(dict(payload=payload, variant=v, variant_path=v.split('-')[0], mode=mode, n=5 if SMOKE else n))
    return cells


if SMOKE:
    plan = [(0, 'lan'), (0, 'mob2')]
else:
    plan = [(rep, p) for rep in range(protocol['repetitions']) for p in (PROFILES[rep % len(PROFILES):] + PROFILES[:rep % len(PROFILES)])]
for rep, prof in plan:
    stem = f'g03-v1-{"smoke-" if SMOKE else ""}{rep}-{prof}'
    target = e / (stem + '.json')
    if target.exists():
        raise RuntimeError('Refusing evidence overwrite')
    run_dir = out_root / stem
    run_dir.mkdir(parents=True, exist_ok=False)
    net = 'cr-g03-obva7te6'
    call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', net, capture_output=True)
    names = [f'{net}-server', f'{net}-shaper', f'{net}-client']
    try:
        call('run', '--detach', '--rm', '--name', names[0], '--label', 'stremhu.task=obva7te6', '--network', net, '--network-alias', 'g03-server',
             '--read-only', '--cpus', '1', '--cpuset-cpus', protocol['cpusets']['server'], '--memory', '512m', '--tmpfs', '/tmp',
             '--env', 'HOST_IP', '--env', 'SESSION_SECRET', '--env', 'STREMHU_LOAD_DOTENV', '--env', 'PYTHONDONTWRITEBYTECODE=1',
             '--env', 'PYTHONPATH=/app:/fixture', '--workdir', '/fixture',
             '--mount', f'type=bind,source={src},target=/app/app,readonly', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
             '--entrypoint', 'python', IMAGE, '/fixture/server.py', env=env, capture_output=True)
        deadline = time.monotonic() + 60
        while subprocess.run(['docker', '--context', 'desktop-linux', 'exec', names[0], 'python', '-c',
                              "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/__stats',timeout=2)"],
                             capture_output=True).returncode != 0:
            if time.monotonic() > deadline:
                raise RuntimeError('Server not ready')
            time.sleep(.2)
        p = protocol['profile_params'][prof]
        base = 'http://g03-server:8080'
        if p['rate_Bps']:
            call('run', '--detach', '--rm', '--name', names[1], '--label', 'stremhu.task=obva7te6', '--network', net, '--network-alias', 'g03-shaper',
                 '--read-only', '--cpus', '1', '--cpuset-cpus', protocol['cpusets']['shaper'], '--memory', '256m', '--tmpfs', '/tmp',
                 '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--entrypoint', 'python', IMAGE, '/fixture/shaper.py',
                 '8081', 'g03-server', '8080', str(p['rate_Bps']), str(p['one_way_delay_ms']), capture_output=True)
            base = 'http://g03-shaper:8081'
            time.sleep(1)
        cfg = dict(profile=prof, repetition=rep, smoke=SMOKE, base_url=base, stats_url='http://g03-server:8080/__stats', warmup=protocol['warmup'],
                   cells=cells_for(rep))
        (run_dir / 'config.json').write_text(json.dumps(cfg), encoding='utf-8')
        print(stem, 'starting', flush=True)
        with (e / (stem + '.stdout')).open('w', encoding='utf-8') as so, (e / (stem + '.stderr')).open('w', encoding='utf-8') as se:
            call('run', '--rm', '--name', names[2], '--label', 'stremhu.task=obva7te6', '--network', net, '--read-only', '--cpus', '2',
                 '--cpuset-cpus', protocol['cpusets']['client'], '--memory', '1g', '--tmpfs', '/tmp', '--env', 'PYTHONDONTWRITEBYTECODE=1',
                 '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--mount', f'type=bind,source={run_dir},target=/out',
                 '--entrypoint', 'python', IMAGE, '/fixture/client.py', '/out/config.json', '/out/result.json', stdout=so, stderr=se)
        d = json.loads((run_dir / 'result.json').read_text(encoding='utf-8'))
        d.update(image=IMAGE, profile_params=p, fixture_sha256=protocol['fixture_sha256'])
        target.write_text(json.dumps(d), encoding='utf-8')
        print(stem, 'saved', flush=True)
    finally:
        for n in names:
            subprocess.run(['docker', '--context', 'desktop-linux', 'stop', '--time', '5', n], capture_output=True)
        subprocess.run(['docker', '--context', 'desktop-linux', 'network', 'rm', net], capture_output=True)
if not SMOKE:
    (e / 'g03-v1-complete.json').write_text(json.dumps(dict(plan=plan, complete=True)), encoding='utf-8')
print('G03 v1 controller finished', flush=True)
