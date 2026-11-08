"""Register the CR15a after-gate protocol (v1) before any measured run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'cr15a-after-v1-fixture'
t = e / 'cr15a-after-v1-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


p = dict(
    id='cr15a-after-v1', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='Final CR15a (packet 25) gate; registered before any measured run (only a 4-request smoke of each probe ran).',
    change=('IndexerClient.get_bounded: streamed GET under the adapter semaphore, declared-length precheck and decoded-byte cap '
            '(indexer_torrent_max_bytes = 48 MiB, user decision 2026-11-07), session-error relogin retry and redirect history kept; '
            'download_torrent uses it. Redirect intermediate bodies are still read by HTTPX (CR15/b scope).'),
    before='frozen aaa9ee5 server/app (g02-post-cr17-v2 manifest)', after='frozen wip/cr15a-bounded-download 7b3e58d server/app (cr15a-after-v1-source-manifest)',
    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',
    fixture_sha256={n.name: sha(n) for n in sorted(fx.iterdir())},
    controller_sha256=sha(r / 'cr15a_after_v1.py'), assessor_sha256=sha(r / 'assess_cr15a_after_v1.py'),
    workload=('Normal: unchanged G15 normal-transport v2 probe and private tracker fixture (small, many-files, large-valid 21.5 MB, login-redirect with one relogin, '
              'cdn-redirect, 4 s drip) x concurrency 1/4/8 x 100 requests, cold and warmup separate. Giant: chunked-large 64 MiB and gzip-large '
              '585706 B -> 134217728 B decoded, concurrency 1/4/8 x 100 requests, outcome per request.'),
    sampling=('Two series x five before/after pairs, pair order alternating (ABBA); then one giant-after run per series; then one giant-before confirmation '
              '(expected OOM; earlier evidence g15-gzip-controls-assessment-v3: 75/75 OOM). A/B: the download path is unchanged from the G15 normal-transport '
              'v2 A/B references (download modules unchanged 050cb33..aaa9ee5); no new A/B runs.'),
    resources='client 2 CPU on 8,9 / 1 GiB; private HTTP server 1 CPU on 10 / 512 MiB; internal network, no outbound, no real credentials.',
    concurrency_note='Runs alongside G03 (CPU 2-5) and G04 (12-14) on disjoint cpusets; alternating pairs absorb slow drift.',
    decision=('Plan 2.3 safety/correctness rule. PASS iff all 20 normal runs complete with the probe checks (hash, relogin count, cookie/outbound boundary), both '
              'giant-after runs exit 0 without OOM and every request is rejected as too-large, and no (kind, concurrency) metric among p50/p95, CPU seconds, '
              'anon after and per-cell anon peak shows repeatable degradation (both series medians > before max + J). Otherwise FAIL; missing runs INVALID.'),
    smoke='giant c1 x4: before peak anon 279 MiB (chunked) / 590 MiB (gzip), accepted bodies; after 79 / 55 MiB, all too-large. Normal smoke both sides OK.',
)
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
