"""Packet 27 (CR15/c) after-gate controller (v2: v1 PASS on the CR15a v2 base; rerun on the CR15a v3 landing tree). argv: smoke | register | run
before = frozen a4b9229 (CR15a v3 + 26a + 26b, the landing base), after = frozen 438b72f (+ packet 27).
Workload = the unchanged burst27 fixture/harness (real provider/search/download/DB path, synthetic adapter search page).
Two series x five before/after pairs per cell, pair order alternating (ABBA); one fresh client and server per run.
"""
import datetime
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

r = Path(__file__).parent
repo = Path.cwd()
e = r / 'evidence'
fx = r / 'burst27-v1-fixture'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
SOURCES = {'before': (r / 'cr15b2-after-v4-source/server/app', e / 'cr15b2-after-v4-source-manifest.json'),
           'after': (r / 'cr15c-after-v2-source/server/app', e / 'cr15c-after-v2-source-manifest.json')}
CELLS = [('typical', 1), ('typical', 4), ('typical', 8), ('typical', 12), ('typical', 16), ('heavy', 1), ('heavy', 4), ('heavy', 12)]
FIXTURE_FILES = ['server.py', 'harness.py', 'metadata_sizes.py']
CLIENT_CPUS, SERVER_CPUS = '0,1', '6'
GUARD = 300


def docker(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], **kw)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sources_ok():
    for side, (src, man) in SOURCES.items():
        for name, digest in json.loads(man.read_text(encoding='utf-8'))['files'].items():
            assert sha(src / name) == digest, (side, name)


def one(side, n, mix, run, stem):
    assert 'npipe://' in docker('context', 'inspect', 'desktop-linux', capture_output=True, text=True, check=True).stdout
    network = f'cr-cr15c-v2-obva7te6-{stem}'
    client = network + '-client'
    env = os.environ.copy()
    env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false',
               TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1', BURST_N=str(n), BURST_MIX=mix, BURST_RUN=str(run),
               BURST_GUARD_SECONDS=str(GUARD))
    docker('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', network, capture_output=True, check=True)
    server = None
    try:
        server = docker('run', '--detach', '--rm', '--name', network + '-server', '--network', network, '--network-alias', 'tracker.fixture.invalid',
                        '--read-only', '--cpus', '1', '--cpuset-cpus', SERVER_CPUS, '--memory', '512m', '--tmpfs', '/tmp',
                        '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--workdir', '/fixture', '--entrypoint', 'python', IMAGE,
                        '/fixture/server.py', capture_output=True, text=True, check=True).stdout.strip()
        deadline = time.monotonic() + 90
        while docker('exec', server, 'python', '-c',
                     "import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/ready',timeout=1))['ready']",
                     capture_output=True).returncode != 0:
            if time.monotonic() > deadline:
                raise RuntimeError('fixture not ready')
            time.sleep(.2)
        cmd = ['run', '--name', client, '--network', network, '--read-only', '--cpus', '2', '--cpuset-cpus', CLIENT_CPUS, '--memory', '1g', '--memory-swap', '1g',
               '--tmpfs', '/tmp', '--mount', 'type=volume,target=/app/data', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
               '--mount', f'type=bind,source={SOURCES[side][0]},target=/app/app,readonly']
        for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE', 'BURST_N', 'BURST_MIX', 'BURST_RUN',
                    'BURST_GUARD_SECONDS']:
            cmd += ['--env', key]
        cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, '/fixture/harness.py']
        began = time.monotonic()
        res = docker(*cmd, env=env, capture_output=True, text=True, encoding='utf-8')
        seconds = time.monotonic() - began
        state = docker('inspect', '-f', '{{.State.OOMKilled}} {{.State.ExitCode}}', client, capture_output=True, text=True).stdout.split()
        docker('rm', '-v', client, capture_output=True)
        row = dict(side=side, mix=mix, n=n, exit_code=res.returncode, oom_killed=bool(state) and state[0] == 'true', container_seconds=seconds)
        if res.returncode == 0:
            row['result'] = json.loads(res.stdout)
        return row, res
    finally:
        if server is not None:
            docker('stop', '--time', '5', server, capture_output=True)
        docker('network', 'rm', network, capture_output=True)


def order():
    runs = []
    for s in ('s1', 's2'):
        for i in range(5):
            pair = ['before', 'after'] if i % 2 == 0 else ['after', 'before']
            for mix, n in CELLS:
                runs += [(s, i, side, mix, n) for side in pair]
    return runs


mode = sys.argv[1]
if mode == 'smoke':
    sources_ok()
    out = r / 'cr15c-after-v2-smoke'
    out.mkdir(exist_ok=True)
    for side, mix, n in [('before', 'typical', 4), ('after', 'typical', 4), ('after', 'typical', 16), ('after', 'heavy', 1)]:
        row, res = one(side, n, mix, 900, f'smoke-{side}-{mix}-{n}')
        (out / f'{side}-{mix}-{n}.json').write_text(json.dumps(row, indent=1), encoding='utf-8')
        (out / f'{side}-{mix}-{n}.stderr').write_text(res.stderr, encoding='utf-8')
        print(side, mix, n, row['exit_code'], row['oom_killed'], flush=True)
elif mode == 'register':
    sources_ok()
    t = e / 'cr15c-after-v2-protocol.json'
    assert not t.exists()
    p = dict(
        id='cr15c-after-v2', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='Final packet 27 (CR15/c) gate; registered before any measured run (a wiring smoke of 4 runs preceded it).',
        slo=dict(source='User decision 2026-11-07, recorded in the feature doc before this gate', deadline_s=15, max_parallel=12, container_memory='1 GiB'),
        change=('Process-wide admission (12 unique source searches, joiners free, the 13th fast SearchOverloadedError -> 503); 15 s overall deadline from owned-task '
                'start with partial results; per-indexer download gate (5) admitting only while the process-wide pending-byte budget (32 MiB) has room; one store '
                'at a time in chunks of at most 16 MiB; TorrentInfo cache also bounded by 50 000 file entries.'),
        before='frozen wip/cr15-chain-v3 a4b9229 server/app (landing base)', after='frozen wip/cr15-chain-v3 438b72f server/app', previous='cr15c-after-v1 PASS on the CR15a v2 base',
        image=IMAGE, fixture_sha256={n: sha(fx / n) for n in FIXTURE_FILES}, controller_sha256=sha(Path(__file__)),
        assessor_sha256=sha(r / 'assess_cr15c_after_v2.py'), cells=CELLS, guard_seconds=GUARD,
        workload='Unchanged burst27 fixture/harness (as burst27-v3): N simultaneous unique IMDb searches, 40 candidates each, typical ~5.7 MB and heavy ~111 MB per search.',
        sampling='Two series x five before/after pairs; within a pair index all cells run, each as an ABBA-ordered before/after pair; fresh client and server per run.',
        resources='client 2 CPU on 0,1 / 1 GiB, no swap, DB on a fresh anonymous volume; server 1 CPU on 6 / 512 MiB; runs alongside the CR15a v3 (8-10), 26b (2-4) and G04 (12-14) gates on disjoint cpusets.',
        decision=('PASS iff all of: (A) every after run exits 0 without OOM, guard timeout or outbound call, and every before typical run N<=12 completes; '
                  '(B) after typical N in {1,4,8,12}: every search returns 40 sources, 0 errors, 40 unique hashes; after typical N=16: exactly 12 searches complete '
                  'correctly and exactly 4 raise SearchOverloadedError within 100 ms each; after heavy N in {1,4,12}: every search returns either 40 correct sources '
                  'or a partial result with exactly one error (the deadline message), no exception, and no search exceeds 18 000 ms (15 s deadline + bounded store '
                  'of already downloaded bytes); (C) after typical N<=12: both series medians of run p95 <= 15 000 ms; (D) no repeatable degradation for typical '
                  'N in {1,4,8,12} in p50_ms, p95_ms, anon_peak_delta, cpu_seconds: degradation iff both after series medians > before max (all ten) + J, '
                  'J = max(|median before s1 - median before s2|, resolution 1 ms / 1 ms / 1 MiB / 0.01 s). Before heavy and N=16 cells are descriptive. '
                  'FAIL otherwise; INVALID if runs are missing or a before typical N<=12 run fails.'),
        pre_registration_diagnostics=('Candidate tuning on the burst harness (not gate data): heavy N=4 anon peak +745 MiB at 64/32 MiB budget, +497 MiB at 32/16 MiB; '
                                      'typical N=12 p95 9.7 s; heavy N=12 no OOM, searches end by ~15.2 s.'))
    t.write_text(json.dumps(p, indent=1), encoding='utf-8')
    print('registered', p['registered_at_utc'], sha(t)[:12])
elif mode == 'run':
    protocol = json.loads((e / 'cr15c-after-v2-protocol.json').read_text(encoding='utf-8'))
    assert protocol['controller_sha256'] == sha(Path(__file__)) and protocol['assessor_sha256'] == sha(r / 'assess_cr15c_after_v2.py')
    assert all(sha(fx / n) == d for n, d in protocol['fixture_sha256'].items())
    sources_ok()
    for index, (s, i, side, mix, n) in enumerate(order()):
        stem = f'cr15c-after-v2-{mix}-{n}-{side}-{s}-{i}'
        assert not (e / (stem + '.json')).exists()
        row, res = one(side, n, mix, 1000 + index, stem.removeprefix('cr15c-after-v2-'))
        (e / (stem + '.stderr')).write_text(res.stderr, encoding='utf-8')
        (e / (stem + '.json')).write_text(json.dumps(row, indent=1), encoding='utf-8')
        print(stem, row['exit_code'], 'oom' if row['oom_killed'] else '', flush=True)
    (e / 'cr15c-after-v2-complete.json').write_text(json.dumps(dict(id='cr15c-after-v2', runs=len(order()),
                                                                     completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())), encoding='utf-8')
else:
    raise SystemExit('unknown mode')
