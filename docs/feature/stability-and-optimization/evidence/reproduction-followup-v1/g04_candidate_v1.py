"""G04 candidate gate (CR04 row memo) v1: five full 16-cell candidate profiles, two interleaved drift controls on the
baseline profile image, then one full heap run of the candidate. Same fixture, resources and validation as g04 baseline v1."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

r = pathlib.Path(__file__).parent
e = r / 'evidence'
f = r / 'g04-baseline-v1'
protocol = json.loads((e / 'g04-candidate-v1-protocol.json').read_text(encoding='utf-8'))
for name, expected in protocol['fixture_hashes'].items():
    if hashlib.sha256((f / name).read_bytes()).hexdigest() != expected:
        raise RuntimeError('Fixture changed')


def call(*args, **kw):
    return subprocess.run(['docker', '--context', 'desktop-linux', *args], check=True, **kw)


context = json.loads(call('context', 'inspect', 'desktop-linux', capture_output=True, text=True).stdout)[0]
if not context['Endpoints']['docker']['Host'].startswith('npipe://'):
    raise RuntimeError('Not local Docker Desktop')
SMOKE = '--smoke' in sys.argv
network = 'cr-g04-candidate-obva7te6'
call('network', 'create', '--internal', '--label', 'stremhu.task=obva7te6', network, capture_output=True)
env = os.environ.copy()
env['TEST_BASE_URL'] = 'http://g04.fixture.invalid:8080/__cr_g04__/index.html'
order = [['smoke', 'after', False]] if SMOKE else protocol['order']
try:
    for stem_part, kind, heap in order:
        image = protocol['candidate_image'] if kind == 'after' else protocol['control_image']
        stem = f'g04-candidate-v1-{stem_part}'
        target = e / (stem + '.json')
        if target.exists():
            raise RuntimeError('Refusing evidence overwrite')
        server = call('run', '--detach', '--rm', '--name', network + '-server', '--label', 'stremhu.task=obva7te6', '--network', network,
                      '--network-alias', 'g04.fixture.invalid', '--read-only', '--cpus', '1', '--cpuset-cpus', '14', '--memory', '512m',
                      '--tmpfs', '/tmp', '--mount', f'type=bind,source={f / "server.cjs"},target=/fixture/server.cjs,readonly',
                      '--entrypoint', 'node', image, '/fixture/server.cjs', capture_output=True, text=True).stdout.strip()
        try:
            deadline = time.monotonic() + 30
            while True:
                p = subprocess.run(['docker', '--context', 'desktop-linux', 'exec', server, 'node', '-e',
                                    "fetch('http://127.0.0.1:8080/fixture/ready').then(r=>r.json()).then(x=>process.exit(x.ready?0:1)).catch(()=>process.exit(1))"],
                                   capture_output=True)
                if p.returncode == 0:
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError('Profiling fixture not ready')
                time.sleep(.1)
            name = 'cr-' + stem + '-obva7te6'
            vol = name + '-output'
            call('volume', 'create', '--driver', 'local', '--label', 'stremhu.cr-task=obva7te6', '--label', 'stremhu.disposable=true', vol, capture_output=True)
            metadata = json.loads(call('volume', 'inspect', vol, capture_output=True, text=True).stdout)[0]
            if metadata['Driver'] != 'local' or metadata['Labels'].get('stremhu.cr-task') != 'obva7te6':
                raise RuntimeError('Unknown output volume')
            cmd = ['run', '--name', name, '--label', 'stremhu.task=obva7te6', '--init', '--network', network, '--read-only', '--cpus', '2',
                   '--cpuset-cpus', '12,13', '--memory', '2g', '--shm-size', '512m', '--tmpfs', '/tmp', '--env', 'TEST_BASE_URL',
                   '--mount', f'type=bind,source={f / "probe.cjs"},target=/fixture/probe.cjs,readonly',
                   '--mount', f'type=volume,source={vol},target=/fixture-output', '--entrypoint', 'node', protocol['browser_image'], '/fixture/probe.cjs']
            if heap:
                cmd += ['--heap']
            if SMOKE:
                cmd += ['--fixture-smoke']
            print(stem, kind, 'heap' if heap else 'profile', 'starting', flush=True)
            try:
                with (e / (stem + '.stdout')).open('w', encoding='utf-8') as out, (e / (stem + '.stderr')).open('w', encoding='utf-8') as err:
                    call(*cmd, stdout=out, stderr=err, env=env)
                d = json.loads((e / (stem + '.stdout')).read_text(encoding='utf-8'))
                if not SMOKE:
                    if not d['is_measurement'] or len(d['rows']) != (1 if heap else 16) or any(
                            row['errors'] or row['elapsed_ms'] < (1815000 if heap else 300000) or row['warmupRequests'] < 3 for row in d['rows']):
                        raise RuntimeError('Incomplete profile; raw results retained')
                    if heap and d['rows'][0]['navigations'] != 50:
                        raise RuntimeError('Incomplete navigation matrix')
                d.update(profile_image=image, browser_image=protocol['browser_image'], kind=kind, heap_run=heap, fixture_hashes=protocol['fixture_hashes'])
                target.write_text(json.dumps(d), encoding='utf-8')
                print(stem, 'saved', flush=True)
            finally:
                state = json.loads(call('inspect', name, capture_output=True, text=True).stdout)[0]['State']
                if state['Running']:
                    call('stop', '--time', '15', name, capture_output=True)
                call('rm', name, capture_output=True)
        finally:
            subprocess.run(['docker', '--context', 'desktop-linux', 'stop', '--time', '5', server], capture_output=True)
finally:
    subprocess.run(['docker', '--context', 'desktop-linux', 'network', 'rm', network], capture_output=True)
if not SMOKE:
    (e / 'g04-candidate-v1-complete.json').write_text(json.dumps(dict(order=protocol['order'], complete=True)), encoding='utf-8')
print('G04 candidate controller finished', flush=True)
