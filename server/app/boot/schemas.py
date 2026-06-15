from pydantic import BaseModel

from app.modules.settings.schemas.internal import NetworkSettings


class BootNetworkConfig(BaseModel):
    network_settings: NetworkSettings
    cert_path: str | None = None
    key_path: str | None = None
