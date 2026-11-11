"""Verify final native Python-reference release in an owned worker."""

import asyncio
import collections
import json
import time
from pathlib import Path

import libtorrent


def threads():
    return dict(collections.Counter(path.read_text().strip() for path in Path("/proc/self/task").glob("*/comm")))


async def main():
    baseline=threads()
    holder=[libtorrent.session({"listen_interfaces":"127.0.0.1:0","enable_dht":False,"enable_lsd":False,"enable_upnp":False,"enable_natpmp":False})]
    holder[0].set_alert_notify(lambda:None)
    holder[0].pause()
    created=threads()
    probes=[]
    stop=asyncio.Event()

    async def heartbeat():
        while not stop.is_set():
            due=asyncio.get_running_loop().time()+.001
            await asyncio.sleep(.001)
            probes.append(max(0,asyncio.get_running_loop().time()-due)*1000)

    pulse=asyncio.create_task(heartbeat())
    began=time.perf_counter()
    await asyncio.to_thread(holder.clear)
    elapsed=time.perf_counter()-began
    deadline=asyncio.get_running_loop().time()+5
    while sum(threads().values())>sum(baseline.values())+1 and asyncio.get_running_loop().time()<deadline:
        await asyncio.sleep(.01)
    final=threads()
    stop.set()
    await pulse
    print(json.dumps(dict(fixture="g17-owned-final-native-reference-v1",libtorrent=libtorrent.__version__,baseline_threads=baseline,created_threads=created,final_threads=final,allowed_default_executor_workers=1,holder_empty=not holder,native_threads_released=sum(final.values())<=sum(baseline.values())+1,release_seconds=elapsed,heartbeat_samples=len(probes),heartbeat_max_lag_ms=max(probes,default=0),scope="No torrent, peer, tracker, dotenv, application startup or user data. Native notify replaced with known no-op callable; final session reference cleared in worker. No unsupported close/abort API.")))


asyncio.run(main())
