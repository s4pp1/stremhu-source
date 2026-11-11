"""CR15/b (26b): the bounded download only reaches the tracker's own domain and subdomains, same scheme."""

import httpx
import pytest

from app.modules.indexer_definitions.exceptions import (
    IndexerDefinitionException,
    IndexerDownloadHostNotAllowedException,
)
from tests.test_indexer_bounded_download import make_adapter

TORRENT = b"d8:announce4:fixte"


def recording_handler(seen):
    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": request.url.params["to"]})
        return httpx.Response(200, content=TORRENT)

    return handler


@pytest.mark.anyio
@pytest.mark.parametrize(
    "target",
    ["https://fixture.invalid/t", "https://dl.fixture.invalid/t", "https://fixture.invalid:8443/t", "/relative/t"],
)
async def test_own_domain_subdomain_and_port_are_allowed(target):
    seen = []
    adapter = await make_adapter(recording_handler(seen))
    try:
        assert await adapter.download_torrent(target) == TORRENT
        assert len(seen) == 1
    finally:
        await adapter.close()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "target",
    [
        "https://cdn.example.invalid/t",
        "https://fixture.invalid.example.invalid/t",
        "https://evilfixture.invalid/t",
        "http://fixture.invalid/t",
        "https://127.0.0.1/t",
    ],
)
async def test_foreign_lookalike_downgrade_and_ip_targets_are_never_contacted(target):
    seen = []
    adapter = await make_adapter(recording_handler(seen))
    try:
        with pytest.raises(IndexerDownloadHostNotAllowedException) as caught:
            await adapter._client.get_bounded(target, max_bytes=len(TORRENT))
        assert "?" not in str(caught.value) and "/t" not in str(caught.value)
        with pytest.raises(IndexerDefinitionException):
            await adapter.download_torrent(target)
        assert seen == []
    finally:
        await adapter.close()


@pytest.mark.anyio
@pytest.mark.parametrize("to", ["https://cdn.example.invalid/file.torrent", "http://fixture.invalid/file.torrent"])
async def test_redirect_off_the_tracker_domain_stops_before_the_hop(to):
    seen = []
    adapter = await make_adapter(recording_handler(seen))
    try:
        start = httpx.URL("https://fixture.invalid/redirect", params={"to": to})
        with pytest.raises(IndexerDownloadHostNotAllowedException):
            await adapter._client.get_bounded(start, max_bytes=len(TORRENT))
        assert seen == [str(start)]
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_redirect_to_a_subdomain_is_followed():
    seen = []
    adapter = await make_adapter(recording_handler(seen))
    try:
        target = httpx.URL("https://fixture.invalid/redirect", params={"to": "https://static.fixture.invalid/file.torrent"})
        response = await adapter._client.get_bounded(target, max_bytes=len(TORRENT))
        assert response.content == TORRENT
        assert seen[-1] == "https://static.fixture.invalid/file.torrent"
    finally:
        await adapter.close()
