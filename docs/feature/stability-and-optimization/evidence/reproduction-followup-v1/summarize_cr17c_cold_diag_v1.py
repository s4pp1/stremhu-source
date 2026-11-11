"""Diagnostic summary for the cr17c-after-v1 heap/cold1 FAIL. Not a gate, not a waiver."""
from pathlib import Path
import hashlib, json, statistics
r = Path(__file__).parent
d = r / 'diag-cold-v1'
runs = {}
for mode in ['heap', 'heapnocp', 'heapgcnocp']:
    for f in sorted(d.glob(f'{mode}-*.stdout')):
        stem = f.stem
        if stem.split('-')[0] != mode:
            continue
        raw = f.read_bytes()
        out = json.loads(raw.decode('utf-8').strip().splitlines()[-1])
        runs[stem] = dict(mode=mode, label=stem.split('-')[1], cold_ms=[round(c['wall_seconds'] * 1000, 2) for c in out['cold']],
                          cold_sql=[c['sql_statements'] for c in out['cold']], payload=[c['payload_hash'] for c in out['cold']],
                          gc_gen1plus_or_ge1ms=out.get('gc'), stdout_sha256=hashlib.sha256(raw).hexdigest())
def summary(mode):
    res = {}
    for label in ['before', 'after']:
        xs = [v['cold_ms'] for v in runs.values() if v['mode'] == mode and v['label'] == label]
        res[label] = dict(cold0_median_ms=statistics.median(x[0] for x in xs), cold1_median_ms=statistics.median(x[1] for x in xs),
                          sum_median_ms=statistics.median(x[0] + x[1] for x in xs), n=len(xs))
    return res
report = dict(
    id='cr17c-cold-gc-diagnostic-v1', type='diagnostic', is_measurement_gate=False,
    purpose='Explain the single cr17c-after-v1 FAIL row heap/cold1 wall_seconds. Does not change, waive or re-evaluate the registered assessment.',
    method='Fixture cr17c-policy-fixture-v1 with the heap-profile mode cut after the two cold requests (count=100, user0 then user1, tracemalloc on). Same image, cpuset 6,7, 2 CPU, 1 GiB, no network; before=Source2 frozen, after=frozen packet21b source; 3 alternating pairs per mode. Modes: heap = cProfile around each cold request; heapnocp = no cProfile; heapgcnocp = no cProfile plus gc.callbacks recording collections of generation>=1 or >=1 ms.',
    fixture_sha256=hashlib.sha256((r / 'cr17c-cold-diagnostic-v1.py').read_bytes()).hexdigest(),
    runner_sha256=hashlib.sha256((r / 'run_cold_diag.py').read_bytes()).hexdigest(),
    summaries={m: summary(m) for m in ['heap', 'heapnocp', 'heapgcnocp']},
    runs=runs,
    finding='Reproduced 3/3: without cProfile the after cold0 is ~30-40 ms faster and cold1 ~30 ms slower, the sum is unchanged. In every after run one ~28 ms generation-2 collection fires in cold-1, in every before run in cold-0; after runs an extra generation-1 collection in cold-0. Payloads and SQL (10/10) are identical. Under cProfile the shift disappears and the profiles are equivalent. This is the same gen2-phase mechanism V7 identified for packet20.',
    limits='Diagnostic only: 3 pairs per mode, single fixture, tracemalloc on. It does not show that the after path allocates more or less in general and it is not an acceptance argument; the registered FAIL stands.',
)
(r / 'evidence' / 'cr17c-cold-gc-diagnostic-v1.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report['summaries'], indent=1))
