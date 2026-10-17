import httpx

from core.common.logger import logger
from core.config import config
from core.modules.network.ddns import discover_dns_providers
from core.modules.network.ddns.base import BaseDDNSProvider
from core.modules.network.ddns.schemas.internal import DDNSIpUpdate, DDNSTxtUpdate
from core.modules.settings.enums import NetworkConnectionEnum


class DDNSService:
    def __init__(self):
        ddns_provider_classes = discover_dns_providers()
        self._providers = {
            provider_class().id: provider_class()
            for provider_class in ddns_provider_classes
        }
        logger.info(
            "📡 Regisztrált DDNS szolgáltatók: %s", list(self._providers.keys())
        )

    def get_list(self) -> list[BaseDDNSProvider]:
        return list(self._providers.values())

    def get_by_id(self, provider_id: str) -> BaseDDNSProvider:
        provider = self._providers.get(provider_id)
        if not provider:
            raise ValueError(f"Nem támogatott DDNS szolgáltató: {provider_id}")
        return provider

    async def update(
        self, provider_id: str, payload: DDNSIpUpdate | DDNSTxtUpdate
    ) -> None:
        provider = self.get_by_id(provider_id)
        await provider.update(payload)

    async def get_current_ip(self, connection: NetworkConnectionEnum) -> str:
        if connection == NetworkConnectionEnum.LOCAL:
            return config.host_ip
        return await self.get_public_ip()

    async def get_public_ip(self) -> str:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://api.ipify.org")
                response.raise_for_status()
                return response.text.strip()
        except Exception as e:
            logger.error("Nem sikerült lekérdezni a publikus IP-t: %s", e)
            raise
