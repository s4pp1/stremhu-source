"""Derive the cr15a-after-v4 gate (controller, assessor, register, fixture) from v3.

Only change: the probe process imports app.config before the unchanged probe/giant scripts, on BOTH sides (the production
server always has it loaded; diag3/diag4 showed the v3 small-kind anon excess is mostly this one-time import).
Code under test (after = 0864a87), before (aaa9ee5), image, workload, resources, rules and thresholds unchanged."""
import pathlib
import shutil

r = pathlib.Path(__file__).parent
fx3, fx4 = r / 'cr15a-after-v3-fixture', r / 'cr15a-after-v4-fixture'
assert not fx4.exists()
shutil.copytree(fx3, fx4)
for name, target in (('preload_probe.py', 'probe.py'), ('preload_giant.py', 'giant.py')):
    (fx4 / name).write_text(
        '"""cr15a-after-v4 harness: load app.config (the production server always has it loaded) before the unchanged\n'
        f'{target}, identically on the before and after side. sys.argv is passed through unchanged."""\n'
        'import runpy\n\n'
        'import app.config  # noqa: F401\n\n'
        f"runpy.run_path('/fixture/{target}', run_name='__main__')\n", encoding='utf-8', newline='\n')


def derive(src, dst, pairs):
    t = (r / src).read_text(encoding='utf-8')
    for old, new in pairs:
        assert t.count(old) >= 1, (src, old[:60])
        t = t.replace(old, new)
    assert 'cr15a-after-v3' not in t.replace('cr15a-after-v3-source', ''), (dst, [l for l in t.splitlines() if 'cr15a-after-v3' in l][:5])
    (r / dst).write_text(t, encoding='utf-8', newline='\n')


derive('cr15a_after_v3.py', 'cr15a_after_v4.py', [
    ('"""CR15a after-gate controller (v3; v1 and v2 FAILED, v3 = same protocol, after source 0864a87).',
     '"""CR15a after-gate controller (v4; v1, v2 and v3 FAILED; v4 = v3 code and protocol, probe process preloads app.config on both sides).'),
    ("fx = r / 'cr15a-after-v3-fixture'", "fx = r / 'cr15a-after-v4-fixture'"),
    ("(e / 'cr15a-after-v3-protocol.json')", "(e / 'cr15a-after-v4-protocol.json')"),
    ("network = 'cr-cr15a-after-v3-obva7te6'", "network = 'cr-cr15a-after-v4-obva7te6'"),
    ("stem = f'cr15a-after-v3-{probe}-{side}-{tag}'", "stem = f'cr15a-after-v4-{probe}-{side}-{tag}'"),
    ("out = r / 'cr15a-after-v3-output' / stem", "out = r / 'cr15a-after-v4-output' / stem"),
    ("""f'/fixture/{"probe" if probe == "normal" else "giant"}.py'""", """f'/fixture/preload_{"probe" if probe == "normal" else "giant"}.py'"""),
    ("(e / 'cr15a-after-v3-complete.json')", "(e / 'cr15a-after-v4-complete.json')"),
])
derive('assess_cr15a_after_v3.py', 'assess_cr15a_after_v4.py', [
    ('"""Preregistered CR15a after-gate assessor (v3, rules identical to v1/v2);', '"""Preregistered CR15a after-gate assessor (v4, rules identical to v1-v3);'),
    ("f'cr15a-after-v3-normal-{side}-{s}-{i}'", "f'cr15a-after-v4-normal-{side}-{s}-{i}'"),
    ("f'cr15a-after-v3-giant-after-{s}-giant'", "f'cr15a-after-v4-giant-after-{s}-giant'"),
    ("'cr15a-after-v3-giant-before-confirm-giant-state.json'", "'cr15a-after-v4-giant-before-confirm-giant-state.json'"),
    ("(e / 'cr15a-after-v3-complete.json')", "(e / 'cr15a-after-v4-complete.json')"),
    ("(e / 'cr15a-after-v3-protocol.json')", "(e / 'cr15a-after-v4-protocol.json')"),
    ("(e / 'cr15a-after-v3-assessment.json')", "(e / 'cr15a-after-v4-assessment.json')"),
])
print('derived v4')
