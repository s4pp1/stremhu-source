from pathlib import Path
import json
import subprocess

r=Path(__file__).parent
code="import json,urllib.request;d=json.load(urllib.request.urlopen('http://127.0.0.1:8080/fixture/ready',timeout=2));print(json.dumps({'encoded_bytes_per_full_gzip_body':d['gzip_raw_bytes'],'decoded_bytes_per_full_gzip_body':d['gzip_decoded_bytes']}))"
result=subprocess.run(['docker','--context','desktop-linux','exec','cr-g15-gzip-reference-v3-obva7te6-server','python','-c',code],check=True,capture_output=True,text=True)
d=json.loads(result.stdout)
assert d['decoded_bytes_per_full_gzip_body']==128<<20 and d['encoded_bytes_per_full_gzip_body']<1<<20
d['scope']='Exact private server fixture envelope per fullbody. This is not total transferred wirebytes for an OOM/incomplete response; receivedrequest counts are recorded separately. No production size policy.'
target=r/'evidence/g15-gzip-fixture-envelope-v3.json'
assert not target.exists()
target.write_text(json.dumps(d,indent=2),encoding='utf-8')
print(json.dumps(d))
