"""Derive the cr15a-after-v5 gate (source snapshot + manifest, controller, assessor) from v4.

Only change: code under test = wip/cr15a-bounded-download 7c01689 (v3 code + after aread() the identity path swaps the
response stream for a ByteStream over the read bytes, so the body is freed by reference counting instead of the cyclic GC).
Harness (cr15a-after-v4-fixture incl. the app.config preload), before (aaa9ee5), image, workload, resources, rules and
thresholds unchanged from v4."""
import hashlib
import io
import json
import pathlib
import subprocess
import tarfile

r = pathlib.Path(__file__).parent
e = r / 'evidence'
COMMIT, BRANCH, WT = '7c01689', 'wip/cr15a-bounded-download', 'D:/Git/stremhu-wt-cr15a'
src = r / 'cr15a-after-v5-source'
assert not src.exists() and not (e / 'cr15a-after-v5-source-manifest.json').exists()
raw = subprocess.run(['git', '-C', WT, 'archive', '--format=tar', COMMIT, 'server/app'], capture_output=True, check=True).stdout
files = {}
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
    for m in tar.getmembers():
        if m.isfile():
            data = tar.extractfile(m).read()
            rel = m.name.removeprefix('server/app/')
            (src / 'server/app' / rel).parent.mkdir(parents=True, exist_ok=True)
            (src / 'server/app' / rel).write_bytes(data)
            files[rel] = hashlib.sha256(data).hexdigest()
(e / 'cr15a-after-v5-source-manifest.json').write_text(json.dumps(dict(commit=COMMIT, branch=BRANCH, scope='server/app', files=dict(sorted(files.items()))), indent=1), encoding='utf-8')
v3 = json.loads((e / 'cr15a-after-v3-source-manifest.json').read_text(encoding='utf-8'))['files']
diff = sorted(k for k in set(v3) | set(files) if v3.get(k) != files.get(k))
assert diff == ['modules/indexer_definitions/base_indexer_definition.py'], diff


def derive(src_name, dst, pairs):
    t = (r / src_name).read_text(encoding='utf-8')
    for old, new in pairs:
        assert t.count(old) >= 1, (src_name, old[:60])
        t = t.replace(old, new)
    leftover = t.replace('cr15a-after-v4-fixture', '')
    assert 'cr15a-after-v4' not in leftover, (dst, [l for l in t.splitlines() if 'cr15a-after-v4' in l.replace('cr15a-after-v4-fixture', '')][:5])
    (r / dst).write_text(t, encoding='utf-8', newline='\n')


derive('cr15a_after_v4.py', 'cr15a_after_v5.py', [
    ('"""CR15a after-gate controller (v4; v1, v2 and v3 FAILED; v4 = v3 code and protocol, probe process preloads app.config on both sides).',
     '"""CR15a after-gate controller (v5; v1-v4 FAILED; v5 = v4 harness and protocol, after source 7c01689 releases the read body without the cyclic GC).'),
    ('after = frozen CR15a 0864a87 server/app', 'after = frozen CR15a 7c01689 server/app'),
    ("(e / 'cr15a-after-v4-protocol.json')", "(e / 'cr15a-after-v5-protocol.json')"),
    ("'after': (r / 'cr15a-after-v3-source/server/app', e / 'cr15a-after-v3-source-manifest.json')",
     "'after': (r / 'cr15a-after-v5-source/server/app', e / 'cr15a-after-v5-source-manifest.json')"),
    ("network = 'cr-cr15a-after-v4-obva7te6'", "network = 'cr-cr15a-after-v5-obva7te6'"),
    ("stem = f'cr15a-after-v4-{probe}-{side}-{tag}'", "stem = f'cr15a-after-v5-{probe}-{side}-{tag}'"),
    ("out = r / 'cr15a-after-v4-output' / stem", "out = r / 'cr15a-after-v5-output' / stem"),
    ("(e / 'cr15a-after-v4-complete.json')", "(e / 'cr15a-after-v5-complete.json')"),
])
derive('assess_cr15a_after_v4.py', 'assess_cr15a_after_v5.py', [
    ('"""Preregistered CR15a after-gate assessor (v4, rules identical to v1-v3);', '"""Preregistered CR15a after-gate assessor (v5, rules identical to v1-v4);'),
    ("f'cr15a-after-v4-normal-{side}-{s}-{i}'", "f'cr15a-after-v5-normal-{side}-{s}-{i}'"),
    ("f'cr15a-after-v4-giant-after-{s}-giant'", "f'cr15a-after-v5-giant-after-{s}-giant'"),
    ("'cr15a-after-v4-giant-before-confirm-giant-state.json'", "'cr15a-after-v5-giant-before-confirm-giant-state.json'"),
    ("(e / 'cr15a-after-v4-complete.json')", "(e / 'cr15a-after-v5-complete.json')"),
    ("(e / 'cr15a-after-v4-protocol.json')", "(e / 'cr15a-after-v5-protocol.json')"),
    ("(e / 'cr15a-after-v4-assessment.json')", "(e / 'cr15a-after-v5-assessment.json')"),
])
print('derived v5;', len(files), 'source files; diff vs v3:', diff)
