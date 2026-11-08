"""Derive the cr17e-after-v1 (packet 22b) controller and assessor from the cr17d-after-v1 ones.
Only names, the after source/manifest and docstrings change; fixtures (cr17d-*-v2.py), gates and thresholds are reused unchanged."""
from pathlib import Path
r = Path(__file__).parent


def derive(src, dst, pairs):
    raw = (r / src).read_bytes().decode('utf-8')
    nl = '\r\n' if '\r\n' in raw else '\n'
    s = raw.replace('\r\n', '\n')
    for old, new, count in pairs:
        assert s.count(old) == count, (src, old, s.count(old))
        s = s.replace(old, new)
    assert 'cr17d-after-v1' not in s and 'cr17d-after-v1-source' not in s, src
    (r / dst).write_bytes(s.replace('\n', nl).encode('utf-8'))


derive('cr17d_after_v1.py', 'cr17e_after_v1.py', [
    ('"""CR17/d packet 22 runtime gate controller (cr17d-after-v1).', '"""CR17/d packet 22b runtime gate controller (cr17e-after-v1).', 1),
    ('before = frozen packet21b, after/C = frozen packet22.', 'before = frozen packet21b, after/C = frozen packet22b.', 1),
    ('after/C = frozen packet22 (cr17d-after-v1-source)', 'after/C = frozen packet22b (cr17e-after-v1-source)', 1),
    ("'after': r / 'cr17d-after-v1-source/server'", "'after': r / 'cr17e-after-v1-source/server'", 1),
    ("'after': 'cr17d-checked-v1-manifest.json'", "'after': 'cr17e-checked-v1-manifest.json'", 1),
    ('cr17d-after-v1', 'cr17e-after-v1', 4),
])
derive('assess_cr17d_after_v1.py', 'assess_cr17e_after_v1.py', [
    ('"""Assessor for cr17d-after-v1 (packet 22).', '"""Assessor for cr17e-after-v1 (packet 22b).', 1),
    ('after = frozen packet22.', 'after = frozen packet22b.', 1),
    ('cr17d-after-v1', 'cr17e-after-v1', 2),
])
print('ok')
