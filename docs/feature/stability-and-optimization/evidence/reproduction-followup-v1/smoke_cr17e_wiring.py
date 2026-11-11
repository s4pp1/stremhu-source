"""Pre-registration wiring smoke for the cr17d-after-v1 fixtures (packet 22): exit code, cold gc_collections present,
no external HTTP, on both sources (before = frozen packet21b, after = frozen packet22) so the provider-constructor
adapter is exercised both ways. Outputs go to a scratch dir and are never measurement data; timings are not read."""
from pathlib import Path
import json, os, secrets, subprocess, sys
r = Path(sys.argv[1]); repo = Path(sys.argv[2])
image = json.loads((r / 'evidence/cr17c-after-v2-protocol.json').read_text(encoding='utf-8'))['images']['C']
out = r / 'smoke-cr17e-v1'; out.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
fixtures = ['cr17d-policy-fixture-v2.py', 'cr17d-policy-reference-fixture-v2.py', 'cr17d-policy-direct-fixture-v2.py', 'cr17d-kodi-ownership-observation-v2.py']
cases = [(f, s, '--fixture-smoke') for f in fixtures for s in ['after']] + [('cr17d-policy-fixture-v2.py', 'after', '--profile-smoke')]
sources = {'before': r / 'cr17c-after-v1-source/server', 'after': r / 'cr17e-after-v1-source/server'}
for i, (fixture, label, flag) in enumerate(cases):
    cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--name', f'smoke-cr17e-{i}-obva7te6', '--label', 'stremhu.cr.owner=obva7te6',
           '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9', '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--tmpfs', '/fixture-output']
    for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'PYTHONDONTWRITEBYTECODE']:
        cmd += ['--env', key]
    cmd += ['--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={r / fixture},target=/fixture/probe.py,readonly',
            '--mount', f'type=bind,source={sources[label] / "app"},target=/app/app,readonly', '--entrypoint', 'python', image, '/fixture/probe.py', flag]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=900)
    (out / f'{i}.stderr').write_text(res.stderr, encoding='utf-8')
    (out / f'{i}.stdout').write_text(res.stdout, encoding='utf-8')
    ok = res.returncode == 0
    if ok:
        d = json.loads(res.stdout.strip().splitlines()[-1])
        ok = bool(d['cold']) and all(len(c.get('gc_collections', [])) == 3 for c in d['cold']) and not d['external_http_attempts']
    print(fixture, label, flag, 'exit', res.returncode, 'wiring_ok', ok, 'DetachedInstanceError' in res.stderr, flush=True)
