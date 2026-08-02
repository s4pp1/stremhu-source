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

    @property
    def domain_regex(self) -> str:
        return r"^[a-zA-Z0-9-]+\.duckdns\.org$"

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
        except httpx.HTTPError as e:
            logger.error("DuckDNS hálózati hiba: %s", e)
            raise RuntimeError(f"DuckDNS hálózati hiba: {e}") from e

        if "OK" not in response.text:
            logger.error("DuckDNS API hiba: %s", response.text)
            raise RuntimeError(f"DuckDNS frissítése sikertelen: {response.text}")
