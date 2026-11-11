"""CR15/b: a korlátos letöltés a redirect közbülső válaszainak törzsét nem olvassa be."""

import httpx
import pytest

from app.modules.indexer_definitions.exceptions import IndexerDefinitionException
from tests.test_indexer_bounded_download import CHUNK, CountingStream, make_adapter

TORRENT = b"d8:announce4:fixte"


@pytest.mark.anyio
async def test_redirect_bodies_are_closed_unread_and_history_is_kept():
    redirect_bodies = []

    def handler(request):
        if request.url.path == "/download":
            stream = CountingStream(b"r" * (256 * CHUNK))
            redirect_bodies.append(stream)
            return httpx.Response(302, headers={"location": "/hop"}, stream=stream)
        if request.url.path == "/hop":
            stream = CountingStream(b"r" * (256 * CHUNK))
            redirect_bodies.append(stream)
            return httpx.Response(302, headers={"location": "https://cdn.fixture.invalid/file.torrent"}, stream=stream)
        return httpx.Response(200, content=TORRENT)

    adapter = await make_adapter(handler)
    try:
        response = await adapter._client.get_bounded("https://fixture.invalid/download", max_bytes=len(TORRENT))
        assert response.content == TORRENT
        assert str(response.url) == "https://cdn.fixture.invalid/file.torrent"
        assert [str(item.url) for item in response.history] == ["https://fixture.invalid/download", "https://fixture.invalid/hop"]
        assert [(body.pulled, body.closed) for body in redirect_bodies] == [(0, True), (0, True)]
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_redirect_loop_stops_after_ten_hops():
    hops = 0

    def handler(request):
        nonlocal hops
        hops += 1
        return httpx.Response(302, headers={"location": f"/loop/{hops}"})

    adapter = await make_adapter(handler)
    try:
        with pytest.raises(httpx.TooManyRedirects):
            await adapter._client.get_bounded("https://fixture.invalid/loop/0", max_bytes=CHUNK)
        assert hops == 11
        with pytest.raises(IndexerDefinitionException):
            await adapter.download_torrent("https://fixture.invalid/loop/0")
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_cookie_set_on_a_redirect_reaches_the_next_hop():
    seen = []

    def handler(request):
        seen.append((request.url.path, request.headers.get("cookie")))
        if request.url.path == "/download":
            return httpx.Response(302, headers={"location": "/file", "set-cookie": "hop=fixture; Path=/"})
        return httpx.Response(200, content=TORRENT)

    adapter = await make_adapter(handler)
    try:
        response = await adapter._client.get_bounded("https://fixture.invalid/download", max_bytes=len(TORRENT))
        assert response.content == TORRENT
        assert seen == [("/download", None), ("/file", "hop=fixture")]
    finally:
        await adapter.close()
