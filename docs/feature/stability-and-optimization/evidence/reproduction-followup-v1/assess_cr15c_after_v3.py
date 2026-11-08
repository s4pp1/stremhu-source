"""Preregistered packet 27 (CR15/c) gate assessor (v3, rules identical to v2); rules in the protocol's decision field."""
import hashlib
import json
import pathlib
import statistics

r = pathlib.Path(__file__).parent
e = r / 'evidence'
MIB = 2 ** 20
RES = dict(p50_ms=1.0, p95_ms=1.0, anon_peak_delta=MIB, cpu_seconds=0.01)
TYPICAL = [1, 4, 8, 12]


def load(mix, n, side, s, i):
    p = e / f'cr15c-after-v3-{mix}-{n}-{side}-{s}-{i}.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def assess():
    problems, failures, checks = [], [], []
    runs = {}
    for s in ('s1', 's2'):
        for i in range(5):
            for mix, n in [('typical', 1), ('typical', 4), ('typical', 8), ('typical', 12), ('typical', 16), ('heavy', 1), ('heavy', 4), ('heavy', 12)]:
                for side in ('before', 'after'):
                    d = load(mix, n, side, s, i)
                    if d is None:
                        problems.append(f'missing {mix}-{n}-{side}-{s}-{i}')
                        continue
                    runs[(mix, n, side, s, i)] = d
    if problems:
        return dict(status='INVALID', problems=problems)

    def result(d):
        return d.get('result') or {}

    for (mix, n, side, s, i), d in runs.items():
        res = result(d)
        if side == 'after' and (d['exit_code'] or d['oom_killed'] or res.get('guard_timeout') or res.get('external_http_attempts')):
            failures.append(dict(rule='A', run=f'{mix}-{n}-{side}-{s}-{i}', exit=d['exit_code'], oom=d['oom_killed']))
        if side == 'before' and mix == 'typical' and n <= 12 and (d['exit_code'] or not res.get('ok')):
            problems.append(f'before typical run failed {n}-{s}-{i}')
    if problems:
        return dict(status='INVALID', problems=problems, failures=failures)
    for (mix, n, side, s, i), d in runs.items():
        if side != 'after' or d['exit_code']:
            continue
        rows = result(d)['rows']
        ok_row = [x for x in rows if x.get('results') == 40 and x.get('errors') == 0 and x.get('unique_hashes') == 40]
        name = f'{mix}-{n}-{s}-{i}'
        if mix == 'typical' and n <= 12:
            if len(ok_row) != n:
                failures.append(dict(rule='B-typical', run=name))
        elif mix == 'typical' and n == 16:
            rejected = [x for x in rows if x.get('exception') == 'SearchOverloadedError' and x['wall_ms'] <= 100]
            if len(ok_row) != 12 or len(rejected) != 4:
                failures.append(dict(rule='B-overload', run=name, complete=len(ok_row), rejected=len(rejected)))
        else:
            partial = [x for x in rows if 'results' in x and x['results'] < 40 and x.get('errors') == 1 and x.get('unique_hashes') == x['results']]
            slow = [x['wall_ms'] for x in rows if x['wall_ms'] > 18000]
            if len(ok_row) + len(partial) != n or slow:
                failures.append(dict(rule='B-heavy', run=name, complete=len(ok_row), partial=len(partial), over_18s=slow))
    rows = []
    for n in TYPICAL:
        def series(side, s, metric):
            return [result(runs[('typical', n, side, s, i)])[metric] for i in range(5)]
        for metric in RES:
            b1, b2 = series('before', 's1', metric), series('before', 's2', metric)
            a = [statistics.median(series('after', s, metric)) for s in ('s1', 's2')]
            j = max(abs(statistics.median(b1) - statistics.median(b2)), RES[metric])
            hi = max(b1 + b2)
            row = dict(cell=f'typical-{n}', metric=metric, before_series_medians=[statistics.median(b1), statistics.median(b2)], before_max=hi, J=j,
                       after_series_medians=a, repeatable_degradation=all(v > hi + j for v in a))
            rows.append(row)
            if row['repeatable_degradation']:
                failures.append(dict(rule='D', cell=row['cell'], metric=metric))
        p95 = [statistics.median(series('after', s, 'p95_ms')) for s in ('s1', 's2')]
        checks.append(dict(rule='C', cell=f'typical-{n}', after_p95_series_medians=p95, passed=all(v <= 15000 for v in p95)))
        if not all(v <= 15000 for v in p95):
            failures.append(dict(rule='C', cell=f'typical-{n}'))
    descriptive = {}
    for mix, n in [('typical', 16), ('heavy', 1), ('heavy', 4), ('heavy', 12)]:
        for side in ('before', 'after'):
            ds = [runs[(mix, n, side, s, i)] for s in ('s1', 's2') for i in range(5)]
            ok = [result(d) for d in ds if not d['exit_code']]
            descriptive[f'{mix}-{n}-{side}'] = dict(runs=len(ds), oom=sum(d['oom_killed'] for d in ds), completed=len(ok),
                                                    anon_peak_delta_mib_median=statistics.median(x['anon_peak_delta'] / MIB for x in ok) if ok else None,
                                                    max_ms_median=statistics.median(x['max_ms'] for x in ok if x['max_ms'] is not None) if ok else None)
    return dict(status='FAIL' if failures else 'PASS', problems=[], failures=failures, checks=checks, rows=rows, descriptive=descriptive)


if __name__ == '__main__':
    if not (e / 'cr15c-after-v3-complete.json').exists():
        raise SystemExit('Gate not complete')
    out = assess()
    out.update(protocol_sha256=hashlib.sha256((e / 'cr15c-after-v3-protocol.json').read_bytes()).hexdigest(),
               assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    (e / 'cr15c-after-v3-assessment.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(dict(status=out['status'], problems=len(out.get('problems', [])), failures=len(out.get('failures', [])))))
