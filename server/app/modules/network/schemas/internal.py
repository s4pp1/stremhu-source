import re
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.common.validators import validate_domain
from app.modules.network.ddns import discover_dns_providers
from app.modules.settings.enums import NetworkConnectionEnum, NetworkModeEnum


class NetworkLocalSetup(BaseModel):
    mode: Literal[NetworkModeEnum.LOCAL]


class NetworkAutoSetup(BaseModel):
    mode: Literal[NetworkModeEnum.AUTO]
    host: str
    connection: NetworkConnectionEnum
    provider: str
    token: str
    email: EmailStr

    @model_validator(mode="after")
    def validate_auto_setup(self) -> "NetworkAutoSetup":

        providers = discover_dns_providers()
        provider_class = next((p for p in providers if p().id == self.provider), None)
        if not provider_class:
            raise ValueError(f"Ismeretlen szolgáltató: {self.provider}")

        provider = provider_class()
        if not re.match(provider.domain_regex, self.host):
            raise ValueError(f"Érvénytelen domain a(z) {provider.name} szolgáltatóhoz")

        return self


class NetworkManualSetup(BaseModel):
    mode: Literal[NetworkModeEnum.MANUAL]
    host: str

    @model_validator(mode="after")
    def validate_host(self) -> "NetworkManualSetup":
        validate_domain(self.host)

        return self


NetworkSetup = Annotated[
    NetworkLocalSetup | NetworkAutoSetup | NetworkManualSetup,
    Field(discriminator="mode"),
]
