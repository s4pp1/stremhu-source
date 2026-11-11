"""Assessor for cr17c-after-v1 (packet 21b). Written and hashed into the protocol before any run.

Thresholds are the V6 ones: HTTP p95 max(before medians)+10ms, CPU max*1.10, memory +2MiB
(+2048KiB RSS), SQL <= max before value, strict metrics <= max(before values)+J where J is the
spread of the before group medians. Every after group median must be within its limit.
Ownership gate: zero DetachedInstanceError and zero non-200 in the C Kodi and direct series.
Kodi timing and all A/B/C references are observations. Old Source2 long runs are context only.
"""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import statistics

r = Path(__file__).parent
e = r / 'evidence'
target = e / 'cr17c-after-v1-assessment.json'
if target.exists():
    raise RuntimeError('Refusing assessment overwrite')
med = statistics.median
rows, failures, observations, used = [], [], [], []
P = 'cr17c-after-v1'


def read(name):
    used.append(name)
    return json.loads((e / name).read_text(encoding='utf-8'))


def record(row, gate=True):
    (rows if gate else observations).append(row)
    if gate and not row['passed']:
        failures.append(row)


def attempt(phase, label, series, i):
    stem = f'{P}-{phase}-{label}-{series}-{i}'
    if (e / (stem + '.json')).exists():
        return read(stem + '.json')
    if (e / (stem + '-failed.json')).exists():
        read(stem + '-failed.json')
    return None


def budget(scope, metric, kind, before, after, gate=True):
    bm, am = [med(g) for g in before], [med(g) for g in after]
    flat = [x for g in before for x in g]
    J = max(bm) - min(bm)
    limit = {'http': max(bm) + 10, 'cpu': max(bm) * 1.10, 'bytes': max(bm) + 2097152, 'kib': max(bm) + 2048,
             'sql': max(flat)}.get(kind, max(flat) + J)
    record(dict(scope=scope, metric=metric, kind=kind, before_medians=bm, after_medians=am, J=J,
                before_range=[min(flat), max(flat)], limit=limit, passed=all(a <= limit for a in am)), gate)


MEMORY = [('anon_bytes', 'bytes'), ('current_bytes', 'bytes'), ('peak_bytes', 'bytes'), ('max_rss_kib', 'kib')]


def series_runs(phase, label):
    return [[attempt(phase, label, s, i) for i in range(5)] for s in 'ab']


def complete(phase, label, groups, gate=True):
    missing = [f'{s}-{i}' for s, g in zip('ab', groups) for i, d in enumerate(g) if d is None]
    record(dict(scope=phase, metric=f'{label}_all_attempts_complete', missing=missing, passed=not missing), gate)


def cells(scope, bg_runs, ag_runs, gate=True, row_ok=lambda row: True):
    keyf = lambda row: (row['count'], row['kind'], row['concurrency'])
    before = [[d for d in g if d] for g in bg_runs]
    after = [[d for d in g if d] for g in ag_runs]
    template = next(d for g in before + after for d in g)
    for key in [keyf(x) for x in template['rows']]:
        pick = lambda groups: [[x for d in g for x in d['rows'] if keyf(x) == key and row_ok(x)] for g in groups]
        bg, ag = pick(before), pick(after)
        allrows = [x for g in bg + ag for x in g]
        identical = len({tuple(x['payload_hashes']) for x in allrows}) <= 1 and len({tuple(x['result_counts']) for x in allrows}) <= 1
        record(dict(scope=f'{scope}/{key}', metric='payload_order_count_identity', rows=len(allrows), passed=identical and bool(allrows)))
        if not all(bg) or not all(ag):
            record(dict(scope=f'{scope}/{key}', metric='timing_rows_available', passed=False), gate)
            continue
        for metric, kind in [('p95_ms', 'http'), ('cpu_seconds', 'cpu'), ('sql_statements', 'sql')]:
            budget(f'{scope}/{key}', metric, kind, [[x[metric] for x in g] for g in bg], [[x[metric] for x in g] for g in ag], gate)
        for metric, kind in MEMORY:
            budget(f'{scope}/{key}', 'memory.' + metric, kind, [[x['memory'][metric] for x in g] for g in bg], [[x['memory'][metric] for x in g] for g in ag], gate)


def colds(scope, bg_runs, ag_runs, gate=True):
    before = [[d for d in g if d] for g in bg_runs]
    after = [[d for d in g if d] for g in ag_runs]
    for index in range(len(next(d for g in before for d in g)['cold'])):
        bg = [[d['cold'][index] for d in g] for g in before]
        ag = [[d['cold'][index] for d in g] for g in after]
        allc = [c for g in bg + ag for c in g]
        record(dict(scope=f'{scope}/cold{index}', metric='payload_identity',
                    passed=len({(c['count'], c['user'], c['payload_hash'], c['result_count']) for c in allc}) == 1))
        budget(f'{scope}/cold{index}', 'wall_seconds', 'strict', [[c['wall_seconds'] for c in g] for g in bg], [[c['wall_seconds'] for c in g] for g in ag], gate)
        budget(f'{scope}/cold{index}', 'sql_statements', 'sql', [[c['sql_statements'] for c in g] for g in bg], [[c['sql_statements'] for c in g] for g in ag], gate)


def references(phase):
    files = {label: [attempt(phase, label, 'ref', i) for i in range(5)] for label in 'ABC'}
    counts = {label: sum(d is not None for d in v) for label, v in files.items()}
    a_failed = []
    for i in range(5):
        name = f'{P}-{phase}-A-ref-{i}-failed.json'
        if (e / name).exists():
            a_failed.append(read(name))
    observations.append(dict(scope=f'{phase}/reference', metric='complete_files', files=counts,
                             A_failed_detached_instance_error=[f['detached_instance_error'] for f in a_failed]))
    record(dict(scope=f'{phase}/reference', metric='B_C_complete', files=counts, passed=counts['B'] == 5 and counts['C'] == 5))


# 0. Smoke.
for label in ['after', 'before']:
    record(dict(scope='smoke', metric=f'{label}_complete', passed=attempt('smoke', label, 'smoke', 0) is not None))

# 1. Primary short: fresh paired cohorts.
sb, sa = series_runs('short', 'before'), series_runs('short', 'after')
complete('short', 'after', sa)
complete('short', 'before', sb)
cells('short', sb, sa)
colds('short', sb, sa)
references('short')

# 2. Direct: ownership gate and timing gate.
db, da = series_runs('direct', 'before'), series_runs('direct', 'after')
complete('direct', 'after', da)
observations.append(dict(scope='direct', metric='before_failed_attempts', failed=sum(d is None for g in db for d in g)))
if all(d is not None for g in db for d in g):
    cells('direct', db, da)
    colds('direct', db, da)
else:
    record(dict(scope='direct', metric='before_cohorts_complete_for_timing', passed=False))
references('direct')

# 3. Kodi: ownership gate; timing observational.


def kodi_totals(groups):
    errors, statuses, error_cells = collections.Counter(), collections.Counter(), 0
    for d in [x for g in groups for x in g if x]:
        errors.update(d['reference_errors'])
        statuses.update(d['reference_statuses'])
        error_cells += sum(bool(x['reference_errors']) for x in d['rows'])
    return dict(errors=dict(errors), statuses={str(k): v for k, v in statuses.items()}, error_cells=error_cells)


kb, ka = series_runs('kodi', 'before'), series_runs('kodi', 'after')
complete('kodi', 'after', ka)
tb, ta = kodi_totals(kb), kodi_totals(ka)
record(dict(scope='kodi', metric='after_zero_errors_only_200', before=tb, after=ta,
            passed=not ta['errors'] and set(ta['statuses']) <= {'200'} and all(d is not None for g in ka for d in g)))
clean = lambda row: not row['reference_errors']
# Payload identity on clean cells is recorded as a gate inside cells(); Kodi timing is an observation.
cells('kodi', kb, ka, gate=False, row_ok=clean)
references('kodi')

# 4. Heap long: three contemporaneous pairs, fresh Source2 before.
lb = [attempt('long', 'before', 'pair', i) for i in range(3)]
la = [attempt('long', 'after', 'pair', i) for i in range(3)]
for label, runs in [('before', lb), ('after', la)]:
    for i, d in enumerate(runs):
        ok = d is not None and d['profile']['measured_seconds'] >= 1800 and len(d['rows']) == 60 and not d['external_http_attempts'] and all(
            x['tasks_quiescent'] == 1 and x['pool_checked_out'] == 0 and x['background_tasks'] == 0 for x in d['rows'])
        record(dict(scope='heap', metric=f'{label}{i}_complete_quiescent_pool0_background0', passed=ok))
if all(lb) and all(la):
    keyf = lambda x: (x['kind'], x['concurrency'])
    for key in sorted({keyf(x) for x in lb[0]['rows']}):
        bg = [[x for x in d['rows'] if keyf(x) == key] for d in lb]
        ag = [[x for x in d['rows'] if keyf(x) == key] for d in la]
        allrows = [x for g in bg + ag for x in g]
        record(dict(scope=f'heap/{key}', metric='payload_order_count_identity',
                    passed=len({tuple(x['payload_hashes']) for x in allrows}) == 1 and len({tuple(x['result_counts']) for x in allrows}) == 1))
        for metric, kind in [('p95_ms', 'http'), ('cpu_seconds', 'cpu'), ('sql_statements', 'sql'), ('heap_bytes_after_gc', 'bytes'), ('loop_lag_p99_ms', 'strict')]:
            budget(f'heap/{key}', metric, kind, [[x[metric] for x in g] for g in bg], [[x[metric] for x in g] for g in ag])
        for metric, kind in MEMORY + [('file_bytes', 'strict')]:
            budget(f'heap/{key}', 'memory.' + metric, kind, [[x['memory'][metric] for x in g] for g in bg], [[x['memory'][metric] for x in g] for g in ag])
        paired = [med(x['p95_ms'] for x in a) - med(x['p95_ms'] for x in b) for a, b in zip(ag, bg)]
        observations.append(dict(scope=f'heap/{key}', metric='p95_contemporaneous_paired_diffs_ms', diffs=paired, median=med(paired)))
    colds('heap', [[d] for d in lb], [[d] for d in la])
    for label, runs in [('before', lb), ('after', la)]:
        for i, d in enumerate(runs):
            gen2 = [g['phase'] for g in d.get('gc_events', []) if g.get('generation') == 2 and str(g.get('phase', '')).startswith('cold-')]
            observations.append(dict(scope='heap/trend', run=f'{label}{i}', gen2_cold_phases=gen2,
                                     first12_heap_after_gc=med(x['heap_bytes_after_gc'] for x in d['rows'][:12]),
                                     last12_heap_after_gc=med(x['heap_bytes_after_gc'] for x in d['rows'][-12:])))

report = dict(
    status='PASS' if not failures else 'FAIL',
    evaluated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    protocol=P + '-protocol.json',
    protocol_sha256=hashlib.sha256((e / (P + '-protocol.json')).read_bytes()).hexdigest(),
    assessor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    gate_checks=len(rows), failures=failures, rows=rows, observations=observations,
    raw_sha256={name: hashlib.sha256((e / name).read_bytes()).hexdigest() for name in sorted(set(used))},
)
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(dict(status=report['status'], gate_checks=len(rows), failures=[(x['scope'], x['metric']) for x in failures],
                      kodi_before=tb, kodi_after=ta)))
