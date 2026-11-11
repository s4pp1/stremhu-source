from pathlib import Path
import json, os, secrets, subprocess, sys
r = Path(sys.argv[1]); repo = Path(sys.argv[2])
protocol = json.loads((r / 'evidence/cr17c-after-v1-protocol.json').read_text(encoding='utf-8'))
image = protocol['images']['C']
sources = {'before': r / 'cr17a-drain-fix-v2-source/server', 'after': r / 'cr17c-after-v1-source/server'}
out = r / 'diag-cold-v1'; out.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
mode = sys.argv[3]
for i in range(3):
    for label in (['before', 'after'] if i % 2 == 0 else ['after', 'before']):
        stem = f'{mode}-{label}-{i}'
        cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--name', 'diag-' + stem + '-obva7te6', '--label', 'stremhu.cr.owner=obva7te6',
               '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', '6,7', '--memory', '1g',
               '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--tmpfs', '/fixture-output']
        for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'PYTHONDONTWRITEBYTECODE']:
            cmd += ['--env', key]
        cmd += ['--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={r / "cr17c-cold-diagnostic-v1.py"},target=/fixture/probe.py,readonly',
                '--mount', f'type=bind,source={sources[label] / "app"},target=/app/app,readonly', '--entrypoint', 'python', image, '/fixture/probe.py']
        if mode.startswith('heap'):
            cmd.append('--heap-profile')
        if mode.endswith('nocp'):
            cmd.append('--no-cprofile')
        with (out / (stem + '.stdout')).open('w', encoding='utf-8') as o, (out / (stem + '.stderr')).open('w', encoding='utf-8') as e:
            code = subprocess.run(cmd, env=env, stdout=o, stderr=e, timeout=600).returncode
        if code:
            print(stem, 'FAILED', code); continue
        d = json.loads((out / (stem + '.stdout')).read_text(encoding='utf-8').strip().splitlines()[-1])
        print(stem, [(c['count'], c['user'], round(c['wall_seconds'] * 1000, 1)) for c in d['cold']], d.get('gc'), flush=True)
