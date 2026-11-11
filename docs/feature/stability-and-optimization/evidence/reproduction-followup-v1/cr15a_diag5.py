"""Diagnostic only (not gate data): is the cr15a-after-v4 many-files anon_after excess live memory or freeable allocator retention?

before (aaa9ee5 tree) vs after (cr15a v3 code, 0864a87), both with app.config preloaded as in cr15a-after-v4; gate order small -> many-files,
same image, fixture, cpus (probe 8,9, server 10) and limits. After each many-files row: immediate, gc+3 s, malloc_trim(0)+3 s snapshots of
memcg anon, /proc RssAnon and glibc mallinfo2. 2 variants x 6 reps, alternating order. c4/c8 rows start after a trim (differs from the gate).
"""
import json, os, pathlib, secrets, subprocess, time
r = pathlib.Path(__file__).parent
fx = r / 'cr15a-after-v4-fixture'
dx = r / 'cr15a-diag5-fixture'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
SRC = {'before': r / 'g02-post-cr17-v2-source/server/app', 'after': r / 'cr15a-after-v3-source/server/app'}
VARIANTS = [('before', 'w_cfg.py'), ('after', 'w_cfg.py')]
def call(*a, **kw): return subprocess.run(['docker', '--context', 'desktop-linux', *a], **kw)
env = os.environ.copy()
env.update(HOST_IP=(pathlib.Path('D:/Git/stremhu-source-anime/.git/cr-test-host')).read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48),
           STREMHU_LOAD_DOTENV='false', TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1')
net = 'cr-cr15a-diag5-obva7te6'
call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', net, capture_output=True, check=True)
server = None
out = r / 'cr15a-diag5-output'
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
        order = VARIANTS if rep % 2 == 0 else VARIANTS[::-1]
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
                results.append(dict(variant=name, rep=rep, kind=x['kind'], concurrency=x['concurrency'], anon_after=x['memory']['anon_bytes'], anon_peak=x['memory_peaks']['anon_bytes'],
                                    p50_ms=x['p50_ms'], cpu_seconds=x['cpu_seconds'], retention=x.get('retention')))
            print(name, rep, ' '.join(f"c{x['concurrency']} anon={x['memory']['anon_bytes']/1048576:.2f} settled={x['retention']['settled']['rss_anon']/1048576:.2f} trimmed={x['retention']['trimmed']['rss_anon']/1048576:.2f} inuse={x['retention']['trimmed']['heap_in_use']/1048576:.2f}"
                                      for x in d['rows'] if x['kind'] == 'many-files'), flush=True)
finally:
    if server: call('stop', '--time', '5', server, capture_output=True)
    call('network', 'rm', net, capture_output=True)
    (r / 'evidence' / 'cr15a-diag5-results.json').write_text(json.dumps(dict(diagnostic_only=True, results=results), indent=1), encoding='utf-8')
