import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from app.modules.stremio.cache import StreamCacheState
from app.modules.stremio.schemas import ImdbStreamId, StremioStream
from app.modules.stremio.service import StremioService, invalidate_stream_cache
from app.modules.users.models import UserModel


def streams(name="fixture"):
    return [StremioStream(name=name, description="fixture", url="https://fixture.invalid/stream")]


def test_global_epoch_never_reaccepts_a_pre_reset_revision():
    cache = StreamCacheState(max_user_revisions=2)
    original = cache.revision("user")
    assert cache.put_if_revision("user", "old", original, streams())
    cache.invalidate_all()
    assert cache.revision("user") != original
    assert not cache.put_if_revision("user", "stale", original, streams())
    assert cache.get("old") is None
    assert cache.get("stale") is None
    before_overflow = cache.revision("user")
    for identity in ["one", "two", "three"]:
        cache.invalidate_user(identity)
    assert not cache.put_if_revision("user", "stale", before_overflow, streams())


def test_user_scope_ttl_and_entry_capacity():
    now = [0.0]
    cache = StreamCacheState(clock=lambda: now[0], max_entries=2)
    assert cache.put_if_revision("one", "one", cache.revision("one"), streams("one"))
    assert cache.put_if_revision("two", "two", cache.revision("two"), streams("two"))
    cache.invalidate_user("one")
    assert cache.get("one") is None
    cached = cache.get("two")
    assert cached is not None and cached[0].name == "two"
    now[0] = 60
    assert cache.get("two") is None
    for index in range(3):
        assert cache.put_if_revision("one", str(index), cache.revision("one"), streams(str(index)))
    assert cache.get("0") is None
    cached = cache.get("2")
    assert cached is not None and cached[0].name == "2"


@pytest.mark.parametrize("global_reset", [False, True])
def test_worker_thread_compare_put_rejects_revision_invalidated_before_write(global_reset):
    cache = StreamCacheState()
    revision = cache.revision("user")
    started, write = threading.Event(), threading.Event()

    def finish_fetch():
        started.set()
        assert write.wait(1)
        return cache.put_if_revision("user", "key", revision, streams())

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(finish_fetch)
        assert started.wait(1)
        if global_reset:
            cache.invalidate_all()
        else:
            cache.invalidate_user("user")
        write.set()
        assert result.result(timeout=1) is False
    assert cache.get("key") is None


@pytest.mark.anyio
@pytest.mark.parametrize("global_reset", [False, True])
async def test_new_revision_does_not_join_old_fetch_or_accept_its_result(global_reset):
    invalidate_stream_cache()
    user = UserModel(id="epoch-fixture", username="fixture")
    identity = ImdbStreamId(imdb_id="tt1234567")
    service = StremioService(Mock(), Mock())
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def fetch(user, parsed_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            await release.wait()
            return streams("old")
        return streams("new")

    service._get_streams_uncached = fetch
    old = asyncio.create_task(service.get_streams(user, identity))
    await started.wait()
    try:
        invalidate_stream_cache(None if global_reset else user.id)
        new = await asyncio.wait_for(service.get_streams(user, identity), 1)
        assert new[0].name == "new"
        release.set()
        assert (await old)[0].name == "old"
        assert (await service.get_streams(user, identity))[0].name == "new"
        assert calls == 2
    finally:
        release.set()
        await old
        invalidate_stream_cache()
