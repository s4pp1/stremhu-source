from pathlib import Path
import hashlib
import json
import statistics

r=Path(__file__).parent
e=r/'evidence'
def med(values):return statistics.median(values)
before=[[json.loads((e/f'cr17b-after-short-v6-before-{s}-{i}.json').read_text()) for i in range(5)] for s in ['a','b']]
after=[[json.loads((e/f'cr17b-after-short-v6-after-{s}-{i}.json').read_text()) for i in range(5)] for s in ['a','b']]
rows=[]
failures=[]
for index in range(12):
    bg=[[d['rows'][index] for d in group] for group in before]
    ag=[[d['rows'][index] for d in group] for group in after]
    allrows=[row for group in bg+ag for row in group]
    assert len({(row['count'],row['kind'],row['concurrency']) for row in allrows})==1
    assert all(len(row['samples_ms'])==100 for row in allrows)
    assert len({tuple(row['payload_hashes']) for row in allrows})==1
    assert len({tuple(row['result_counts']) for row in allrows})==1
    key=dict(count=allrows[0]['count'],kind=allrows[0]['kind'],concurrency=allrows[0]['concurrency'])
    for metric,read,kind in [('p95_ms',lambda row:row['p95_ms'],'http'),('cpu_seconds',lambda row:row['cpu_seconds'],'cpu'),('sql_statements',lambda row:row['sql_statements'],'sql')]+[('memory.'+name,lambda row,name=name:row['memory'][name],'kib' if name=='max_rss_kib' else 'bytes') for name in ['anon_bytes','current_bytes','peak_bytes','max_rss_kib']]:
        b=[med(read(row) for row in group) for group in bg]
        a=[med(read(row) for row in group) for group in ag]
        limit=max(b)+(10 if kind=='http' else 2048 if kind=='kib' else 2097152 if kind=='bytes' else 0)
        if kind=='cpu':limit=max(b)*1.10
        result=dict(**key,metric=metric,before_cohort_medians=b,after_cohort_medians=a,J=abs(b[0]-b[1]),limit=limit,passed=all(value<=limit for value in a))
        rows.append(result)
        if not result['passed']:failures.append(result)
for index in range(4):
    bg=[[d['cold'][index] for d in group] for group in before]
    ag=[[d['cold'][index] for d in group] for group in after]
    assert len({(row['count'],row['user'],row['payload_hash'],row['result_count']) for group in bg+ag for row in group})==1
    b=[med(row['wall_seconds'] for row in group) for group in bg]
    a=[med(row['wall_seconds'] for row in group) for group in ag]
    J=abs(b[0]-b[1])
    limit=max(row['wall_seconds'] for group in bg for row in group)+J
    result=dict(scope='cold',index=index,metric='wall_seconds',before_cohort_medians=b,after_cohort_medians=a,J=J,limit=limit,passed=all(value<=limit for value in a))
    rows.append(result)
    if not result['passed']:failures.append(result)
report=dict(status='PASS' if not failures else 'FAIL',scope='SourceV4/fresh pairedSource2,unchangedV5criteria. Only primary normal12cells and4unprofiledcold controls; NOT packet20 acceptance. Fullprofile,direct/Kodi,refs and ownership tests separate.',rows=rows,failures=failures)
target=e/'cr17b-primary-short-assessment-v6.json'
assert not target.exists()
target.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(status=report['status'],metric_checks=len(rows),failures=failures)))
