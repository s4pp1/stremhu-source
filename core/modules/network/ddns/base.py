from abc import ABC, abstractmethod

from core.modules.network.ddns.schemas.internal import DDNSIpUpdate, DDNSTxtUpdate


class BaseDDNSProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """A szolgáltató egyedi string azonosítója (pl. 'duckdns', 'myaddr')"""

    @property
    @abstractmethod
    def name(self) -> str:
        """A szolgáltató neve (pl. 'DuckDNS', 'MyAddr')"""

    @property
    @abstractmethod
    def website_url(self) -> str:
        """A szolgáltató weboldala (pl. 'https://www.duckdns.org')"""

    @property
    @abstractmethod
    def domain_regex(self) -> str:
        """A szolgáltatóhoz tartozó érvényes domain reguláris kifejezése"""

    @abstractmethod
    async def update(self, payload: DDNSIpUpdate | DDNSTxtUpdate) -> None:
        """IP cím vagy TXT rekord (ACME challenge) frissítése a szolgáltatónál"""
