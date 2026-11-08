"""Diagnostic (not a gate) for the cr17d-after-v1 memory FAIL: per-engine physical SQLite connections and peak
simultaneous checkouts, before (frozen packet21b) vs after (frozen packet22), short mode, alternating, 2 each."""
from pathlib import Path
import json, os, secrets, subprocess, sys
r = Path(__file__).parent; repo = Path(sys.argv[1])
image = json.loads((r / 'evidence/cr17d-after-v1-protocol.json').read_text(encoding='utf-8'))['images']['C']
out = r / 'diag-pool-v1'; out.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
sources = {'before': r / 'cr17c-after-v1-source/server', 'after': r / 'cr17d-after-v1-source/server'}
for i, label in enumerate(['before', 'after', 'after', 'before']):
    name = f'{i}-{label}'
    cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--name', f'diag-pool-{name}-obva7te6', '--label', 'stremhu.cr.owner=obva7te6',
           '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9', '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--tmpfs', '/fixture-output']
    for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'PYTHONDONTWRITEBYTECODE']:
        cmd += ['--env', key]
    cmd += ['--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={r / "cr17d-pool-diagnostic-v1.py"},target=/fixture/probe.py,readonly',
            '--mount', f'type=bind,source={sources[label] / "app"},target=/app/app,readonly', '--entrypoint', 'python', image, '/fixture/probe.py']
    res = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=900)
    (out / f'{name}.stdout').write_text(res.stdout, encoding='utf-8'); (out / f'{name}.stderr').write_text(res.stderr, encoding='utf-8')
    diag = [json.loads(l) for l in res.stderr.splitlines() if l.startswith('{"diag_db"')]
    print(name, 'exit', res.returncode, diag, flush=True)
