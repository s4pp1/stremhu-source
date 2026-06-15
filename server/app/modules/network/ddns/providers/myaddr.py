import httpx

from app.common.logger import logger
from app.modules.network.ddns.base import BaseDDNSProvider
from app.modules.network.ddns.schemas.internal import DDNSIpUpdate, DDNSTxtUpdate


class MyAddrProvider(BaseDDNSProvider):
    @property
    def id(self) -> str:
        return "myaddr"

    @property
    def name(self) -> str:
        return "MyAddr"

    @property
    def website_url(self) -> str:
        return "https://myaddr.tools"

    async def update(self, payload: DDNSIpUpdate | DDNSTxtUpdate) -> None:
        params = {"key": payload.provider_token}

        if isinstance(payload, DDNSIpUpdate):
            params["ip"] = payload.ip

        if isinstance(payload, DDNSTxtUpdate):
            if payload.clear_txt:
                return

            params["acme_challenge"] = payload.txt

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.website_url}/update", params=params)
                response.raise_for_status()
            if "OK" not in response.text:
                raise ValueError(f"MyAddr DDNS frissítése sikertelen: {response.text}")
        except Exception as e:
            logger.error("MyAddr frissítési hiba: %s", e)
            raise ValueError(f"MyAddr frissítési hiba: {e}") from e
