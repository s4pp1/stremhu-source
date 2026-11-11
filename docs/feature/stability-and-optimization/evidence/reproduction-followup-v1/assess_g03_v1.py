"""Preregistered G03 v1 assessor (CR03 gzip benefit/cost under the plan's common gate, section 2.3).
Baseline = identity-a + identity-b (same C build, same process, interleaved). Per (profile, payload, mode, metric):
J = max(|median_a - median_b| over repetitions, resolution); range = min/max of all identity per-repetition values.
Benefit: median over repetitions < range_min - J and >= 2 repetitions individually below range_min - J.
Repeatable degradation: median > range_max - and + J, i.e. median > range_max + J and >= 2 repetitions individually > range_max + J.
(L, T) eligible at profile P iff: correctness; streams/40 in G(T) with benefit at P in all modes; every payload in G(T) with
identity >= 16 KiB has >= 30 % wire-byte reduction; and no payload in G(T) shows repeatable degradation of total p95,
ttfb p95 or server CPU/request in any mode at ANY profile (LAN included). G(T) = payloads with identity size >= T KiB.
No CPU/UX budget was designated in writing before measurement, so the strict common gate applies."""
import hashlib
import json
import pathlib
import statistics
import sys

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'g03-v1'
P = json.loads((fx / 'params.json').read_text(encoding='utf-8'))
LEVELS = [1, 4, 6]
THRESHOLDS_KIB = [1, 2, 4, 8]
RES = dict(total_p95=0.01, ttfb_p95=0.01, total_p50=0.01, total_p99=0.01, cpu_ms_per_req=0.01)
LARGE = 16 * 1024


def pct(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def cell_metrics(c):
    t = [x['total_ms'] for x in c['rows']]
    return dict(total_p50=pct(t, .5), total_p95=pct(t, .95), total_p99=pct(t, .99), ttfb_p95=pct([x['ttfb_ms'] for x in c['rows']], .95),
                cpu_ms_per_req=c['server_cpu_ms'] / len(c['rows']), wire=statistics.median(x['wire_bytes'] for x in c['rows']),
                decode_ms_p50=pct([x['decode_ms'] for x in c['rows']], .5))


def assess(names, expected_reps):
    runs = [json.loads((e / n).read_text(encoding='utf-8')) for n in names]
    problems = []
    sha = {}
    data = {}  # (profile, payload, variant, mode) -> list over reps of metrics
    seen = set()
    for d in runs:
        seen.add((d['repetition'], d['profile']))
        pids = {d['server_start']['pid'], d['server_end']['pid']}
        for c in d['cells']:
            gz = c['variant'].startswith('gzip')
            if not c['same_server_pid'] or c['server_before']['pid'] not in pids or len(c['rows']) != c['n']:
                problems.append(dict(run=(d['repetition'], d['profile']), cell=(c['payload'], c['variant'], c['mode']), problem='pid/rowcount'))
            for x in c['rows']:
                ok = x['status'] == 200 and x['encoding'] == ('gzip' if gz else None) and (not gz or 'accept-encoding' in (x['vary'] or '').lower())
                if not ok:
                    problems.append(dict(run=(d['repetition'], d['profile']), cell=(c['payload'], c['variant'], c['mode']), problem='status/encoding/vary'))
                    break
                sha.setdefault(c['payload'], set()).add(x['decoded_sha256'])
            data.setdefault((d['profile'], c['payload'], c['variant'], c['mode']), []).append(cell_metrics(c))
    if expected_reps is not None:
        want = {(rep, p) for rep in range(expected_reps) for p in P['profiles']}
        if seen != want:
            problems.append(dict(problem='missing batches', missing=sorted(want - seen)))
    for payload, s in sha.items():
        if len(s) != 1:
            problems.append(dict(payload=payload, problem='decoded body differs'))
    identity_size = {x: data[(P['profiles'][0], x, 'identity-a', 'c1')][0]['wire'] for x in P['payloads']}
    rows = []
    verdict = {}  # (profile, payload, level, mode, metric) -> dict
    for prof in P['profiles']:
        for x in P['payloads']:
            for mode in P['modes']:
                a, b = data[(prof, x, 'identity-a', mode)], data[(prof, x, 'identity-b', mode)]
                for m in RES:
                    va, vb = [q[m] for q in a], [q[m] for q in b]
                    j = max(abs(statistics.median(va) - statistics.median(vb)), RES[m])
                    lo, hi = min(va + vb), max(va + vb)
                    for lv in LEVELS:
                        vg = [q[m] for q in data[(prof, x, f'gzip{lv}', mode)]]
                        med = statistics.median(vg)
                        benefit = med < lo - j and sum(v < lo - j for v in vg) >= 2
                        degr = med > hi + j and sum(v > hi + j for v in vg) >= 2
                        row = dict(profile=prof, payload=x, level=lv, mode=mode, metric=m, gzip_median=med, identity_min=lo, identity_max=hi, J=j,
                                   identity_median=statistics.median(va + vb), benefit=benefit, repeatable_degradation=degr)
                        rows.append(row)
                        verdict[(prof, x, lv, mode, m)] = row
    bytes_rows = []
    for x in P['payloads']:
        for lv in LEVELS:
            gz = data[(P['profiles'][0], x, f'gzip{lv}', 'c1')][0]['wire']
            bytes_rows.append(dict(payload=x, level=lv, identity_bytes=identity_size[x], gzip_bytes=gz, reduction=1 - gz / identity_size[x]))
    red = {(q['payload'], q['level']): q['reduction'] for q in bytes_rows}
    eligibility = []
    for prof in P['profiles']:
        for lv in LEVELS:
            for t in THRESHOLDS_KIB:
                g = [x for x in P['payloads'] if identity_size[x] >= t * 1024]
                reasons = []
                if 'streams/40' not in g:
                    reasons.append('streams/40 not compressed')
                else:
                    miss = [mode for mode in P['modes'] if not verdict[(prof, 'streams/40', lv, mode, 'total_p95')]['benefit']]
                    if miss:
                        reasons.append(f'no total_p95 benefit for streams/40 at {prof} in {miss}')
                small = [x for x in g if identity_size[x] >= LARGE and red[(x, lv)] < .30]
                if small:
                    reasons.append(f'<30% byte reduction: {small}')
                deg = sorted({(q['profile'], q['payload'], q['mode'], q['metric']) for q in rows
                              if q['level'] == lv and q['payload'] in g and q['repeatable_degradation'] and q['metric'] in ('total_p95', 'ttfb_p95', 'cpu_ms_per_req')})
                if deg:
                    reasons.append(dict(repeatable_degradation=[list(z) for z in deg]))
                eligibility.append(dict(profile=prof, level=lv, threshold_kib=t, compressed_payloads=g, eligible=not reasons, reasons=reasons))
    if problems:
        status = 'INVALID'
    elif any(q['eligible'] for q in eligibility):
        status = 'PASS_CANDIDATE'
    else:
        status = 'REJECT_UNDER_COMMON_GATE'
    chosen = {}
    for prof in P['profiles']:
        ok = [q for q in eligibility if q['profile'] == prof and q['eligible']]
        if ok:
            best = min(ok, key=lambda q: (verdict[(prof, 'streams/40', q['level'], 'c1', 'total_p95')]['gzip_median'], q['level'], -q['threshold_kib']))
            chosen[prof] = dict(level=best['level'], threshold_kib=best['threshold_kib'])
    tradeoff = [dict(profile=q['profile'], payload=q['payload'], level=q['level'], mode=q['mode'], identity_p95_ms=q['identity_median'],
                     gzip_p95_ms=q['gzip_median'], delta_ms=q['gzip_median'] - q['identity_median'])
                for q in rows if q['metric'] == 'total_p95']
    cpu = [dict(profile=q['profile'], payload=q['payload'], level=q['level'], mode=q['mode'], identity_cpu_ms=q['identity_median'],
                gzip_cpu_ms=q['gzip_median']) for q in rows if q['metric'] == 'cpu_ms_per_req']
    return dict(status=status, problems=problems, chosen_per_profile=chosen, eligibility=eligibility, bytes=bytes_rows, tradeoff_total_p95=tradeoff,
                cpu_per_request=cpu, rows=rows)


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        res = assess(['g03-v1-smoke-0-lan.json', 'g03-v1-smoke-0-mob2.json'], None)
        print(json.dumps(dict(status=res['status'], problems=res['problems'][:5], chosen=res['chosen_per_profile'])))
        sys.exit(0)
    protocol = json.loads((e / 'g03-v1-protocol.json').read_text(encoding='utf-8'))
    if not (e / 'g03-v1-complete.json').exists():
        raise SystemExit('Gate not complete')
    names = [f'g03-v1-{rep}-{p}.json' for rep in range(P['repetitions']) for p in P['profiles']]
    res = assess(names, P['repetitions'])
    res.update(protocol_sha256=hashlib.sha256((e / 'g03-v1-protocol.json').read_bytes()).hexdigest(),
               assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    (e / 'g03-v1-assessment.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(dict(status=res['status'], problems=len(res['problems']), chosen=res['chosen_per_profile'])))
