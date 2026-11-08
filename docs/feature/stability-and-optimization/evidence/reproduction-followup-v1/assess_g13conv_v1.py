"""Preregistered G13-convert v1 assessor. Decision on C inline loop stall (max heartbeat gap p95 per run):
NO_CHANGE if every fixture's median-over-runs < 10 ms (plan budget: piece p95 / normal HTTP +10 ms);
BUDGET_EXCEEDED_NOT_DOMINANT if the largest is >= 10 ms but no fixture exceeds DOMINANCE_MS;
OFFLOAD_CANDIDATE if some fixture's median > DOMINANCE_MS (largest remaining CR13/b post looplag p99-median, 500 fixture)
and >= 2 runs individually exceed it. to_thread numbers are informative design input, not a decision."""
import hashlib
import json
import pathlib
import statistics

r = pathlib.Path(__file__).parent
e = r / 'evidence'
BUDGET_MS = 10.0
DOMINANCE_MS = 29.016


def assess(runs):
    problems, table = [], {}
    c_runs = [d for d in runs if d['reference'] == 'C']
    if len(c_runs) != 5 or not all(d['converter_available'] for d in c_runs):
        problems.append('C runs missing or converter unavailable')
    shas = {}
    for d in runs:
        for c in d['cells']:
            if not c['starts_webvtt'] or len(c['output_sha256']) != 1 or len(c['max_loop_gap_ms']) != c['n']:
                problems.append(f"{d['reference']}-{d['repetition']} {c['fixture']} {c['mode']} output/count")
            shas.setdefault((d['reference'], c['fixture']), set()).update(c['output_sha256'])
            table.setdefault((d['reference'], c['fixture'], c['mode']), []).append(c)
    for (ref, fixture), s in shas.items():
        if len(s) != 1:
            problems.append(f'{ref} {fixture} output differs between runs')
    rows = []
    for (ref, fixture, mode), cells in sorted(table.items()):
        gaps = [c['gap_p95'] for c in cells]
        walls = [c['wall_p95'] for c in cells]
        rows.append(dict(reference=ref, fixture=fixture, mode=mode, runs=len(cells), gap_p95_median=statistics.median(gaps), gap_p95_runs=gaps,
                         wall_p95_median=statistics.median(walls), runs_above_dominance=sum(g > DOMINANCE_MS for g in gaps),
                         runs_above_budget=sum(g >= BUDGET_MS for g in gaps), output_bytes=cells[0]['output_bytes'], cues=cells[0]['cues']))
    inline_c = [x for x in rows if x['reference'] == 'C' and x['mode'] == 'inline']
    dominant = [x['fixture'] for x in inline_c if x['gap_p95_median'] > DOMINANCE_MS and x['runs_above_dominance'] >= 2]
    over = [x['fixture'] for x in inline_c if x['gap_p95_median'] >= BUDGET_MS]
    if problems:
        decision = 'INVALID'
    elif dominant:
        decision = 'OFFLOAD_CANDIDATE'
    elif over:
        decision = 'BUDGET_EXCEEDED_NOT_DOMINANT'
    else:
        decision = 'NO_CHANGE'
    same_bc = {f: shas.get(('B', f)) == shas.get(('C', f)) for f in ['typical', 'typical-cp1250', 'heavy', 'limit']}
    return dict(decision=decision, problems=problems, dominant_fixtures=dominant, over_budget_fixtures=over, budget_ms=BUDGET_MS, dominance_ms=DOMINANCE_MS,
                b_c_output_identical=same_bc, a_converter_available=any(d['converter_available'] for d in runs if d['reference'] == 'A'), rows=rows)


if __name__ == '__main__':
    if not (e / 'g13conv-v1-complete.json').exists():
        raise SystemExit('Gate not complete')
    runs = [json.loads((e / f'g13conv-v1-{ref}-{rep}.json').read_text(encoding='utf-8')) for rep in range(5) for ref in 'ABC']
    res = assess(runs)
    res.update(protocol_sha256=hashlib.sha256((e / 'g13conv-v1-protocol.json').read_bytes()).hexdigest(),
               assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    (e / 'g13conv-v1-assessment.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ['decision', 'problems', 'dominant_fixtures', 'over_budget_fixtures', 'b_c_output_identical', 'a_converter_available']}))
