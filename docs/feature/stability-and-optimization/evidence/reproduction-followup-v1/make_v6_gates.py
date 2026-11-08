"""Derive the CR15a v6 gate and the 26a/26b/27 re-gates on the CR15a v6 landing runtime (wip/cr15-chain-v6).

v6 = v5 code (server/app byte-identical, asserted below) + the Dockerfile ENV MALLOC_MMAP_THRESHOLD_=32 MiB / MALLOC_TRIM_THRESHOLD_=64 MiB
(ff1a39a). The gates run the pinned image with the frozen server/app bind-mounted, so the Dockerfile ENV of each frozen commit is recorded
in its source manifest (runtime_env) and passed to that side's container exactly as the image would set it; the pre-CR15a before side
(aaa9ee5) has none. Harness, fixtures, workloads, image, rules and thresholds unchanged; the 26a/26b functional re-gates move to cpus
12,13 / 14 so that every gate runs on its own cpuset."""
import hashlib
import io
import json
import pathlib
import re
import subprocess
import tarfile

r = pathlib.Path(__file__).parent
e = r / 'evidence'
EXPECTED_ENV = {'MALLOC_MMAP_THRESHOLD_': '33554432', 'MALLOC_TRIM_THRESHOLD_': '67108864'}


def snapshot(name, wt, branch, commit, old):
    src = r / f'{name}-source'
    man = e / f'{name}-source-manifest.json'
    if man.exists() and json.loads(man.read_text(encoding='utf-8')).get('commit') == commit:
        print('snapshot exists', name)
        return
    assert not src.exists() and not man.exists(), name
    raw = subprocess.run(['git', '-C', wt, 'archive', '--format=tar', commit, 'server/app'], capture_output=True, check=True).stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        for m in tar.getmembers():
            if m.isfile():
                data = tar.extractfile(m).read()
                rel = m.name.removeprefix('server/app/')
                (src / 'server/app' / rel).parent.mkdir(parents=True, exist_ok=True)
                (src / 'server/app' / rel).write_bytes(data)
                files[rel] = hashlib.sha256(data).hexdigest()
    dockerfile = subprocess.run(['git', '-C', wt, 'show', f'{commit}:Dockerfile'], capture_output=True, check=True).stdout
    env = dict(re.findall(r'^ENV (MALLOC_[A-Z_]+)=(\S+)\s*$', dockerfile.decode('utf-8'), re.M))
    assert env == EXPECTED_ENV, (name, env)
    prev = json.loads((e / f'{old}-source-manifest.json').read_text(encoding='utf-8'))
    assert prev['files'] == files and 'runtime_env' not in prev, (name, 'server/app must equal ' + old)
    man.write_text(json.dumps(dict(commit=commit, branch=branch, scope='server/app', runtime_env=env, dockerfile_sha256=hashlib.sha256(dockerfile).hexdigest(),
                                   identical_server_app_to=old, files=dict(sorted(files.items()))), indent=1), encoding='utf-8')
    print('snapshot', name, commit, len(files), 'files; server/app identical to', old, '; runtime_env', env)


A, C = ('D:/Git/stremhu-wt-cr15a', 'wip/cr15a-bounded-download'), ('D:/Git/stremhu-wt-chain-v6', 'wip/cr15-chain-v6')
snapshot('cr15a-after-v6', *A, 'ff1a39a', 'cr15a-after-v5')
snapshot('cr15b-after-v5', *C, '5a1ee58', 'cr15b-after-v4')
snapshot('cr15b2-after-v6', *C, '6bd0370', 'cr15b2-after-v5')
snapshot('cr15c-after-v4', *C, '7767945', 'cr15c-after-v3')

HELPER = '''

def manifest_env(side):
    """CR15a v6: the frozen commit's Dockerfile MALLOC_* ENV (runtime_env in its source manifest; none before CR15a v6)."""
    return json.loads(SOURCES[side][1].read_text(encoding='utf-8')).get('runtime_env', {})


def runtime_env_args(side):
    return [a for k, v in sorted(manifest_env(side).items()) for a in ('--env', f'{k}={v}')]
'''
REGISTER_ENV = "    p['runtime_env'] = {s: manifest_env(s) for s in SOURCES}\n    t.write_text(json.dumps(p, indent=1), encoding='utf-8')"


def derive(src_name, dst, ids, prose, forbidden, controller=True, register_env=False):
    if (r / dst).exists():
        print('derived exists', dst)
        return
    t = (r / src_name).read_text(encoding='utf-8')
    for old, new in ids:
        assert old in t, (src_name, old)
        t = t.replace(old, new)
    for old, new in prose:
        assert t.count(old) == 1, (src_name, old[:80])
        t = t.replace(old, new)
    if controller:
        i = t.index("           'after': (r / ")
        j = t.index('\n', i) + 1
        assert t[i:j].rstrip().endswith(')}'), t[i:j]
        t = t[:j] + HELPER + t[j:]
        k = t.index("cmd += ['--env', 'PYTHONPATH=/app'")
        assert t.count("cmd += ['--env', 'PYTHONPATH=/app'") == 1
        line_start = t.rindex('\n', 0, k) + 1
        t = t[:line_start] + t[line_start:k] + 'cmd += runtime_env_args(side)\n' + t[line_start:]
    if register_env:
        old = "    t.write_text(json.dumps(p, indent=1), encoding='utf-8')"
        assert t.count(old) == 1, dst
        t = t.replace(old, REGISTER_ENV)
    for f in forbidden:
        bad = [line for line in t.splitlines() if f in line]
        assert not bad, (dst, f, bad[:3])
    assert not (r / dst).exists(), dst
    (r / dst).write_text(t, encoding='utf-8', newline='\n')
    print('derived', dst)


OLD = ['7c01689', '0b60f76', '8604355', '368fb57', 'chain-v5']
V6_NOTE = 'CR15a v6: Dockerfile glibc ENV, ff1a39a'

derive('cr15a_after_v5.py', 'cr15a_after_v6.py', [('cr15a-after-v5', 'cr15a-after-v6')], [
    ('"""CR15a after-gate controller (v5; v1-v4 FAILED; v5 = v4 harness and protocol, after source 7c01689 releases the read body without the cyclic GC).',
     '"""CR15a after-gate controller (v6; v1-v5 FAILED; v6 = v5 code and the v4 harness/protocol, the after side runs with the ff1a39a Dockerfile glibc ENV).'),
    ('after = frozen CR15a 7c01689 server/app,', 'after = frozen CR15a ff1a39a server/app (= v5 code) with its Dockerfile MALLOC_* ENV,'),
], OLD + ['cr15a-after-v5'])
derive('assess_cr15a_after_v5.py', 'assess_cr15a_after_v6.py', [('cr15a-after-v5', 'cr15a-after-v6')], [
    ('"""Preregistered CR15a after-gate assessor (v5, rules identical to v1-v4);', '"""Preregistered CR15a after-gate assessor (v6, rules identical to v1-v5);'),
], OLD + ['cr15a-after-v5'], controller=False)

derive('cr15b_origin_v4.py', 'cr15b_origin_v5.py', [('cr15b-origin-v4', 'cr15b-origin-v5'), ('cr15b-after-v4-source', 'cr15b-after-v5-source')], [
    ('"""Packet 26a functional origin gate (v4): same as v1-v3 (PASS) on the landing tree after the CR15a v5 read path: before (frozen aaa9ee5) and\n'
     'after (frozen wip/cr15-chain-v5 0b60f76 = CR15a v5 7c01689 + 26a), after twice.',
     '"""Packet 26a functional origin gate (v5): same as v1-v4 (PASS) on the CR15a v6 landing runtime: before (frozen aaa9ee5) and\n'
     'after (frozen wip/cr15-chain-v6 5a1ee58 = CR15a v6 ff1a39a + 26a, with its Dockerfile MALLOC_* ENV), after twice.'),
    ("previous='cr15b-origin-v1 PASS (87dfeba), -v2 PASS (f90e752) and -v3 PASS (CR15a v3 tree); rerun because the landing tree changed (CR15a v5 read path, 7c01689)'",
     f"previous='cr15b-origin-v1 PASS (87dfeba), -v2 PASS (f90e752), -v3 PASS (CR15a v3 tree) and -v4 PASS (CR15a v5 tree); rerun because the landing runtime changed ({V6_NOTE}; server/app identical to v4)'"),
    ("status='Final packet 26a functional gate (v4, landing tree); registered before any run.'",
     "status='Final packet 26a functional gate (v5, landing tree); registered before any run. Client 12,13 / server 14 (CA generation on 12).'"),
    ("after='frozen wip/cr15-chain-v5 0b60f76 server/app (CR15a v5 7c01689 included)'",
     "after='frozen wip/cr15-chain-v6 5a1ee58 server/app (CR15a v6 ff1a39a included; runs with its Dockerfile MALLOC_* ENV)'"),
    ("'--cpuset-cpus', '0', '--memory', '256m'", "'--cpuset-cpus', '12', '--memory', '256m'"),
    ("'--read-only', '--cpus', '1', '--cpuset-cpus', '6',", "'--read-only', '--cpus', '1', '--cpuset-cpus', '14',"),
    ("'--read-only', '--cpus', '2', '--cpuset-cpus', '0,1', '--memory', '1g',", "'--read-only', '--cpus', '2', '--cpuset-cpus', '12,13', '--memory', '1g',"),
], OLD + ['cr15b-origin-v4', 'cr15b-after-v4'], register_env=True)

derive('cr15b2_redirect_v5.py', 'cr15b2_redirect_v6.py',
       [('cr15b2-redirect-v5', 'cr15b2-redirect-v6'), ('cr15b-after-v4-source', 'cr15b-after-v5-source'), ('cr15b2-after-v5-source', 'cr15b2-after-v6-source')], [
    ('"""Packet 26b functional gate (v5):', '"""Packet 26b functional gate (v6):'),
    ('before = frozen 0b60f76 (CR15a v5 + 26a), after = frozen 8604355 (+ 26b), after twice. v4 PASS on the CR15a v3 tree, v3 PASS on the CR15a v2 base; v1/v2 never run.',
     'before = frozen 5a1ee58 (CR15a v6 + 26a), after = frozen 6bd0370 (+ 26b), after twice, both with the CR15a v6 Dockerfile MALLOC_* ENV.\n'
     'v5 PASS on the CR15a v5 tree, v4 on the CR15a v3 tree, v3 on the CR15a v2 base; v1/v2 never run.'),
    ("CPUS = dict(smoke=('2,3', '4'), run=('2,3', '4'))", "CPUS = dict(smoke=('12,13', '14'), run=('12,13', '14'))"),
    ("before='frozen 0b60f76 server/app (CR15a v5 + 26a; cr15b-after-v4 manifest)', after='frozen 8604355 server/app (cr15b2-after-v5 manifest)'",
     "before='frozen 5a1ee58 server/app (CR15a v6 + 26a; cr15b-after-v5 manifest)', after='frozen 6bd0370 server/app (cr15b2-after-v6 manifest)'"),
    ("supersedes='cr15b2-redirect-v6 PASS on the CR15a v3 tree and -v3 PASS on the CR15a v2 base (51854ca); rerun on the CR15a v5 landing tree. v1/v2 registered, never run.'",
     f"supersedes='cr15b2-redirect-v5 PASS on the CR15a v5 tree, -v4 PASS on the CR15a v3 tree and -v3 PASS on the CR15a v2 base (51854ca); rerun on the landing runtime ({V6_NOTE}; server/app identical to v5). v1/v2 registered, never run. (The v5 protocol text names itself where -v4 was meant.)'"),
    ("resources='client 2 CPU on 2,3 / 1 GiB; server 1 CPU on 4 / 512 MiB; internal network, no outbound; runs beside the CR15a v5 gate (8-10) and the 26a/27 re-gates (0,1,6) on disjoint cpusets.'",
     "resources='client 2 CPU on 12,13 / 1 GiB; server 1 CPU on 14 / 512 MiB; internal network, no outbound; runs after the 26a v5 re-gate on the same cpus, beside the CR15a v6 (8-10), 26b normal v6 (2-4) and 27 v4 (0,1,6) gates on disjoint cpusets.'"),
], OLD + ['redirect-v5-', 'cr15b-after-v4', 'cr15b2-after-v5'], register_env=True)

derive('cr15b2_after_v5.py', 'cr15b2_after_v6.py', [('cr15b2-after-v5', 'cr15b2-after-v6'), ('cr15b-after-v4-source', 'cr15b-after-v5-source')], [
    ('(v5: before = 0b60f76, after = 8604355 on the CR15a v5 landing tree; v4 ran on the CR15a v3 tree, v3 on the CR15a v2 base)',
     '(v6: before = 5a1ee58, after = 6bd0370 on the CR15a v6 landing runtime, both with its Dockerfile MALLOC_* ENV; v5 ran on the CR15a v5 tree, v4 on the CR15a v3 tree, v3 on the CR15a v2 base)'),
    ('before = frozen 0b60f76 server/app\n(CR15a v5 + 26a), after = frozen 8604355 server/app', 'before = frozen 5a1ee58 server/app\n(CR15a v6 + 26a), after = frozen 6bd0370 server/app'),
], OLD + ['cr15b2-after-v5', 'cr15b-after-v4'])
derive('assess_cr15b2_after_v5.py', 'assess_cr15b2_after_v6.py', [('cr15b2-after-v5', 'cr15b2-after-v6')], [
    ('"""Preregistered packet 26b after-gate assessor (v5, rules identical to v4);', '"""Preregistered packet 26b after-gate assessor (v6, rules identical to v4/v5);'),
], OLD + ['cr15b2-after-v5'], controller=False)
derive('register_cr15b2_after_v5.py', 'register_cr15b2_after_v6.py',
       [('cr15b2_after_v5', 'cr15b2_after_v6'), ('cr15b2-after-v5', 'cr15b2-after-v6'), ('cr15b2-redirect-v5', 'cr15b2-redirect-v6'), ('cr15b-after-v4-source', 'cr15b-after-v5-source')], [
    ('"""Register the packet 26b normal after-gate protocol (v5, CR15a v5 landing tree) before any measured run."""',
     '"""Register the packet 26b normal after-gate protocol (v6, CR15a v6 landing runtime) before any measured run."""'),
    ("before='frozen wip/cr15-chain-v5 0b60f76 server/app (CR15a v5 + 26a; cr15b-after-v5-source manifest)'",
     "before='frozen wip/cr15-chain-v6 5a1ee58 server/app (CR15a v6 + 26a; cr15b-after-v5-source manifest)'"),
    ("after='frozen wip/cr15-chain-v5 8604355 server/app (cr15b2-after-v6-source manifest; strict host policy)', previous='cr15b2-after-v6 PASS on the CR15a v3 tree (75 checks); rerun because the landing tree changed (CR15a v5 read path, 7c01689)'",
     f"after='frozen wip/cr15-chain-v6 6bd0370 server/app (cr15b2-after-v6-source manifest; strict host policy)', previous='cr15b2-after-v5 PASS on the CR15a v5 tree and cr15b2-after-v4 PASS on the CR15a v3 tree (75 checks each); rerun because the landing runtime changed ({V6_NOTE}; server/app identical to v5). (The v5 protocol text names itself where -v4 was meant.)'"),
    ("concurrency_note='Runs after the 26b redirect v5 gate on cpus 2-4; CR15a v5 gate (8-10) and the 26a/27 re-gates (0,1,6) on disjoint cpusets.'",
     "concurrency_note='Runs on cpus 2-4 beside the CR15a v6 gate (8-10), the 27 v4 gate (0,1,6) and the 26a/26b functional re-gates (12-14) on disjoint cpusets.'"),
    ("    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',\n",
     "    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',\n"
     "    runtime_env={s: json.loads((e / f'{m}-source-manifest.json').read_text(encoding='utf-8'))['runtime_env'] for s, m in (('before', 'cr15b-after-v5'), ('after', 'cr15b2-after-v6'))},\n"),
], OLD + ['cr15b2-after-v5-', 'cr15b2_after_v5', 'cr15b-after-v4', 'redirect-v5'], controller=False)

derive('cr15c_after_v3.py', 'cr15c_after_v4.py',
       [('cr15c-after-v3', 'cr15c-after-v4'), ('assess_cr15c_after_v3', 'assess_cr15c_after_v4'), ('cr15b2-after-v5-source', 'cr15b2-after-v6-source'),
        ("network = f'cr-cr15c-v3-obva7te6-{stem}'", "network = f'cr-cr15c-v4-obva7te6-{stem}'")], [
    ('(v3: v1 PASS on the CR15a v2 base, v2 PASS on the CR15a v3 tree; rerun on the CR15a v5 landing tree)',
     '(v4: v1 PASS on the CR15a v2 base, v2 on the CR15a v3 tree, v3 on the CR15a v5 tree; rerun on the CR15a v6 landing runtime)'),
    ('before = frozen 8604355 (CR15a v5 + 26a + 26b, the landing base), after = frozen 368fb57 (+ packet 27).',
     'before = frozen 6bd0370 (CR15a v6 + 26a + 26b, the landing base), after = frozen 7767945 (+ packet 27), both with the CR15a v6 Dockerfile MALLOC_* ENV.'),
    ("before='frozen wip/cr15-chain-v5 8604355 server/app (landing base)', after='frozen wip/cr15-chain-v5 368fb57 server/app', previous='cr15c-after-v1 PASS on the CR15a v2 base, cr15c-after-v4 PASS on the CR15a v3 tree; rerun because the landing tree changed (CR15a v5 read path, 7c01689)'",
     f"before='frozen wip/cr15-chain-v6 6bd0370 server/app (landing base)', after='frozen wip/cr15-chain-v6 7767945 server/app', previous='cr15c-after-v1 PASS on the CR15a v2 base, -v2 PASS on the CR15a v3 tree, -v3 PASS on the CR15a v5 tree; rerun because the landing runtime changed ({V6_NOTE}; server/app identical to v3). (The v3 protocol text names itself where -v2 was meant.)'"),
    ('runs alongside the CR15a v5 (8-10) and 26b v5 (2-4) gates on disjoint cpusets.',
     'runs alongside the CR15a v6 (8-10), 26b normal v6 (2-4) and 26a/26b functional (12-14) gates on disjoint cpusets.'),
], OLD + ['cr15c-v3', 'cr15b2-after-v5'], register_env=True)
derive('assess_cr15c_after_v3.py', 'assess_cr15c_after_v4.py', [('cr15c-after-v3', 'cr15c-after-v4')], [
    ('"""Preregistered packet 27 (CR15/c) gate assessor (v3, rules identical to v2);', '"""Preregistered packet 27 (CR15/c) gate assessor (v4, rules identical to v2/v3);'),
], OLD + ['cr15c-after-v3'], controller=False)
