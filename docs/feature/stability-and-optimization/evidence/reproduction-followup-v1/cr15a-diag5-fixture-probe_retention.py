"""DIAGNOSTIC copy (not gate data): gate order small -> many-files at c1/c4/c8; after each many-files row additionally
memory after gc+3 s and after malloc_trim(0)+3 s, with /proc RssAnon and glibc mallinfo2 (in-use vs free heap)."""
import ctypes
import asyncio
import gc
import hashlib
import json
import os
import resource
import sys
import time
from collections import deque
from pathlib import Path

import httpx
import libtorrent

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.indexer_definitions.schemas.internal import AuthSessionError

SMOKE='--fixture-smoke' in sys.argv
COUNT=4 if SMOKE else 100
EXPECTED=json.loads(Path('/fixture/expected.json').read_text())
BASE=os.environ['TEST_BASE_URL']
if httpx.URL(BASE).host!='tracker.fixture.invalid':raise RuntimeError('Private fixture required')

def memory():
    stat=dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
    return dict(anon_bytes=int(stat['anon']),file_bytes=int(stat['file']),current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()),peak_bytes=int(Path('/sys/fs/cgroup/memory.peak').read_text()),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

class _MI2(ctypes.Structure):
    _fields_=[(n,ctypes.c_size_t) for n in ('arena','ordblks','smblks','hblks','hblkhd','usmblks','fsmblks','uordblks','fordblks','keepcost')]
_libc=ctypes.CDLL('libc.so.6')
_libc.mallinfo2.restype=_MI2
def snapshot():
    rss=[int(l.split()[1])*1024 for l in Path('/proc/self/status').read_text().splitlines() if l.startswith('RssAnon:')][0]
    mi=_libc.mallinfo2()
    return dict(cg_anon=memory()['anon_bytes'],rss_anon=rss,heap_in_use=mi.uordblks,heap_free=mi.fordblks,heap_arena=mi.arena,mmapped=mi.hblkhd)

def percentile(values,fraction):return sorted(values)[int((len(values)-1)*fraction)]

async def main():
    original=httpx.AsyncClient.send
    outbound=0
    async def guarded(client,request,*args,**kwargs):
        nonlocal outbound
        if request.url.host not in {'tracker.fixture.invalid','cdn.other.invalid'}:
            outbound+=1
            raise RuntimeError('External HTTP blocked')
        return await original(client,request,*args,**kwargs)
    httpx.AsyncClient.send=guarded
    rows=[]
    cold=[]
    output=Path('/fixture-output/rows.jsonl')
    if output.exists():raise RuntimeError('Refusing output overwrite')
    try:
        # Giant invalid bodies last; a failed bounded container leaves completed
        # rows on the owned output bind mount, never fabricated timing results.
        for kind in ['small','many-files']:
            for concurrency in [1,4,8]:
                adapter=NcoreIndexerDefinition()
                await adapter._client.aclose()
                adapter._client=IndexerClient(adapter,base_url=BASE,follow_redirects=True,timeout=20,trust_env=False)
                logins=0
                async def login(credential=None):
                    nonlocal logins
                    logins+=1
                    response=await adapter._client.post('/fixture/login',content=b'synthetic')
                    response.raise_for_status()
                adapter.login=login
                adapter._detect_authentication_error=lambda response:AuthSessionError() if response.headers.get('X-Fixture-Auth-Required')=='1' else None
                async def request():
                    began=time.perf_counter_ns()
                    # Harness deadline includes semaphore wait, accommodates
                    # 8x4second drip even on a serialized legacy adapter.
                    async with asyncio.timeout(90):body=await adapter.download_torrent(BASE+'/payload/'+kind)
                    elapsed=(time.perf_counter_ns()-began)/1e6
                    if len(body)!=EXPECTED[kind]['decoded_bytes'] or hashlib.sha256(body).hexdigest()!=EXPECTED[kind]['sha256']:
                        raise RuntimeError('Synthetic decoded body changed')
                    del body
                    return elapsed
                try:
                    cold.append(dict(kind=kind,concurrency=concurrency,wall_ms=await request()))
                    # Distinct warmup; never included in the measured samples.
                    await request()
                    gc.collect()
                    gate=asyncio.Semaphore(concurrency)
                    done=asyncio.Event()
                    samples=deque(maxlen=100)
                    sample_count=0
                    peaks={}
                    async def monitor():
                        nonlocal sample_count
                        while not done.is_set():
                            measured=memory()
                            sample_count+=1
                            samples.append(measured)
                            for key,value in measured.items():peaks[key]=max(peaks.get(key,0),value)
                            await asyncio.sleep(.05)
                    async def measured():
                        async with gate:return await request()
                    ticker=asyncio.create_task(monitor())
                    began=time.perf_counter();cpu=time.process_time()
                    try:values=await asyncio.gather(*(measured() for _ in range(COUNT)))
                    finally:done.set();await ticker
                    row=dict(kind=kind,concurrency=concurrency,samples_ms=values,p50_ms=percentile(values,.5),p95_ms=percentile(values,.95),p99_ms=percentile(values,.99),wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu,memory=memory(),memory_samples=list(samples),memory_sample_count=sample_count,memory_peaks=peaks,decoded_bytes=EXPECTED[kind]['decoded_bytes'],sha256=EXPECTED[kind]['sha256'],native_validation=EXPECTED[kind]['native_state'],native_validation_scope='Exact hash matches separately native-validated wiring body; native parser is not added to the transport timing.',login_calls=logins,max_concurrent=adapter.max_concurrent)
                    if kind=='many-files':
                        ret=dict(immediate=snapshot())
                        gc.collect();await asyncio.sleep(3)
                        ret['settled']=snapshot()
                        _libc.malloc_trim(0);await asyncio.sleep(3)
                        ret['trimmed']=snapshot()
                        row['retention']=ret
                    if logins!=(1 if kind=='login-redirect' else 0):raise RuntimeError('Unexpected auth refresh count')
                    with output.open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
                    rows.append(row)
                    print(json.dumps(dict(kind=kind,concurrency=concurrency,count=len(values),p95_ms=row['p95_ms'])),file=sys.stderr,flush=True)
                finally:await adapter.close()
        async with httpx.AsyncClient(base_url=BASE,trust_env=False) as client:stats=(await client.get('/fixture/stats')).json()
        if stats.get('foreign-cookie-present',0) or outbound:raise RuntimeError('Cookie or outbound boundary violated')
    finally:httpx.AsyncClient.send=original
    print(json.dumps(dict(fixture='g15-normal-download-transport-baseline-v2',native_version=libtorrent.version,is_measurement=not SMOKE,rows=rows,cold=cold,external_http_attempts=outbound,server_stats=stats,scope='Actual IndexerClient semaphore/auth/relogin/redirect/decoded body. No native parse overhead in timed call. PrivateHTTP only;TLS origin,admission,overall-deadline,cancellation and provider result-retention gates remain separate. No production policy selected.')))

asyncio.run(main())
