"""Run the G17 ownership trace (scripts/trace_cr_search_ownership.py) on a frozen source in Docker (not a gate)."""
from pathlib import Path
import json, os, secrets, subprocess, sys
X = Path(__file__).parent; W = X.parent; repo = Path(sys.argv[1]); src = W / sys.argv[2]; script = Path(sys.argv[3]); tag = sys.argv[4]
env = os.environ.copy()
env.update(HOST_IP=(repo / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false', PYTHONDONTWRITEBYTECODE='1')
cmd = ['docker', '--context', 'desktop-linux', 'run', '--rm', '--network', 'none', '--read-only', '--cpus', '2', '--cpuset-cpus', '8,9', '--memory', '1g',
       '--tmpfs', '/tmp', '--tmpfs', '/app/data', '--env', 'HOST_IP', '--env', 'SESSION_SECRET', '--env', 'STREMHU_LOAD_DOTENV', '--env', 'PYTHONDONTWRITEBYTECODE',
       '--env', 'PYTHONPATH=/app', '--mount', f'type=bind,source={src / "app"},target=/app/app,readonly',
       '--mount', f'type=bind,source={script},target=/fixture/probe.py,readonly', '--entrypoint', 'python',
       'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52', '/fixture/probe.py']
p = subprocess.run(cmd, env=env, capture_output=True, encoding='utf-8', errors='replace')
(X / f'trace-{tag}.out').write_text(p.stdout, encoding='utf-8'); (X / f'trace-{tag}.err').write_text(p.stderr, encoding='utf-8')
print('exit', p.returncode)
