import pathlib,subprocess,os,time,json,hashlib
r=pathlib.Path(__file__).parent;repo=pathlib.Path.cwd();e=r/'evidence';f=r/'g04-baseline-v1'
protocol=json.loads((e/'g04-baseline-protocol-v1.json').read_text())
for name,expected in protocol['fixture_hashes'].items():
 if hashlib.sha256((f/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('Fixture changed')
def call(*args,**kw):return subprocess.run(['docker','--context','desktop-linux',*args],check=True,**kw)
context=json.loads(call('context','inspect','desktop-linux',capture_output=True,text=True).stdout)[0]
if not context['Endpoints']['docker']['Host'].startswith('npipe://'):raise RuntimeError('Not local Docker Desktop')
network='cr-g04-baseline-obva7te6';server=None
call('network','create','--internal','--label','stremhu.task=obva7te6',network,capture_output=True)
try:
 server=call('run','--detach','--rm','--name',network+'-server','--label','stremhu.task=obva7te6','--network',network,'--network-alias','g04.fixture.invalid','--read-only','--cpus','1','--cpuset-cpus','14','--memory','512m','--tmpfs','/tmp','--mount',f'type=bind,source={f/"server.cjs"},target=/fixture/server.cjs,readonly','--entrypoint','node',protocol['profile_image'],'/fixture/server.cjs',capture_output=True,text=True).stdout.strip()
 deadline=time.monotonic()+30
 while True:
  p=subprocess.run(['docker','--context','desktop-linux','exec',server,'node','-e',"fetch('http://127.0.0.1:8080/fixture/ready').then(r=>r.json()).then(x=>process.exit(x.ready?0:1)).catch(()=>process.exit(1))"],capture_output=True)
  if p.returncode==0:break
  if time.monotonic()>deadline:raise RuntimeError('Profiling fixture not ready')
  time.sleep(.1)
 env=os.environ.copy();env['TEST_BASE_URL']='http://g04.fixture.invalid:8080/__cr_g04__/index.html'
 order=[('before-a',0,False),('before-b',0,False),('heap-a',0,True),('heap-b',0,True)]+[(s,i,False) for i in range(1,5) for s in ['before-a','before-b']]
 for series,repetition,heap in order:
  stem=f'g04-{series}-{repetition}-v1';target=e/(stem+'.json');name='cr-'+stem+'-obva7te6';vol=name+'-output'
  if target.exists():raise RuntimeError('Refusing evidence overwrite')
  call('volume','create','--driver','local','--label','stremhu.cr-task=obva7te6','--label','stremhu.disposable=true',vol,capture_output=True)
  metadata=json.loads(call('volume','inspect',vol,capture_output=True,text=True).stdout)[0]
  if metadata['Driver']!='local' or metadata['Labels'].get('stremhu.cr-task')!='obva7te6':raise RuntimeError('Unknown output volume')
  cmd=['run','--name',name,'--label','stremhu.task=obva7te6','--init','--network',network,'--read-only','--cpus','2','--cpuset-cpus','12,13','--memory','2g','--shm-size','512m','--tmpfs','/tmp','--env','TEST_BASE_URL','--mount',f'type=bind,source={f/"probe.cjs"},target=/fixture/probe.cjs,readonly','--mount',f'type=volume,source={vol},target=/fixture-output','--entrypoint','node',protocol['browser_image'],'/fixture/probe.cjs']
  if heap:cmd+=['--heap']
  print(stem,'starting full1815second heap' if heap else 'starting16x300real second cells',flush=True)
  try:
   with (e/(stem+'.stdout')).open('w',encoding='utf-8') as out,(e/(stem+'.stderr')).open('w',encoding='utf-8') as err:call(*cmd,stdout=out,stderr=err,env=env)
   if heap:call('cp',name+':/fixture-output/g04-final.heapsnapshot',str(e/(stem+'.heapsnapshot')),capture_output=True)
   d=json.loads((e/(stem+'.stdout')).read_text())
   if not d['is_measurement'] or len(d['rows'])!=(1 if heap else 16) or any(row['errors'] or row['elapsed_ms']<(1815000 if heap else 300000) or row['warmupRequests']<3 for row in d['rows']):raise RuntimeError('Incomplete profile; raw results retained')
   if heap and d['rows'][0]['navigations']!=50:raise RuntimeError('Incomplete navigation matrix')
   d.update(profile_image=protocol['profile_image'],browser_image=protocol['browser_image'],source=protocol['client_source'],resources=protocol['resource'],fixture_hashes=protocol['fixture_hashes'],series=series,repetition=repetition)
   target.write_text(json.dumps(d),encoding='utf-8');print(stem,'saved; errors0',flush=True)
  finally:
   state=json.loads(call('inspect',name,capture_output=True,text=True).stdout)[0]['State']
   if state['Running']:call('stop','--time','15',name,capture_output=True)
   call('rm',name,capture_output=True)
 print('All unchanged baseline profiles saved; G04 decision still requires analysis.',flush=True)
finally:
 if server is not None:call('stop','--time','5',server,capture_output=True)
 call('network','rm',network,capture_output=True)
