"""Register the CR15a after-gate protocol (v4) before any measured run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'cr15a-after-v4-fixture'
t = e / 'cr15a-after-v4-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')
v3 = json.loads((e / 'cr15a-after-v3-assessment.json').read_text(encoding='utf-8'))
assert v3['status'] == 'FAIL' and len(v3['failures']) == 4


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


p = dict(
    id='cr15a-after-v4', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status=('CR15a (packet 25) gate v4; registered before any measured run (only a 4-request smoke of each probe ran). Code under test, before, image, '
            'workload, resources, rules and thresholds are those of v3; the only change is the harness confound found after the v3 FAIL (see harness_change). '
            'The v3 FAIL stands. Because the harness changed after a FAIL, a v4 PASS is not landed without the user\'s acknowledgement.'),
    supersedes=[dict(id='cr15a-after-v1', status='FAIL', failures=13, cause='bytearray growth + bytes() copy (~3.5x CPU per large body)'),
                dict(id='cr15a-after-v2', status='FAIL', failures=5, cause='own chunk-list buffering: c1 large-body p50/CPU slower, many-files c1 slower, small c1 anon +0.4 MiB; c4/c8 improved'),
                dict(id='cr15a-after-v3', status='FAIL', failures=4,
                     cause='small-kind anon only (c1 after/peak, c4 after, c8 peak; after medians +1.2..+1.9 MiB); every latency/CPU check and the giant control passed')],
    harness_change=('The probe imports only IndexerClient and the nCore adapter. On the before side that import chain never loads app.config; on the after side '
                    'base_indexer_definition imports it (for indexer_torrent_max_bytes), so the after process also carries app.config and its 35 dependent '
                    'modules (pydantic-settings, dotenv, ...). The production server always has app.config loaded at startup, so this one-time cost is not '
                    'caused by the change in production. v4 runs the unchanged probe.py/giant.py through preload_probe.py/preload_giant.py, which import '
                    'app.config first, identically on the before and after side.'),
    diagnostics_before_registration=('Not gate data. cr15a_diag3_import: importing app.config in the before probe process loads 35 new modules, +0.94 MiB '
                                     'RssAnon; in the after process it is already loaded. cr15a_diag3 (small kind only, 4 reps, rotated): c1 anon after median '
                                     'before 36.58 / v3 38.60 MiB without preload, before 38.15 / v3 38.55 MiB with preload on both sides. cr15a_diag4 (6 reps, '
                                     'preload on all): c1 anon after median before 38.14 / v3 38.15 MiB (v3 range 37.99-39.11, before 37.94-38.15); c4/c8 '
                                     'differences in both directions within ~0.5 MiB; p50/CPU equal. Residual risk: v3 shows occasional +0.4-1.0 MiB c1 values '
                                     'while the before side is very tight, so the strict anon rule can still fail.'),
    change=('Unchanged from v3: IndexerClient.get_bounded: streamed GET under the adapter semaphore, declared-length precheck and decoded-byte cap '
            '(indexer_torrent_max_bytes = 48 MiB, user decision 2026-11-07), session-error relogin retry and redirect history kept; download_torrent '
            'uses it; identity bodies run httpx aread() over a counting raw-stream wrapper and return the original response; encoded bodies count decoded bytes.'),
    before='frozen aaa9ee5 server/app (g02-post-cr17-v2 manifest)', after='frozen wip/cr15a-bounded-download 0864a87 server/app (cr15a-after-v3-source-manifest)',
    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',
    fixture_sha256={n.name: sha(n) for n in sorted(fx.iterdir())},
    fixture_note='probe.py, giant.py, server.py, expected.json, metadata_sizes.py byte-identical to cr15a-after-v3-fixture; preload_probe.py and preload_giant.py added.',
    controller_sha256=sha(r / 'cr15a_after_v4.py'), assessor_sha256=sha(r / 'assess_cr15a_after_v4.py'),
    workload=('Normal: unchanged G15 normal-transport v2 probe and private tracker fixture (small, many-files, large-valid 21.5 MB, login-redirect with one relogin, '
              'cdn-redirect, 4 s drip) x concurrency 1/4/8 x 100 requests, cold and warmup separate. Giant: chunked-large 64 MiB and gzip-large '
              '585706 B -> 134217728 B decoded, concurrency 1/4/8 x 100 requests, outcome per request. Both run after the app.config preload.'),
    sampling=('Two series x five before/after pairs, pair order alternating (ABBA); then one giant-after run per series; then one giant-before confirmation '
              '(expected OOM). Identical to v3.'),
    resources='client 2 CPU on 8,9 / 1 GiB; private HTTP server 1 CPU on 10 / 512 MiB; internal network, no outbound, no real credentials.',
    concurrency_note='Starts while the 26b v4 chain finishes on CPU 2-4; disjoint cpusets; alternating pairs absorb slow drift.',
    decision=('Plan 2.3 safety/correctness rule, identical to v3. PASS iff all 20 normal runs complete with the probe checks (hash, relogin count, cookie/outbound '
              'boundary), both giant-after runs exit 0 without OOM and every request is rejected as too-large, and no (kind, concurrency) metric among p50/p95, '
              'CPU seconds, anon after and per-cell anon peak shows repeatable degradation (both series medians > before max + J). Otherwise FAIL; missing runs INVALID.'),
    smoke='v4 smoke (4 requests per cell, both sides, both probes) completed before registration; results in the smoke evidence files.',
)
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
