"""Preregistered G02 decision assessor (v2). Reads references and the two post-CR17 runs; writes the assessment."""
import hashlib
import json
import math
import pathlib
import sys

r = pathlib.Path(__file__).parent
e = r / 'evidence'
sys.path.insert(0, str(r))
from g02_summarize_v2 import summarize  # noqa: E402

ORDINARY = ['short/1', 'short/4', 'short/8', 'select-await/1', 'select-await/4', 'select-await/8']
EXPLICIT = ['explicit-snapshot/1', 'explicit-snapshot/4', 'explicit-snapshot/8']


def load(name):
    return json.loads((e / name).read_text(encoding='utf-8'))


def ordinary_high_water(d):
    return max(s['wal_bytes'] for s in d['wal_samples'] if f"{s['reader']}/{s['writers']}" in ORDINARY)


def assess(ref_names, post_names):
    refs = {k: load(v) for k, v in ref_names.items()}
    posts = [load(n) for n in post_names]
    ca, cb = summarize(refs['C_a'])['cells'], summarize(refs['C_b'])['cells']
    hw_bound = max(ordinary_high_water(d) for d in refs.values())
    rows, correctness = [], []
    for i, d in enumerate(posts):
        s = summarize(d)
        fc = s['final_checkpoint']
        ok = (d['is_measurement'] and s['measured_seconds'] >= 3600 and len(s['cells']) == 9
              and all(c['elapsed_seconds'] >= 400 and c['errors'] == 0 for c in s['cells'].values())
              and s['final_checkouts'] == 0 and fc[0] == 0 and fc[1] == fc[2])
        correctness.append(dict(run=i, passed=bool(ok), final_checkpoint=fc, final_checkouts=s['final_checkouts']))
        for cell in ORDINARY:
            a, b, p = ca[cell], cb[cell], s['cells'][cell]
            floor = max(2, math.floor(min(a['wal_header_epochs'], b['wal_header_epochs']) / 2))
            rows.append(dict(run=i, cell=cell, metric='wal_header_epochs', value=p['wal_header_epochs'], limit_min=floor,
                             passed=p['wal_header_epochs'] >= floor))
            for m in ['commit_p99_ms', 'transaction_p99_ms']:
                j = abs(a[m] - b[m])
                limit = max(a[m], b[m]) + j
                rows.append(dict(run=i, cell=cell, metric=m, value=p[m], limit_max=limit, passed=p[m] <= limit))
        hw = ordinary_high_water(d)
        rows.append(dict(run=i, cell='ordinary', metric='wal_high_water_bytes', value=hw, limit_max=hw_bound, passed=hw <= hw_bound))
    failed = [x for x in rows if not x['passed']]
    keys = {}
    for x in failed:
        keys.setdefault((x['cell'], x['metric']), set()).add(x['run'])
    repeatable = [dict(cell=c, metric=m) for (c, m), runs in keys.items() if runs == set(range(len(posts)))]
    if not all(c['passed'] for c in correctness):
        decision = 'INVALID'
    elif repeatable:
        decision = 'PASSIVE_CANDIDATE'
    else:
        decision = 'NO_CHANGE'
    observations = [dict(run=i, cell=cell, **{k: summarize(d)['cells'][cell][k] for k in ['wal_max_bytes', 'wal_header_epochs', 'commit_p99_ms']})
                    for i, d in enumerate(posts) for cell in EXPLICIT]
    return dict(decision=decision, correctness=correctness, repeatable_violations=repeatable,
                single_run_violations=[x for x in failed if dict(cell=x['cell'], metric=x['metric']) not in repeatable],
                ordinary_high_water_bound_bytes=hw_bound, rows=rows, explicit_snapshot_observations=observations)


if __name__ == '__main__':
    protocol = load('g02-post-cr17-v2-protocol.json')
    if not (e / 'g02-post-cr17-v2-complete.json').exists():
        raise SystemExit('Control not complete')
    result = assess(protocol['references'], [f'g02-post-cr17-{n}-v2.json' for n in protocol['runs']])
    result.update(protocol='g02-post-cr17-v2-protocol.json',
                  protocol_sha256=hashlib.sha256((e / 'g02-post-cr17-v2-protocol.json').read_bytes()).hexdigest(),
                  assessor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
                  summarizer_sha256=hashlib.sha256((r / 'g02_summarize_v2.py').read_bytes()).hexdigest())
    (e / 'g02-post-cr17-v2-assessment.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    print(json.dumps(dict(decision=result['decision'], correctness=result['correctness'],
                          repeatable=result['repeatable_violations'], single=len(result['single_run_violations']))))
