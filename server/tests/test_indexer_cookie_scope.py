import httpx
import pytest

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.indexer_definitions.schemas.internal import IndexerDefinitionLogin

PERSISTED = {"nick": "synthetic-nick", "pass": "synthetic-pass"}


class Storage:
    def get_credentials(self, indexer_id):
        return IndexerDefinitionLogin(username="u", password="p", cookies=dict(PERSISTED))

    def save_cookies(self, indexer_id, cookies):
        pass


def record(seen):
    def handler(request):
        seen.append((str(request.url), request.headers.get("cookie")))
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": request.url.params["to"]})
        return httpx.Response(200, content=b"ok")

    return handler


async def adapter_with_persisted_cookies(seen):
    adapter = NcoreIndexerDefinition(indexer_account_storage=Storage())
    jar = adapter._client.cookies
    await adapter._client.aclose()
    adapter._client = IndexerClient(adapter, transport=httpx.MockTransport(record(seen)), follow_redirects=True, cookies=jar)
    adapter._detect_authentication_error = lambda response: None
    return adapter


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("target", "sent"),
    [
        ("https://ncore.pro/torrents.php", True),
        ("https://ncore.pro:8443/torrents.php", True),
        ("https://static.ncore.pro/file.torrent", True),
        ("https://cdn.example.invalid/file.torrent", False),
        ("https://ncore.pro.example.invalid/file.torrent", False),
        ("http://ncore.pro/torrents.php", False),
    ],
)
async def test_restored_cookies_only_reach_the_indexer_host_over_https(target, sent):
    seen = []
    adapter = await adapter_with_persisted_cookies(seen)
    try:
        await adapter._client.get(target)
        header = seen[0][1] or ""
        assert ("nick=synthetic-nick" in header) is sent
        assert ("pass=synthetic-pass" in header) is sent
        assert adapter.cookies == PERSISTED
    finally:
        await adapter.close()


@pytest.mark.anyio
async def test_restored_cookies_are_not_forwarded_on_foreign_redirect():
    seen = []
    adapter = await adapter_with_persisted_cookies(seen)
    try:
        await adapter._client.get("https://ncore.pro/redirect", params={"to": "https://cdn.example.invalid/file.torrent"})
        assert "nick=synthetic-nick" in (seen[0][1] or "")
        assert seen[1][0] == "https://cdn.example.invalid/file.torrent"
        assert seen[1][1] is None
    finally:
        await adapter.close()
