"""CR17/b V6 FAIL follow-up: preregistered diagnostics only (no acceptance, no budget change)."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import secrets
import subprocess

r = Path(__file__).parent
repo = Path.cwd()
e = r / 'evidence'
image = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
gc_fixture = r / 'cr17a-cold-gc-diagnostic-fixture-v4.py'
long_fixture = r / 'cr17b-policy-fixture-v2.py'
sources = {'S2': r / 'cr17a-drain-fix-v2-source/server', 'S4': r / 'cr17b-after-v4-source/server'}
manifests = {'S2': 'cr17a-drain-checked-v2-manifest.json', 'S4': 'cr17b-checked-v4-manifest.json'}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def verify(label):
    files = json.loads((e / manifests[label]).read_text())['files']
    assert all(sha(sources[label] / name) == digest for name, digest in files.items() if name.startswith('app/'))


protocol = dict(
    id='cr17b-noise-gc-diagnostic-v7',
    registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    reason='cr17b-policy-composite-assessment-v6 FAIL: heap c8 p95 (same-result-key, unique-result-key-warm-metadata) and heap cold user1 wall. Existing five Source2 long runs span 165.5-190.2ms (same c8) and 1120.4-1162.5ms (unique c8); cold user1 is bimodal (Source7 ~106ms, Source2 ~75ms, SourceV4 ~104ms) and resembles the CR17/a gen2 GC phase shift.',
    status_rule='Diagnostic only. The V6 FAIL is never relabelled; no threshold, acceptance or production GC change follows from this protocol. Results inform a separate user decision.',
    sampling=('Phase1 GC: five fresh-process pairs S2/S4 with the unchanged published cr17a GC fixture v4, order S2,S4 for even and S4,S2 for odd repetitions. '
              'Phase2 long: three contemporaneous full1800s/60cycle pairs with the unchanged cr17b policy fixture v2, order S4,S2 / S2,S4 / S4,S2. All completed runs retained; no truncation or selection.'),
    analysis=('GC: per run the generation-2 event phase and cold user0/user1/combined wall. GC-shift hypothesis is supported only if in >=4/5 pairs S2 gen2 falls in cold-0 and S4 gen2 in cold-1, and the median paired combined-wall difference S4-S2 is within +-10ms. '
              'Long: per (kind,concurrency) run medians of p95_ms, cpu_seconds, heap_bytes_after_gc, memory; per pair S4-S2 difference; S2 pooled range over the five existing plus three new runs and S4 over two V6 plus three new runs. '
              'c8 p95 is described as within noise only if the median contemporaneous paired difference is <=+10ms AND every S4 run median is <= max(pooled S2 run medians); otherwise it stays a regression candidate.'),
    resources='Pinned C image, 2CPU6,7/1GiB, networknone, read-only frozen app, tmpfs disposable DB, no dotenv/real credentials; strictly serial; no other Docker benchmark during this protocol.',
    image=image,
    gc_fixture_sha256=sha(gc_fixture),
    long_fixture_sha256=sha(long_fixture),
    source_manifest_sha256={label: sha(e / name) for label, name in manifests.items()},
)
path = e / 'cr17b-noise-gc-diagnostic-v7-protocol.json'
if path.exists():
    raise RuntimeError('Refusing protocol overwrite')
path.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
print('registered', protocol['id'], flush=True)

env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48),
           STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')


def run(stem, label, fixture):
    verify(label)
    assert sha(fixture) == (protocol['gc_fixture_sha256'] if fixture == gc_fixture else protocol['long_fixture_sha256'])
    assert not (e / (stem + '.json')).exists()
    cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--name', stem.lower() + '-obva7te6', '--label', 'stremhu.cr.owner=obva7te6',
           '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', '6,7', '--memory', '1g',
           '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--tmpfs', '/fixture-output']
    for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'PYTHONDONTWRITEBYTECODE']:
        cmd += ['--env', key]
    cmd += ['--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={fixture},target=/fixture/probe.py,readonly',
            '--mount', f'type=bind,source={sources[label] / "app"},target=/app/app,readonly',
            '--entrypoint', 'python', image, '/fixture/probe.py', '--heap-profile']
    with (e / (stem + '.stdout')).open('w', encoding='utf-8') as out, (e / (stem + '.stderr')).open('w', encoding='utf-8') as err:
        result = subprocess.run(cmd, env=env, stdout=out, stderr=err)
    if result.returncode:
        raise RuntimeError(f'{stem} exit {result.returncode}; raw retained, protocol stopped')
    data = json.loads((e / (stem + '.stdout')).read_text(encoding='utf-8'))
    data.update(protocol=protocol['id'], label=label, source=sources[label].parent.name, image=image)
    return data


for i in range(5):
    for label in (['S2', 'S4'] if i % 2 == 0 else ['S4', 'S2']):
        stem = f'cr17b-noise-gc-v7-{label}-{i}'
        d = run(stem, label, gc_fixture)
        assert not d['is_measurement'] and d['default_gc_enabled'] and len(d['cold']) == 2
        (e / (stem + '.json')).write_text(json.dumps(d, indent=2), encoding='utf-8')
        print(stem, dict(cold_ms=[round(c['wall_seconds'] * 1000, 1) for c in d['cold']],
                         gc2=[(g['phase'], round(g['seconds'] * 1000, 1)) for g in d['gc_events'] if g['generation'] == 2]), flush=True)

for pair, order in enumerate([['S4', 'S2'], ['S2', 'S4'], ['S4', 'S2']]):
    for label in order:
        stem = f'cr17b-noise-long-v7-{label}-{pair}'
        print(stem, 'starting full1800seconds', flush=True)
        d = run(stem, label, long_fixture)
        assert d['is_measurement'] and d['profile']['measured_seconds'] >= 1800 and len(d['rows']) == 60 and not d['external_http_attempts']
        assert all(x['tasks_quiescent'] == 1 and x['pool_checked_out'] == 0 and x['background_tasks'] == 0 for x in d['rows'])
        d.update(pair=pair)
        (e / (stem + '.json')).write_text(json.dumps(d), encoding='utf-8')
        print(stem, 'saved', flush=True)
print('All V7 diagnostics complete; analysis still required', flush=True)
