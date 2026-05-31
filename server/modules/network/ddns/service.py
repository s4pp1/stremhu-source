import logging

import httpx
from config import config
from modules.network.ddns import discover_dns_providers
from modules.network.ddns.base import BaseDDNSProvider
from modules.network.ddns.schemas import DDNSIpUpdate, DDNSTxtUpdate
from modules.settings.schemas import NetworkConnectionEnum

logger = logging.getLogger(__name__)


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

    def _get_provider(self, provider_id: str) -> BaseDDNSProvider:
        provider = self._providers.get(provider_id)
        if not provider:
            raise ValueError(f"Nem támogatott DDNS szolgáltató: {provider_id}")
        return provider

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

    async def validate(self, provider_id: str, host: str, token: str) -> None:
        provider = self._get_provider(provider_id)
        await provider.validate(host, token)

    async def update(
        self, provider_id: str, payload: DDNSIpUpdate | DDNSTxtUpdate
    ) -> None:
        provider = self._get_provider(provider_id)
        await provider.update(payload)
