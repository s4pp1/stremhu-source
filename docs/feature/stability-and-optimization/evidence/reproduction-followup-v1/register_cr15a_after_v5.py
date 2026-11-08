"""Register the CR15a after-gate protocol (v5) before any measured run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'cr15a-after-v4-fixture'
t = e / 'cr15a-after-v5-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')
v4 = json.loads((e / 'cr15a-after-v4-assessment.json').read_text(encoding='utf-8'))
assert v4['status'] == 'FAIL' and len(v4['failures']) == 2


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


p = dict(
    id='cr15a-after-v5', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status=('CR15a (packet 25) gate v5; registered before any measured run (only a 4-request smoke of each probe ran). Harness (cr15a-after-v4-fixture '
            'with the app.config preload), before, image, workload, resources, rules and thresholds are those of v4; the code under test changes (see change). '
            'The v1-v4 FAILs stand.'),
    user_decision=('2026-11-08: the user approved v5 and, if v5 and the re-gated 26a/26b/27 chain on top of it PASS, landing 25 -> 26a -> 26b -> 27; '
                   'this includes the v4 harness (app.config preloaded on both sides).'),
    supersedes=[dict(id='cr15a-after-v1', status='FAIL', failures=13, cause='bytearray growth + bytes() copy (~3.5x CPU per large body)'),
                dict(id='cr15a-after-v2', status='FAIL', failures=5, cause='own chunk-list buffering: c1 large-body p50/CPU slower, many-files c1 slower, small c1 anon +0.4 MiB; c4/c8 improved'),
                dict(id='cr15a-after-v3', status='FAIL', failures=4,
                     cause='small-kind anon only; mostly the probe harness confound (app.config not loaded on the before side), fixed in the v4 harness'),
                dict(id='cr15a-after-v4', status='FAIL', failures=2,
                     cause='many-files anon_after c1 (after medians 63.7/65.5 vs before max 59.9 MiB) and c4 (82.5/73.3 vs 72.4 MiB); peak lower; other 88 checks and giant passed')],
    diagnostics_before_registration=('Not gate data. cr15a_diag5 (before vs v3 code, preload, 6 reps): right after the many-files batch the glibc heap in use is '
                                     'c1 28.5 vs 33.0 MiB; after gc.collect + 3 s both sides RssAnon ~39-40 MiB, after malloc_trim 37.4-37.6 MiB, heap in use '
                                     '10.25 vs 10.26 MiB. cr15a_diag6 (4 reps): 3 s without GC releases nothing; a DEBUG_SAVEALL pass finds the downloaded bodies '
                                     'in cyclic garbage on BOTH sides (c1 before 9-15 bodies / after 16-18, c8 35-42 / 38-42). Local cycle probe (MockTransport): '
                                     'every download leaves Response <-> BoundAsyncStream (httpx) in a cycle with its body, before and after alike; the extra '
                                     'counting wrapper only shifts the GC timing. With the v5 stream swap the probe finds 0 bodies in cyclic garbage.'),
    change=('v4 code (IndexerClient.get_bounded: streamed GET under the adapter semaphore, declared-length precheck, decoded-byte cap '
            'indexer_torrent_max_bytes = 48 MiB (user decision 2026-11-07), session-error relogin retry and redirect history kept; download_torrent uses it; '
            'identity bodies run httpx aread() over a counting raw-stream wrapper and return the original response; encoded bodies count decoded bytes) '
            'plus: after aread() the identity path replaces response.stream with httpx.ByteStream(response.content), breaking the Response <-> stream '
            'reference cycle so the body is freed by reference counting. Regression test: the response is released with the GC disabled.'),
    before='frozen aaa9ee5 server/app (g02-post-cr17-v2 manifest)', after='frozen wip/cr15a-bounded-download 7c01689 server/app (cr15a-after-v5-source-manifest)',
    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',
    fixture_sha256={n.name: sha(n) for n in sorted(fx.iterdir())},
    fixture_note='cr15a-after-v4-fixture reused unchanged (probe.py, giant.py, server.py, expected.json, metadata_sizes.py, preload_probe.py, preload_giant.py).',
    controller_sha256=sha(r / 'cr15a_after_v5.py'), assessor_sha256=sha(r / 'assess_cr15a_after_v5.py'),
    workload=('Normal: unchanged G15 normal-transport v2 probe and private tracker fixture (small, many-files, large-valid 21.5 MB, login-redirect with one relogin, '
              'cdn-redirect, 4 s drip) x concurrency 1/4/8 x 100 requests, cold and warmup separate. Giant: chunked-large 64 MiB and gzip-large '
              '585706 B -> 134217728 B decoded, concurrency 1/4/8 x 100 requests, outcome per request. Both run after the app.config preload.'),
    sampling=('Two series x five before/after pairs, pair order alternating (ABBA); then one giant-after run per series; then one giant-before confirmation '
              '(expected OOM). Identical to v4.'),
    resources='client 2 CPU on 8,9 / 1 GiB; private HTTP server 1 CPU on 10 / 512 MiB; internal network, no outbound, no real credentials.',
    concurrency_note='The re-gates of the 26a/26b/27 chain on top of v5 run on disjoint cpusets; alternating pairs absorb slow drift.',
    decision=('Plan 2.3 safety/correctness rule, identical to v1-v4. PASS iff all 20 normal runs complete with the probe checks (hash, relogin count, cookie/outbound '
              'boundary), both giant-after runs exit 0 without OOM and every request is rejected as too-large, and no (kind, concurrency) metric among p50/p95, '
              'CPU seconds, anon after and per-cell anon peak shows repeatable degradation (both series medians > before max + J). Otherwise FAIL; missing runs INVALID.'),
    smoke='v5 smoke (4 requests per cell, both sides, both probes) completed before registration; results in the smoke evidence files.',
)
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
