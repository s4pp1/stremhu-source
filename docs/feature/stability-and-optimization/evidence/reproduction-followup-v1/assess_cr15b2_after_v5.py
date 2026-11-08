"""Preregistered packet 26b after-gate assessor (v5, rules identical to v4); plan 2.3 rule for a safety/correctness fix.
Correctness: all 20 normal runs complete (15 cells x 100 requests; cdn-redirect excluded, body hash/login/cookie/outbound checks inside the probe).
Repeatable degradation per (kind, concurrency, metric): in BOTH series the median of the
five after values > before range max (all ten) + J, J = max(|median before s1 - median before s2|, resolution).
PASS = correctness and no repeatable degradation; FAIL otherwise; INVALID if runs are missing."""
import hashlib
import json
import pathlib
import statistics

r = pathlib.Path(__file__).parent
e = r / 'evidence'
RES = dict(p95_ms=0.01, p50_ms=0.01, cpu_seconds=0.001, anon_after=4096, anon_peak=4096)


def metrics(row):
    return dict(p95_ms=row['p95_ms'], p50_ms=row['p50_ms'], cpu_seconds=row['cpu_seconds'], anon_after=row['memory']['anon_bytes'],
                anon_peak=row['memory_peaks']['anon_bytes'])


def load(stem):
    p = e / (stem + '.json')
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def assess():
    problems = []
    data = {}
    for s in ('s1', 's2'):
        for i in range(5):
            for side in ('before', 'after'):
                d = load(f'cr15b2-after-v5-normal-{side}-{s}-{i}')
                if d is None or not d['is_measurement'] or len(d['rows']) != 15 or any(len(x['samples_ms']) != 100 for x in d['rows']) \
                        or d['external_http_attempts'] or d['state']['oom_killed'] or d['state']['exit_code']:
                    problems.append(f'normal {side} {s}-{i} missing/incomplete')
                    continue
                for row in d['rows']:
                    data.setdefault((row['kind'], row['concurrency'], side, s), []).append(metrics(row))
    rows = []
    if not problems:
        for kind, conc in sorted({(k[0], k[1]) for k in data}):
            for m in RES:
                b1 = [x[m] for x in data[(kind, conc, 'before', 's1')]]
                b2 = [x[m] for x in data[(kind, conc, 'before', 's2')]]
                j = max(abs(statistics.median(b1) - statistics.median(b2)), RES[m])
                hi = max(b1 + b2)
                meds = [statistics.median(x[m] for x in data[(kind, conc, 'after', s)]) for s in ('s1', 's2')]
                rows.append(dict(kind=kind, concurrency=conc, metric=m, before_min=min(b1 + b2), before_max=hi, J=j, after_series_medians=meds,
                                 before_series_medians=[statistics.median(b1), statistics.median(b2)],
                                 repeatable_degradation=all(v > hi + j for v in meds)))
    failures = [x for x in rows if x['repeatable_degradation']]
    status = 'INVALID' if any('missing' in p for p in problems) else 'FAIL' if problems or failures else 'PASS'
    return dict(status=status, problems=problems, failures=failures, rows=rows)


if __name__ == '__main__':
    if not (e / 'cr15b2-after-v5-complete.json').exists():
        raise SystemExit('Gate not complete')
    res = assess()
    res.update(protocol_sha256=hashlib.sha256((e / 'cr15b2-after-v5-protocol.json').read_bytes()).hexdigest(),
               assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    (e / 'cr15b2-after-v5-assessment.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(dict(status=res['status'], problems=res['problems'], failures=len(res['failures']), checks=len(res['rows']))))
