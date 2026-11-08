import asyncio

import httpx
import pytest

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.exceptions import IndexerDefinitionException
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.indexer_definitions.schemas.internal import AuthSessionError


@pytest.mark.anyio
@pytest.mark.parametrize("cancelled_waiter", [None, 0, 1])
async def test_relogin_deduplicates_and_survives_either_waiter_cancel(cancelled_waiter):
    adapter = NcoreIndexerDefinition()
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def login(credential=None):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()

    adapter.login = login
    try:
        waiters = [asyncio.create_task(adapter.relogin())]
        await started.wait()
        waiters.extend(asyncio.create_task(adapter.relogin()) for _ in range(4))
        await asyncio.sleep(0)
        if cancelled_waiter is not None:
            waiters[cancelled_waiter].cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiters[cancelled_waiter]
        release.set()
        await asyncio.wait_for(asyncio.gather(*(task for i, task in enumerate(waiters) if i != cancelled_waiter)), 1)
        assert calls == 1
        # A completed wave must not leave a permanently cached login result.
        await adapter.relogin()
        assert calls == 2
    finally:
        release.set()
        await adapter.close()


@pytest.mark.anyio
async def test_relogin_error_reaches_waiters_and_next_wave_retries():
    adapter = NcoreIndexerDefinition()
    started, release = asyncio.Event(), asyncio.Event()
    failing = True
    calls = 0

    async def login(credential=None):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        if failing:
            raise RuntimeError("fixture login failure")

    adapter.login = login
    try:
        owner = asyncio.create_task(adapter.relogin())
        await started.wait()
        joiner = asyncio.create_task(adapter.relogin())
        await asyncio.sleep(0)
        release.set()
        results = await asyncio.gather(owner, joiner, return_exceptions=True)
        assert all(isinstance(result, RuntimeError) for result in results)
        failing = False
        await adapter.relogin()
        assert calls == 2
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_all_cancelled_waiters_late_failure_is_consumed():
    adapter = NcoreIndexerDefinition()
    started, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
    loop = asyncio.get_running_loop()
    previous = loop.get_exception_handler()
    unhandled = []
    loop.set_exception_handler(lambda loop, context: unhandled.append(context))

    async def login(credential=None):
        started.set()
        await release.wait()
        finished.set()
        raise RuntimeError("late fixture failure")

    adapter.login = login
    try:
        owner = asyncio.create_task(adapter.relogin())
        await started.wait()
        joiner = asyncio.create_task(adapter.relogin())
        await asyncio.sleep(0)
        owner.cancel()
        joiner.cancel()
        await asyncio.gather(owner, joiner, return_exceptions=True)
        release.set()
        await asyncio.wait_for(finished.wait(), 1)
        await adapter.close()
        await asyncio.sleep(0)
        assert unhandled == []
    finally:
        release.set()
        await adapter.close()
        loop.set_exception_handler(previous)


@pytest.mark.anyio
async def test_close_awaits_login_cancellation_before_closing_http_client():
    adapter = NcoreIndexerDefinition()
    started, cancelled = asyncio.Event(), asyncio.Event()
    original_close = adapter._client.aclose

    async def login(credential=None):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async def close_client():
        assert cancelled.is_set()
        await original_close()

    adapter.login = login
    adapter._client.aclose = close_client
    owner = asyncio.create_task(adapter.relogin())
    await started.wait()
    await adapter.close()
    result = await asyncio.gather(owner, return_exceptions=True)
    assert isinstance(result[0], asyncio.CancelledError)
    assert adapter._client.is_closed
    with pytest.raises(IndexerDefinitionException):
        await adapter.relogin()


@pytest.mark.anyio
async def test_authorized_retry_releases_single_slot_semaphore_during_login():
    adapter = NcoreIndexerDefinition()
    await adapter._client.aclose()
    adapter._semaphore = asyncio.Semaphore(1)
    logged_in = False
    login_calls = 0

    def respond(request):
        return httpx.Response(200, request=request)

    adapter._client = IndexerClient(adapter, transport=httpx.MockTransport(respond))
    adapter._detect_authentication_error = lambda response: None if logged_in else AuthSessionError()

    async def login(credential=None):
        nonlocal logged_in, login_calls
        login_calls += 1
        # Exercise the same slot used by the real login HTTP request.
        async with adapter._semaphore:
            await asyncio.sleep(0)
            logged_in = True

    adapter.login = login
    try:
        responses = await asyncio.wait_for(asyncio.gather(*(adapter._client.get("https://fixture.invalid") for _ in range(5))), 1)
        assert all(response.status_code == 200 for response in responses)
        assert login_calls == 1
    finally:
        await adapter.close()
