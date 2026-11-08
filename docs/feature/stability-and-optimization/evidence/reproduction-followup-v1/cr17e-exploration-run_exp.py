"""Exploratory runs (not a gate): python run_exp.py REPO label=srcdir:fixture ... ; order as given."""
from pathlib import Path
import json, os, secrets, subprocess, sys
X = Path(__file__).parent; W = X.parent; repo = Path(sys.argv[1])
image = json.loads((W / 'evidence/cr17d-after-v1-protocol.json').read_text(encoding='utf-8'))['images']['C']
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
out = X / 'out'; out.mkdir(exist_ok=True)
for i, spec in enumerate(sys.argv[2:]):
    label, rest = spec.split('=', 1); src, fixture = rest.split(':', 1)
    src_p = (W / src) if not Path(src).is_absolute() else Path(src)
    cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--name', f'exp22b-{i}-obva7te6', '--label', 'stremhu.cr.owner=obva7te6',
           '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9', '--memory', '1g', '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--tmpfs', '/fixture-output']
    for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'PYTHONDONTWRITEBYTECODE']:
        cmd += ['--env', key]
    cmd += ['--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={W / fixture},target=/fixture/probe.py,readonly',
            '--mount', f'type=bind,source={src_p / "app"},target=/app/app,readonly', '--entrypoint', 'python', image, '/fixture/probe.py']
    res = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=900)
    (out / f'{i}-{label}.stdout').write_text(res.stdout, encoding='utf-8'); (out / f'{i}-{label}.stderr').write_text(res.stderr, encoding='utf-8')
    diag = [json.loads(l) for l in res.stderr.splitlines() if l.startswith('{"diag_db"')]
    mem = ''
    if res.returncode == 0:
        d = json.loads(res.stdout.strip().splitlines()[-1])
        m = {(r['count'], r['kind'][:4], r['concurrency']): r for r in d['rows']}
        mem = ' '.join(f"{k[0]}/{k[1]}/c{k[2]}:{m[k]['memory']['anon_bytes']/2**20:.1f}/p95={m[k]['p95_ms']:.1f}" for k in [(100,'uniq',1),(100,'uniq',4),(100,'uniq',8),(20,'uniq',8)])
    print(f'{i}-{label}', 'exit', res.returncode, [(x['connects'], x['peak_checked_out']) for x in diag], mem, flush=True)
