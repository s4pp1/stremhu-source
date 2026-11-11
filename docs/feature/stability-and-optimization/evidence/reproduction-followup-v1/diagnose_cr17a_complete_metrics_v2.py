"""No acceptance: preserve the stopped assessor, inspect all remaining metrics."""
from pathlib import Path
import hashlib
import json

r=Path(__file__).parent
e=r/'evidence'
source=(r/'assess_cr17a_drain_v2.py').read_text()
registration=json.loads((e/'cr17a-drain-v2-assessor-registration.json').read_text())
assert hashlib.sha256((r/'assess_cr17a_drain_v2.py').read_bytes()).hexdigest()==registration['assessor_sha256']
needle="    assert len({x['sql_statements'] for group in before+after for x in group})==1"
assert source.count(needle)==1
source=source.replace(needle,"    if len({x['sql_statements'] for group in before+after for x in group})!=1: failures.append(dict(scope='SQL invariance diagnostic/'+str(key),status='ORIGINAL ASSERTION FAILED;not waived'))")
source=source.replace('cr17a-drain-final-assessment-v2.json','cr17a-drain-complete-diagnostic-v2.json')
source=source.replace("scope='Cleanup-only conditional-yield v2; not policy packet20 or whole provider ORM ownership acceptance'", "scope='DIAGNOSTIC ONLY: original assessor stopped at exact SQL invariance; all original thresholds kept, assertion failures retained, no acceptance or publication marker'")
exec(compile(source,str(r/'assess_cr17a_drain_v2.py'),'exec'),{'__file__':str(r/'assess_cr17a_drain_v2.py'),'__name__':'__main__'})
