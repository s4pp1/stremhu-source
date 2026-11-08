from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys
import time

r=Path(__file__).parent
e=r/'evidence'
assessor=r/'assess_cr17a_approved_v5.py'
registration=dict(id='cr17a-approved-v5-assessor-registration',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),assessor_sha256=hashlib.sha256(assessor.read_bytes()).hexdigest(),scope='Registered before freshV5samples: userexplicitlyapproved firstcold+40ms,second+10ms,combinedfirsttwo+10ms; pooledrunmedian AND pooledp95.100freshprocesses/Csource,150native-scopeABCrefs. NormalHTTPp95+10ms,CPU+10%,fixedmemory+2MiB and otheroriginal93metrics unchanged. DefaultGCenabled,no forcedcollect/thresholdchange. V1/V2/V3 negatives retained,never relabelled. Same appSourceV2.')
target=e/'cr17a-approved-v5-assessor-registration.json'
assert not target.exists()
target.write_text(json.dumps(registration,indent=2),encoding='utf-8')
required=[f'cr17a-cold-qualified-v5-{label}-{cohort}-{i}-{sample}.json' for label in ['before','after'] for cohort in ['a','b'] for i in range(5) for sample in range(10)]
required += [f'cr17a-cold-qualified-v5-{label}-ref-{i}-{sample}.json' for i in range(5) for label in ['A','B','C'] for sample in range(10)]
deadline=time.monotonic()+14400
count=-1
while True:
    complete=sum((e/name).exists() for name in required)
    if complete//20!=count:
        count=complete//20
        print('Fresh cold qualification cases',complete,'/',len(required),flush=True)
    if complete==len(required):break
    if time.monotonic()>deadline:raise RuntimeError('Cold qualification incomplete;no acceptance')
    time.sleep(5)
assert hashlib.sha256(assessor.read_bytes()).hexdigest()==registration['assessor_sha256']
result=subprocess.run([sys.executable,'-X','utf8',str(assessor)])
raise SystemExit(result.returncode)
