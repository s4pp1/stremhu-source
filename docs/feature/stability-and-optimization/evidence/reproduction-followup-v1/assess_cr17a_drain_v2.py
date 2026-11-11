from pathlib import Path
import datetime
import hashlib
import json
import statistics

r=Path(__file__).parent
e=r/'evidence'
if (e/'cr17a-drain-final-assessment-v2.json').exists():
    raise RuntimeError('Refusing final assessment overwrite')
required=[f'cr17a-drain-paired-long-v2-{label}-{i}.json' for i in range(5) for label in ['before','after']]+[f'cr17a-drain-lifecycle-{s}-v2.json' for s in ['a','b']]+[f'cr17a-drain-after-references-v2-{label}-ref-{i}.json' for i in range(5) for label in ['A','B','C']]
missing=[name for name in required if not (e/name).exists()]
if missing:
    print(json.dumps(dict(status='PENDING',missing=len(missing),completed=len(required)-len(missing))))
    raise SystemExit(0)
rows=[]
failures=[]
def compare(scope,metric,before,after,kind='strict',resolution=.000001):
    bm=[statistics.median(values) for values in before]
    am=[statistics.median(values) for values in after]
    baseline=[x for group in before for x in group]
    J=max(abs(bm[0]-bm[1]),resolution)
    b=statistics.median(bm)
    a=statistics.median(am)
    limit=b+10 if kind=='http' else b*1.1 if kind=='cpu' else b+(2048 if kind=='kib' else 2097152) if kind in ['bytes','kib'] else max(baseline)+J
    passed=a<=limit
    row=dict(scope=scope,metric=metric,before_run_medians=bm,after_run_medians=am,before_median=b,after_median=a,effect=a-b,J=J,before_range=[min(baseline),max(baseline)],limit=limit,kind=kind,passed=passed)
    rows.append(row)
    if not passed:failures.append(row)

life_before=[json.loads((e/name).read_text()) for name in ['cr17-lifecycle-after-b-v7.json','cr17-lifecycle-after-c-v7-approved.json']]
life_after=[json.loads((e/f'cr17a-drain-lifecycle-{s}-v2.json').read_text()) for s in ['a','b']]
for data in life_after:
    assert data['is_measurement'] and data['measured_seconds']>=1800 and len(data['rows'])==60
    assert data['final_checkouts']==0 and data['external_http_attempts']==0
    for row in [data['cold'],*data['rows']]:
        assert not row['errors'] and row['worker_finished_at_close'] and not row['shared_tasks_at_close'] and not row['controlled_retainers_at_close']
        assert not row['closed_clients_at_start'] and row['closed_clients_after']==row['active_adapter_count'] and not row['resume_callbacks_after']
        assert row['pool_checked_out_quiescent']==0 and row['python_tasks_quiescent']==1
for concurrency in [1,4,8]:
    before=[[x for x in d['rows'] if x['concurrency']==concurrency] for d in life_before]
    after=[[x for x in d['rows'] if x['concurrency']==concurrency] for d in life_after]
    for metric,kind in [('http_cpu_seconds','cpu'),('heap_bytes_quiescent','bytes'),('heap_bytes_at_close','bytes'),('max_rss_kib','kib'),('startup_seconds','strict'),('shutdown_seconds','strict'),('sql_statements','strict')]:
        compare(f'lifecycle/{concurrency}',metric,[[x[metric] for x in group] for group in before],[[x[metric] for x in group] for group in after],kind)
    for index in [0,1]:
        compare(f'lifecycle/{concurrency}',f'http{index}.p95_ms',[[x['http'][index]['p95_ms'] for x in group] for group in before],[[x['http'][index]['p95_ms'] for x in group] for group in after],'http',.001)
for metric,kind in [('http_cpu_seconds','cpu'),('heap_bytes_quiescent','bytes'),('max_rss_kib','kib'),('startup_seconds','strict'),('shutdown_seconds','strict')]:
    compare('lifecycle/cold',metric,[[d['cold'][metric]] for d in life_before],[[d['cold'][metric]] for d in life_after],kind)

heap_before=[json.loads((e/f'cr17a-drain-paired-long-v2-before-{i}.json').read_text()) for i in range(5)]
heap_after=[json.loads((e/f'cr17a-drain-paired-long-v2-after-{i}.json').read_text()) for i in range(5)]
for data in heap_before+heap_after:
    assert data['profile']['measured_seconds']>=1800 and len(data['rows'])==60 and not data['external_http_attempts']
    assert all(x['tasks_quiescent']==1 and x['pool_checked_out']==0 and x['background_tasks']==0 for x in data['rows'])
for key in sorted({(x['kind'],x['concurrency']) for x in heap_before[0]['rows']}):
    before=[[x for x in d['rows'] if (x['kind'],x['concurrency'])==key] for d in heap_before]
    after=[[x for x in d['rows'] if (x['kind'],x['concurrency'])==key] for d in heap_after]
    assert all(len(group)==10 for group in before+after)
    assert len({tuple(x['payload_hashes']) for group in before+after for x in group})==1
    assert len({tuple(x['result_counts']) for group in before+after for x in group})==1
    assert len({x['sql_statements'] for group in before+after for x in group})==1
    for metric,kind in [('cpu_seconds','cpu'),('p95_ms','http'),('heap_bytes_after_gc','bytes'),('sql_statements','strict'),('loop_lag_p99_ms','strict')]:
        compare('policy-heap/'+str(key),metric,[[x[metric] for x in group] for group in before],[[x[metric] for x in group] for group in after],kind)
    for metric in ['anon_bytes','current_bytes','peak_bytes','file_bytes','max_rss_kib']:
        kind='strict' if metric=='file_bytes' else 'kib' if metric=='max_rss_kib' else 'bytes'
        compare('policy-heap/'+str(key),'memory.'+metric,[[x['memory'][metric] for x in group] for group in before],[[x['memory'][metric] for x in group] for group in after],kind,4096 if metric.endswith('bytes') else 1)
for index in [0,1]:
    before=[[d['cold'][index]['wall_seconds']*1000] for d in heap_before]
    after=[[d['cold'][index]['wall_seconds']*1000] for d in heap_after]
    assert len({d['cold'][index]['payload_hash'] for d in heap_before+heap_after})==1
    compare('policy-heap/cold',f'user{index}.wall_ms',before,after,'http',.001)

short=json.loads((e/'cr17a-drain-http-assessment-v2.json').read_text())
if short['status']!='PASS':failures.append(dict(scope='normalHTTP',status=short['status']))
for i in range(5):
    for label in ['A','B','C']:
        data=json.loads((e/f'cr17a-drain-after-references-v2-{label}-ref-{i}.json').read_text())
        assert len(data['rows'])==12 and not data['external_http_attempts']
        assert all(len(row['samples_ms'])==100 for row in data['rows'])
native=[]
for case in ['4-r0','4-r1','4-r2','4-r3','4-r4','15-r0','32-r0']:
    data=json.loads((e/f'cr17-drain-runtime-v2-{case}.json').read_text())
    assert data['exit_code']==0 and data['worker_finished'] and data['native_resume_saved'] and data['native_resume_roundtrip'] and data['native_reference_released'] and data['pool_checked_out']==0 and data['outbound_http_attempts']==0
    native.append(case)
report=dict(status='PASS' if not failures else 'FAIL',evaluated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Cleanup-only conditional-yield v2; not policy packet20 or whole provider ORM ownership acceptance',protocol=json.loads((e/'cr17a-drain-paired-long-v2-protocol.json').read_text()),rows=rows,failures=failures,normal_http_status=short['status'],native_cases=native,raw_sha256={name:hashlib.sha256((e/name).read_bytes()).hexdigest() for name in required},previous_v1_failed_assessment_sha256=hashlib.sha256((e/'cr17a-drain-final-assessment-v1.json').read_bytes()).hexdigest())
(e/'cr17a-drain-final-assessment-v2.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(status=report['status'],metric_checks=len(rows),failures=[(x.get('scope'),x.get('metric')) for x in failures])))
