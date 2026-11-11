"""Derive the re-gates of the 26a/26b/27 chain on top of CR15a v5 (wip/cr15-chain-v5): source snapshots + manifests and
controllers/assessors/registers from the v3-tree versions. Only change in every snapshot: the CR15a v5 cycle break in
base_indexer_definition.py (4 added lines). Gate rules, fixtures, workloads, image and resources unchanged; the 26b redirect
smoke moves to the run cpus (2,3 / 4) because 0,1 / 6 host the 26a and 27 re-gates."""
import hashlib
import io
import json
import pathlib
import subprocess
import tarfile

r = pathlib.Path(__file__).parent
e = r / 'evidence'
WT, BRANCH = 'D:/Git/stremhu-wt-chain-v5', 'wip/cr15-chain-v5'
ADDED = ['                # A HTTPX folyamburka visszahivatkozik a válaszra; ciklusként a törzs csak a\n',
         '                # ciklikus GC-vel szabadulna fel (cr15a-after-v4). A beolvasott törzs után a\n',
         '                # válasz már nem olvas a hálózatról, a folyamot a meglévő bájtokra cseréljük.\n',
         '                response.stream = httpx.ByteStream(response.content)\n']
BID = 'modules/indexer_definitions/base_indexer_definition.py'


def snapshot(name, commit, old):
    src = r / f'{name}-source'
    man = e / f'{name}-source-manifest.json'
    assert not src.exists() and not man.exists(), name
    raw = subprocess.run(['git', '-C', WT, 'archive', '--format=tar', commit, 'server/app'], capture_output=True, check=True).stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        for m in tar.getmembers():
            if m.isfile():
                data = tar.extractfile(m).read()
                rel = m.name.removeprefix('server/app/')
                (src / 'server/app' / rel).parent.mkdir(parents=True, exist_ok=True)
                (src / 'server/app' / rel).write_bytes(data)
                files[rel] = hashlib.sha256(data).hexdigest()
    man.write_text(json.dumps(dict(commit=commit, branch=BRANCH, scope='server/app', files=dict(sorted(files.items()))), indent=1), encoding='utf-8')
    prev = json.loads((e / f'{old}-source-manifest.json').read_text(encoding='utf-8'))['files']
    diff = sorted(k for k in set(prev) | set(files) if prev.get(k) != files.get(k))
    assert diff == [BID], (name, diff)
    new_lines = (src / 'server/app' / BID).read_bytes().decode('utf-8').splitlines(keepends=True)
    i = new_lines.index(ADDED[0])
    assert new_lines[i:i + 4] == ADDED
    old_lines = (r / f'{old}-source/server/app' / BID).read_bytes().decode('utf-8').splitlines(keepends=True)
    assert new_lines[:i] + new_lines[i + 4:] == old_lines, name
    print('snapshot', name, commit, len(files), 'files; only the v5 cycle break differs from', old)


snapshot('cr15b-after-v4', '0b60f76', 'cr15b-after-v3')
snapshot('cr15b2-after-v5', '8604355', 'cr15b2-after-v4')
snapshot('cr15c-after-v3', '368fb57', 'cr15c-after-v2')


def derive(src_name, dst, pairs, forbidden):
    t = (r / src_name).read_text(encoding='utf-8')
    for old, new in pairs:
        assert t.count(old) >= 1, (src_name, old[:70])
        t = t.replace(old, new)
    for f in forbidden:
        bad = [line for line in t.splitlines() if f in line]
        assert not bad, (dst, f, bad[:3])
    assert not (r / dst).exists(), dst
    (r / dst).write_text(t, encoding='utf-8', newline='\n')
    print('derived', dst)


OLD_IDS = ['ecafdeb', 'a4b9229', '438b72f', '0864a87', 'chain-v3']
derive('cr15b_origin_v3.py', 'cr15b_origin_v4.py', [
    ('"""Packet 26a functional origin gate (v3): same as v1/v2 (PASS) on the landing tree after the CR15a v3 read path:',
     '"""Packet 26a functional origin gate (v4): same as v1-v3 (PASS) on the landing tree after the CR15a v5 read path:'),
    ('after (frozen wip/cr15-chain-v3 ecafdeb = CR15a v3 0864a87 + 26a)', 'after (frozen wip/cr15-chain-v5 0b60f76 = CR15a v5 7c01689 + 26a)'),
    ("previous='cr15b-origin-v1 PASS (87dfeba) and -v2 PASS (f90e752); rerun because the landing tree changed (CR15a v3 read path)'",
     "previous='cr15b-origin-v1 PASS (87dfeba), -v2 PASS (f90e752) and -v3 PASS (CR15a v3 tree); rerun because the landing tree changed (CR15a v5 read path, 7c01689)'"),
    ("status='Final packet 26a functional gate (v3, landing tree); registered before any run.'",
     "status='Final packet 26a functional gate (v4, landing tree); registered before any run.'"),
    ("after='frozen wip/cr15-chain-v3 ecafdeb server/app (CR15a v3 0864a87 included)'", "after='frozen wip/cr15-chain-v5 0b60f76 server/app (CR15a v5 7c01689 included)'"),
    ('cr15b-origin-v3', 'cr15b-origin-v4'),
    ('cr15b-after-v3-source', 'cr15b-after-v4-source'),
], OLD_IDS + ['cr15b-origin-v3', 'cr15b-after-v3'])
derive('cr15b2_redirect_v4.py', 'cr15b2_redirect_v5.py', [
    ('"""Packet 26b functional gate (v4):', '"""Packet 26b functional gate (v5):'),
    ('before = frozen ecafdeb (CR15a v3 + 26a), after = frozen a4b9229 (+ 26b), after twice. v3 PASS on the CR15a v2 base; v1/v2 never run.',
     'before = frozen 0b60f76 (CR15a v5 + 26a), after = frozen 8604355 (+ 26b), after twice. v4 PASS on the CR15a v3 tree, v3 PASS on the CR15a v2 base; v1/v2 never run.'),
    ("CPUS = dict(smoke=('0,1', '6'), run=('2,3', '4'))", "CPUS = dict(smoke=('2,3', '4'), run=('2,3', '4'))"),
    ("before='frozen ecafdeb server/app (CR15a v3 + 26a; cr15b-after-v3 manifest)', after='frozen a4b9229 server/app (cr15b2-after-v4 manifest)'",
     "before='frozen 0b60f76 server/app (CR15a v5 + 26a; cr15b-after-v4 manifest)', after='frozen 8604355 server/app (cr15b2-after-v5 manifest)'"),
    ("supersedes='cr15b2-redirect-v3 PASS on the CR15a v2 base (51854ca); rerun on the CR15a v3 landing tree. v1/v2 registered, never run.'",
     "supersedes='cr15b2-redirect-v4 PASS on the CR15a v3 tree and -v3 PASS on the CR15a v2 base (51854ca); rerun on the CR15a v5 landing tree. v1/v2 registered, never run.'"),
    ("runs after G03 has finished.'", "runs beside the CR15a v5 gate (8-10) and the 26a/27 re-gates (0,1,6) on disjoint cpusets.'"),
    ('cr15b2-redirect-v4', 'cr15b2-redirect-v5'),
    ('cr15b-after-v3-source', 'cr15b-after-v4-source'),
    ('cr15b2-after-v4-source', 'cr15b2-after-v5-source'),
], OLD_IDS + ['cr15b2-redirect-v4', 'cr15b-after-v3', 'cr15b2-after-v4'])
derive('cr15b2_after_v4.py', 'cr15b2_after_v5.py', [
    ('(v4: before = ecafdeb, after = a4b9229 on the CR15a v3 landing tree; v3 ran on the CR15a v2 base)',
     '(v5: before = 0b60f76, after = 8604355 on the CR15a v5 landing tree; v4 ran on the CR15a v3 tree, v3 on the CR15a v2 base)'),
    ('before = frozen ecafdeb server/app\n(CR15a v3 + 26a), after = frozen a4b9229 server/app', 'before = frozen 0b60f76 server/app\n(CR15a v5 + 26a), after = frozen 8604355 server/app'),
    ('cr15b2-after-v4', 'cr15b2-after-v5'),
    ('cr15b-after-v3-source', 'cr15b-after-v4-source'),
], OLD_IDS + ['cr15b2-after-v4', 'cr15b-after-v3'])
derive('assess_cr15b2_after_v4.py', 'assess_cr15b2_after_v5.py', [
    ('"""Preregistered packet 26b after-gate assessor (v4);', '"""Preregistered packet 26b after-gate assessor (v5, rules identical to v4);'),
    ('cr15b2-after-v4', 'cr15b2-after-v5'),
], OLD_IDS + ['cr15b2-after-v4'])
derive('register_cr15b2_after_v4.py', 'register_cr15b2_after_v5.py', [
    ('"""Register the packet 26b normal after-gate protocol (v4) before any measured run."""',
     '"""Register the packet 26b normal after-gate protocol (v5, CR15a v5 landing tree) before any measured run."""'),
    ("before='frozen wip/cr15-chain-v3 ecafdeb server/app (CR15a v3 + 26a; cr15b-after-v3-source manifest)'",
     "before='frozen wip/cr15-chain-v5 0b60f76 server/app (CR15a v5 + 26a; cr15b-after-v4-source manifest)'"),
    ("after='frozen wip/cr15-chain-v3 a4b9229 server/app (cr15b2-after-v4-source manifest; strict host policy)'",
     "after='frozen wip/cr15-chain-v5 8604355 server/app (cr15b2-after-v5-source manifest; strict host policy)', "
     "previous='cr15b2-after-v4 PASS on the CR15a v3 tree (75 checks); rerun because the landing tree changed (CR15a v5 read path, 7c01689)'"),
    ("concurrency_note='Runs after the 26b v3 gate on cpus 2-4; CR15a v3 gate (8-10), G04 (12-14) and the packet 27 v2 gate (0,1,6) on disjoint cpusets.'",
     "concurrency_note='Runs after the 26b redirect v5 gate on cpus 2-4; CR15a v5 gate (8-10) and the 26a/27 re-gates (0,1,6) on disjoint cpusets.'"),
    ('cr15b2_after_v4', 'cr15b2_after_v5'),
    ('cr15b2-after-v4', 'cr15b2-after-v5'),
    ('cr15b2-redirect-v4', 'cr15b2-redirect-v5'),
], OLD_IDS + ['cr15b2-after-v4', 'cr15b-after-v3', 'redirect-v4'])
derive('cr15c_after_v2.py', 'cr15c_after_v3.py', [
    ('(v2: v1 PASS on the CR15a v2 base; rerun on the CR15a v3 landing tree)', '(v3: v1 PASS on the CR15a v2 base, v2 PASS on the CR15a v3 tree; rerun on the CR15a v5 landing tree)'),
    ('before = frozen a4b9229 (CR15a v3 + 26a + 26b, the landing base), after = frozen 438b72f (+ packet 27).',
     'before = frozen 8604355 (CR15a v5 + 26a + 26b, the landing base), after = frozen 368fb57 (+ packet 27).'),
    ("before='frozen wip/cr15-chain-v3 a4b9229 server/app (landing base)', after='frozen wip/cr15-chain-v3 438b72f server/app', previous='cr15c-after-v1 PASS on the CR15a v2 base'",
     "before='frozen wip/cr15-chain-v5 8604355 server/app (landing base)', after='frozen wip/cr15-chain-v5 368fb57 server/app', "
     "previous='cr15c-after-v1 PASS on the CR15a v2 base, cr15c-after-v2 PASS on the CR15a v3 tree; rerun because the landing tree changed (CR15a v5 read path, 7c01689)'"),
    ('runs alongside the CR15a v3 (8-10), 26b (2-4) and G04 (12-14) gates on disjoint cpusets.', 'runs alongside the CR15a v5 (8-10) and 26b v5 (2-4) gates on disjoint cpusets.'),
    ("network = f'cr-cr15c-v2-obva7te6-{stem}'", "network = f'cr-cr15c-v3-obva7te6-{stem}'"),
    ('assess_cr15c_after_v2', 'assess_cr15c_after_v3'),
    ('cr15c-after-v2', 'cr15c-after-v3'),
    ('cr15b2-after-v4-source', 'cr15b2-after-v5-source'),
], OLD_IDS + ['cr15c-after-v2', 'cr15b2-after-v4', 'cr15c-v2'])
derive('assess_cr15c_after_v2.py', 'assess_cr15c_after_v3.py', [
    ('"""Preregistered packet 27 (CR15/c) gate assessor (v2);', '"""Preregistered packet 27 (CR15/c) gate assessor (v3, rules identical to v2);'),
    ('cr15c-after-v2', 'cr15c-after-v3'),
], OLD_IDS + ['cr15c-after-v2'])
