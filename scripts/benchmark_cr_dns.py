"""Real DNS propagation loop with a local 30ms resolver fixture, no DNS I/O."""

import asyncio
import json
import statistics
import time
from types import SimpleNamespace

from app.modules.network.ssl import service as ssl_module


class Resolver:
    def __init__(self, **kwargs):
        pass

    def resolve(self, *args, **kwargs):
        time.sleep(0.03)
        return [SimpleNamespace(strings=[b"fixture-txt"])]


async def async_txt(host):
    await asyncio.sleep(0.03)
    return ["fixture-txt"]


if hasattr(ssl_module, "resolve_txt_async"):
    ssl_module.resolve_txt_async = async_txt
else:
    ssl_module.dns.resolver.Resolver = Resolver


async def main():
    rows = []
    loop = asyncio.get_running_loop()
    for concurrency in (1, 4, 8):
        for _ in range(5):
            assert await ssl_module.wait_for_dns_propagation("fixture.invalid", "fixture-txt")
        gate = asyncio.Semaphore(concurrency)
        samples, lags = [], []

        async def request():
            async with gate:
                probe = loop.create_future()
                due = loop.time() + 0.001
                loop.call_later(0.001, lambda:probe.set_result(max(0, loop.time()-due)*1000))
                start = time.perf_counter_ns()
                assert await ssl_module.wait_for_dns_propagation("fixture.invalid", "fixture-txt")
                samples.append((time.perf_counter_ns()-start)/1e6)
            lags.append(await probe)

        cpu = time.process_time()
        await asyncio.gather(*(request() for _ in range(100)))
        ordered, lag_ordered = sorted(samples), sorted(lags)
        rows.append(dict(workload="dns-propagation-one-local-txt-lookup", concurrency=concurrency, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[94], p99_ms=ordered[98], loop_lag_samples_ms=lags, loop_lag_p99_ms=lag_ordered[98], cpu_seconds=time.process_time()-cpu, errors=[]))
    print(json.dumps(dict(fixture="dns-local-30ms-resolver-heartbeat-v1", external_network=False, rows=rows)))


asyncio.run(main())
