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

    @property
    def domain_regex(self) -> str:
        return r"^[a-zA-Z0-9-]+\.myaddr\.(tools|dev|io)$"

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
        except httpx.HTTPError as e:
            logger.error("MyAddr hálózati hiba: %s", e)
            raise RuntimeError(f"MyAddr hálózati hiba: {e}") from e

        if "OK" not in response.text:
            logger.error("MyAddr API hiba: %s", response.text)
            raise RuntimeError(f"MyAddr DDNS frissítése sikertelen: {response.text}")
