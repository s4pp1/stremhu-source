"""G02 post-CR17 C control (v2): two sequential monitor-free 3600 s runs of the unchanged G02 fixture on the frozen post-CR17 source."""
import hashlib
import json
import os
import pathlib
import secrets
import subprocess

r = pathlib.Path(__file__).parent
repo = pathlib.Path.cwd()
e = r / 'evidence'
protocol = json.loads((e / 'g02-post-cr17-v2-protocol.json').read_text(encoding='utf-8'))
if hashlib.sha256((r / 'g02-wal-fixture-v1.py').read_bytes()).hexdigest() != protocol['fixture_sha256']:
    raise RuntimeError('Fixture drift')
manifest = json.loads((e / 'g02-post-cr17-v2-source-manifest.json').read_text(encoding='utf-8'))
src = r / 'g02-post-cr17-v2-source/server/app'
for name, digest in manifest['files'].items():
    if hashlib.sha256((src / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError('Frozen source drift: ' + name)


def call(*args, **kwargs):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], check=True, **kwargs)


context = json.loads(call('context', 'inspect', 'desktop-linux', capture_output=True, text=True).stdout)[0]
if not context['Endpoints']['docker']['Host'].startswith('npipe://'):
    raise RuntimeError('Not local Docker Desktop')
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48),
           STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
import sys  # noqa: E402
RUNS = ['smoke'] if '--smoke' in sys.argv else protocol['runs']
for run in RUNS:
    stem = f'g02-post-cr17-{run}-v2'
    target = e / (stem + '.json')
    vol = 'cr-obva7te6-' + stem
    if target.exists():
        raise RuntimeError('Refusing evidence overwrite')
    call('volume', 'create', '--driver', 'local', '--label', 'stremhu.cr-task=obva7te6', '--label', 'stremhu.disposable=true', vol, capture_output=True)
    volume = json.loads(call('volume', 'inspect', vol, capture_output=True, text=True).stdout)[0]
    if volume['Driver'] != 'local' or volume['Labels'].get('stremhu.cr-task') != 'obva7te6' or volume['Labels'].get('stremhu.disposable') != 'true':
        raise RuntimeError('Unknown volume')
    cmd = ['run', '--rm', '--name', 'cr-obva7te6-' + stem, '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', protocol['cpuset'],
           '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--env', 'HOST_IP', '--env', 'SESSION_SECRET', '--env', 'STREMHU_LOAD_DOTENV',
           '--env', 'PYTHONDONTWRITEBYTECODE', '--env', 'PYTHONPATH=/app', '--env', 'TMPDIR=/fixture-db',
           '--mount', f'type=volume,source={vol},target=/fixture-db',
           '--mount', f'type=bind,source={src},target=/app/app,readonly',
           '--mount', f'type=bind,source={r / "g02-wal-fixture-v1.py"},target=/fixture/benchmark.py,readonly',
           '--entrypoint', 'python', protocol['image'], '/fixture/benchmark.py']
    if run == 'smoke':
        cmd.append('--fixture-smoke')
    print(run, 'starting', flush=True)
    with (e / (stem + '.stdout')).open('w', encoding='utf-8') as out, (e / (stem + '.stderr')).open('w', encoding='utf-8') as err:
        call(*cmd, env=env, stdout=out, stderr=err)
    d = json.loads((e / (stem + '.stdout')).read_text(encoding='utf-8'))
    if run != 'smoke' and (not d['is_measurement'] or d['measured_seconds'] < 3600):
        raise RuntimeError('Full run too short; raw retained')
    if len(d['cells']) != 9 or any(c['errors'] for c in d['cells']) or d['final_checkouts']:
        raise RuntimeError('Run invalid; raw retained')
    d.update(source_overlay=protocol['source'], image=protocol['image'], fixture_sha256=protocol['fixture_sha256'], cpuset=protocol['cpuset'], volume_name=vol)
    target.write_text(json.dumps(d), encoding='utf-8')
    print(run, 'saved', round(d['measured_seconds'], 1), 'seconds', flush=True)
if RUNS != ['smoke']:
    (e / 'g02-post-cr17-v2-complete.json').write_text(json.dumps(dict(runs=protocol['runs'], complete=True)), encoding='utf-8')
print('G02 post-CR17 control finished', flush=True)
