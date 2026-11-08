"""Synthetic native streaming profile; policy candidate is fixture-only.

No claim about a native player's buffer/trust behavior is made. The consumer
rate and late-data threshold are explicit, fixed workload properties.
"""
import asyncio
import hashlib
import json
import os
import resource
import socket
import sys
import time
from pathlib import Path

import httpx
import libtorrent

from app.common.async_utils import drain_background_tasks
from app.config import config
from app.modules.relay.schemas import RelaySettingsUpdate
from app.modules.relay.service import RelayService


class ConnectedRequest:
    async def is_disconnected(self):
        return False


def memory():
    counters=dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
    return dict(anon_bytes=int(counters['anon']),file_bytes=int(counters['file']),current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()),peak_bytes=int(Path('/sys/fs/cgroup/memory.peak').read_text()),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


async def main():
    base=os.environ['TEST_BASE_URL']
    if httpx.URL(base).host!='seeder.fixture.invalid':raise RuntimeError('Private seed required')
    variant=os.environ['G01_VARIANT']
    delay=int(os.environ['G01_BLOCK_DELAY_MS'])
    if variant not in ['legacy','hardcap'] or delay not in [2,50]:raise RuntimeError('Unregistered native profile')
    case=json.loads(os.environ['G01_CASE'])
    global_limit,base_limit,stream_count,piece,ram_mib=(case[key] for key in ['global','base','streams','piece_bytes','ram_mib'])
    assert global_limit in [50,100,200] and base_limit in [10,20,50,80]
    assert stream_count in [0,1,4,8] and piece in [256<<10,1<<20,4<<20] and ram_mib in [512,1024,2048]
    assert variant=='legacy'  # Candidate policy is outside this baseline preparation.
    total=32<<20
    rate=4 << 20
    profiles=[]
    for index in range(max(1,stream_count)):
        info={b'name':f'g01-paced-{index}.mkv'.encode(),b'piece length':piece,b'length':total,b'pieces':hashlib.sha1(bytes(piece)).digest()*(total//piece),b'private':1}
        profiles.append((info,hashlib.sha1(libtorrent.bencode(info)).digest()))
    expected=hashlib.sha256()
    for _ in range(total//(1 << 20)):expected.update(bytes(1 << 20))
    expected_digest=expected.hexdigest()
    relay=RelayService()
    priority=None
    samples=[]
    stop_sampling=asyncio.Event()

    async def monitor():
        while not stop_sampling.is_set():
            states=[torrent.torrent_handle.status() for torrent in relay._torrents.values()]
            samples.append(dict(seconds=time.monotonic(),connections=[status.num_connections for status in states],limits=[status.connections_limit for status in states],memory=memory()))
            await asyncio.sleep(.05)

    try:
        config.downloads_dir.mkdir(parents=True,exist_ok=True)
        relay._libtorrent_session.apply_settings({'listen_interfaces':'0.0.0.0:0','allow_multiple_connections_per_ip':True,'enable_upnp':False,'enable_natpmp':False,'enable_dht':False,'enable_lsd':False,'out_enc_policy':int(libtorrent.enc_policy.disabled),'in_enc_policy':int(libtorrent.enc_policy.disabled)})
        relay.update_settings(RelaySettingsUpdate(connections_limit=global_limit,torrent_connections_limit=base_limit))
        if variant=='hardcap':
            def apply(torrent):
                with relay._connection_policy_lock:
                    handle=torrent.torrent_handle
                    target=relay._torrent_connections_limit
                    if handle.is_valid() and (torrent._last_applied_limit!=target or torrent._last_applied_handle is not handle):
                        handle.set_max_connections(target)
                        torrent._last_applied_limit=target
                        torrent._last_applied_handle=handle
            relay.apply_torrent_connection_policy=apply
        async with httpx.AsyncClient(base_url=base,trust_env=False,timeout=30) as client:
            response=await client.post('/control/case',json=dict(torrents=[dict(info_hash=digest.hex(),piece_bytes=piece,total_bytes=total) for _,digest in profiles],peers=100,block_delay_ms=delay))
            response.raise_for_status()
            ports=response.json()['ports']
            address=(await asyncio.get_running_loop().getaddrinfo('seeder.fixture.invalid',ports[0],family=socket.AF_INET,type=socket.SOCK_STREAM))[0][4][0]
            readers=[]
            for index,(info,digest) in enumerate(profiles):
                relay.add_torrent(libtorrent.bencode({b'info':info}))
                torrent=relay._torrents[libtorrent.sha1_hash(digest)]
                torrent.torrent_handle.unset_flags(libtorrent.torrent_flags.paused|libtorrent.torrent_flags.auto_managed)
                file=relay.get_torrent_file(digest.hex(),0)
                stream=None if stream_count==0 else await file.stream(f'g01-paced-play-{index}',f'g01-paced-user-{index}',0,total-1,ConnectedRequest(),raise_errors=True)
                relay.apply_torrent_connection_policy(torrent)
                readers.append((torrent,stream))
            priority=asyncio.create_task(relay.priority_manager_loop())
            # An idle case has one native torrent but no registered stream.
            # No transient stream is created: destroying a registered stream
            # can legitimately prefetch boundary pieces during its250ms grace.
            if stream_count==0:
                assert not any(torrent.has_active_streams for torrent,_ in readers)
                for torrent,_ in readers:relay.apply_torrent_connection_policy(torrent)
            for port in ports:
                for torrent,_ in readers:torrent.torrent_handle.connect_peer((address,port))
            ticker=asyncio.create_task(monitor())
            started=time.perf_counter()
            cpu=time.process_time()

            async def read(torrent,stream):
                began=time.perf_counter()
                first=None
                received=0
                digest=hashlib.sha256()
                late=[]
                waits=[]
                iterator=stream.__aiter__()
                while True:
                    waiting=time.perf_counter()
                    try:chunk=await anext(iterator)
                    except StopAsyncIteration:break
                    now=time.perf_counter()
                    waits.append((now-waiting)*1000)
                    if first is None:first=now
                    else:late.append(max(0,now-(first+received/rate))*1000)
                    digest.update(chunk)
                    received+=len(chunk)
                    await asyncio.sleep(max(0,first+received/rate-time.perf_counter()))
                if received!=total or digest.hexdigest()!=expected_digest:raise RuntimeError('Native paced stream data differs')
                return dict(bytes=received,sha256=digest.hexdigest(),startup_ms=(first-began)*1000,wall_seconds=time.perf_counter()-began,read_samples_ms=waits,late_data_samples_ms=late,late_over_100ms=sum(value>100 for value in late),native_limit=torrent.torrent_handle.status().connections_limit,tracked_limit=torrent._last_applied_limit)

            seek_rows=[]
            try:
                if stream_count==0:
                    # Real ten-second native idle observation, not a busy spin.
                    await asyncio.sleep(10)
                    rows=[]
                else:
                    async with asyncio.timeout(120):rows=await asyncio.gather(*(read(torrent,stream) for torrent,stream in readers))
                    await drain_background_tasks()
                    # At least100 real warmed Range reads/cell. Every range uses
                    # the normal stream and cleanup; 250ms destruction delay is
                    # awaited outside its latency. Cold/partly cold seeks remain
                    # separate work; these must never be labelled uncached seeks.
                    async def seeks(index,torrent):
                        observations=[]
                        file=relay.get_torrent_file(str(torrent.info_hash),0)
                        for seek in range((100+stream_count-1)//stream_count):
                            offset=((seek*104729+index*8191)%(total-(1<<20)))
                            began=time.perf_counter()
                            stream=await file.stream(f'g01-seek-{index}-{seek}',f'g01-user-{index}',offset,offset+(1<<20)-1,ConnectedRequest(),raise_errors=True)
                            relay.apply_torrent_connection_policy(torrent)
                            data=bytearray()
                            async for chunk in stream:data.extend(chunk)
                            elapsed=(time.perf_counter()-began)*1000
                            assert len(data)==1<<20 and not any(data)
                            observations.append(dict(offset=offset,bytes=len(data),wall_ms=elapsed,cache_state='warm-native-pieces-after-full-verified-download'))
                            await drain_background_tasks()
                        return observations
                    async with asyncio.timeout(120):seek_rows=await asyncio.gather(*(seeks(index,torrent) for index,(torrent,_) in enumerate(readers)))
                await drain_background_tasks()
            finally:
                stop_sampling.set()
                await ticker
            stats=(await client.get('/control/stats')).json()
            expected_limit=max(base_limit,50) if stream_count else base_limit
            if stats['errors'] or any(row['native_limit']!=expected_limit or row['tracked_limit']!=expected_limit for row in rows):raise RuntimeError('Native paced stream state differs')
            if stream_count:
                assert sum(len(group) for group in seek_rows)>=100
                assert sum(row['bytes'] for row in rows)==stream_count*total
            for torrent,_ in readers:
                relay.apply_torrent_connection_policy(torrent)
                assert torrent.torrent_handle.status().connections_limit==base_limit
                assert torrent._last_applied_limit==base_limit
            if stream_count==0:assert stats['bytes_sent']==0
            result=dict(fixture='g01-full-parameter-native-warm-seek-v4',is_measurement='--fixture-smoke' not in sys.argv,variant=variant,peer_block_delay_ms=delay,case=case,streams=stream_count,warm_seek_rows=seek_rows,piece_bytes=piece,bytes_per_stream=total,consumer_bytes_per_second=rate,late_data_threshold_ms=100,rows=rows,resource_samples=samples,wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu,seed_stats=stats,scope='Parameterized full432cell legacy fixture; this invocation alone is one case.32MiB/file verified paced4MiB/s; cold startup separate, >=100warm-native Range observations per activecell, not uncached seek. Idle0 has one native torrent/no stream/no payload and10real seconds. Test-only sameIP seed setting, nativeplayer buffer/trust untested; no policy decision or productionchange.')
    finally:
        if priority is not None:
            priority.cancel()
            await asyncio.gather(priority,return_exceptions=True)
        await relay.close_piece_requests()
        await relay.close_native()
    print(json.dumps(result))


asyncio.run(main())
