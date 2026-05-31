from modules.settings.schemas import NetworkModeEnum
from pydantic import BaseModel


class BootNetworkConfig(BaseModel):
    """A rendszerindításhoz feloldott hálózati és SSL beállítások sémája."""

    cert_path: str | None = None
    key_path: str | None = None
    mode: NetworkModeEnum
    host: str
