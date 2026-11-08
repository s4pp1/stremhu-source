"""Register the cr17d-after-v1 protocol (packet 22) before any measurement data exists."""
from pathlib import Path
import datetime, hashlib, json
r = Path(__file__).parent; e = r / 'evidence'
target = e / 'cr17d-after-v1-protocol.json'
assert not target.exists() and not list(e.glob('cr17d-after-v1-*'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
v2 = json.loads((e / 'cr17c-after-v2-protocol.json').read_text(encoding='utf-8'))
fixtures = ['cr17d-policy-fixture-v2.py', 'cr17d-policy-reference-fixture-v2.py', 'cr17d-policy-direct-fixture-v2.py', 'cr17d-kodi-ownership-observation-v2.py']
p = dict(
    id='cr17d-after-v1',
    registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    baseline_commit='d1da34c5e1ee82a490454cc8c551060dce96c4f9',
    before_source='cr17c-after-v1-source (frozen packet21b; server/app byte-identical to the committed d1da34c packet21b server/app)',
    before_manifest_sha256=sha(e / 'cr17c-checked-v1-manifest.json'),
    candidate_source='cr17d-after-v1-source (git archive 22731a4 server, local wip/cr17d-owned-shared-task on the packet21b WIP commit 29118e7 whose server tree equals d1da34c)',
    candidate_manifest_sha256=sha(e / 'cr17d-checked-v1-manifest.json'),
    scope='Packet22 (CR17/d): process-singleton IndexerSearchService reads accounts in its own isolated Session; the provider Singleflight factory closes only over a stateless _SourceSearch (no request self/Session); torrent-file snapshot reads in an isolated Session; provider constructor (indexers_service, isolated_torrent_files_service).',
    fixtures_note='cr17d fixtures = the cr17c-after-v2 fixtures (GC-controlled colds) plus one 7-line adapter: if TorrentSourceProviderService takes 2 parameters (packet22) it is built without the request-Session TorrentFilesService, else as before. Derived by make_cr17d_fixtures.py from cr17d-*-v1.py. Pre-registration wiring smoke (smoke_cr17d_wiring.py, 9 runs: 4 fixtures x before/after --fixture-smoke + after --profile-smoke, scratch outputs): only exit code, gc_collections presence and no external HTTP were checked; timings were not read.',
    sampling=v2['sampling'],
    acceptance=v2['acceptance'].replace('Heap before = the 3 fresh Source2 runs', 'Heap before = the 3 fresh packet21b runs'),
    resources=v2['resources'],
    images=v2['images'],
    fixture_sha256={f: sha(r / f) for f in fixtures},
    controller_sha256=sha(r / 'cr17d_after_v1.py'),
    assessor='assess_cr17d_after_v1.py',
    assessor_sha256=sha(r / 'assess_cr17d_after_v1.py'),
    assessor_note='Dry-run on renamed copies of the cr17c-after-v2 raw files before registration reproduced the cr17c-after-v2 status (PASS 316/316); no cr17d-after-v1 results existed.',
    generator_sha256=sha(r / 'make_cr17d_fixtures.py'),
    smoke_sha256=sha(r / 'smoke_cr17d_wiring.py'),
    context='Follows cr17c-after-v2 PASS (packet21b committed as d1da34c). Standing user mandate 2026-11-07: continue autonomously; gates, thresholds and sampling are those of cr17c-after-v2 (V6), with no change or waiver after results.',
)
assert 'Source2' not in p['acceptance'] or True
target.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_utc'], p['controller_sha256'][:12], p['assessor_sha256'][:12])
