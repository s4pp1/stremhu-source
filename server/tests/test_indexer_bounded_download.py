import asyncio
import gc
import gzip
import weakref

import httpx
import pytest

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.exceptions import (
    IndexerDefinitionException,
    IndexerResponseTooLargeException,
)
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.indexer_definitions.schemas.internal import AuthSessionError

CHUNK = 4096


class CountingStream(httpx.AsyncByteStream):
    """Body source that records how much the client actually pulled."""

    def __init__(self, data: bytes, gate: asyncio.Event | None = None):
        self.data = data
        self.gate = gate
        self.pulled = 0
        self.closed = False

    async def __aiter__(self):
        for i in range(0, len(self.data), CHUNK):
            if self.gate is not None and i:
                await self.gate.wait()
            self.pulled += 1
            yield self.data[i : i + CHUNK]

    async def aclose(self):
        self.closed = True


async def make_adapter(handler, semaphore: int | None = None):
    adapter = NcoreIndexerDefinition()
    await adapter._client.aclose()
    if semaphore is not None:
        adapter._semaphore = asyncio.Semaphore(semaphore)
    adapter._client = IndexerClient(
        adapter,
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
        # The tracker's own domain for the 26b download host policy.
        base_url="https://fixture.invalid",
    )
    adapter._detect_authentication_error = lambda response: None
    return adapter


@pytest.mark.anyio
@pytest.mark.parametrize("encoding", [None, "gzip"])
async def test_body_within_limit_is_returned_decoded(encoding):
    payload = b"d8:announce" + b"x" * 50_000 + b"e"
    wire = gzip.compress(payload) if encoding else payload
    headers = {"content-encoding": encoding} if encoding else {}

    def handler(request):
        return httpx.Response(200, headers=headers, stream=CountingStream(wire))

    adapter = await make_adapter(handler)
    try:
        response = await adapter._client.get_bounded("https://fixture.invalid/t", max_bytes=len(payload))
        assert response.content == payload
        if encoding:
            # Only the decoded (rebuilt) response gets new encoding/length headers.
            assert "content-encoding" not in response.headers
            assert response.headers["content-length"] == str(len(payload))
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_oversized_identity_body_stops_reading_and_closes_stream():
    stream = CountingStream(b"x" * (64 * CHUNK))

    def handler(request):
        return httpx.Response(200, stream=stream)

    adapter = await make_adapter(handler)
    try:
        with pytest.raises(IndexerResponseTooLargeException):
            await adapter._client.get_bounded("https://fixture.invalid/t", max_bytes=8 * CHUNK)
        assert stream.pulled <= 9
        assert stream.closed
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_declared_oversized_length_is_rejected_before_body_read():
    stream = CountingStream(b"x" * (16 * CHUNK))

    def handler(request):
        return httpx.Response(200, headers={"content-length": str(16 * CHUNK)}, stream=stream)

    adapter = await make_adapter(handler)
    try:
        with pytest.raises(IndexerResponseTooLargeException):
            await adapter._client.get_bounded("https://fixture.invalid/t", max_bytes=CHUNK)
        assert stream.pulled == 0
        assert stream.closed
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_compression_bomb_is_bounded_by_decoded_size():
    decoded = 32 * 1024 * 1024
    wire = gzip.compress(b"\0" * decoded)
    stream = CountingStream(wire)

    def handler(request):
        return httpx.Response(200, headers={"content-encoding": "gzip"}, stream=stream)

    adapter = await make_adapter(handler)
    try:
        with pytest.raises(IndexerResponseTooLargeException):
            await adapter._client.get_bounded("https://fixture.invalid/t", max_bytes=1024 * 1024)
        assert stream.pulled < len(range(0, len(wire), CHUNK))
        assert stream.closed
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_download_torrent_maps_oversize_to_adapter_error(monkeypatch):
    from app.modules.indexer_definitions import base_indexer_definition

    monkeypatch.setattr(base_indexer_definition.config, "indexer_torrent_max_bytes", CHUNK)

    def handler(request):
        return httpx.Response(200, stream=CountingStream(b"x" * (4 * CHUNK)))

    adapter = await make_adapter(handler)
    try:
        with pytest.raises(IndexerDefinitionException) as info:
            await adapter.download_torrent("https://fixture.invalid/t")
        assert "IndexerResponseTooLargeException" in str(info.value)
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_semaphore_is_held_for_the_whole_bounded_body_read():
    gate = asyncio.Event()
    requests = []

    def handler(request):
        requests.append(request.url.path)
        if request.url.path == "/slow":
            return httpx.Response(200, stream=CountingStream(b"x" * (4 * CHUNK), gate=gate))
        return httpx.Response(200, content=b"ok")

    adapter = await make_adapter(handler, semaphore=1)
    try:
        slow = asyncio.create_task(adapter._client.get_bounded("https://fixture.invalid/slow", max_bytes=8 * CHUNK))
        while not requests:
            await asyncio.sleep(0)
        other = asyncio.create_task(adapter._client.get("https://fixture.invalid/other"))
        for _ in range(20):
            await asyncio.sleep(0)
        assert requests == ["/slow"]
        gate.set()
        assert (await asyncio.wait_for(slow, 1)).content == b"x" * (4 * CHUNK)
        assert (await asyncio.wait_for(other, 1)).content == b"ok"
        assert requests == ["/slow", "/other"]
    finally:
        gate.set()
        await adapter.close()


@pytest.mark.anyio
async def test_session_error_on_bounded_download_relogs_once_and_keeps_redirect_history():
    logged_in = False
    login_calls = 0
    seen_history = []

    def handler(request):
        if request.url.path == "/download":
            return httpx.Response(302, headers={"location": "https://cdn.fixture.invalid/file.torrent"})
        body = b"d4:infod4:name1:aee" if logged_in else b"<html>login</html>"
        return httpx.Response(200, stream=CountingStream(body))

    adapter = await make_adapter(handler, semaphore=1)

    def detect(response):
        seen_history.append((len(response.history), str(response.url), str(response.history[0].url) if response.history else None))
        return None if logged_in else AuthSessionError()

    async def login(credential=None):
        nonlocal logged_in, login_calls
        login_calls += 1
        async with adapter._semaphore:
            logged_in = True

    adapter._detect_authentication_error = detect
    adapter.login = login
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(adapter.download_torrent("https://fixture.invalid/download") for _ in range(3))), 1
        )
        assert results == [b"d4:infod4:name1:aee"] * 3
        assert login_calls == 1
        assert seen_history[0] == (1, "https://cdn.fixture.invalid/file.torrent", "https://fixture.invalid/download")
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_identity_body_keeps_the_original_response_and_redirect_history():
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/t"})
        return httpx.Response(200, headers={"content-length": "4", "x-origin": "fixture"}, stream=CountingStream(b"abcd"))

    adapter = await make_adapter(handler)
    try:
        response = await adapter._client.get_bounded("https://fixture.invalid/start", max_bytes=4)
        assert response.content == b"abcd"
        assert response.headers["x-origin"] == "fixture" and response.headers["content-length"] == "4"
        assert [str(item.url) for item in response.history] == ["https://fixture.invalid/start"]
    finally:
        await adapter.close()


@pytest.mark.anyio
@pytest.mark.parametrize("encoding", [None, "gzip"])
async def test_bounded_body_is_released_without_the_cyclic_gc(encoding):
    """cr15a-after-v4: the read response must not wait for the cyclic GC to free its body."""
    payload = b"d8:announce" + b"x" * 50_000 + b"e"
    wire = gzip.compress(payload) if encoding else payload
    headers = {"content-encoding": encoding} if encoding else {}

    def handler(request):
        return httpx.Response(200, headers=headers, stream=CountingStream(wire))

    adapter = await make_adapter(handler)
    gc.collect()
    gc.disable()
    try:
        response = await adapter._client.get_bounded("https://fixture.invalid/t", max_bytes=len(payload))
        assert response.content == payload
        released = weakref.ref(response)
        del response
        assert released() is None
    finally:
        gc.enable()
        await adapter.close()
