"""Register the CR15a after-gate protocol (v1) before any measured run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'cr15a-after-v3-fixture'
t = e / 'cr15a-after-v3-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


p = dict(
    id='cr15a-after-v3', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='Final CR15a (packet 25) gate v3; registered before any measured run (only a 4-request smoke of each probe ran). Follows the FAILED cr15a-after-v1 and -v2; rules, workload and resources unchanged.',
    supersedes=[dict(id='cr15a-after-v1', status='FAIL', failures=13, cause='bytearray growth + bytes() copy (~3.5x CPU per large body)'),
                dict(id='cr15a-after-v2', status='FAIL', failures=5, cause='own chunk-list buffering: c1 large-body p50/CPU slower, many-files c1 slower, small c1 anon +0.4 MiB; c4/c8 improved')],
    change=('IndexerClient.get_bounded: streamed GET under the adapter semaphore, declared-length precheck and decoded-byte cap '
            '(indexer_torrent_max_bytes = 48 MiB, user decision 2026-11-07), session-error relogin retry and redirect history kept; '
            'download_torrent uses it; v3: identity bodies run httpx aread() over a counting raw-stream wrapper and return the original response; encoded bodies count decoded bytes. Redirect intermediate bodies are still read by HTTPX (CR15/b scope).'),
    before='frozen aaa9ee5 server/app (g02-post-cr17-v2 manifest)', after='frozen wip/cr15a-bounded-download 0864a87 server/app (cr15a-after-v3-source-manifest)',
    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',
    fixture_sha256={n.name: sha(n) for n in sorted(fx.iterdir())},
    controller_sha256=sha(r / 'cr15a_after_v3.py'), assessor_sha256=sha(r / 'assess_cr15a_after_v3.py'),
    workload=('Normal: unchanged G15 normal-transport v2 probe and private tracker fixture (small, many-files, large-valid 21.5 MB, login-redirect with one relogin, '
              'cdn-redirect, 4 s drip) x concurrency 1/4/8 x 100 requests, cold and warmup separate. Giant: chunked-large 64 MiB and gzip-large '
              '585706 B -> 134217728 B decoded, concurrency 1/4/8 x 100 requests, outcome per request.'),
    sampling=('Two series x five before/after pairs, pair order alternating (ABBA); then one giant-after run per series; then one giant-before confirmation '
              '(expected OOM; earlier evidence g15-gzip-controls-assessment-v3: 75/75 OOM). A/B: the download path is unchanged from the G15 normal-transport '
              'v2 A/B references (download modules unchanged 050cb33..aaa9ee5); no new A/B runs.'),
    resources='client 2 CPU on 8,9 / 1 GiB; private HTTP server 1 CPU on 10 / 512 MiB; internal network, no outbound, no real credentials.',
    concurrency_note='Runs alongside G03 (CPU 2-5, until ~21:30), G04 (12-14) and later fixture-only gates on disjoint cpusets; alternating pairs absorb slow drift.',
    decision=('Plan 2.3 safety/correctness rule. PASS iff all 20 normal runs complete with the probe checks (hash, relogin count, cookie/outbound boundary), both '
              'giant-after runs exit 0 without OOM and every request is rejected as too-large, and no (kind, concurrency) metric among p50/p95, CPU seconds, '
              'anon after and per-cell anon peak shows repeatable degradation (both series medians > before max + J). Otherwise FAIL; missing runs INVALID.'),
    smoke='v2 smoke results recorded in the smoke evidence files before registration.',
    diagnostic_before_registration=('Focused diagnostic, not gate data (cr15a_diag2.py): small/many-files/large-valid at c1/c4/c8 x100, before/v2/v3 '
                                    'interleaved x3. large c1 p50 before 20.6-22.8 ms, v2 29.0-30.6, v3 20.8-22.9; many-files c1 2.8/3.1-3.3/2.8 ms; '
                                    'c4/c8 v3 equal to before; small c1 anon after before 37.05-37.16 MiB, v3 38.34-38.66 MiB (risk under the strict anon rule). Rules unchanged.'),
)
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
