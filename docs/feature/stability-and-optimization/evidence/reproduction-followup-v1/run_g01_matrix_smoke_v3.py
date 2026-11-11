"""Independent pre-measurement wiring of representative full-matrix edges."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys
import time

r=Path(__file__).parent
e=r/'evidence'
cases=[dict(zip(['global','base','streams','piece_bytes','ram_mib'],values)) for values in [(50,10,0,256<<10,512),(50,10,1,256<<10,512),(100,20,4,1<<20,1024),(200,80,8,4<<20,2048),(200,10,8,4<<20,512),(50,80,1,1<<20,1024)]]
protocol=dict(id='g01-matrix-edge-wiring-v3',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cases=cases,scope='Six separate actual native/Range edge wiring cases,NOT benchmark or whole432case matrix. Legacy50 preserved.>=100warmRange observations/activecase,not uncachedseeks. Before measurement run must complete this wiring and separately qualify coldseeks/noise/ABC.',resource='Client2CPU0,1/RAM512,1024,2048MiB percase;private seedCPU15/256MiB,new own labelled local volume eachcase,total<=1GiBsyntheticpayload,volumes retained. Wait until all cold qualification/reference processes finish;no measurement shortened.',fixture_sha256=hashlib.sha256((r/'g01_matrix_native_v3.py').read_bytes()).hexdigest())
target=e/'g01-matrix-edge-wiring-v3-protocol.json'
assert not target.exists()
target.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
deadline=time.monotonic()+14400
while True:
    gate=e/'cr17a-drain-final-assessment-v3.json'
    names=subprocess.check_output(['docker','--context','desktop-linux','ps','--format','{{.Names}}'],text=True).splitlines()
    if gate.exists() and not names:break
    if time.monotonic()>deadline:raise RuntimeError('Cold controls not finished;nativewiring not started')
    time.sleep(1)
context=json.loads(subprocess.check_output(['docker','--context','desktop-linux','context','inspect','desktop-linux'],text=True))[0]
assert context['Endpoints']['docker']['Host'].startswith('npipe://')
volume='cr-g01-freecheck-v2-obva7te6'
details=json.loads(subprocess.check_output(['docker','--context','desktop-linux','volume','inspect',volume],text=True))[0]
assert details['Driver']=='local' and details['Labels']['stremhu.task']=='obva7te6' and not details.get('Options')
image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'
free=int(subprocess.check_output(['docker','--context','desktop-linux','run','--rm','--network','none','--read-only','--cpus','1','--cpuset-cpus','0','--memory','128m','--mount',f'type=volume,source={volume},target=/app/data','--entrypoint','python',image,'-c',"import shutil;print(shutil.disk_usage('/app/data').free)"],text=True))
assert free>=16*(1<<30),'Insufficient test disk budget;no native wiring started'
for index,case in enumerate(cases):
    assert hashlib.sha256((r/'g01_matrix_native_v3.py').read_bytes()).hexdigest()==protocol['fixture_sha256']
    stem=f'g01-matrix-edge-wiring-v3-{index}'
    source=(r/'run_g01_paced_smoke_v1.py').read_text()
    source=source.replace('cr-g01-paced-smoke-obva7te6','cr-'+stem+'-obva7te6').replace('g01-paced-smoke-v1',stem)
    source=source.replace('g01_paced_native_v1.py','g01_matrix_native_v3.py').replace('cr17a-drain-fix-v1-source','cr17a-drain-fix-v2-source')
    source=source.replace("G01_BLOCK_DELAY_MS='50'", "G01_BLOCK_DELAY_MS='2',G01_CASE="+repr(json.dumps(case)))
    source=source.replace("'--env','G01_VARIANT'", "'--env','G01_CASE','--env','G01_VARIANT'")
    source=source.replace("'--memory','1g'", "'--memory',"+repr(str(case['ram_mib'])+'m'))
    source=source.replace("len(data['rows'])==8", "len(data['rows'])=="+str(case['streams']))
    source=source.replace("'2CPU0,1/1GiB'", repr('2CPU0,1/'+str(case['ram_mib'])+'MiB'))
    source=source.replace("'Paced native profile wiring PASS; not fullG01 matrix or measurement.'", repr(stem+' functional PASS; not fullG01 benchmark'))
    child=r/(stem+'-controller.py')
    child.write_text(source,encoding='utf-8')
    print(stem,'starting actual native/Range wiring',flush=True)
    with (e/(stem+'-controller.stdout')).open('w',encoding='utf-8') as out,(e/(stem+'-controller.stderr')).open('w',encoding='utf-8') as err:
        result=subprocess.run([sys.executable,str(child)],stdout=out,stderr=err)
    if result.returncode:raise RuntimeError('Native matrix edge wiring failed;raw retained,no matrix benchmark started')
    d=json.loads((e/(stem+'.json')).read_text())
    assert not d['is_measurement'] and d['case']==case
    if case['streams']:assert sum(len(group) for group in d['warm_seek_rows'])>=100
    print(stem,'saved actual native/Range results',flush=True)
print('Six edge wiring cases complete;fullmatrix/coldseek/noise/ABC gates remain OPEN',flush=True)
