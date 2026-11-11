"""G02 per-cell summary used by the post-CR17 control assessor (v2). Pure function of a fixture output."""
import json
import sys


def summarize(d):
    out = {}
    for c in d['cells']:
        key = f"{c['reader']}/{c['writers']}"
        samples = [s for s in d['wal_samples'] if s['reader'] == c['reader'] and s['writers'] == c['writers']]
        sizes = [s['wal_bytes'] for s in samples]
        epochs = []
        for s in samples:
            h = s['wal_header_sha256']
            if s['wal_bytes'] and (not epochs or epochs[-1] != h):
                epochs.append(h)
        tail = sizes[-30:] if sizes else [0]
        out[key] = dict(
            errors=len(c['errors']),
            elapsed_seconds=c['elapsed_seconds'],
            transactions=c['counters'].get('transactions'),
            commit_p95_ms=c['commit_p95_ms'], commit_p99_ms=c['commit_p99_ms'],
            transaction_p95_ms=c['transaction_p95_ms'], transaction_p99_ms=c['transaction_p99_ms'],
            wal_max_bytes=max(sizes) if sizes else 0,
            wal_tail_max_bytes=max(tail),
            wal_header_epochs=len(epochs),
            samples=len(sizes),
        )
    return dict(cells=out, final_checkpoint=d['final_checkpoint_after_all_readers_closed'],
                final_checkouts=d['final_checkouts'], measured_seconds=d['measured_seconds'],
                cpu_seconds=d['cpu_seconds'])


if __name__ == '__main__':
    for path in sys.argv[1:]:
        s = summarize(json.load(open(path, encoding='utf-8')))
        print(path.split('/')[-1], 'final', s['final_checkpoint'], 'checkouts', s['final_checkouts'])
        for k, v in s['cells'].items():
            print(f"  {k:14} tx={v['transactions']:5} c95={v['commit_p95_ms']:.3f} c99={v['commit_p99_ms']:.3f} "
                  f"t99={v['transaction_p99_ms']:.2f} walmax={v['wal_max_bytes']/1e6:6.2f}MB tail={v['wal_tail_max_bytes']/1e6:6.2f}MB "
                  f"epochs={v['wal_header_epochs']} err={v['errors']}")
