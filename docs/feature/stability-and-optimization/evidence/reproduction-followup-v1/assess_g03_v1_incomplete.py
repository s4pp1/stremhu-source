"""G03 v1 closing analysis after an incomplete run (written after the failure; NOT the preregistered decision).

The preregistered assessor requires all 20 batches; batch rep 4 / mob2 failed (client RemoteProtocolError: the fixture
server closed a keep-alive connection without a response, streams/200 identity-b c8), so the gate status is INVALID and
no complete marker exists. This script only checks whether the missing batch could matter: it applies the unchanged
assess_g03_v1.assess() rules to the 19 complete batches and tests whether every (level, threshold) is already excluded
by a repeatable degradation on the LAN profile, whose 5/5 batches are complete and whose rows use LAN data only.
"""
import hashlib
import json
import pathlib

import assess_g03_v1 as g

r = pathlib.Path(__file__).parent
e = r / 'evidence'
assert not (e / 'g03-v1-complete.json').exists()
names = [f'g03-v1-{rep}-{p}.json' for rep in range(g.P['repetitions']) for p in g.P['profiles'] if not (rep == 4 and p == 'mob2')]
assert all((e / n).exists() for n in names) and not (e / 'g03-v1-4-mob2.json').exists()
res = g.assess(names, None)
size = {q['payload']: q['identity_bytes'] for q in res['bytes']}
lan_degr = {(q['payload'], q['level']) for q in res['rows']
            if q['profile'] == 'lan' and q['repeatable_degradation'] and q['metric'] in ('total_p95', 'ttfb_p95', 'cpu_ms_per_req')}
combos = []
for lv in g.LEVELS:
    for t in g.THRESHOLDS_KIB:
        compressed = [x for x in g.P['payloads'] if size[x] >= t * 1024]
        combos.append(dict(level=lv, threshold_kib=t, lan_degraded_compressed_payloads=sorted(x for x in compressed if (x, lv) in lan_degr)))
decided = all(c['lan_degraded_compressed_payloads'] for c in combos)
out = dict(
    id='g03-v1', status='INVALID', is_preregistered_decision=False,
    failure=dict(batch='repetition 4, profile mob2', cell='streams/200 identity-b c8', error='httpx.RemoteProtocolError: server disconnected without sending a response',
                 completed_batches=len(names), expected_batches=g.P['repetitions'] * len(g.P['profiles'])),
    lan_batches_complete=sum(n.endswith('-lan.json') for n in names) == g.P['repetitions'],
    every_combination_excluded_by_lan=decided, combinations=combos,
    consequence=('Formal status INVALID. The decisive LAN rows are complete and exclude every (level, threshold), so no outcome of the missing mob2 batch '
                 'could make gzip eligible under the preregistered rule; no rerun. Practical result: no change (CR03 not adopted).'),
    nineteen_batch_view=dict(note='Same assess() rules on 19 batches; mob2 medians over 4 repetitions. Informational only.', status=res['status'],
                             bytes=res['bytes'], tradeoff_total_p95=res['tradeoff_total_p95'], cpu_per_request=res['cpu_per_request'], rows=res['rows']),
    protocol_sha256=hashlib.sha256((e / 'g03-v1-protocol.json').read_bytes()).hexdigest(),
    preregistered_assessor_sha256=hashlib.sha256((r / 'assess_g03_v1.py').read_bytes()).hexdigest(),
    analysis_script_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
(e / 'g03-v1-incomplete-assessment.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(dict(status=out['status'], decided_by_lan=decided, batches=len(names))))
