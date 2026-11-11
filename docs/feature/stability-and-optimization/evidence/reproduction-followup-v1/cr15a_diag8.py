"""Diagnostic only (not gate data), follow-up of diag7: does pinning glibc at its own dynamic maximum (mmap 32 MiB, trim 2x = 64 MiB)
remove the cr15a-after-v5 c1 page faults as the diag7 hypothesis setting (trim 128 MiB) did? Earlier diag7 text:
Hypothesis: once bodies are freed by refcount, glibc returns the freed body memory to the OS and every next body is page-faulted
afresh. Measures minor page faults per measured batch and mallinfo2; same image, fixture, limits and preload as the v5 gate
(cpus 8,9 probe / 10 server, after the gate finished). Variants: before, after-v4 code (0864a87), after-v5 (7c01689), and
before/after-v5 with a fixed glibc mmap/trim threshold (hypothesis test only, not a selected setting). 3 reps, rotated order.
"""
import json, os, pathlib, secrets, subprocess, time
r = pathlib.Path(__file__).parent
fx = r / 'cr15a-after-v4-fixture'
dx = r / 'cr15a-diag7-fixture'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
SRC = {'before': r / 'g02-post-cr17-v2-source/server/app', 'after-v4code': r / 'cr15a-after-v3-source/server/app',
       'after-v5': r / 'cr15a-after-v5-source/server/app'}
TUNINGS = {'t64': {'MALLOC_MMAP_THRESHOLD_': '33554432', 'MALLOC_TRIM_THRESHOLD_': '67108864'},
           't128': {'MALLOC_MMAP_THRESHOLD_': '33554432', 'MALLOC_TRIM_THRESHOLD_': '134217728'}}
VARIANTS = [('before', None), ('after-v5', 't64'), ('after-v5', 't128'), ('before', 't64')]
def call(*a, **kw): return subprocess.run(['docker', '--context', 'desktop-linux', *a], **kw)
env = os.environ.copy()
env.update(HOST_IP=(pathlib.Path('D:/Git/stremhu-source-anime/.git/cr-test-host')).read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48),
           STREMHU_LOAD_DOTENV='false', TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1')
net = 'cr-cr15a-diag8-obva7te6'
call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', net, capture_output=True, check=True)
server = None
out = r / 'cr15a-diag8-output'
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
    for rep in range(4):
        order = VARIANTS[rep:] + VARIANTS[:rep]
        for side, tuned in order:
            name = side + ('-' + tuned if tuned else '')
            o = out / f'{name}-{rep}'
            o.mkdir()
            cmd = ['run', '--rm', '--network', net, '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9', '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data',
                   '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--mount', f'type=bind,source={dx},target=/diag,readonly',
                   '--mount', f'type=bind,source={o},target=/fixture-output', '--mount', f'type=bind,source={SRC[side]},target=/app/app,readonly']
            for k in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE']: cmd += ['--env', k]
            for k, v in (TUNINGS[tuned].items() if tuned else ()): cmd += ['--env', f'{k}={v}']
            cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, '/diag/w_cfg.py']
            res = call(*cmd, env=env, capture_output=True, text=True, encoding='utf-8')
            if res.returncode: print(name, rep, 'FAILED', res.returncode, flush=True); continue
            d = json.loads(res.stdout)
            for x in d['rows']:
                results.append(dict(variant=name, rep=rep, kind=x['kind'], concurrency=x['concurrency'], p50_ms=x['p50_ms'], p95_ms=x['p95_ms'], cpu_seconds=x['cpu_seconds'],
                                    minflt=x['minflt'], majflt=x['majflt'], mallinfo=x['mallinfo'], anon_after=x['memory']['anon_bytes'], anon_peak=x['memory_peaks']['anon_bytes']))
            print(name, rep, ' '.join(f"{x['kind'][:5]}c{x['concurrency']} p50={x['p50_ms']:.2f} cpu={x['cpu_seconds']:.3f} flt={x['minflt']}"
                                      for x in d['rows'] if x['kind'] != 'small'), flush=True)
finally:
    if server: call('stop', '--time', '5', server, capture_output=True)
    call('network', 'rm', net, capture_output=True)
    (r / 'evidence' / 'cr15a-diag8-results.json').write_text(json.dumps(dict(diagnostic_only=True, malloc_env=TUNINGS, results=results), indent=1), encoding='utf-8')
