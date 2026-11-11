"""Register the cr17e-after-v1 protocol (packet 22b) before any measurement data exists."""
from pathlib import Path
import datetime, hashlib, json
r = Path(__file__).parent; e = r / 'evidence'
target = e / 'cr17e-after-v1-protocol.json'
assert not target.exists() and not list(e.glob('cr17e-after-v1-*'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
d = json.loads((e / 'cr17d-after-v1-protocol.json').read_text(encoding='utf-8'))
p = dict(
    id='cr17e-after-v1',
    registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    baseline_commit=d['baseline_commit'], before_source=d['before_source'], before_manifest_sha256=d['before_manifest_sha256'],
    candidate_source='cr17e-after-v1-source (git archive of the packet22b server tree, local wip/cr17e-shared-read-gate 5be09f2 on 41623ce = packet22 cherry-picked onto d1da34c)',
    candidate_manifest_sha256=sha(e / 'cr17e-checked-v1-manifest.json'),
    scope='Packet22b (CR17/d): packet22 (stateless shared search, isolated reads) plus a process-wide one-slot gate (database.shared_read_session, non-reentrant) around the isolated reads of shared searches, so they add at most one connection next to the request Sessions.',
    fixtures_note='Fixtures reused unchanged from cr17d-after-v1 (same sha256; provider-constructor adapter and GC-controlled colds). Pre-registration wiring smoke on 22b (smoke_cr17e_wiring.py, 5 runs: 4 fixtures --fixture-smoke + --profile-smoke, after only; before was smoked for cr17d): only exit code, gc_collections presence and no external HTTP were checked; timings and memory were not read. Exploratory pool pre-screen (cr17d-pool-diagnostic-v1 fixture, 2 runs per arm) read connection counts and memory to choose the candidate; those runs are not gate data.',
    sampling=d['sampling'], acceptance=d['acceptance'], resources=d['resources'], images=d['images'],
    fixture_sha256=d['fixture_sha256'],
    controller_sha256=sha(r / 'cr17e_after_v1.py'),
    assessor='assess_cr17e_after_v1.py', assessor_sha256=sha(r / 'assess_cr17e_after_v1.py'),
    assessor_note='Dry-run on renamed copies of the cr17d-after-v1 raw files before registration reproduced the cr17d-after-v1 status (FAIL, 35 memory rows); no cr17e-after-v1 results existed.',
    generator='make_cr17e_gate.py', generator_sha256=sha(r / 'make_cr17e_gate.py'),
    smoke_sha256=sha(r / 'smoke_cr17e_wiring.py'),
    supersedes=dict(protocol='cr17d-after-v1', protocol_sha256=sha(e / 'cr17d-after-v1-protocol.json'),
                    status='FAIL (35/316, memory only); retained unchanged, not waived', diagnostic='cr17d-pool-diagnostic-v1.json'),
    decision='User decision 2026-11-07: option 1, a new 22b candidate that keeps simultaneous connections at the before level, then a new preregistered gate.',
    change_from_cr17d='Candidate source only (packet22 -> packet22b). Controller and assessor: cr17d versions with names/after source/manifest changed (make_cr17e_gate.py). Fixtures, sampling, order, resources, images, before source, gates and thresholds unchanged. All data fresh; cr17d data is context only and not pooled.',
)
for f, h in p['fixture_sha256'].items():
    assert sha(r / f) == h, f
target.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_utc'], p['controller_sha256'][:12], p['assessor_sha256'][:12])
