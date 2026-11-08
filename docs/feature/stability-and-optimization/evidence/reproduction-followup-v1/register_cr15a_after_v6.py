"""Register the CR15a after-gate protocol (v6) before any measured run. argv[1] = the user's decision, verbatim summary (English)."""
import datetime
import hashlib
import json
import pathlib
import sys

r = pathlib.Path(__file__).parent
e = r / 'evidence'
fx = r / 'cr15a-after-v4-fixture'
t = e / 'cr15a-after-v6-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')
decision_text = sys.argv[1].strip()
assert decision_text.startswith('2026-11-08')
v5p = json.loads((e / 'cr15a-after-v5-protocol.json').read_text(encoding='utf-8'))
v5 = json.loads((e / 'cr15a-after-v5-assessment.json').read_text(encoding='utf-8'))
assert v5['status'] == 'FAIL' and len(v5['failures']) == 4 and all(f['concurrency'] == 1 for f in v5['failures'])
man = json.loads((e / 'cr15a-after-v6-source-manifest.json').read_text(encoding='utf-8'))
assert man['commit'] == 'ff1a39a' and man['identical_server_app_to'] == 'cr15a-after-v5'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


assert v5p['decision'].startswith('Plan 2.3 safety/correctness rule, identical to v1-v4. ')
p = dict(
    id='cr15a-after-v6', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status=('CR15a (packet 25) gate v6; registered before any measured run (only a 4-request smoke of each probe ran). Harness (cr15a-after-v4-fixture '
            'with the app.config preload), before, image, workload, resources, rules and thresholds are those of v4/v5; server/app is byte-identical to v5; '
            'the after side runs with the glibc ENV of the ff1a39a Dockerfile. The v1-v5 FAILs stand.'),
    user_decision=decision_text,
    supersedes=v5p['supersedes'] + [dict(id='cr15a-after-v5', status='FAIL', failures=4,
                                          cause=('c1 only: large-valid p50 (after medians 29.4/28.4 vs before max 21.9 ms) and CPU (3.96/3.88 vs 3.21 s), many-files p50 '
                                                 '(3.11/3.06 vs 2.80 ms) and CPU (0.311/0.309 vs 0.281 s); the v4 memory excess gone, c4/c8 faster, other 86 checks and giant passed'))],
    diagnostics_before_registration=(
        'Not gate data. cr15a_diag7 (before, v4 code, v5 code, each also with a fixed glibc mmap 32 MiB / trim 128 MiB as a hypothesis test; 3 reps, same '
        'image/fixture/limits/preload): v5 frees each body at once and glibc trims the heap back to the OS after every request (arena 12 MiB), so the next '
        'request page-faults the chunks and the joined body afresh: large-valid c1 11 755-11 760 minor faults/request vs before 3 444-5 247; with the fixed '
        'thresholds 0 faults, p50 14.3-14.8 vs 20.0-22.5 ms, peak anon 84 vs 573-597 MiB, and faster/lower than before in every row. cr15a_diag8 (4 reps): '
        'trim 64 MiB (= 2 x 32 MiB, the state glibc\'s own dynamic adjustment converges to) also gives 0-1 faults/request at c1, large-valid c1 p50 '
        '14.5-16.5 vs before 20.4-21.9 ms, anon after the batch 84 MiB at c1 and 38 MiB at c4 (before 538-571 and 712-815 MiB); selected for v6.'),
    change=('v5 code unchanged (IndexerClient.get_bounded with the 48 MiB decoded-byte cap, httpx aread() over a counting raw-stream wrapper, then the '
            'response stream swapped for a ByteStream so the body is freed by reference counting) plus, in the Docker runtime image (ff1a39a Dockerfile): '
            'ENV MALLOC_MMAP_THRESHOLD_=33554432 and MALLOC_TRIM_THRESHOLD_=67108864. The gate passes these two variables to the after-side probe container '
            '(runtime_env of cr15a-after-v6-source-manifest), exactly as the image would set them; the before side (aaa9ee5, no such ENV) runs without them.'),
    before=v5p['before'], after='frozen wip/cr15a-bounded-download ff1a39a server/app (cr15a-after-v6-source-manifest; = v5 server/app) + its Dockerfile MALLOC_* ENV',
    image=v5p['image'], runtime_env=dict(before={}, after=man['runtime_env']), dockerfile_sha256=man['dockerfile_sha256'],
    fixture_sha256={n.name: sha(n) for n in sorted(fx.iterdir())},
    fixture_note=v5p['fixture_note'],
    controller_sha256=sha(r / 'cr15a_after_v6.py'), assessor_sha256=sha(r / 'assess_cr15a_after_v6.py'),
    workload=v5p['workload'],
    sampling=v5p['sampling'].replace('Identical to v4.', 'Identical to v4/v5.'),
    resources=v5p['resources'],
    concurrency_note=('The 26b normal v6 (2-4), 27 v4 (0,1,6) and 26a/26b functional (12-14) re-gates on the v6 runtime run on disjoint cpusets; '
                      'alternating pairs absorb slow drift.'),
    decision=v5p['decision'].replace('identical to v1-v4. ', 'identical to v1-v5. ', 1),
    smoke='v6 smoke (4 requests per cell, both sides, both probes) completed before registration; results in the smoke evidence files.',
)
assert p['fixture_sha256'] == v5p['fixture_sha256'], 'fixture drift vs v5'
assert p['sampling'] != v5p['sampling'] and p['decision'] != v5p['decision']
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
