"""Composite requalification; original stopped/negative V2 is never overwritten."""
from pathlib import Path
import datetime
import hashlib
import json
import statistics

r=Path(__file__).parent
e=r/'evidence'
output=e/'cr17a-drain-final-assessment-v3.json'
assert not output.exists()
registration=json.loads((e/'cr17a-composite-v3-assessor-registration.json').read_text())
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==registration['assessor_sha256']
required=[f'cr17a-cold-focus-v3-{label}-{cohort}-{i}-{sample}.json' for label in ['before','after'] for cohort in ['a','b'] for i in range(5) for sample in range(10)]
required += [f'cr17a-cold-reference-v4-{label}-ref-{i}-{sample}.json' for i in range(5) for label in ['A','B','C'] for sample in range(10)]
if not all((e/name).exists() for name in required):
    print('PENDING fresh cold qualification/reference cases')
    raise SystemExit(0)
diagnostic=json.loads((e/'cr17a-drain-complete-diagnostic-v2.json').read_text())
assert diagnostic['status']=='FAIL' and len(diagnostic['rows'])==94
expected={('policy-heap/cold','user0.wall_ms')}
actual={(row['scope'],row['metric']) for row in diagnostic['rows'] if not row['passed']}
assert actual==expected
assert len(diagnostic['failures'])==4
assert sum(row['scope'].startswith('SQL invariance diagnostic/') for row in diagnostic['failures'])==3
# All retained steady-state/lifecycle/cold-other metrics retain exact V2 limits.
sql={}
for label in ['before','after']:
    name=f'cr17a-cache-SQL-state-diagnostic-v5-{label}.json'
    d=json.loads((e/name).read_text())
    assert not d['is_measurement'] and len(d['rows'])==9
    for row in d['rows']:
        assert row['stage_formula_residual']==0
        obs=row['cache_observations']
        assert obs['put']==(0 if row['state']=='warm' else 2)
        assert row['sql_statements']==100+7*obs['put']+2*obs['provider']+row['touch_updates']
    sql[label]=d
assert [row['payload_hashes'] for row in sql['before']['rows']]==[row['payload_hashes'] for row in sql['after']['rows']]
assert [row['result_counts'] for row in sql['before']['rows']]==[row['result_counts'] for row in sql['after']['rows']]
rows=[]
failures=[]
def percentile(values,p):return sorted(values)[int((len(values)-1)*p)]
for user in [0,1]:
    groups={}
    all_values={}
    all_sql={}
    payloads=set()
    for label in ['before','after']:
        groups[label]=[]
        all_values[label]=[]
        all_sql[label]=[]
        for cohort in ['a','b']:
            for i in range(5):
                group=[]
                for sample in range(10):
                    name=f'cr17a-cold-focus-v3-{label}-{cohort}-{i}-{sample}.json'
                    d=json.loads((e/name).read_text())
                    assert d['label']==label and len(d['cold'])==2 and not d['rows'] and not d['external_http_attempts']
                    row=d['cold'][user]
                    assert row['user']==user and row['count']==100
                    group.append(row['wall_seconds']*1000)
                    all_sql[label].append(row['sql_statements'])
                    payloads.add((row['payload_hash'],row['result_count']))
                groups[label].append(group)
                all_values[label].extend(group)
    assert len(payloads)==1 and set(all_sql['before'])==set(all_sql['after']) and len(set(all_sql['before']))==1
    for metric,read in [('pooled-run-median',lambda label:statistics.median(statistics.median(group) for group in groups[label])),('pooled-p95',lambda label:percentile(all_values[label],.95))]:
        before,after=read('before'),read('after')
        result=dict(user=user,metric=metric,before_ms=before,after_ms=after,effect_ms=after-before,limit_ms=before+10,passed=after<=before+10)
        rows.append(result)
        if not result['passed']:failures.append(result)
    rows.append(dict(user=user,metric='noise-context',before_run_medians=[statistics.median(g) for g in groups['before']],after_run_medians=[statistics.median(g) for g in groups['after']],before_range=[min(all_values['before']),max(all_values['before'])],after_range=[min(all_values['after']),max(all_values['after'])],samples_per_source=100))
for i in range(5):
    for label in ['A','B','C']:
        for sample in range(10):
            d=json.loads((e/f'cr17a-cold-reference-v4-{label}-ref-{i}-{sample}.json').read_text())
            assert len(d['cold'])==2 and not d['external_http_attempts'] and not d['rows']
            assert 'native_search_db_scope' in d and 'native_auth_db_scope' in d
short=json.loads((e/'cr17a-drain-http-assessment-v2.json').read_text())
assert short['status']=='PASS'
report=dict(status='PASS' if not failures else 'FAIL',evaluated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Cleanup-only conditional-yield SourceV2 requalified by separately preregistered cold control and cache-state SQL diagnostic; not CR17/b acceptance',retained_v2_metric_checks=94,retained_v2_passed=93,retained_negative_cold_metric=next(row for row in diagnostic['rows'] if not row['passed']),original_assessor_outcome='Stopped at impossible exact SQL invariant, also observed within unchanged baseline; original script and stderr preserved. Supplementary diagnostic retains original failures and thresholds.',sql_resolution='Controlled1800 API calls across9cache states/source: same auth cost100 +7per-user refill +2actual shared-provider run +counted stale-touch UPDATE. Residual0 on both sources; same payload/count. TTL expiry and variable provider dedup explain varying totals; no production clock/policy change.',cold_rows=rows,failures=failures,native_cases=diagnostic['native_cases'],normal_http_status=short['status'],raw_sha256={name:hashlib.sha256((e/name).read_bytes()).hexdigest() for name in required},earlier_diagnostic_sha256=hashlib.sha256((e/'cr17a-drain-complete-diagnostic-v2.json').read_bytes()).hexdigest(),assessor_registration=registration)
output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(status=report['status'],cold_rows=rows,failures=failures)))
