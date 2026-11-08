"""G13-convert v2 candidate gate controller: two series x five before/after pairs (ABBA), fresh 1-CPU process each,
same deterministic fixtures as v1. before = frozen aaa9ee5 server/app, after = frozen wip/cr13c-subtitle-yield."""
import hashlib
import json
import os
import pathlib
import secrets
import subprocess

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'g13conv-v2'
protocol = json.loads((e / 'g13conv-v2-protocol.json').read_text(encoding='utf-8'))
if hashlib.sha256((fx / 'bench.py').read_bytes()).hexdigest() != protocol['fixture_sha256']:
    raise RuntimeError('Fixture drift')
SOURCES = {'before': (r / 'g02-post-cr17-v2-source/server/app', e / 'g02-post-cr17-v2-source-manifest.json'),
           'after': (r / 'g13conv-v2-after-source/server/app', e / 'g13conv-v2-after-source-manifest.json')}
for label, (src, man) in SOURCES.items():
    for name, digest in json.loads(man.read_text(encoding='utf-8'))['files'].items():
        if hashlib.sha256((src / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Frozen {label} source drift: {name}')


def call(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], check=True, **kw)


context = json.loads(call('context', 'inspect', 'desktop-linux', capture_output=True, text=True).stdout)[0]
if not context['Endpoints']['docker']['Host'].startswith('npipe://'):
    raise RuntimeError('Not local Docker Desktop')
env = os.environ.copy()
env.update(HOST_IP=(pathlib.Path.cwd() / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false')
for s in ('s1', 's2'):
    for i in range(5):
        for side in (['before', 'after'] if i % 2 == 0 else ['after', 'before']):
            stem = f'g13conv-v2-{side}-{s}-{i}'
            target = e / (stem + '.json')
            if target.exists():
                raise RuntimeError('Refusing evidence overwrite')
            out = r / 'g13conv-v2-output' / stem
            out.mkdir(parents=True, exist_ok=False)
            cmd = ['run', '--rm', '--name', 'cr-obva7te6-' + stem, '--label', 'stremhu.task=obva7te6', '--network', 'none', '--read-only', '--cpus', '1',
                   '--cpuset-cpus', protocol['cpuset'], '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--env', 'HOST_IP', '--env',
                   'SESSION_SECRET', '--env', 'STREMHU_LOAD_DOTENV', '--env', 'PYTHONPATH=/app', '--env', 'PYTHONDONTWRITEBYTECODE=1',
                   '--mount', f'type=bind,source={fx},target=/fixture,readonly', '--mount', f'type=bind,source={out},target=/out',
                   '--mount', f'type=bind,source={SOURCES[side][0]},target=/app/app,readonly',
                   '--entrypoint', 'python', protocol['image'], '-W', 'ignore', '/fixture/bench.py', stem, '/out/result.json']
            print(stem, 'starting', flush=True)
            with (e / (stem + '.stdout')).open('w', encoding='utf-8') as so, (e / (stem + '.stderr')).open('w', encoding='utf-8') as se:
                call(*cmd, env=env, stdout=so, stderr=se)
            d = json.loads((out / 'result.json').read_text(encoding='utf-8'))
            d.update(side=side, series=s, pair=i, image=protocol['image'])
            target.write_text(json.dumps(d), encoding='utf-8')
            print(stem, 'saved', flush=True)
(e / 'g13conv-v2-complete.json').write_text(json.dumps(dict(complete=True)), encoding='utf-8')
print('G13-convert v2 controller finished', flush=True)
