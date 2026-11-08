"""Analysis of cr17b-noise-gc-diagnostic-v7 exactly as its protocol 'analysis' field states. Diagnostic only."""
from pathlib import Path
import datetime
import hashlib
import json
import statistics

r = Path(__file__).parent
e = r / 'evidence'
target = e / 'cr17b-noise-gc-diagnostic-v7-analysis.json'
if target.exists():
    raise RuntimeError('Refusing analysis overwrite')
med = statistics.median
used = []


def load(name):
    used.append(name)
    return json.loads((e / name).read_text(encoding='utf-8'))


protocol = load('cr17b-noise-gc-diagnostic-v7-protocol.json')

# GC phase.
gc_pairs = []
for i in range(5):
    pair = {}
    for label in ['S2', 'S4']:
        d = load(f'cr17b-noise-gc-v7-{label}-{i}.json')
        gen2 = [g['phase'] for g in d['gc_events'] if g['generation'] == 2 and g['phase'].startswith('cold-')]
        cold = [c['wall_seconds'] * 1000 for c in d['cold']]
        pair[label] = dict(cold_ms=cold, combined_ms=sum(cold), gen2_cold_phases=gen2)
    pair['combined_diff_ms'] = pair['S4']['combined_ms'] - pair['S2']['combined_ms']
    pair['shift'] = pair['S2']['gen2_cold_phases'] == ['cold-0'] and pair['S4']['gen2_cold_phases'] == ['cold-1']
    gc_pairs.append(pair)
shift_pairs = sum(p['shift'] for p in gc_pairs)
median_combined_diff = med(p['combined_diff_ms'] for p in gc_pairs)
gc_result = dict(pairs=gc_pairs, shift_pairs=shift_pairs, median_combined_diff_ms=median_combined_diff,
                 median_user1_diff_ms=med(p['S4']['cold_ms'][1] - p['S2']['cold_ms'][1] for p in gc_pairs),
                 median_user0_diff_ms=med(p['S4']['cold_ms'][0] - p['S2']['cold_ms'][0] for p in gc_pairs),
                 hypothesis_supported=shift_pairs >= 4 and abs(median_combined_diff) <= 10)

# Long phase.
new = {(label, pair): load(f'cr17b-noise-long-v7-{label}-{pair}.json') for pair in range(3) for label in ['S2', 'S4']}
old_s2 = [load(f'cr17a-drain-paired-long-v2-after-{i}.json') for i in range(5)]
old_s4 = [load(f'cr17b-after-long-v6-C-{s}-0.json') for s in 'ab']
keyf = lambda x: (x['kind'], x['concurrency'])
runmed = lambda d, key, read: med(read(x) for x in d['rows'] if keyf(x) == key)
reads = {'p95_ms': lambda x: x['p95_ms'], 'cpu_seconds': lambda x: x['cpu_seconds'], 'heap_bytes_after_gc': lambda x: x['heap_bytes_after_gc'],
         'memory.anon_bytes': lambda x: x['memory']['anon_bytes'], 'memory.max_rss_kib': lambda x: x['memory']['max_rss_kib']}
long_rows = []
for key in sorted({keyf(x) for x in old_s2[0]['rows']}):
    for metric, read in reads.items():
        s2 = [runmed(d, key, read) for d in old_s2] + [runmed(new[('S2', p)], key, read) for p in range(3)]
        s4 = [runmed(d, key, read) for d in old_s4] + [runmed(new[('S4', p)], key, read) for p in range(3)]
        paired = [runmed(new[('S4', p)], key, read) - runmed(new[('S2', p)], key, read) for p in range(3)]
        row = dict(key=list(key), metric=metric, s2_pooled_run_medians=s2, s4_pooled_run_medians=s4, s2_range=[min(s2), max(s2)],
                   s4_range=[min(s4), max(s4)], contemporaneous_paired_diffs=paired, median_paired_diff=med(paired))
        if metric == 'p95_ms' and key[1] == 8:
            row['within_noise'] = med(paired) <= 10 and all(v <= max(s2) for v in s4)
        long_rows.append(row)
cold_long = []
for index in [0, 1]:
    s2 = [d['cold'][index]['wall_seconds'] * 1000 for d in old_s2] + [new[('S2', p)]['cold'][index]['wall_seconds'] * 1000 for p in range(3)]
    s4 = [d['cold'][index]['wall_seconds'] * 1000 for d in old_s4] + [new[('S4', p)]['cold'][index]['wall_seconds'] * 1000 for p in range(3)]
    cold_long.append(dict(user=index, s2_ms=s2, s4_ms=s4, median_diff_ms=med(s4) - med(s2)))
c8 = [x for x in long_rows if 'within_noise' in x]
report = dict(
    status='DIAGNOSTIC ONLY; V6 FAIL unchanged',
    evaluated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    protocol_sha256=hashlib.sha256((e / 'cr17b-noise-gc-diagnostic-v7-protocol.json').read_bytes()).hexdigest(),
    analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    analyzer_note='Written while V7 runs were in progress, before any V7 result was read.',
    gc=gc_result,
    c8_p95_within_noise={'/'.join(map(str, x['key'])): x['within_noise'] for x in c8},
    cold_long=cold_long,
    long=long_rows,
    raw_sha256={name: hashlib.sha256((e / name).read_bytes()).hexdigest() for name in sorted(set(used))},
)
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(dict(gc_shift_pairs=shift_pairs, gc_hypothesis_supported=gc_result['hypothesis_supported'],
                      median_combined_diff_ms=round(median_combined_diff, 2), c8_within_noise=report['c8_p95_within_noise'],
                      c8=[(x['key'], [round(v, 1) for v in x['contemporaneous_paired_diffs']], [round(v, 1) for v in x['s2_range']], [round(v, 1) for v in x['s4_pooled_run_medians']]) for x in c8],
                      cold_long=[(c['user'], round(c['median_diff_ms'], 1)) for c in cold_long])))
