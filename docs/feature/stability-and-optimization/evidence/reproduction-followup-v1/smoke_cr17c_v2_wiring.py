"""Pre-registration wiring smoke for the v2 fixtures: exit code, cold gc_collections present,
no external HTTP. Outputs go to a scratch dir and are never measurement data; timings are not read."""
from pathlib import Path
import json, os, secrets, subprocess, sys
r = Path(sys.argv[1]); repo = Path(sys.argv[2])
image = json.loads((r / 'evidence/cr17c-after-v1-protocol.json').read_text(encoding='utf-8'))['images']['C']
out = r / 'smoke-cr17c-v2'; out.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
cases = [(f, s, flag) for f in ['cr17c-policy-fixture-v2.py', 'cr17c-policy-reference-fixture-v2.py', 'cr17c-policy-direct-fixture-v2.py', 'cr17c-kodi-ownership-observation-v2.py']
         for s, flag in [('after', '--fixture-smoke')]] + [('cr17c-policy-fixture-v2.py', 'after', '--profile-smoke'), ('cr17c-policy-fixture-v2.py', 'before', '--fixture-smoke')]
sources = {'before': r / 'cr17a-drain-fix-v2-source/server', 'after': r / 'cr17c-after-v1-source/server'}
for i, (fixture, label, flag) in enumerate(cases):
    cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--name', f'smoke-v2-{i}-obva7te6', '--label', 'stremhu.cr.owner=obva7te6',
           '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9', '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--tmpfs', '/fixture-output']
    for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'PYTHONDONTWRITEBYTECODE']:
        cmd += ['--env', key]
    cmd += ['--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={r / fixture},target=/fixture/probe.py,readonly',
            '--mount', f'type=bind,source={sources[label] / "app"},target=/app/app,readonly', '--entrypoint', 'python', image, '/fixture/probe.py', flag]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=900)
    (out / f'{i}.stderr').write_text(res.stderr, encoding='utf-8')
    ok = res.returncode == 0
    if ok:
        d = json.loads(res.stdout.strip().splitlines()[-1])
        ok = bool(d['cold']) and all(len(c.get('gc_collections', [])) == 3 for c in d['cold']) and not d['external_http_attempts']
    print(fixture, label, flag, 'exit', res.returncode, 'wiring_ok', ok, flush=True)
