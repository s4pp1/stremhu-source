"""Composite CR17/b SourceV4 assessment for cr17b-policy-after-composite-v6.

Written after all V6 controllers finished, before any composite result was computed.
Implements the preregistered protocol text verbatim; no threshold differs from V5/V6:
- normal/direct/profiled: after cohort/run median <= max(before medians)+10ms (HTTP),
  <= max(before medians)*1.10 (CPU), <= max(before medians)+2MiB (memory), SQL no increase;
- strict other metrics: after median <= full before range max + J;
- cold wall: after <= before range max + J;
- complete quiescence/pool0/background0, identical payload/order/count;
- Kodi is an observation: gate is no new functional error class and identical successful
  payloads; its timing is reported, not gated. Upstream A direct failures are recorded.
"""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import statistics

r = Path(__file__).parent
e = r / 'evidence'
target = e / 'cr17b-policy-composite-assessment-v6.json'
if target.exists():
    raise RuntimeError('Refusing composite assessment overwrite')
med = statistics.median
load = lambda name: json.loads((e / name).read_text(encoding='utf-8'))
rows = []
failures = []
observations = []
used = []


def read(name):
    used.append(name)
    return load(name)


def record(row, gate=True):
    (rows if gate else observations).append(row)
    if gate and not row['passed']:
        failures.append(row)


def budget(scope, metric, kind, before, after, gate=True):
    """before/after: list of value lists (one list per cohort/run)."""
    bm = [med(group) for group in before]
    am = [med(group) for group in after]
    J = abs(bm[0] - bm[1]) if len(bm) == 2 else 0
    flat = [x for group in before for x in group]
    if kind == 'http':
        limit = max(bm) + 10
    elif kind == 'cpu':
        limit = max(bm) * 1.10
    elif kind == 'bytes':
        limit = max(bm) + 2097152
    elif kind == 'kib':
        limit = max(bm) + 2048
    elif kind == 'sql':
        limit = max(flat)
    else:
        limit = max(flat) + J
    record(dict(scope=scope, metric=metric, kind=kind, before_medians=bm, after_medians=am, J=J,
                before_range=[min(flat), max(flat)], limit=limit, passed=all(a <= limit for a in am)), gate)


MEMORY = [('anon_bytes', 'bytes'), ('current_bytes', 'bytes'), ('peak_bytes', 'bytes'), ('max_rss_kib', 'kib')]


def cells(scope, before_runs, after_runs, gate=True, row_ok=lambda row: True):
    keyf = lambda row: (row['count'], row['kind'], row['concurrency'])
    keys = [keyf(row) for row in before_runs[0][0]['rows']]
    for key in keys:
        pick = lambda groups: [[row for d in group for row in d['rows'] if keyf(row) == key and row_ok(row)] for group in groups]
        bg, ag = pick(before_runs), pick(after_runs)
        allrows = [row for group in bg + ag for row in group]
        identical = len({tuple(row['payload_hashes']) for row in allrows}) == 1 and len({tuple(row['result_counts']) for row in allrows}) == 1
        record(dict(scope=f'{scope}/{key}', metric='payload_order_count_identity', rows=len(allrows), passed=identical))
        if not all(bg) or not all(ag):
            record(dict(scope=f'{scope}/{key}', metric='timing_rows_available', passed=False), gate)
            continue
        metrics = [('p95_ms', 'http'), ('cpu_seconds', 'cpu'), ('sql_statements', 'sql')]
        for metric, kind in metrics:
            budget(f'{scope}/{key}', metric, kind, [[x[metric] for x in g] for g in bg], [[x[metric] for x in g] for g in ag], gate)
        for metric, kind in MEMORY:
            budget(f'{scope}/{key}', 'memory.' + metric, kind, [[x['memory'][metric] for x in g] for g in bg], [[x['memory'][metric] for x in g] for g in ag], gate)
        budget(f'{scope}/{key}', 'memory.file_bytes', 'strict', [[x['memory']['file_bytes'] for x in g] for g in bg], [[x['memory']['file_bytes'] for x in g] for g in ag], gate)


def colds(scope, before_runs, after_runs, gate=True):
    for index in range(len(before_runs[0][0]['cold'])):
        bg = [[d['cold'][index] for d in group] for group in before_runs]
        ag = [[d['cold'][index] for d in group] for group in after_runs]
        allc = [c for group in bg + ag for c in group]
        identical = len({(c['count'], c['user'], c['payload_hash'], c['result_count']) for c in allc}) == 1
        record(dict(scope=f'{scope}/cold{index}', metric='payload_identity', passed=identical))
        budget(f'{scope}/cold{index}', 'wall_seconds', 'strict', [[c['wall_seconds'] for c in g] for g in bg], [[c['wall_seconds'] for c in g] for g in ag], gate)
        budget(f'{scope}/cold{index}', 'sql_statements', 'sql', [[c['sql_statements'] for c in g] for g in bg], [[c['sql_statements'] for c in g] for g in ag], gate)


# 1. Primary short (separately preregistered assessor).
short = read('cr17b-primary-short-assessment-v6.json')
record(dict(scope='primary-short', metric='registered_short_assessor_status', status=short['status'], passed=short['status'] == 'PASS'))

# 2. Two full 1800s heap controls vs preselected accepted Source2 long runs 0/1.
heap_before = [[read(f'cr17a-drain-paired-long-v2-after-{i}.json')] for i in range(2)]
heap_after = [[read(f'cr17b-after-long-v6-C-{s}-0.json')] for s in ['a', 'b']]
for (d,) in heap_before + heap_after:
    ok = (d['profile']['measured_seconds'] >= 1800 and len(d['rows']) == 60 and not d['external_http_attempts']
          and all(x['tasks_quiescent'] == 1 and x['pool_checked_out'] == 0 and x['background_tasks'] == 0 for x in d['rows']))
    record(dict(scope='heap', metric='complete_quiescent_pool0_background0', run=d.get('protocol'), passed=ok))
heap_keyf = lambda row: (row['kind'], row['concurrency'])
for key in sorted({heap_keyf(x) for x in heap_before[0][0]['rows']}):
    bg = [[x for x in g[0]['rows'] if heap_keyf(x) == key] for g in heap_before]
    ag = [[x for x in g[0]['rows'] if heap_keyf(x) == key] for g in heap_after]
    allrows = [x for g in bg + ag for x in g]
    record(dict(scope=f'heap/{key}', metric='payload_order_count_identity', rows=len(allrows),
                passed=all(len(g) == 10 for g in bg + ag) and len({tuple(x['payload_hashes']) for x in allrows}) == 1 and len({tuple(x['result_counts']) for x in allrows}) == 1))
    for metric, kind in [('p95_ms', 'http'), ('cpu_seconds', 'cpu'), ('sql_statements', 'sql'), ('heap_bytes_after_gc', 'bytes'), ('loop_lag_p99_ms', 'strict')]:
        budget(f'heap/{key}', metric, kind, [[x[metric] for x in g] for g in bg], [[x[metric] for x in g] for g in ag])
    for metric, kind in MEMORY + [('file_bytes', 'strict')]:
        budget(f'heap/{key}', 'memory.' + metric, kind, [[x['memory'][metric] for x in g] for g in bg], [[x['memory'][metric] for x in g] for g in ag])
colds('heap', heap_before, heap_after)
for (d,) in heap_after:
    first, last = d['rows'][:12], d['rows'][-12:]
    observations.append(dict(scope='heap/trend', run=d.get('protocol') + '/' + str(d.get('source_C')),
                             first12_median_heap_after_gc=med(x['heap_bytes_after_gc'] for x in first),
                             last12_median_heap_after_gc=med(x['heap_bytes_after_gc'] for x in last),
                             first12_median_anon=med(x['memory']['anon_bytes'] for x in first),
                             last12_median_anon=med(x['memory']['anon_bytes'] for x in last)))

# 3. Complementary direct: exact Source2 before V4 cohorts vs SourceV4 after V6 cohorts.
direct_before = [[read(f'cr17b-complementary-before-v4-C-direct-exact-{s}-{i}.json') for i in range(5)] for s in ['a', 'b']]
direct_after = [[read(f'cr17b-complementary-after-v6-C-direct-exact-{s}-{i}.json') for i in range(5)] for s in ['a', 'b']]
for d in [x for g in direct_after for x in g]:
    record(dict(scope='direct', metric='complete_no_external_http', series=d['series'], repetition=d['repetition'],
                passed=len(d['rows']) == 12 and not d['external_http_attempts'] and all(len(x['samples_ms']) == 100 for x in d['rows'])))
cells('direct', direct_before, direct_after)
colds('direct', direct_before, direct_after)
direct_refs = {label: [name for i in range(5) if (e / (name := f'cr17b-complementary-after-v6-{label}-direct-exact-reference-{i}.json')).exists()] for label in 'ABC'}
for label in 'BC':
    record(dict(scope='direct/reference', metric=f'{label}_complete_files', files=len(direct_refs[label]), passed=len(direct_refs[label]) == 5))
    used.extend(direct_refs[label])
a_failures = {}
for i in range(5):
    name = f'cr17b-complementary-after-v6-A-direct-exact-reference-{i}.stderr'
    raw = (e / name).read_bytes()
    text = raw.decode('utf-8', 'replace')
    a_failures[name] = dict(error_kind='DetachedInstanceError' if 'DetachedInstanceError' in text else ('no stderr' if not raw else 'other'), sha256=hashlib.sha256(raw).hexdigest(), timing_usable=False)
record(dict(scope='direct/reference', metric='A_upstream_failures_preexisting_class_only', A_complete_files=len(direct_refs['A']),
            failures=a_failures, passed=all(v['error_kind'] in ('DetachedInstanceError', 'no stderr') for v in a_failures.values())))

# 4. Kodi observation: functional gate on error classes and successful payloads; timing observational.
kodi_before = [[read(f'cr17b-kodi-observation-before-v4-C-kodi-observation-{s}-{i}.json') for i in range(5)] for s in ['a', 'b']]
kodi_after = [[read(f'cr17b-kodi-observation-after-v6-C-kodi-observation-{s}-{i}.json') for i in range(5)] for s in ['a', 'b']]


def kodi_totals(groups):
    errors, statuses, error_cells, cells_total = collections.Counter(), collections.Counter(), 0, 0
    for d in [x for g in groups for x in g]:
        errors.update(d['reference_errors'])
        statuses.update(d['reference_statuses'])
        for row in d['rows']:
            cells_total += 1
            error_cells += bool(row['reference_errors'])
    return dict(errors=dict(errors), statuses=dict(statuses), error_cells=error_cells, cells=cells_total)


kb, ka = kodi_totals(kodi_before), kodi_totals(kodi_after)
record(dict(scope='kodi', metric='no_new_error_class_or_status', before=kb, after=ka,
            passed=set(ka['errors']) <= set(kb['errors']) and set(ka['statuses']) <= set(kb['statuses'])))
clean = lambda row: not row['reference_errors']
# Payload identity on successful cells stays a functional gate; Kodi timing is observational.
cells('kodi', kodi_before, kodi_after, gate=False, row_ok=clean)
colds('kodi', kodi_before, kodi_after, gate=False)
for d in [x for g in kodi_after for x in g]:
    record(dict(scope='kodi', metric='no_external_http', series=d['series'], repetition=d['repetition'], passed=not d['external_http_attempts']))
kodi_refs = {label: len([i for i in range(5) if (e / f'cr17b-kodi-observation-after-v6-{label}-kodi-observation-reference-{i}.json').exists()]) for label in 'ABC'}
record(dict(scope='kodi/reference', metric='ABC_complete_files', files=kodi_refs, passed=all(v == 5 for v in kodi_refs.values())))

# 5. Primary ABC references: completeness only (A/B/C are context, not gate inputs).
for label in 'ABC':
    names = [f'cr17b-after-references-v6-{label}-ref-{i}.json' for i in range(5)]
    ok = True
    for name in names:
        d = read(name)
        ok = ok and len(d['rows']) == 12 and not d['external_http_attempts'] and all(len(x['samples_ms']) == 100 for x in d['rows'])
    record(dict(scope='primary/reference', metric=f'{label}_complete', passed=ok))

report = dict(
    status='PASS' if not failures else 'FAIL',
    evaluated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    protocol='cr17b-policy-after-composite-v6-protocol.json',
    protocol_sha256=hashlib.sha256((e / 'cr17b-policy-after-composite-v6-protocol.json').read_bytes()).hexdigest(),
    assessor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    assessor_note='Composite assessor written after V6 data collection finished and before any composite result was computed; criteria copied from the preregistered protocol, no threshold changed.',
    scope='Packet20 SourceV4 policy snapshot + in-flight policy Singleflight. Provider/file UoW (21/22) and Kodi residual DetachedInstanceError ownership remain open.',
    gate_checks=len(rows),
    failures=failures,
    rows=rows,
    observations=observations,
    raw_sha256={name: hashlib.sha256((e / name).read_bytes()).hexdigest() for name in sorted(set(used))},
)
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(dict(status=report['status'], gate_checks=len(rows), observations=len(observations),
                      failures=[(x['scope'], x['metric']) for x in failures], kodi_before=kb, kodi_after=ka)))
