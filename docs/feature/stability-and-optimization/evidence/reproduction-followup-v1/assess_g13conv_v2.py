"""Preregistered G13-convert v2 candidate assessor.
Correctness: 20 runs; before converter_kind sync-inline, after cooperative; one output sha per fixture across ALL runs
(before and after byte-identical), WEBVTT start, full sample counts.
Target: for every fixture and both series, median over the five after runs of the per-run stall p95 < 10 ms;
for heavy and limit additionally both series after medians < before min - J.
No regression: per fixture, conversion wall p95 is not repeatably worse: NOT (both series after medians > before max + J).
J = max(|median before s1 - median before s2|, 0.01 ms). PASS iff all hold; INVALID on correctness; FAIL otherwise."""
import hashlib
import json
import pathlib
import statistics

r = pathlib.Path(__file__).parent
e = r / 'evidence'
FIXTURES = ['typical', 'typical-cp1250', 'heavy', 'limit']
BUDGET_MS = 10.0


def assess(runs):
    problems = []
    vals = {}
    shas = {}
    for d in runs:
        want = 'cooperative' if d['side'] == 'after' else 'sync-inline'
        if d.get('converter_kind') != want or len(d['cells']) != 4:
            problems.append(f"{d['side']} {d['series']}-{d['pair']} converter/cells")
            continue
        for c in d['cells']:
            if not c['starts_webvtt'] or len(c['output_sha256']) != 1 or len(c['max_loop_gap_ms']) != c['n'] or c['n'] != 20:
                problems.append(f"{d['side']} {d['series']}-{d['pair']} {c['fixture']} output/count")
            shas.setdefault(c['fixture'], set()).update(c['output_sha256'])
            vals.setdefault((c['fixture'], d['side'], d['series']), []).append(dict(gap=c['gap_p95'], wall=c['wall_p95']))
    if len(runs) != 20:
        problems.append('missing runs')
    for f, s in shas.items():
        if len(s) != 1:
            problems.append(f'{f} output differs')
    rows = []
    if not problems:
        for f in FIXTURES:
            for m in ('gap', 'wall'):
                b1 = [x[m] for x in vals[(f, 'before', 's1')]]
                b2 = [x[m] for x in vals[(f, 'before', 's2')]]
                j = max(abs(statistics.median(b1) - statistics.median(b2)), 0.01)
                after = [statistics.median(x[m] for x in vals[(f, 'after', s)]) for s in ('s1', 's2')]
                row = dict(fixture=f, metric=m, before_min=min(b1 + b2), before_max=max(b1 + b2), before_series_medians=[statistics.median(b1), statistics.median(b2)],
                           J=j, after_series_medians=after)
                if m == 'gap':
                    row['within_budget'] = all(v < BUDGET_MS for v in after)
                    row['improved'] = all(v < row['before_min'] - j for v in after) if f in ('heavy', 'limit') else None
                    row['passed'] = row['within_budget'] and row['improved'] is not False
                else:
                    row['repeatable_regression'] = all(v > row['before_max'] + j for v in after)
                    row['passed'] = not row['repeatable_regression']
                rows.append(row)
    status = 'INVALID' if problems else 'PASS' if all(x['passed'] for x in rows) else 'FAIL'
    return dict(status=status, problems=problems, failures=[x for x in rows if not x['passed']], rows=rows)


if __name__ == '__main__':
    if not (e / 'g13conv-v2-complete.json').exists():
        raise SystemExit('Gate not complete')
    runs = [json.loads((e / f'g13conv-v2-{side}-{s}-{i}.json').read_text(encoding='utf-8')) for s in ('s1', 's2') for i in range(5) for side in ('before', 'after')]
    res = assess(runs)
    res.update(protocol_sha256=hashlib.sha256((e / 'g13conv-v2-protocol.json').read_bytes()).hexdigest(),
               assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    (e / 'g13conv-v2-assessment.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(dict(status=res['status'], problems=res['problems'], failures=len(res['failures']))))
