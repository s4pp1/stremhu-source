from pathlib import Path
import hashlib
import json
import statistics

r=Path(__file__).parent
e=r/'evidence'

def load(name):
    return json.loads((e/name).read_text())

def digest(name):
    return hashlib.sha256((e/name).read_bytes()).hexdigest()

def med(values):
    return statistics.median(values)

g04={}
g04hashes={}
for cohort in ['a','b']:
    g04[cohort]=[]
    for i in range(5):
        name=f'g04-before-{cohort}-{i}-'+('v1' if i<3 else 'v2')+'.json'
        data=load(name)
        assert data['is_measurement'] and len(data['rows'])==16
        assert all(row['elapsed_ms']>=300000 and not row['errors'] and row['warmupRequests']>=3 for row in data['rows'])
        g04[cohort].append(data)
        g04hashes[name]=digest(name)
rows=[]
for index in range(16):
    groups=[[d['rows'][index] for d in g04[cohort]] for cohort in ['a','b']]
    assert len({(row['count'],row['pattern']) for group in groups for row in group})==1
    metrics={}
    for metric,read in [('requests',lambda row:row['requests']),('route_renders',lambda row:row['routeRenders']),('row_render_calls',lambda row:sum(row['rowRenders'].values())),('react_actual_ms',lambda row:sum(c['actualDuration'] for c in row['commits'])),('react_commits',lambda row:len(row['commits']))]:
        values=[[read(row) for row in group] for group in groups]
        medians=[med(group) for group in values]
        metrics[metric]=dict(cohort_medians=medians,J=abs(medians[0]-medians[1]),range=[min(x for g in values for x in g),max(x for g in values for x in g)])
    rows.append(dict(count=groups[0][0]['count'],pattern=groups[0][0]['pattern'],metrics=metrics))
g04report=dict(status='Two unchanged5-run full baseline cohorts COMPLETE; G04 decision still OPEN',rows=rows,raw_sha256=g04hashes,scope='10complete profiles x16cells x300real seconds, warmup excluded. Interrupted a3-v1 retained separately, not a sample. Heap and coldDOM supplements separate. No frontend source change; table29 and candidate comparison still required. A reference profiling build unavailable due preexisting lint; plan permits C two versions decisive when ABC not comparable.')
target=e/'g04-complete-baseline-summary-v1.json'
assert not target.exists()
target.write_text(json.dumps(g04report,indent=2),encoding='utf-8')

normal={}
hashes={}
sample_count=0
for label,cohort,i in [('C',s,i) for s in ['a','b'] for i in range(5)]+[(label,'ref',i) for i in range(5) for label in ['A','B','C']]:
    name=f'g15-normal-before-v2-{label}-{cohort}-{i}.json'
    data=load(name)
    assert data['is_measurement'] and len(data['rows'])==18 and len(data['cold'])==18 and data['external_http_attempts']==0
    assert all(len(row['samples_ms'])==100 for row in data['rows'])
    assert len({(row['kind'],row['concurrency']) for row in data['rows']})==18
    for row in data['rows']:
        sample_count+=len(row['samples_ms'])
    normal.setdefault((label,cohort),[]).append(data)
    hashes[name]=digest(name)
summary=[]
for index in range(18):
    allrows=[data['rows'][index] for group in normal.values() for data in group]
    assert len({(row['kind'],row['concurrency'],row['sha256'],row['decoded_bytes']) for row in allrows})==1
    kind=allrows[0]['kind']
    concurrency=allrows[0]['concurrency']
    groups=[[d['rows'][index] for d in normal['C',cohort]] for cohort in ['a','b']]
    metrics={}
    for metric,read in [('p50_ms',lambda row:row['p50_ms']),('p95_ms',lambda row:row['p95_ms']),('p99_ms',lambda row:row['p99_ms']),('cpu_seconds',lambda row:row['cpu_seconds']),('peak_anon_bytes',lambda row:row['memory_peaks']['anon_bytes']),('peak_cgroup_bytes',lambda row:row['memory_peaks']['peak_bytes'])]:
        values=[[read(row) for row in group] for group in groups]
        medians=[med(group) for group in values]
        metrics[metric]=dict(cohort_medians=medians,J=abs(medians[0]-medians[1]),range=[min(x for g in values for x in g),max(x for g in values for x in g)],reference_medians={label:med(read(d['rows'][index]) for d in normal[label,'ref']) for label in ['A','B','C']})
    summary.append(dict(kind=kind,concurrency=concurrency,decoded_bytes=allrows[0]['decoded_bytes'],sha256=allrows[0]['sha256'],metrics=metrics))
assert sample_count==45000
g15report=dict(status='Normal18-cell two5-runC cohorts and5rotatedABC COMPLETE; full G15 OPEN',measured_requests=sample_count,separate_cold_observations=450,rows=summary,raw_sha256=hashes,scope='All25complete files included,100requests/cell, exact bodyhash and sizes acrossABC, no outbound. Native parser validation separate from transport timing. This subset excludes giant64MiBchunked/128MiBgzip, provider retention/burst, per-adapter origin approval, totaldeadline policy and after-ownership controls. No production limit/default, no speed claim. Peak cgroup is process-lifetime cumulative and is not per-cell live-retention proof.')
target=e/'g15-normal-complete-baseline-summary-v2.json'
assert not target.exists()
target.write_text(json.dumps(g15report,indent=2),encoding='utf-8')
print(json.dumps(dict(g04_profiles=10,g04_full_cells=160,g15_complete_runs=25,g15_measured_requests=sample_count,gates='OPEN; baseline collection complete only')))
