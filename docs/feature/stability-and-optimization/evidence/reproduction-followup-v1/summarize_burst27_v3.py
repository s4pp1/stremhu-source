"""Summary of burst27-v3 by the registered summary_rule (descriptive; no pass/fail, no parameter chosen).
Per cell: median and range over repetitions of run p50/p95/max and anon peak delta; OOM count; noise = spread (max-min) of run p95."""
import hashlib
import json
import pathlib
import statistics

r = pathlib.Path(__file__).parent
e = r / 'evidence'
protocol = json.loads((e / 'burst27-v3-protocol.json').read_text(encoding='utf-8'))
assert (e / 'burst27-v3-complete.json').exists()
MIB = 2 ** 20


def stat(values):
    return dict(median=statistics.median(values), min=min(values), max=max(values)) if values else None


cells = []
for mix, n in [tuple(c) for c in protocol['cells']]:
    runs = [json.loads((e / f'burst27-v3-{mix}-{n}-r{rep}.json').read_text(encoding='utf-8')) for rep in range(protocol['repetitions'])]
    ok = [d['result'] for d in runs if d['exit_code'] == 0]
    cells.append(dict(
        mix=mix, n=n, runs=len(runs), completed=len(ok), oom_killed=sum(d['oom_killed'] for d in runs),
        other_failures=sum(1 for d in runs if d['exit_code'] and not d['oom_killed']),
        all_results_correct=all(x['ok'] and not x['guard_timeout'] and x['external_http_attempts'] == 0 for x in ok),
        p50_ms=stat([x['p50_ms'] for x in ok]), p95_ms=stat([x['p95_ms'] for x in ok]), max_ms=stat([x['max_ms'] for x in ok]),
        p95_noise_ms=(max(x['p95_ms'] for x in ok) - min(x['p95_ms'] for x in ok)) if ok else None,
        anon_peak_delta_mib=stat([x['anon_peak_delta'] / MIB for x in ok]), current_peak_delta_mib=stat([x['current_peak_delta'] / MIB for x in ok]),
        tasks_peak=stat([x['tasks_peak'] for x in ok]), loop_lag_max_ms=stat([x['loop_lag_max_ms'] for x in ok]),
        retained_downloaded_mib=stat([x['retained_downloaded_bytes_peak'] / MIB for x in ok]),
        store_seconds_max=stat([x['store_seconds_max'] for x in ok]), server_download_peak=stat([x['server']['downloads_peak'] for x in ok]),
        cpu_seconds=stat([x['cpu_seconds'] for x in ok])))
out = dict(id='burst27-v3-summary', protocol_sha256=hashlib.sha256((e / 'burst27-v3-protocol.json').read_bytes()).hexdigest(),
           summarizer_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
           rule=protocol['summary_rule'], note='Descriptive input for the packet 27 UX/SLO decision; no pass/fail and no parameter is chosen here.', cells=cells)
(e / 'burst27-v3-summary.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
for c in cells:
    f = lambda s, d=0: '-' if s is None else f"{s['median']:.{d}f} [{s['min']:.{d}f}-{s['max']:.{d}f}]"
    print(f"{c['mix']:8s} N={c['n']:2d} ok={c['completed']}/{c['runs']} oom={c['oom_killed']} correct={c['all_results_correct']} "
          f"p50={f(c['p50_ms'])} p95={f(c['p95_ms'])} noise={c['p95_noise_ms'] and round(c['p95_noise_ms'])} anon+={f(c['anon_peak_delta_mib'])}MiB "
          f"cur+={f(c['current_peak_delta_mib'])} lag={f(c['loop_lag_max_ms'])} retained={f(c['retained_downloaded_mib'], 1)} tasks={f(c['tasks_peak'])}")
