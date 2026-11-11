import httpx

from app.common.log_safety import network_error_fields
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
            summary = network_error_fields(e)
            logger.error("provider=duckdns operation=update %s", summary)
            raise RuntimeError(f"DuckDNS hálózati hiba ({summary.kind}, status={summary.status_code})") from None

        if "OK" not in response.text:
            logger.error("provider=duckdns operation=update invalid-response status=%s", response.status_code)
            raise RuntimeError("DuckDNS frissítése sikertelen: érvénytelen szolgáltatói válasz.")
