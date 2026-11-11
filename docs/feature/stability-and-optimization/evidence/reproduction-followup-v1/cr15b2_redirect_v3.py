"""Packet 26b functional gate (v3): redirect bodies unread + strict tracker-domain host policy (user decision 2026-11-07).
before = frozen f90e752 (CR15a v2 + 26a), after = frozen 51854ca (+ 26b with host policy), after twice. v1/v2 registered, never run.
argv: smoke | register | run | assess. smoke = wiring only (2 requests per concurrency), never data."""
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
fx = r / 'cr15b2-redirect-v3-fixture'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
SOURCES = {'before': (r / 'cr15b-after-v2-source/server/app', e / 'cr15b-after-v2-source-manifest.json'),
           'after': (r / 'cr15b2-after-v3-source/server/app', e / 'cr15b2-after-v3-source-manifest.json')}
RUNS = [('before', 0), ('after', 0), ('after', 1)]
FIXTURE = ['redirect_server.py', 'redirect_probe.py', 'metadata_sizes.py']
CPUS = dict(smoke=('0,1', '6'), run=('2,3', '4'))
AFTER_MAX_BYTES_PER_REQUEST = 16 << 20


def docker(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], **kw)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def one(side, stem, smoke):
    for name, digest in json.loads(SOURCES[side][1].read_text(encoding='utf-8'))['files'].items():
        assert sha(SOURCES[side][0] / name) == digest, name
    assert 'npipe://' in docker('context', 'inspect', 'desktop-linux', capture_output=True, text=True, check=True).stdout
    client_cpus, server_cpus = CPUS['smoke' if smoke else 'run']
    network = f'cr-cr15b2-redirect-v3-obva7te6-{stem}'
    env = os.environ.copy()
    env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false',
               TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1', REDIRECT_SMOKE='1' if smoke else '0')
    docker('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', network, capture_output=True, check=True)
    server = None
    try:
        server = docker('run', '--detach', '--rm', '--name', network + '-server', '--network', network, '--network-alias', 'tracker.fixture.invalid',
                        '--network-alias', 'dl.tracker.fixture.invalid', '--network-alias', 'cdn.other.invalid', '--read-only', '--cpus', '1', '--cpuset-cpus', server_cpus, '--memory', '512m', '--tmpfs', '/tmp',
                        '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--workdir', '/fixture', '--entrypoint', 'python', IMAGE,
                        '/fixture/redirect_server.py', capture_output=True, text=True, check=True).stdout.strip()
        deadline = time.monotonic() + 45
        while docker('exec', server, 'python', '-c',
                     "import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/ready',timeout=1))['ready']",
                     capture_output=True).returncode != 0:
            if time.monotonic() > deadline:
                raise RuntimeError('fixture not ready')
            time.sleep(.2)
        name = network + '-client'
        cmd = ['run', '--name', name, '--network', network, '--read-only', '--cpus', '2', '--cpuset-cpus', client_cpus, '--memory', '1g',
               '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
               '--mount', f'type=bind,source={SOURCES[side][0]},target=/app/app,readonly']
        for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE', 'REDIRECT_SMOKE']:
            cmd += ['--env', key]
        cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, '/fixture/redirect_probe.py']
        res = docker(*cmd, env=env, capture_output=True, text=True, encoding='utf-8')
        state = docker('inspect', '-f', '{{.State.OOMKilled}} {{.State.ExitCode}}', name, capture_output=True, text=True).stdout.split()
        docker('rm', name, capture_output=True)
        return res, dict(oom_killed=bool(state) and state[0] == 'true', exit_code=res.returncode)
    finally:
        if server is not None:
            docker('stop', '--time', '5', server, capture_output=True)
        docker('network', 'rm', network, capture_output=True)


mode = sys.argv[1]
if mode == 'smoke':
    out = r / 'cr15b2-redirect-v3-smoke'
    out.mkdir(exist_ok=True)
    for side in ('before', 'after'):
        res, state = one(side, f'smoke-{side}', True)
        (out / f'{side}.stdout').write_text(res.stdout, encoding='utf-8')
        (out / f'{side}.stderr').write_text(res.stderr, encoding='utf-8')
        print(side, state, flush=True)
elif mode == 'register':
    t = e / 'cr15b2-redirect-v3-protocol.json'
    assert not t.exists()
    p = dict(id='cr15b2-redirect-v3', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             status='Final packet 26b functional redirect-body gate; registered before any run (a 2-request wiring smoke preceded it).',
             change=('get_bounded follows redirects itself via Response.next_request, closes each redirect body unread, keeps history, max 10 hops; every hop must '
                     'target the tracker host or a subdomain with the tracker scheme (user decision 2026-11-07), otherwise no request is sent.'),
             before='frozen f90e752 server/app (CR15a v2 + 26a; cr15b-after-v2 manifest)', after='frozen 51854ca server/app (cr15b2-after-v3 manifest)',
             supersedes='cr15b2-redirect-v1 and -v2 (registered, never run; v2 lacked the host policy decided afterwards)',
             image=IMAGE, fixture_sha256={n: sha(fx / n) for n in FIXTURE}, controller_sha256=sha(Path(__file__)), runs=RUNS,
             workload=('giant: download_torrent through a 302 (Location: /final) whose chunked body is 64 MiB, 20 sequential then 20 at concurrency 4; '
                       'subdomain: 10 downloads redirected to dl.tracker.fixture.invalid; foreign: 10 downloads redirected to cdn.other.invalid. '
                       'Final = one natively valid 1 GiB/1-file metadata-only torrent; one server under three names; fresh client process per run.'),
             resources='client 2 CPU on 2,3 / 1 GiB; server 1 CPU on 4 / 512 MiB; internal network, no outbound; runs after G03 has finished.',
             decision=(f'PASS iff every run exits 0 without OOM; giant and subdomain requests all return the same final hash in every run; before '
                       f'reproduces the defects (every 64 MiB redirect body written completely; every foreign redirect followed: foreign /final hit '
                       f'once per request); in both after runs the server wrote at most {AFTER_MAX_BYTES_PER_REQUEST >> 20} MiB of redirect body per giant '
                       'request on average and no redirect body completed, every subdomain download succeeds via the subdomain, every foreign download '
                       'fails as an indexer error and the foreign host never receives a request. Otherwise FAIL; missing runs INVALID.'))
    t.write_text(json.dumps(p, indent=1), encoding='utf-8')
    print('registered', p['registered_at_utc'], sha(t)[:12])
elif mode == 'run':
    protocol = json.loads((e / 'cr15b2-redirect-v3-protocol.json').read_text(encoding='utf-8'))
    assert protocol['controller_sha256'] == sha(Path(__file__)) and all(sha(fx / n) == d for n, d in protocol['fixture_sha256'].items())
    for side, i in RUNS:
        stem = f'cr15b2-redirect-v3-{side}-{i}'
        assert not (e / (stem + '.json')).exists()
        print(stem, 'starting', flush=True)
        res, state = one(side, f'{side}-{i}', False)
        (e / (stem + '.stderr')).write_text(res.stderr, encoding='utf-8')
        if res.returncode:
            (e / (stem + '.stdout')).write_text(res.stdout, encoding='utf-8')
            (e / (stem + '.json')).write_text(json.dumps(dict(side=side, run=i, state=state)), encoding='utf-8')
        else:
            d = json.loads(res.stdout)
            d.update(side=side, run=i, image=IMAGE, state=state)
            (e / (stem + '.json')).write_text(json.dumps(d, indent=1), encoding='utf-8')
        print(stem, 'saved', state, flush=True)
    (e / 'cr15b2-redirect-v3-complete.json').write_text(json.dumps(dict(runs=RUNS, complete=True)), encoding='utf-8')
elif mode == 'assess':
    assert (e / 'cr15b2-redirect-v3-complete.json').exists()
    runs = {(s, i): json.loads((e / f'cr15b2-redirect-v3-{s}-{i}.json').read_text(encoding='utf-8')) for s, i in RUNS}
    problems = [f'{s}-{i} failed' for (s, i), d in runs.items() if d['state']['exit_code'] or d['state']['oom_killed'] or 'rows' not in d]
    checks = {}
    if not problems:
        def rows(d, case):
            return [row for row in d['rows'] if row['case'] == case]
        hashes = {o for d in runs.values() for case in ('giant', 'subdomain') for row in rows(d, case) for o in row['outcomes']}
        checks['giant_subdomain_success_same_hash'] = len(hashes) == 1 and not next(iter(hashes)).startswith('error:') and all(
            row['successes'] == row['requests'] for d in runs.values() for case in ('giant', 'subdomain') for row in rows(d, case))
        checks['subdomain_used'] = all(row['final_by_host']['dl.tracker.fixture.invalid'] == row['requests'] for d in runs.values() for row in rows(d, 'subdomain'))
        checks['before_reads_redirect_bodies'] = all(row['redirect_body_complete'] == row['requests'] for row in rows(runs[('before', 0)], 'giant'))
        checks['before_follows_foreign'] = all(row['successes'] == row['requests'] and row['final_by_host']['cdn.other.invalid'] == row['requests']
                                               for row in rows(runs[('before', 0)], 'foreign'))
        checks['after_does_not_read'] = all(row['redirect_body_complete'] == 0 and row['redirect_body_bytes'] / row['requests'] <= AFTER_MAX_BYTES_PER_REQUEST
                                            for i in (0, 1) for row in rows(runs[('after', i)], 'giant'))
        checks['after_blocks_foreign'] = all(row['successes'] == 0 and row['outcomes'] == ['error:IndexerDefinitionException']
                                             and row['final_by_host']['cdn.other.invalid'] == 0 for i in (0, 1) for row in rows(runs[('after', i)], 'foreign'))
        checks['no_outbound'] = all(d['external_http_attempts'] == 0 for d in runs.values())
    status = 'INVALID' if problems else 'PASS' if all(checks.values()) else 'FAIL'
    summary = {f'{s}-{i}': [dict(case=row['case'], successes=row['successes'], final_by_host=row['final_by_host'], concurrency=row['concurrency'], redirect_mib_per_request=row['redirect_body_bytes'] / row['requests'] / 2 ** 20,
                                 anon_peak_delta_mib=row['anon_peak_delta'] / 2 ** 20) for row in d.get('rows', [])] for (s, i), d in runs.items()}
    out = dict(status=status, problems=problems, checks=checks, summary=summary, protocol_sha256=sha(e / 'cr15b2-redirect-v3-protocol.json'),
               assessor_sha256=sha(Path(__file__)))
    (e / 'cr15b2-redirect-v3-assessment.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out))
else:
    raise SystemExit('unknown mode')
