from pathlib import Path
from collections import Counter
import hashlib
import json

r=Path(__file__).parent
e=r/'evidence'
registration=json.loads((e/'cr17a-drain-v2-assessor-registration.json').read_text())
assert hashlib.sha256((r/'assess_cr17a_drain_v2.py').read_bytes()).hexdigest()==registration['assessor_sha256']
rows=[]
for i in range(5):
    for label in ['before','after']:
        name=f'cr17a-drain-paired-long-v2-{label}-{i}.json'
        d=json.loads((e/name).read_text())
        bykey={}
        for row in d['rows']:
            key=(row['kind'],row['concurrency'])
            bykey.setdefault(key,[]).append(row['sql_statements'])
        rows.append(dict(label=label,pair=i,counts={str(k):dict(Counter(v)) for k,v in bykey.items()},raw_sha256=hashlib.sha256((e/name).read_bytes()).hexdigest()))
report=dict(status='Original immutable assessor stopped at exact SQL invariance assertion; NOT PASS', rows=rows, assessor_sha256=registration['assessor_sha256'])
(e/'cr17a-drain-sql-invariant-diagnostic-v2.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
