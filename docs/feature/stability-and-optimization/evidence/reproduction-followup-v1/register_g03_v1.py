"""Register the G03 v1 protocol (before any measured batch)."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'g03-v1'
target = e / 'g03-v1-protocol.json'
if target.exists():
    raise SystemExit('Protocol already registered')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


protocol = dict(
    id='g03-v1', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='Final G03 benefit/cost gate and decision rule; registered before any measured batch (only the n=5 fixture smoke ran).',
    question='Does route-scoped gzip of Stremio JSON give a repeatable net benefit without LAN/CPU degradation beyond the plan 2.3 common gate?',
    source='C image + frozen aaa9ee5 server/app overlay (g02-post-cr17-v2 manifest, re-verified by controller).',
    image=json.loads((fx / 'params.json').read_text(encoding='utf-8'))['image'],
    params=json.loads((fx / 'params.json').read_text(encoding='utf-8')),
    fixture_sha256={n: sha(fx / n) for n in ['server.py', 'shaper.py', 'client.py', 'params.json']},
    controller_sha256=sha(r / 'g03_v1.py'), assessor_sha256=sha(r / 'assess_g03_v1.py'),
    workload=('Real StremioStreams/MetaResponse/StremioCatalogResponse models via FastAPI response_model under Hypercorn run() defaults; '
              'payloads streams 0/1/10/40/200 (40 = normal max path, 200 = stress), series meta with 50 videos, catalog 200 (stress). '
              'Upstream cost stubbed constant (prebuilt seeded instances); serialization per request real. Accept-Encoding: gzip on every request.'),
    variants='identity-a and identity-b (noise baseline, same process, interleaved), gzip1/4/6 = Starlette GZipMiddleware minimum_size=1.',
    thresholds='Candidate thresholds 1/2/4/8 KiB are derived: payloads below T stay identity (identity cells), payloads >= T use gzip cells.',
    profiles=('lan = direct Docker internal network; wan50/wan10/mob2 = shared-bottleneck relay (50/10/2 Mbit/s, 20/40/80 ms RTT). '
              'Limit: the relay delays data, not the TCP handshake, so fresh-connection cells do not include handshake RTT (identical for all variants).'),
    sampling='5 repetitions; per repetition one fresh server per profile; profile order rotated by repetition; variant order rotated by repetition+payload; '
             'modes c1/c4/c8 keep-alive and fresh (new connection per request, c1); 100 measured requests per cell after separate warmup.',
    resources='client 2 CPU on 2,3 / 1 GiB; server 1 CPU on 4 / 512 MiB; relay 1 CPU on 5 / 256 MiB; internal network, no host ports, no outbound, no real credentials.',
    concurrency_note='Runs alongside G02 (CPU 0,1, until ~17:00) and G04 (CPU 12-14) on disjoint cpusets; shared host may add noise, absorbed by identity-a/b J and range.',
    metrics='total p50/p95/p99, ttfb p95, server process CPU per request (/__stats process_time delta), wire bytes, client decode time (outside timed window), decoded sha256.',
    correctness='All 200; identity without Content-Encoding; gzip with Content-Encoding gzip and Vary Accept-Encoding; one decoded sha256 per payload across all variants/repetitions; '
                'same server pid per cell; all batches and full row counts. Any failure => INVALID.',
    decision=('Strict plan 2.3 common gate (no CPU/UX budget was designated in writing before measurement). Benefit = median < identity range min - J and >= 2 repetitions below. '
              'Repeatable degradation = median > identity range max + J and >= 2 repetitions above. (level, threshold) eligible at a profile iff streams/40 compressed and benefits in all modes at that profile, '
              '>= 30 % byte reduction for compressed payloads >= 16 KiB, and no compressed payload shows repeatable degradation of total p95, ttfb p95 or server CPU/request at any profile (LAN included). '
              'PASS_CANDIDATE if any profile has an eligible pair (lowest streams/40 c1 p95 chosen); else REJECT_UNDER_COMMON_GATE. Either way the full trade-off table is published; '
              'a later budget-based adoption would be a user product decision, not this gate passing.'),
    not_covered=('Starlette 1.10.0 GZipMiddleware ignores q=0 (g03-api-preparation): even a PASS_CANDIDATE cannot be implemented with it as-is. '
                 'Per-variant server memory is not separable (one process serves all variants); process RSS/maxRSS reported only. TLS not covered (packet 24).'),
    validation_before_registration=('Assessor run on duplicated smoke data: REJECT_UNDER_COMMON_GATE; with LAN cost and CPU/ttfb artificially neutralized: PASS_CANDIDATE at mob2. '
                                    'Smoke: 0 correctness problems, one decoded sha per payload.'),
)
target.write_text(json.dumps(protocol, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', protocol['registered_at_utc'], sha(target)[:12])
