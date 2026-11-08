"""Diagnostic only (not a gate, not data), v2: volume DB like burst27-v3. argv: N MIX MEMORY SRC_DIR LABEL"""
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

r = Path(__file__).parent
fx = r / 'burst27-v1-fixture'
IMAGE = 'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
n, mix, memory, src, label = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]


def docker(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], **kw)


network = f'cr-burst27-diag-obva7te6-{label}'
env = os.environ.copy()
env.update(HOST_IP=(Path.cwd() / '.git/cr-test-host').read_text().strip(), SESSION_SECRET=secrets.token_urlsafe(48), STREMHU_LOAD_DOTENV='false',
           TEST_BASE_URL='http://tracker.fixture.invalid:8080', PYTHONDONTWRITEBYTECODE='1', BURST_N=n, BURST_MIX=mix, BURST_RUN='0', BURST_GUARD_SECONDS='300')
docker('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', network, capture_output=True, check=True)
server = None
try:
    server = docker('run', '--detach', '--rm', '--name', network + '-server', '--network', network, '--network-alias', 'tracker.fixture.invalid', '--read-only',
                    '--cpus', '1', '--cpuset-cpus', '6', '--memory', '512m', '--tmpfs', '/tmp', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
                    '--workdir', '/fixture', '--entrypoint', 'python', IMAGE, '/fixture/server.py', capture_output=True, text=True, check=True).stdout.strip()
    deadline = time.monotonic() + 90
    while docker('exec', server, 'python', '-c', "import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/ready',timeout=1))['ready']",
                 capture_output=True).returncode != 0:
        if time.monotonic() > deadline:
            raise RuntimeError('fixture not ready')
        time.sleep(.2)
    cmd = ['run', '--rm', '--name', network + '-client', '--network', network, '--read-only', '--cpus', '2', '--cpuset-cpus', '0,1', '--memory', memory,
           '--memory-swap', memory, '--tmpfs', '/tmp', '--mount', 'type=volume,target=/app/data', '--mount', f'type=bind,source={fx},target=/fixture,readonly',
           '--mount', f'type=bind,source={src},target=/app/app,readonly']
    for key in ['HOST_IP', 'SESSION_SECRET', 'STREMHU_LOAD_DOTENV', 'TEST_BASE_URL', 'PYTHONDONTWRITEBYTECODE', 'BURST_N', 'BURST_MIX', 'BURST_RUN', 'BURST_GUARD_SECONDS'] + [k for k in os.environ if k.startswith(('SOURCE_SEARCH_', 'TORRENT_INFO_'))]:
        cmd += ['--env', key]
    cmd += ['--env', 'PYTHONPATH=/app', '--entrypoint', 'python', IMAGE, '/fixture/harness.py']
    res = docker(*cmd, env=env, capture_output=True, text=True, encoding='utf-8')
    out = r / 'burst27-v3-diag'; out.mkdir(exist_ok=True)
    (out / f'{label}.stdout').write_text(res.stdout, encoding='utf-8')
    (out / f'{label}.stderr').write_text(res.stderr, encoding='utf-8')
    print(label, 'exit', res.returncode, flush=True)
finally:
    if server is not None:
        docker('stop', '--time', '5', server, capture_output=True)
    docker('network', 'rm', network, capture_output=True)
