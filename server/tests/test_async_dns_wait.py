import asyncio
from types import SimpleNamespace

import dns.resolver
import pytest

from app.modules.network.ssl import service as ssl_module


@pytest.mark.anyio
async def test_async_txt_wrapper_keeps_resolvers_and_txt_segments(monkeypatch):
    instances = []

    class Resolver:
        def __init__(self, *, configure):
            assert configure is False
            self.nameservers = []
            instances.append(self)

        async def resolve(self, host, record_type):
            assert host == "_acme-challenge.fixture.invalid"
            assert record_type == "TXT"
            await asyncio.sleep(0)
            return [SimpleNamespace(strings=[b"first", b"second"]), SimpleNamespace(strings=[b"complete"])]

    monkeypatch.setattr(ssl_module.dns.asyncresolver, "Resolver", Resolver)
    assert await ssl_module.resolve_txt_async("_acme-challenge.fixture.invalid") == ["first", "second", "complete"]
    assert instances[0].nameservers == ["1.1.1.1", "8.8.8.8"]


@pytest.mark.anyio
async def test_retry_noanswer_and_success_use_one_monotonic_deadline(monkeypatch):
    clock = [0.0]
    responses = iter([dns.resolver.NoAnswer(), [], ["expected"]])
    sleeps = []

    async def resolve(host):
        clock[0] += 1
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    async def sleep(delay):
        sleeps.append(delay)
        clock[0] += delay
        await asyncio.sleep(0)

    monkeypatch.setattr(ssl_module, "resolve_txt_async", resolve)
    assert await ssl_module.wait_for_dns_propagation("fixture.invalid", "expected", timeout=10, delay=3, clock=lambda:clock[0], sleep=sleep)
    assert clock[0] == 9
    assert sleeps == [3, 3]


@pytest.mark.anyio
async def test_sleep_is_clamped_and_no_lookup_starts_after_deadline(monkeypatch):
    clock, sleeps, calls = [0.0], [], []

    async def resolve(host):
        calls.append(host)
        raise dns.resolver.NXDOMAIN()

    async def sleep(delay):
        sleeps.append(delay)
        clock[0] += delay

    monkeypatch.setattr(ssl_module, "resolve_txt_async", resolve)
    with pytest.raises(TimeoutError, match="DNS rekord"):
        await ssl_module.wait_for_dns_propagation("fixture.invalid", "expected", timeout=2, delay=10, clock=lambda:clock[0], sleep=sleep)
    assert sleeps == [2]
    assert calls == ["_acme-challenge.fixture.invalid"]


@pytest.mark.anyio
async def test_answer_at_deadline_is_not_accepted(monkeypatch):
    clock = [0.0]

    async def resolve(host):
        clock[0] = 5
        return ["expected"]

    monkeypatch.setattr(ssl_module, "resolve_txt_async", resolve)
    with pytest.raises(TimeoutError):
        await ssl_module.wait_for_dns_propagation("fixture.invalid", "expected", timeout=5, clock=lambda:clock[0])


@pytest.mark.anyio
async def test_lookup_deadline_and_cancel_wait_for_async_resolver_cleanup(monkeypatch):
    started, finished = asyncio.Event(), asyncio.Event()

    async def resolve(host):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()

    monkeypatch.setattr(ssl_module, "resolve_txt_async", resolve)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(ssl_module.wait_for_dns_propagation("fixture.invalid", "expected", timeout=0.02), 0.5)
    assert finished.is_set()
    started.clear()
    finished.clear()
    task = asyncio.create_task(ssl_module.wait_for_dns_propagation("fixture.invalid", "expected"))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished.is_set()
