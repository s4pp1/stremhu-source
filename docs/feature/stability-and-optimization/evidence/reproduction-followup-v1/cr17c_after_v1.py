"""CR17/c packet 21b runtime gate controller (cr17c-after-v1). Strictly serial; all attempts retained.

Phases: smoke -> short (2x5 paired) -> references (5 rotated ABC) -> direct (2x5 paired + 5 rotated ABC)
-> kodi (2x5 paired + 5 rotated ABC) -> long (3 contemporaneous full 1800s pairs).
before = Source2 (050cb337 app), after/C = frozen packet21b source. A failed run is recorded and the
controller continues, so the assessor sees every attempt; acceptance is decided only by the assessor.
"""
from pathlib import Path
import hashlib
import json
import os
import secrets
import subprocess
import sys

r = Path(__file__).parent
repo = Path.cwd()
e = r / 'evidence'
protocol_path = e / 'cr17c-after-v1-protocol.json'
protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert protocol['controller_sha256'] == sha(Path(__file__))
images = protocol['images']
sources = {'before': r / 'cr17a-drain-fix-v2-source/server', 'after': r / 'cr17c-after-v1-source/server', 'B': r / 'baseline/server'}
sources['C'] = sources['after']
fixtures = {name: r / name for name in protocol['fixture_sha256']}
manifests = {'before': 'cr17a-drain-checked-v2-manifest.json', 'after': 'cr17c-checked-v1-manifest.json'}


def verify(label):
    for name, digest in protocol['fixture_sha256'].items():
        assert sha(fixtures[name]) == digest, name
    key = 'after' if label in ('after', 'C') else label
    if key in manifests:
        files = json.loads((e / manifests[key]).read_text())['files']
        assert all(sha(sources[key] / p) == h for p, h in files.items() if p.startswith('app/')), key


env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48),
           STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
failed = []


def run(phase, label, series, repetition, fixture, flag=None, cpus='8,9', timeout=300):
    stem = f'cr17c-after-v1-{phase}-{label}-{series}-{repetition}'
    assert not (e / (stem + '.json')).exists() and not (e / (stem + '-failed.json')).exists()
    verify(label)
    image = images['A' if label == 'A' else 'C']
    cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--name', stem + '-obva7te6', '--label', 'stremhu.cr.owner=obva7te6',
           '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', cpus, '--memory', '1g',
           '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--tmpfs', '/fixture-output']
    for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'PYTHONDONTWRITEBYTECODE']:
        cmd += ['--env', key]
    cmd += ['--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={fixtures[fixture]},target=/fixture/probe.py,readonly']
    if label != 'A':
        cmd += ['--mount', f'type=bind,source={sources[label] / "app"},target=/app/app,readonly']
    cmd += ['--entrypoint', 'python', image, '/fixture/probe.py'] + ([flag] if flag else [])
    with (e / (stem + '.stdout')).open('w', encoding='utf-8') as out, (e / (stem + '.stderr')).open('w', encoding='utf-8') as err:
        try:
            code = subprocess.run(cmd, env=env, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            subprocess.run(['docker', '--context', 'desktop-linux', 'stop', '--time', '5', stem + '-obva7te6'], capture_output=True)
            code = 'timeout'
    if code != 0:
        stderr = (e / (stem + '.stderr')).read_bytes()
        (e / (stem + '-failed.json')).write_text(json.dumps(dict(
            protocol=protocol['id'], phase=phase, label=label, series=series, repetition=repetition, exit=code,
            detached_instance_error='DetachedInstanceError' in stderr.decode('utf-8', 'replace'), stderr_sha256=hashlib.sha256(stderr).hexdigest())), encoding='utf-8')
        failed.append(stem)
        print(stem, 'FAILED', code, flush=True)
        return
    data = json.loads((e / (stem + '.stdout')).read_text(encoding='utf-8'))
    data.update(protocol=protocol['id'], phase=phase, label=label, series=series, repetition=repetition, fixture=fixture,
                fixture_sha256=protocol['fixture_sha256'][fixture], image=image, cpus=cpus,
                actual_source='pinnedAimage' if label == 'A' else sources[label].parent.name)
    (e / (stem + '.json')).write_text(json.dumps(data), encoding='utf-8')
    print(stem, 'saved', flush=True)


paired = lambda i: ['before', 'after'] if i % 2 == 0 else ['after', 'before']
rotated = lambda i: [['A', 'B', 'C'], ['B', 'C', 'A'], ['C', 'A', 'B']][i % 3]
POLICY, REFERENCE = 'cr17c-policy-fixture-v1.py', 'cr17c-policy-reference-fixture-v1.py'
DIRECT, KODI = 'cr17c-policy-direct-fixture-v1.py', 'cr17c-kodi-ownership-observation-v1.py'

for label in ['after', 'before']:
    run('smoke', label, 'smoke', 0, POLICY, '--fixture-smoke')
for phase, fixture in [('short', POLICY), ('direct', DIRECT), ('kodi', KODI)]:
    for series in ['a', 'b']:
        for i in range(5):
            for label in paired(i):
                run(phase, label, series, i, fixture)
    for i in range(5):
        for label in rotated(i):
            run(phase, label, 'ref', i, REFERENCE if phase == 'short' else fixture)
for pair, order in enumerate([['after', 'before'], ['before', 'after'], ['after', 'before']]):
    for label in order:
        print(f'long {label} pair {pair} starting full1800seconds', flush=True)
        run('long', label, 'pair', pair, POLICY, '--heap-profile', cpus='6,7', timeout=3600)
(e / 'cr17c-after-v1-complete.json').write_text(json.dumps(dict(
    protocol=protocol['id'], status='All configured attempts finished; NOT acceptance', failed_attempts=failed)), encoding='utf-8')
print('All cr17c-after-v1 attempts finished; failed:', failed, flush=True)
sys.exit(0)
