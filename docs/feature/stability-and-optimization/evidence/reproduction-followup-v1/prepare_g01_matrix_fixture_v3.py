"""Prepare the actual full parameter space and native Range-seek fixture."""
from pathlib import Path
import hashlib
import itertools
import json

r=Path(__file__).parent
source=(r/'g01_paced_native_v1.py').read_text()
assert "piece=4 << 20\n    total=8*piece" in source
source=source.replace("    piece=4 << 20\n    total=8*piece", """    case=json.loads(os.environ['G01_CASE'])
    global_limit,base_limit,stream_count,piece,ram_mib=(case[key] for key in ['global','base','streams','piece_bytes','ram_mib'])
    assert global_limit in [50,100,200] and base_limit in [10,20,50,80]
    assert stream_count in [0,1,4,8] and piece in [256<<10,1<<20,4<<20] and ram_mib in [512,1024,2048]
    assert variant=='legacy'  # Candidate policy is outside this baseline preparation.
    total=32<<20""")
source=source.replace('for index in range(8):','for index in range(max(1,stream_count)):')
source=source.replace("hashlib.sha1(bytes(piece)).digest()*8", "hashlib.sha1(bytes(piece)).digest()*(total//piece)")
source=source.replace('connections_limit=200,torrent_connections_limit=10','connections_limit=global_limit,torrent_connections_limit=base_limit')
source=source.replace("            priority=asyncio.create_task(relay.priority_manager_loop())", """            priority=asyncio.create_task(relay.priority_manager_loop())
            # An idle case has one native torrent but no registered stream.
            # Existing stream generators are closed without starting them;
            # remove their registrations by the real Stream.destroy contract.
            if stream_count==0:
                for torrent,stream in readers:
                    await stream.aclose()
                    for file in torrent.files.values():
                        await asyncio.gather(*(item.destroy() for item in list(file.streams.values())))
                assert not any(torrent.has_active_streams for torrent,_ in readers)
                for torrent,_ in readers:relay.apply_torrent_connection_policy(torrent)""")
source=source.replace("            try:\n                async with asyncio.timeout(120):rows=await asyncio.gather(*(read(torrent,stream) for torrent,stream in readers))", """            seek_rows=[]
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
                    async with asyncio.timeout(120):seek_rows=await asyncio.gather(*(seeks(index,torrent) for index,(torrent,_) in enumerate(readers)))""")
source=source.replace("expected_limit=50 if variant=='legacy' else 10", "expected_limit=max(base_limit,50) if stream_count else base_limit")
source=source.replace("            if sum(len(row['read_samples_ms']) for row in rows)<100:raise RuntimeError('Insufficient native read observations')", """            if stream_count:
                assert sum(len(group) for group in seek_rows)>=100
                assert sum(row['bytes'] for row in rows)==stream_count*total
            for torrent,_ in readers:
                relay.apply_torrent_connection_policy(torrent)
                assert torrent.torrent_handle.status().connections_limit==base_limit
                assert torrent._last_applied_limit==base_limit
            if stream_count==0:assert stats['bytes_sent']==0""")
source=source.replace("fixture='g01-paced-native-focused-v1'", "fixture='g01-full-parameter-native-warm-seek-v3'")
source=source.replace("streams=8,piece_bytes=piece", "case=case,streams=stream_count,warm_seek_rows=seek_rows,piece_bytes=piece")
source=source.replace("scope='Focused local fixture:global200/base10,8streams,4MiBpieces.Cold first piece startup separate;then256MiB verified paced payload with >100read observations per cell. No added simulated player buffer;not native player compatibility or fullG01 matrix. Test-only same-IP setting and hardcap override;production policy unchanged.'", "scope='Parameterized full432cell legacy fixture; this invocation alone is one case.32MiB/file verified paced4MiB/s; cold startup separate, >=100warm-native Range observations per activecell, not uncached seek. Idle0 has one native torrent/no stream/no payload and10real seconds. Test-only sameIP seed setting, nativeplayer buffer/trust untested; no policy decision or productionchange.'")
target=r/'g01_matrix_native_v3.py'
assert not target.exists()
target.write_text(source,encoding='utf-8')
cases=[dict(zip(['global','base','streams','piece_bytes','ram_mib'],values)) for values in itertools.product([50,100,200],[10,20,50,80],[0,1,4,8],[256<<10,1<<20,4<<20],[512,1024,2048])]
assert len(cases)==432 and len({tuple(case.values()) for case in cases})==432
manifest=dict(status='Prepared fixture only; NO native matrix case executed yet, no gate decision',cases=cases,fixture_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),scope='Warm Range seek extension plus full case enumeration. Full cold/uncached seek coverage, noise cohorts, sequential rotatedABC and eventual candidate comparison still required. Runtime smoke must pass before measurements. No positiveG01 claim.')
output=r/'evidence/g01-full-matrix-fixture-preparation-v3.json'
assert not output.exists()
output.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('432case native fixture prepared; unexecuted, not G01 acceptance')
