"""Diagnostic only (not gate data): small-body anon memory with app.config preloaded on every side: before, v3, v3b (declared length -> plain aread), v3get (v3 module, plain get).

Hypothesis: the cr15a-after-v3 small-kind anon excess is the one-time import of app.config (35 modules), which the
probe process lacks on the before side but the production server always loads. 4 variants x 4 reps, rotated order,
cpus 8,9 for the probe, 10 for the fixture server.
"""
import json, os, pathlib, secrets, subprocess, time
r = pathlib.Path(__file__).parent
fx = r / 'cr15a-diag2-fixture'
dx = r / 'cr15a-diag3-fixture'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
SRC = {'before': r / 'g02-post-cr17-v2-source/server/app', 'v3': r / 'cr15a-after-v3-source/server/app', 'v3b': r / 'cr15a-diag4-v3b-source/server/app', 'v3get': r / 'cr15a-diag4-v3get-source/server/app'}
VARIANTS = [('before', 'w_cfg.py'), ('v3', 'w_cfg.py'), ('v3b', 'w_cfg.py'), ('v3get', 'w_cfg.py')]
def call(*a, **kw): return subprocess.run(['docker', '--context', 'desktop-linux', *a], **kw)
env = os.environ.copy()
env.update(HOST_IP=(pathlib.Path('D:/Git/stremhu-source-anime/.git/cr-test-host')).read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48),
           STREMHU_LOAD_DOTENV='false', TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1')
net = 'cr-cr15a-diag4-obva7te6'
call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', net, capture_output=True, check=True)
server = None
out = r / 'cr15a-diag4-output'
out.mkdir(exist_ok=False)
results = []
try:
    server = call('run', '--detach', '--rm', '--name', net + '-server', '--network', net, '--network-alias', 'tracker.fixture.invalid', '--network-alias', 'cdn.other.invalid',
                  '--read-only', '--cpus', '1', '--cpuset-cpus', '10', '--memory', '512m', '--tmpfs', '/tmp', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
                  '--entrypoint', 'python', IMAGE, '/fixture/server.py', capture_output=True, text=True, check=True).stdout.strip()
    deadline = time.monotonic() + 45
    while call('exec', server, 'python', '-c', "import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/ready',timeout=1))['ready']", capture_output=True).returncode:
        if time.monotonic() > deadline: raise RuntimeError('not ready')
        time.sleep(.1)
    for rep in range(6):
        order = VARIANTS[rep % 4:] + VARIANTS[:rep % 4]
        for side, wrapper in order:
            name = f"{side}-{'cfg' if wrapper == 'w_cfg.py' else 'plain'}"
            o = out / f'{name}-{rep}'
            o.mkdir()
            cmd = ['run', '--rm', '--network', net, '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9', '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data',
                   '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--mount', f'type=bind,source={dx},target=/diag,readonly',
                   '--mount', f'type=bind,source={o},target=/fixture-output', '--mount', f'type=bind,source={SRC[side]},target=/app/app,readonly']
            for k in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE']: cmd += ['--env', k]
            cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, f'/diag/{wrapper}']
            res = call(*cmd, env=env, capture_output=True, text=True, encoding='utf-8')
            if res.returncode: print(name, rep, 'FAILED', res.returncode, flush=True); continue
            d = json.loads(res.stdout)
            for x in d['rows']:
                results.append(dict(variant=name, rep=rep, concurrency=x['concurrency'], anon_after=x['memory']['anon_bytes'], anon_peak=x['memory_peaks']['anon_bytes'],
                                    p50_ms=x['p50_ms'], cpu_seconds=x['cpu_seconds']))
            print(name, rep, ' '.join(f"c{x['concurrency']} anon={x['memory']['anon_bytes']/1048576:.2f} peak={x['memory_peaks']['anon_bytes']/1048576:.2f} p50={x['p50_ms']:.2f}"
                                      for x in d['rows']), flush=True)
finally:
    if server: call('stop', '--time', '5', server, capture_output=True)
    call('network', 'rm', net, capture_output=True)
    (r / 'evidence' / 'cr15a-diag4-results.json').write_text(json.dumps(dict(diagnostic_only=True, results=results), indent=1), encoding='utf-8')
