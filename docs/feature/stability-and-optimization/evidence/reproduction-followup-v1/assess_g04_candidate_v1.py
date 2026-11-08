"""Preregistered G04 candidate assessor v1 (CR04 torrent-row memo)."""
import hashlib
import json
import pathlib
import statistics

r = pathlib.Path(__file__).parent
e = r / 'evidence'
BASE_A = ['g04-before-a-0-v1.json', 'g04-before-a-1-v1.json', 'g04-before-a-2-v1.json', 'g04-before-a-3-v2.json', 'g04-before-a-4-v2.json']
BASE_B = ['g04-before-b-0-v1.json', 'g04-before-b-1-v1.json', 'g04-before-b-2-v1.json', 'g04-before-b-3-v2.json', 'g04-before-b-4-v2.json']
HEAP_BASE = ['g04-heap-a-0-v1.json', 'g04-heap-b-0-v1.json']
RESOLUTION = dict(requests=1, route_renders=1, row_render_calls=1, react_commits=1, react_actual_ms=0.1, cpu_usec=1000, anon_after=4096)
TARGET = [(20, 'one'), (100, 'one'), (500, 'one')]
MIB2 = 2 * 1024 * 1024


def load(name):
    return json.loads((e / name).read_text(encoding='utf-8'))


def metrics(row):
    return dict(requests=row['requests'], route_renders=row['routeRenders'], row_render_calls=sum(row['rowRenders'].values()),
                react_commits=len(row['commits']), react_actual_ms=sum(c['actualDuration'] for c in row['commits']),
                cpu_usec=row['resource_after']['cpu_usec'] - row['resource_before']['cpu_usec'], anon_after=row['resource_after']['anon_bytes'])


def cells(runs):
    out = {}
    for d in runs:
        for row in d['rows']:
            out.setdefault((row['count'], row['pattern']), []).append(metrics(row))
    return out


def run_ok(d, heap):
    rows = d['rows']
    ok = d['is_measurement'] and len(rows) == (1 if heap else 16) and all(
        not row['errors'] and row['elapsed_ms'] >= (1815000 if heap else 300000) and row['warmupRequests'] >= 3 for row in rows)
    if heap:
        ok = ok and rows[0]['navigations'] == 50 and rows[0]['heap'] and rows[0]['heap'][-1]['queries'] == 0
    return bool(ok)


def assess(after_names, control_names, heap_name, base_a=BASE_A, base_b=BASE_B):
    a, b = cells([load(n) for n in base_a]), cells([load(n) for n in base_b])
    after_runs = [load(n) for n in after_names]
    control_runs = [load(n) for n in control_names]
    heap_run = load(heap_name) if heap_name else None
    correctness = [dict(run=n, passed=run_ok(d, False)) for n, d in zip(after_names, after_runs)]
    correctness += [dict(run=n, passed=run_ok(d, False)) for n, d in zip(control_names, control_runs)]
    if heap_run is not None:
        correctness.append(dict(run=heap_name, passed=run_ok(heap_run, True)))
    after, control = cells(after_runs), cells(control_runs)
    rows = []
    for key in sorted(a, key=lambda k: (k[0], ['stable', 'one', 'all', 'stalled'].index(k[1]))):
        for m in RESOLUTION:
            ma, mb = statistics.median(x[m] for x in a[key]), statistics.median(x[m] for x in b[key])
            j = max(abs(ma - mb), RESOLUTION[m])
            lo = min(x[m] for x in a[key] + b[key])
            hi = max(x[m] for x in a[key] + b[key])
            med = statistics.median(x[m] for x in after[key])
            base = dict(cell=f'{key[0]}/{key[1]}', metric=m, after_median=med, before_min=lo, before_max=hi, J=j)
            if m == 'requests':
                rows.append(dict(base, rule='freshness', passed=lo - j <= med <= hi + j))
            elif key in TARGET and m in ('row_render_calls', 'react_actual_ms'):
                rows.append(dict(base, rule='target', passed=med < lo - j))
            elif m == 'cpu_usec':
                rows.append(dict(base, rule='cpu_x1.10', limit=hi * 1.10, passed=med <= hi * 1.10))
            elif m == 'anon_after':
                rows.append(dict(base, rule='memory_+2MiB', limit=hi + MIB2, passed=med <= hi + MIB2))
            else:
                rows.append(dict(base, rule='no_regression', limit=hi + j, passed=med <= hi + j))
            if key in TARGET and m == 'react_actual_ms':
                cmed = statistics.median(x[m] for x in control[key])
                rows.append(dict(base, rule='drift_control', after_median=None, control_median=cmed, passed=lo - j <= cmed <= hi + j))
    if heap_run is not None:
        base_heap = [load(n)['rows'][0]['heap'][-1]['usedSize'] for n in HEAP_BASE]
        final = heap_run['rows'][0]['heap'][-1]['usedSize'] if heap_run['rows'][0]['heap'] else None
        rows.append(dict(cell='heap/500/one', metric='final_used_heap_bytes', rule='memory_+2MiB', after_median=final,
                         before_max=max(base_heap), limit=max(base_heap) + MIB2, passed=final is not None and final <= max(base_heap) + MIB2))
    failures = [x for x in rows if not x['passed']]
    if not all(c['passed'] for c in correctness):
        status = 'INVALID'
    elif any(x['rule'] == 'drift_control' for x in failures):
        status = 'INVALID_DRIFT'
    elif failures:
        status = 'FAIL'
    else:
        status = 'PASS'
    return dict(status=status, correctness=correctness, failures=failures, rows=rows)


if __name__ == '__main__':
    protocol = load('g04-candidate-v1-protocol.json')
    if not (e / 'g04-candidate-v1-complete.json').exists():
        raise SystemExit('Gate not complete')
    names = {k: [f'g04-candidate-v1-{s}.json' for s, kind, heap in protocol['order'] if kind == k and not heap] for k in ('after', 'control')}
    heap = [f'g04-candidate-v1-{s}.json' for s, kind, h in protocol['order'] if h][0]
    result = assess(names['after'], names['control'], heap)
    result.update(protocol_sha256=hashlib.sha256((e / 'g04-candidate-v1-protocol.json').read_bytes()).hexdigest(),
                  assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    (e / 'g04-candidate-v1-assessment.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    print(json.dumps(dict(status=result['status'], failures=len(result['failures']), checks=len(result['rows']),
                          correctness=all(c['passed'] for c in result['correctness']))))
