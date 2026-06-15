import httpx

from app.common.logger import logger
from app.modules.network.ddns.base import BaseDDNSProvider
from app.modules.network.ddns.schemas.internal import DDNSIpUpdate, DDNSTxtUpdate


class DuckDnsProvider(BaseDDNSProvider):
    @property
    def id(self) -> str:
        return "duckdns"

    @property
    def name(self) -> str:
        return "DuckDNS"

    @property
    def website_url(self) -> str:
        return "https://www.duckdns.org"

    async def update(self, payload: DDNSIpUpdate | DDNSTxtUpdate) -> None:
        params = {
            "domains": payload.host,
            "token": payload.provider_token,
        }

        if isinstance(payload, DDNSIpUpdate):
            params["ip"] = payload.ip

        if isinstance(payload, DDNSTxtUpdate):
            if payload.clear_txt:
                params["clear"] = "true"

            params["txt"] = payload.txt

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.website_url}/update", params=params)
                response.raise_for_status()
            if "OK" not in response.text:
                raise ValueError(f"DuckDNS frissítése sikertelen: {response.text}")
        except Exception as e:
            logger.error("DuckDNS frissítési hiba: %s", e)
            raise ValueError(f"DuckDNS frissítési hiba: {e}") from e
