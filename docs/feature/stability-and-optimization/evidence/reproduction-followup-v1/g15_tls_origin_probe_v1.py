"""Real verified fixtureTLS; this does not test native player trust."""
import asyncio
import hashlib
import json
import os
import ssl

import httpx

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.indexer_definitions.schemas.internal import IndexerDefinitionLogin

BASE=os.environ['TEST_BASE_URL']
assert BASE=='https://tracker.fixture.invalid:8443'

class Storage:
    def get_credentials(self,indexer_id):return IndexerDefinitionLogin(username='synthetic',password='synthetic',cookies={'fixture-session':'valid'})
    def save_cookies(self,*args):pass

class Adapter(NcoreIndexerDefinition):
    @property
    def url(self):return BASE

async def main():
    context=ssl.create_default_context(cafile='/fixture/pki/cert.pem')
    assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
    rows=[]
    async with httpx.AsyncClient(base_url=BASE,verify=context,trust_env=False) as observer:
        for mode in ['fresh-host','fresh-wide','persisted']:
            for target in ['relative','same-origin','other-port','subdomain','other-host','downgrade']:
                adapter=Adapter(Storage() if mode=='persisted' else None)
                initial=adapter._client.cookies
                await adapter._client.aclose()
                adapter._client=IndexerClient(adapter,base_url=BASE,follow_redirects=True,timeout=20,trust_env=False,verify=context,cookies=initial)
                adapter._detect_authentication_error=lambda response:None
                case=str(len(rows))
                try:
                    if mode!='persisted':await adapter._client.get('/set-host' if mode=='fresh-host' else '/set-wide')
                    body=await adapter.download_torrent(BASE+'/redirect/'+target+'?case='+case)
                    assert len(body)==82073
                    stats=(await observer.get('/stats')).json()[case]
                    assert stats['payload_requests']==1
                    rows.append(dict(mode=mode,target=target,cookie_present_count=stats['cookie_present'],target_origin=stats['target_origins'][0],decoded_bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),tls_hostname_verification=True))
                finally:await adapter.close()
    print(json.dumps(dict(fixture='g15-verified-fixtureTLS-origin-cookies-v1',is_measurement=False,rows=rows,scope='Actual IndexerClient/redirect with ephemeral fixtureCA trusted only by this HTTPX SSLContext,hostname verification enabled.18functional cases,synthetic cookies only,presencecounts not values. Not native Stremio/Nuvio trust,G06,productionallowlist or publicSSRF proof.')))

asyncio.run(main())
