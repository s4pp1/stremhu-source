"""Fresh-process cold requalification; keeps all failed V1/V2 evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import secrets
import subprocess

r=Path(__file__).parent
repo=Path.cwd()
e=r/'evidence'
original=r/'cr17b-policy-fixture-v2.py'
fixture=r/'cr17a-cold-focus-fixture-v3.py'
text=original.read_text()
needle='duration=60 if PROFILE_SMOKE else 1800'
assert text.count(needle)==1 and not fixture.exists()
# Execution is identical through the original two cold observations. Only the
# subsequent heap loop is omitted. Initialization, tracemalloc, DB, actual
# auth/provider/ranking/payload checks and drain are unchanged.
fixture.write_text(text.replace(needle,'duration=0  # cold-only; full long controls retained separately'),encoding='utf-8')
images={'A':'s4pp1/stremhu-source@sha256:a3a2012893d689795f958ccec666fef6277f8677f24efebe9568cb44ec7a0621','B':'stremhu-source@sha256:6ca708d99b8698e6cf116a6183c283922ebd2e53940c366a93a421b4ca974a38','C':'stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'}
sources={'before':r/'cr17a-after-v7-source/server','after':r/'cr17a-drain-fix-v2-source/server','B':r/'baseline/server'}
manifests={label:json.loads((e/name).read_text())['files'] for label,name in [('before','cr17-a-checked-v7-manifest.json'),('after','cr17a-drain-checked-v2-manifest.json')]}
protocol=dict(id='cr17a-cold-focus-v3',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason='V2 unchanged-source SQL invariant failed even before; remaining94metric diagnostic found colduser0+26.391ms despite all normal/lifecycle/native/steadyheap gates passing. Preserve failures. Focused qualification has no budget change or application edit.',sampling='Two5-run paired cohorts,10fresh processes/source/repeat (100before+100after),alternating source order within each repeat;then5rotatedABC references,10fresh processes/label/repeat.Colduser0/1 separate;all completed samples included,failedprocesses failqualification.',acceptance='Exact payload/order/count and coldSQL no increase for identical state. Per-user pooled run-median and pooled p95 cold wall effect<=+10ms;both cohort effects reported. CPU/fixedmemory still original budgets in retained long/normal gates,not redefined here. No blanket PASS from this subset.',resources='Client2CPU6,7/1GiB,networknone,readonlyfrozenapp,tmpfs syntheticDB;all other local controlled workloads finished before start.',original_fixture_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),source_manifest_sha256={label:hashlib.sha256((e/name).read_bytes()).hexdigest() for label,name in [('before','cr17-a-checked-v7-manifest.json'),('after','cr17a-drain-checked-v2-manifest.json')]})
target=e/'cr17a-cold-focus-v3-protocol.json'
assert not target.exists()
target.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
context=json.loads(subprocess.check_output(['docker','--context','desktop-linux','context','inspect','desktop-linux'],text=True))[0]
assert context['Endpoints']['docker']['Host'].startswith('npipe://')
assert not subprocess.check_output(['docker','--context','desktop-linux','ps','-q'],text=True).strip(), 'Other controlled workloads must finish before cold qualification'
env=os.environ.copy()
env.update(HOST_IP=(repo/'.git/cr-test-host').read_text().strip(),SESSION_SECRET=secrets.token_urlsafe(48),STREMHU_LOAD_DOTENV='false',PYTHONDONTWRITEBYTECODE='1')
cases=[(label,cohort,rep,sample) for cohort in ['a','b'] for rep in range(5) for sample in range(10) for label in (['before','after'] if (rep+sample)%2==0 else ['after','before'])]
# Same provider fixture in A/B: its dependency scope has been checked for the
# original primary cold path. This is the exact same source as the C fixture.
cases += [(label,'ref',rep,sample) for rep in range(5) for label in [['A','B','C'],['B','C','A'],['C','A','B']][rep%3] for sample in range(10)]
for label,cohort,rep,sample in cases:
    stem=f'cr17a-cold-focus-v3-{label}-{cohort}-{rep}-{sample}'
    output=e/(stem+'.json')
    assert not output.exists()
    image=images[label] if label in ['A','B','C'] else images['C']
    source=sources.get(label,sources['after'] if label=='C' else None)
    if label in manifests:
        assert all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in manifests[label].items() if name.startswith('app/'))
    cmd=['docker','--context','desktop-linux','run','--rm','--name',stem+'-obva7te6','--label','stremhu.task=obva7te6','--network','none','--read-only','--cpus','2','--cpuset-cpus','6,7','--memory','1g','--tmpfs','/tmp','--tmpfs','/app/data','--tmpfs','/fixture-output']
    for key in ['HOST_IP','SESSION_SECRET','STREMHU_LOAD_DOTENV','PYTHONDONTWRITEBYTECODE']:cmd+=['--env',key]
    cmd+=['--env','PYTHONPATH=/app','--mount',f'type=bind,source={fixture},target=/fixture/probe.py,readonly']
    if source is not None:cmd+=['--mount',f'type=bind,source={source/"app"},target=/app/app,readonly']
    cmd+=['--entrypoint','python',image,'/fixture/probe.py','--heap-profile']
    result=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8')
    (e/(stem+'.stdout')).write_text(result.stdout,encoding='utf-8')
    (e/(stem+'.stderr')).write_text(result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Fresh-process cold qualification failed;raw retained')
    d=json.loads(result.stdout)
    assert len(d['cold'])==2 and not d['external_http_attempts'] and not d['rows']
    d.update(protocol=protocol['id'],source=source.parent.name if source is not None else 'pinnedAimage',image=image,cohort=cohort,repetition=rep,sample=sample,label=label)
    output.write_text(json.dumps(d),encoding='utf-8')
    if sample==9:print(label,cohort,rep,'10fresh cold samples saved',flush=True)
print('All350fresh processes saved; assessment required',flush=True)
