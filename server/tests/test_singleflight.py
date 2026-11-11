import asyncio

import pytest

from app.common.singleflight import Singleflight


@pytest.mark.anyio
async def test_singleflight_deduplicates_concurrent_calls():
    sf: Singleflight[str] = Singleflight()
    call_count = 0

    async def worker() -> str:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return "result"

    task1 = asyncio.create_task(sf.run("k1", worker))
    task2 = asyncio.create_task(sf.run("k1", worker))

    r1, r2 = await asyncio.gather(task1, task2)
    assert r1 == "result"
    assert r2 == "result"
    assert call_count == 1
    assert not sf.is_running("k1")


@pytest.mark.anyio
async def test_singleflight_waiter_cancellation_does_not_abort_shared_task():
    sf: Singleflight[str] = Singleflight()
    call_count = 0

    async def worker() -> str:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.08)
        return "success"

    # Létrehozó (task1) és csatlakozó (task2)
    task1 = asyncio.create_task(sf.run("k1", worker))
    await asyncio.sleep(0.01)
    task2 = asyncio.create_task(sf.run("k1", worker))

    # Lemondjuk a létrehozót (kliens disconnect)
    task1.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task1

    # A csatlakozó ennek ellenére sikeresen megkapja az eredményt!
    res2 = await task2
    assert res2 == "success"
    assert call_count == 1
    assert not sf.is_running("k1")


@pytest.mark.anyio
async def test_singleflight_joiner_cancellation_does_not_abort_creator():
    sf: Singleflight[str] = Singleflight()
    call_count = 0

    async def worker() -> str:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.08)
        return "success"

    task1 = asyncio.create_task(sf.run("k1", worker))
    await asyncio.sleep(0.01)
    task2 = asyncio.create_task(sf.run("k1", worker))

    # Most a csatlakozót mondjuk le
    task2.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task2

    # A létrehozó sikeresen befejezi
    res1 = await task1
    assert res1 == "success"
    assert call_count == 1


@pytest.mark.anyio
async def test_singleflight_all_waiters_cancelled_cleans_up_safely():
    sf: Singleflight[str] = Singleflight()

    async def worker() -> str:
        await asyncio.sleep(0.04)
        return "done"

    task1 = asyncio.create_task(sf.run("k1", worker))
    task2 = asyncio.create_task(sf.run("k1", worker))
    await asyncio.sleep(0.01)

    task1.cancel()
    task2.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task1
    with pytest.raises(asyncio.CancelledError):
        await task2

    # Várjuk meg a háttértask befejeződését
    await asyncio.sleep(0.06)
    assert not sf.is_running("k1")


@pytest.mark.anyio
async def test_singleflight_error_propagates_and_resets():
    sf: Singleflight[str] = Singleflight()
    should_fail = True

    async def worker() -> str:
        if should_fail:
            raise ValueError("failure")
        return "recovered"

    with pytest.raises(ValueError, match="failure"):
        await sf.run("k1", worker)

    assert not sf.is_running("k1")

    # Új kérés új próbálkozást indít és sikerülhet
    should_fail = False
    res = await sf.run("k1", worker)
    assert res == "recovered"


@pytest.mark.anyio
async def test_singleflight_different_keys_run_in_parallel():
    sf: Singleflight[str] = Singleflight()

    async def worker(val: str) -> str:
        await asyncio.sleep(0.02)
        return val

    t1 = asyncio.create_task(sf.run("a", lambda: worker("res_a")))
    t2 = asyncio.create_task(sf.run("b", lambda: worker("res_b")))

    r1, r2 = await asyncio.gather(t1, t2)
    assert r1 == "res_a"
    assert r2 == "res_b"
