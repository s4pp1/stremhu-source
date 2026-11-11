"""Preregistered CR15a after-gate assessor (v3, rules identical to v1/v2); plan 2.3 rule for a safety/correctness fix.
Correctness: all 20 normal runs complete (18 cells x 100 requests, body hash/login/cookie/outbound checks inside the probe);
both giant-after runs exit 0, no OOM, every one of 600 requests per run 'too-large'. The giant-before confirmation run
is recorded as an outcome only. Repeatable degradation per (kind, concurrency, metric): in BOTH series the median of the
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
                d = load(f'cr15a-after-v3-normal-{side}-{s}-{i}')
                if d is None or not d['is_measurement'] or len(d['rows']) != 18 or any(len(x['samples_ms']) != 100 for x in d['rows']) \
                        or d['external_http_attempts'] or d['state']['oom_killed'] or d['state']['exit_code']:
                    problems.append(f'normal {side} {s}-{i} missing/incomplete')
                    continue
                for row in d['rows']:
                    data.setdefault((row['kind'], row['concurrency'], side, s), []).append(metrics(row))
    giant = {}
    for s in ('s1', 's2'):
        d = load(f'cr15a-after-v3-giant-after-{s}-giant')
        ok = d is not None and d['is_measurement'] and not d['state']['oom_killed'] and d['state']['exit_code'] == 0 and len(d['rows']) == 6 \
            and all(x['outcomes'] == {'too-large': 100} for x in d['rows']) and not d['external_http_attempts']
        giant[s] = dict(passed=bool(ok), rows=[dict(kind=x['kind'], concurrency=x['concurrency'], outcomes=x['outcomes'],
                                                    anon_peak_mib=x['memory_peaks']['anon_bytes'] / 2 ** 20, p95_ms=x['p95_ms']) for x in (d or {}).get('rows', [])])
        if not ok:
            problems.append(f'giant after {s} failed')
    confirm_state = e / 'cr15a-after-v3-giant-before-confirm-giant-state.json'
    confirm = json.loads(confirm_state.read_text(encoding='utf-8')) if confirm_state.exists() else None
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
    return dict(status=status, problems=problems, failures=failures, giant_after=giant, giant_before_confirmation_state=confirm, rows=rows)


if __name__ == '__main__':
    if not (e / 'cr15a-after-v3-complete.json').exists():
        raise SystemExit('Gate not complete')
    res = assess()
    res.update(protocol_sha256=hashlib.sha256((e / 'cr15a-after-v3-protocol.json').read_bytes()).hexdigest(),
               assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    (e / 'cr15a-after-v3-assessment.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(dict(status=res['status'], problems=res['problems'], failures=len(res['failures']), checks=len(res['rows']))))
