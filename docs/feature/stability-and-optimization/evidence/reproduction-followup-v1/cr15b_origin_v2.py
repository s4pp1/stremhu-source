"""Packet 26a functional origin gate (v2): same as v1 (PASS on 87dfeba) on the rebased landing tree: before (frozen aaa9ee5) and
after (frozen wip/cr15b-cookie-scope-v2 f90e752 = fixed CR15a 714afa2 + 26a), after twice. Fresh ephemeral fixture CA in an owned fixture dir; the key
is never displayed, copied elsewhere or staged. argv: register | run | assess"""
import datetime
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

r = Path(__file__).parent
repo = Path.cwd()
e = r / 'evidence'
fx = r / 'cr15b-origin-v2-fixture'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
SOURCES = {'before': (r / 'g02-post-cr17-v2-source/server/app', e / 'g02-post-cr17-v2-source-manifest.json'),
           'after': (r / 'cr15b-after-v2-source/server/app', e / 'cr15b-after-v2-source-manifest.json')}
TARGETS = ['relative', 'same-origin', 'other-port', 'subdomain', 'other-host', 'downgrade']
EXPECTED_AFTER_PERSISTED = [1, 1, 1, 0, 0, 0]
RUNS = [('before', 0), ('after', 0), ('after', 1)]


def call(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], check=True, **kw)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def matrix(d):
    out = {}
    for row in d['rows']:
        out.setdefault(row['mode'], [None] * 6)[TARGETS.index(row['target'])] = row['cookie_present_count']
    return out


if sys.argv[1] == 'register':
    assert not fx.exists()
    fx.mkdir()
    (fx / 'pki').mkdir()
    for name in ['server.py', 'probe.py', 'metadata_sizes.py']:
        shutil.copy2(r / 'g15-tls-origin-fixture-v1' / name, fx / name)
    call('run', '--rm', '--network', 'none', '--read-only', '--cpus', '1', '--cpuset-cpus', '0', '--memory', '256m', '--tmpfs', '/tmp',
         '--mount', f'type=bind,source={fx / "pki"},target=/pki', '--entrypoint', 'openssl', IMAGE, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-sha256', '-days', '30', '-subj', '/CN=tracker.fixture.invalid', '-addext',
         'subjectAltName=DNS:tracker.fixture.invalid,DNS:cdn.fixture.invalid,DNS:cdn.other.invalid', '-keyout', '/pki/key.pem', '-out', '/pki/cert.pem',
         capture_output=True)
    t = e / 'cr15b-origin-v2-protocol.json'
    assert not t.exists()
    p = dict(id='cr15b-origin-v2', previous='cr15b-origin-v1 PASS on 87dfeba (CR15a v1 read path); rerun because the landing tree changed (CR15a v2 read fix)', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             status='Final packet 26a functional gate (v2, landing tree); registered before any run.',
             change='Persisted name/value cookies restored as Secure (https) domain cookies of the indexer host instead of domain-less jar entries.',
             before='frozen aaa9ee5 server/app', after='frozen wip/cr15b-cookie-scope-v2 f90e752 server/app (CR15a v2 714afa2 included)', image=IMAGE,
             fixture='Unchanged G15 verified fixture-TLS origin probe/server (g15-tls-origins-v1), fresh ephemeral fixture CA; adapter url = https://tracker.fixture.invalid:8443.',
             fixture_sha256={n: sha(fx / n) for n in ['server.py', 'probe.py', 'metadata_sizes.py']}, certificate_sha256=sha(fx / 'pki/cert.pem'),
             controller_sha256=sha(Path(__file__)), runs=RUNS, targets=TARGETS,
             decision=('PASS iff every run returns 18 verified rows with the valid 82073-byte body; before reproduces persisted = [1,1,1,1,1,1]; '
                       'both after runs give persisted = [1,1,1,0,0,0] (own host any port over https only; sibling host, foreign host and HTTP downgrade '
                       'without cookie); fresh-host and fresh-wide rows identical to before. Otherwise FAIL.'),
             note='subdomain target here is the sibling host cdn.fixture.invalid, not a subdomain of the indexer host; functional, not a performance gate.')
    t.write_text(json.dumps(p, indent=1), encoding='utf-8')
    print('registered', p['registered_at_utc'], sha(t)[:12])
elif sys.argv[1] == 'run':
    protocol = json.loads((e / 'cr15b-origin-v2-protocol.json').read_text(encoding='utf-8'))
    assert all(sha(fx / n) == d for n, d in protocol['fixture_sha256'].items()) and sha(fx / 'pki/cert.pem') == protocol['certificate_sha256']
    for label, (src, man) in SOURCES.items():
        for name, digest in json.loads(man.read_text(encoding='utf-8'))['files'].items():
            assert sha(src / name) == digest, name
    assert json.loads(call('context', 'inspect', 'desktop-linux', capture_output=True, text=True).stdout)[0]['Endpoints']['docker']['Host'].startswith('npipe://')
    env = os.environ.copy()
    env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false',
               TEST_BASE_URL='https://tracker.fixture.invalid:8443', PYTHONDONTWRITEBYTECODE='1')
    for side, i in RUNS:
        stem = f'cr15b-origin-v2-{side}-{i}'
        assert not (e / (stem + '.json')).exists()
        network = 'cr-cr15b-origin-v2-obva7te6'
        call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', network, capture_output=True)
        server = None
        try:
            server = call('run', '--detach', '--rm', '--name', network + '-server', '--network', network, '--network-alias', 'tracker.fixture.invalid',
                          '--network-alias', 'cdn.fixture.invalid', '--network-alias', 'cdn.other.invalid', '--read-only', '--cpus', '1', '--cpuset-cpus', '6',
                          '--memory', '512m', '--tmpfs', '/tmp', '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--entrypoint', 'python', IMAGE,
                          '/fixture/server.py', capture_output=True, text=True).stdout.strip()
            deadline = time.monotonic() + 45
            while subprocess.run(['docker', '--context', 'desktop-linux', 'exec', server, 'python', '-c',
                                  "import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/ready',timeout=1))['ready']"],
                                 capture_output=True).returncode != 0:
                if time.monotonic() > deadline:
                    raise RuntimeError('fixture not ready')
                time.sleep(.1)
            cmd = ['run', '--rm', '--name', network + '-client', '--network', network, '--read-only', '--cpus', '2', '--cpuset-cpus', '0,1', '--memory', '1g',
                   '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
                   '--mount', f'type=bind,source={SOURCES[side][0]},target=/app/app,readonly']
            for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE']:
                cmd += ['--env', key]
            cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, '/fixture/probe.py']
            res = subprocess.run(['docker', '--context', 'desktop-linux', *cmd], env=env, capture_output=True, text=True, encoding='utf-8')
            (e / (stem + '.stdout')).write_text(res.stdout, encoding='utf-8')
            (e / (stem + '.stderr')).write_text(res.stderr, encoding='utf-8')
            if res.returncode:
                raise RuntimeError('probe failed; raw retained')
            d = json.loads(res.stdout)
            d.update(side=side, run=i, image=IMAGE)
            (e / (stem + '.json')).write_text(json.dumps(d, indent=1), encoding='utf-8')
            print(stem, 'saved', flush=True)
        finally:
            if server is not None:
                subprocess.run(['docker', '--context', 'desktop-linux', 'stop', '--time', '5', server], capture_output=True)
            subprocess.run(['docker', '--context', 'desktop-linux', 'network', 'rm', network], capture_output=True)
else:
    runs = {(s, i): json.loads((e / f'cr15b-origin-v2-{s}-{i}.json').read_text(encoding='utf-8')) for s, i in RUNS}
    ok_rows = all(len(d['rows']) == 18 and all(x['decoded_bytes'] == 82073 and x['tls_hostname_verification'] for x in d['rows']) for d in runs.values())
    m = {k: matrix(d) for k, d in runs.items()}
    before = m[('before', 0)]
    checks = dict(rows_valid=ok_rows, before_reproduces=before['persisted'] == [1] * 6,
                  after_persisted=all(m[('after', i)]['persisted'] == EXPECTED_AFTER_PERSISTED for i in (0, 1)),
                  fresh_unchanged=all(m[('after', i)][mode] == before[mode] for i in (0, 1) for mode in ('fresh-host', 'fresh-wide')))
    out = dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks, matrices={f'{s}-{i}': v for (s, i), v in m.items()}, targets=TARGETS,
               protocol_sha256=sha(e / 'cr15b-origin-v2-protocol.json'), assessor_sha256=sha(Path(__file__)))
    (e / 'cr15b-origin-v2-assessment.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out))
