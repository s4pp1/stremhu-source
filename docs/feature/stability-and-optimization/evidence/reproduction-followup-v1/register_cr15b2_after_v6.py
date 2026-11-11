"""Register the packet 26b normal after-gate protocol (v6, CR15a v6 landing runtime) before any measured run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'cr15b2-after-v3-fixture'
t = e / 'cr15b2-after-v6-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


p = dict(
    id='cr15b2-after-v6', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='Final packet 26b normal-workload gate; registered before any measured run (only a 4-request smoke of each side ran).',
    change=('get_bounded follows redirects itself via the public Response.next_request (relative Location, cookie/header rules unchanged), '
            'closes each redirect body unread, keeps history, max 10 hops. Per-hop origin allowlist not part of this change.'),
    before='frozen wip/cr15-chain-v6 5a1ee58 server/app (CR15a v6 + 26a; cr15b-after-v5-source manifest)',
    after='frozen wip/cr15-chain-v6 6bd0370 server/app (cr15b2-after-v6-source manifest; strict host policy)', previous='cr15b2-after-v5 PASS on the CR15a v5 tree and cr15b2-after-v4 PASS on the CR15a v3 tree (75 checks each); rerun because the landing runtime changed (CR15a v6: Dockerfile glibc ENV, ff1a39a; server/app identical to v5). (The v5 protocol text names itself where -v4 was meant.)',
    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',
    runtime_env={s: json.loads((e / f'{m}-source-manifest.json').read_text(encoding='utf-8'))['runtime_env'] for s, m in (('before', 'cr15b-after-v5'), ('after', 'cr15b2-after-v6'))},
    fixture_sha256={n.name: sha(n) for n in sorted(fx.iterdir())},
    controller_sha256=sha(r / 'cr15b2_after_v6.py'), assessor_sha256=sha(r / 'assess_cr15b2_after_v6.py'),
    workload=('G15 normal-transport v2 probe with only the cdn-redirect kind removed, unchanged private tracker fixture (small, many-files, large-valid 21.5 MB, '
              'login-redirect with one relogin, 4 s drip; cdn-redirect excluded because it leaves the tracker domain, see cr15b2-redirect-v6) x concurrency 1/4/8 x 100 requests, cold and warmup separate.'),
    sampling='Two series x five before/after pairs, pair order alternating (ABBA).',
    resources='client 2 CPU on 2,3 / 1 GiB; private HTTP server 1 CPU on 4 / 512 MiB; internal network, no outbound, no real credentials.',
    concurrency_note='Runs on cpus 2-4 beside the CR15a v6 gate (8-10), the 27 v4 gate (0,1,6) and the 26a/26b functional re-gates (12-14) on disjoint cpusets.',
    decision=('Plan 2.3 safety/correctness rule. PASS iff all 20 normal runs complete with the probe checks (hash, relogin count, cookie/outbound boundary) '
              'and no (kind, concurrency) metric among p50/p95, CPU seconds, anon after and per-cell anon peak shows repeatable degradation '
              '(both series medians > before max + J). Otherwise FAIL; missing runs INVALID. The redirect-body effect itself is the separate '
              'functional gate cr15b2-redirect-v6.'),
)
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
