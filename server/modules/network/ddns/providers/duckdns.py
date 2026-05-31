from common.logger import logger

import httpx
from modules.network.ddns.base import BaseDDNSProvider
from modules.network.ddns.schemas import DDNSIpUpdate, DDNSTxtUpdate

BASE_URL = "https://www.duckdns.org/update"


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

    async def validate(self, host: str, provider_token: str) -> None:
        params = {
            "domains": host,
            "token": provider_token,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{BASE_URL}/update", params=params)
                response.raise_for_status()

            if "OK" not in response.text:
                raise ValueError(
                    f"DuckDNS hitelesítés sikertelen. Válasz: {response.text}"
                )
        except Exception as e:
            logger.error("DuckDNS validációs hiba: %s", e)
            raise ValueError(f"DuckDNS validációs hiba: {e}") from e

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
                response = await client.get(f"{BASE_URL}/update", params=params)
                response.raise_for_status()
            if "OK" not in response.text:
                raise ValueError(f"DuckDNS frissítése sikertelen: {response.text}")
        except Exception as e:
            logger.error("DuckDNS frissítési hiba: %s", e)
            raise ValueError(f"DuckDNS frissítési hiba: {e}") from e
