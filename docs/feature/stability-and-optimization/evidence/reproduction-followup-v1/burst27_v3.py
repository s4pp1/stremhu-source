"""Packet 27 burst input v3 (descriptive baseline, no parameter selected; v3 = v2 on the CR15a v2 landing tree f90e752). argv: diag | register | run
v2 replaces v1 (registered, never run): the test DB lives on a per-run anonymous Docker volume, because a tmpfs DB/WAL is
charged to the 1 GiB container limit as unreclaimable memory and caused OOM kills that production (DB on disk) would not see.
freeze: frozen source of the landing base (wip/cr15b-cookie-scope 87dfeba = CR15a + 26a) with manifest.
smoke: wiring only (not a measurement), small N, never published as a result.
"""
import datetime
import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
import tarfile
import time
from pathlib import Path

r = Path(__file__).parent
repo = Path.cwd()
e = r / 'evidence'
fx = r / 'burst27-v1-fixture'
src = r / 'cr15b-after-v2-source'
COMMIT = 'f90e752'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
CLIENT_CPUS, SERVER_CPUS = '0,1', '6'
MIXES = {'typical': [1, 2, 4, 8, 16, 32], 'heavy': [1, 2, 4]}
REPETITIONS = 5
FIXTURE_FILES = ['server.py', 'harness.py', 'metadata_sizes.py']


def docker(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], **kw)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest_ok():
    man = json.loads((e / 'cr15b-after-v2-source-manifest.json').read_text(encoding='utf-8'))
    for name, digest in man['files'].items():
        assert sha(src / 'server/app' / name) == digest, name
    return man


def one(n, mix, run, stem, guard=900, memory='1g'):
    assert docker('context', 'inspect', 'desktop-linux', capture_output=True, text=True, check=True).stdout.count('npipe://') >= 1
    network = f'cr-burst27-v3-obva7te6-{stem}'
    env = os.environ.copy()
    env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false',
               TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1', BURST_N=str(n), BURST_MIX=mix, BURST_RUN=str(run),
               BURST_GUARD_SECONDS=str(guard))
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
        cmd = ['run', '--name', network + '-client', '--network', network, '--read-only', '--cpus', '2', '--cpuset-cpus', CLIENT_CPUS,
               '--memory', memory, '--memory-swap', memory, '--tmpfs', '/tmp', '--mount', 'type=volume,target=/app/data',
               '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--mount', f'type=bind,source={src / "server/app"},target=/app/app,readonly']
        for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE', 'BURST_N', 'BURST_MIX', 'BURST_RUN',
                    'BURST_GUARD_SECONDS']:
            cmd += ['--env', key]
        cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, '/fixture/harness.py']
        began = time.monotonic()
        res = docker(*cmd, env=env, capture_output=True, text=True, encoding='utf-8')
        seconds = time.monotonic() - began
        state = docker('inspect', '-f', '{{.State.OOMKilled}} {{.State.ExitCode}}', network + '-client', capture_output=True, text=True).stdout.split()
        docker('rm', '-v', network + '-client', capture_output=True)
        res.oom_killed = bool(state) and state[0] == 'true'
        return res, seconds
    finally:
        if server is not None:
            docker('stop', '--time', '5', server, capture_output=True)
        docker('network', 'rm', network, capture_output=True)


mode = sys.argv[1]
if mode == 'diag':
    manifest_ok()
    n, mix, memory = int(sys.argv[2]), sys.argv[3], sys.argv[4]
    res, seconds = one(n, mix, 0, f'diag-{mix}-{n}', guard=300, memory=memory)
    out = r / 'burst27-v3-diag'
    out.mkdir(exist_ok=True)
    (out / f'diag-{mix}-{n}-{memory}.stdout').write_text(res.stdout, encoding='utf-8')
    (out / f'diag-{mix}-{n}-{memory}.stderr').write_text(res.stderr, encoding='utf-8')
    print(mix, n, memory, 'exit', res.returncode, f'{seconds:.1f}s', flush=True)
elif mode == 'register':
    man = manifest_ok()
    t = e / 'burst27-v3-protocol.json'
    assert not t.exists()
    cells = [(mix, n) for mix, ns in MIXES.items() for n in ns]
    p = dict(id='burst27-v3', supersedes=('burst27-v1 (never run; tmpfs DB charged to the memory limit) and burst27-v2 (never run; its source 87dfeba '
                                      'carried the CR15a v1 read path that failed cr15a-after-v1)'), registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             status='Descriptive packet 27 input (baseline + noise), registered before any measured run. Selects no parameter.',
             purpose=('Burst behaviour of the unchanged source-search path before CR15/c: latency, memory, task and retention peaks for N simultaneous '
                      'unique-IMDb searches. Implementation plan 2.3/Q6: baseline+noise first; the UX/SLO frame (deadline, RAM budget, minimum admitted '
                      'parallelism) is fixed in writing by the user before any packet 27 gate measurement and never fitted afterwards.'),
             source=dict(commit=COMMIT, branch='wip/cr15b-cookie-scope-v2 (CR15a v2 714afa2 + 26a, landing base of packet 27)',
                         manifest_sha256=sha(e / 'cr15b-after-v2-source-manifest.json'), files=len(man['files'])),
             image=IMAGE, fixture_sha256={n: sha(fx / n) for n in FIXTURE_FILES}, controller_sha256=sha(Path(__file__)),
             path=('TorrentSourceProviderService.find_by_imdb_id -> IndexerSearchService (12.5 s search timeout, tracker cache) -> shared synthetic '
                   'BaseIndexerDefinition adapter (default semaphore 5, real IndexerClient, bounded download 48 MiB) -> _sync_torrent_files gather -> '
                   'create_many (native parse, SQLite WAL on tmpfs). Only the adapter search parser is synthetic (one JSON page, 40 candidates).'),
             fixture=dict(search_delay_s=0.3, ttfb_s=0.08, rate_bytes_per_s_per_connection=8_000_000, candidates_per_search=40,
                          mixes={'typical': 'index 0 season-box (~1.36 MB, 1000 files), 1-5 remux (~410 KB), 6-15 pack (~104 KB), 16-39 movie (~51 KB); ~5.68 MB/search',
                                 'heavy': 'typical, but every index divisible by 8 is giant-valid (~21.5 MB, 10000 files, natively accepted): stress profile, ~111.5 MB/search'}),
             resources=dict(client='2 CPU, cpuset 0,1 (one physical core), 1 GiB memory, no swap; SQLite DB on a fresh anonymous Docker volume per run (page cache, reclaimable)', server='1 CPU, cpuset 6, 512 MiB',
                            coexisting='G04 gate on cpuset 12-14 may still run; G03/CR15a must have finished before the first measured run'),
             cells=cells, repetitions=REPETITIONS, order='cell order rotated by one position per repetition; one fresh client and server process per run',
             warmup='one unsampled typical-mix search per process before the burst; burst starts all N searches on one event',
             metrics=['per-search wall ms (p50/p95/max per run)', 'cgroup anon peak delta over the post-warm-up level (20 ms sampler)',
                      'OOM kill / exit state', 'asyncio task peak', 'event-loop lag max', 'download in-flight peak (client)',
                      'downloaded-but-not-stored bytes peak', 'store (create_many) call time max', 'server download concurrency peak',
                      'result correctness: 40 sources, 0 indexer errors, 40 unique info hashes per search'],
             summary_rule=('Per cell: median and range over repetitions of run p50/p95/max and anon peak delta; OOM count. Noise: per cell the spread '
                           '(max-min) of the run p95 over repetitions is reported as the noise estimate. No pass/fail; no parameter is chosen here.'),
             smoke_note=('v1 wiring smoke and diagnostics, including heavy N=2 at 4 GiB (anon peak +572 MiB, memory.current +876 MiB incl. tmpfs DB) and a '
                        'v2 volume-DB wiring diagnostic preceded registration and are not data.'))
    t.write_text(json.dumps(p, indent=1), encoding='utf-8')
    print('registered', p['registered_at_utc'], sha(t)[:12])
elif mode == 'run':
    protocol = json.loads((e / 'burst27-v3-protocol.json').read_text(encoding='utf-8'))
    assert protocol['controller_sha256'] == sha(Path(__file__))
    assert all(sha(fx / n) == d for n, d in protocol['fixture_sha256'].items())
    manifest_ok()
    cells = [tuple(c) for c in protocol['cells']]
    for rep in range(REPETITIONS):
        order = cells[rep % len(cells):] + cells[:rep % len(cells)]
        for mix, n in order:
            index = cells.index((mix, n))
            stem = f'burst27-v3-{mix}-{n}-r{rep}'
            assert not (e / (stem + '.json')).exists()
            print(stem, 'starting', flush=True)
            res, seconds = one(n, mix, rep * 100 + index, stem.removeprefix('burst27-v3-'))
            (e / (stem + '.stderr')).write_text(res.stderr, encoding='utf-8')
            row = dict(mix=mix, n=n, rep=rep, exit_code=res.returncode, oom_killed=res.oom_killed, container_seconds=seconds)
            if res.returncode == 0:
                row['result'] = json.loads(res.stdout)
            else:
                (e / (stem + '.stdout')).write_text(res.stdout, encoding='utf-8')
            (e / (stem + '.json')).write_text(json.dumps(row, indent=1), encoding='utf-8')
            print(stem, 'saved', res.returncode, 'oom' if res.oom_killed else '', flush=True)
    (e / 'burst27-v3-complete.json').write_text(json.dumps(dict(id='burst27-v3', completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                                                runs=REPETITIONS * len(cells))), encoding='utf-8')
else:
    raise SystemExit('unknown mode')
