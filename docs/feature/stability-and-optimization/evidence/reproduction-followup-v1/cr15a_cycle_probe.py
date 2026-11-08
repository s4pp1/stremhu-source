"""Local diagnostic: which objects end up in cyclic garbage after one download_torrent (MockTransport, identity body)."""
import asyncio, gc, sys
import httpx
import app.config  # noqa: F401
from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition

BODY = b'd8:announce' + b'x' * 1_362_800 + b'e'


class Chunked(httpx.AsyncByteStream):
    async def __aiter__(self):
        for i in range(0, len(BODY), 65536):
            yield BODY[i:i + 65536]

    async def aclose(self):
        pass


def handler(request):
    return httpx.Response(200, headers={'content-length': str(len(BODY))}, stream=Chunked())


async def main():
    adapter = NcoreIndexerDefinition()
    await adapter._client.aclose()
    adapter._client = IndexerClient(adapter, transport=httpx.MockTransport(handler), base_url='http://tracker.fixture.invalid')
    adapter._detect_authentication_error = lambda response: None
    body = await adapter.download_torrent('http://tracker.fixture.invalid/x')  # warm
    del body
    gc.collect()
    gc.set_debug(gc.DEBUG_SAVEALL)
    for _ in range(3):
        body = await adapter.download_torrent('http://tracker.fixture.invalid/x')
        assert len(body) == len(BODY)
        del body
    n = gc.collect()
    garbage = list(gc.garbage)
    gc.garbage.clear()
    gc.set_debug(0)
    types, big = {}, {}
    for o in garbage:
        types[type(o).__qualname__] = types.get(type(o).__qualname__, 0) + 1
        for ref in gc.get_referents(o):
            if isinstance(ref, (bytes, bytearray)) and len(ref) > 65536:
                big[id(ref)] = (len(ref), type(o).__qualname__)
    print(sys.argv[1], 'collected', n, 'large bytes held by garbage', len(big), sorted({v[1] for v in big.values()}))
    print('  types', sorted(types.items(), key=lambda kv: -kv[1])[:25])
    await adapter.close()

asyncio.run(main())
