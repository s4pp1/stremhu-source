from typing import Optional

from pydantic import BaseModel, Field


class UpdateSettings(BaseModel):
    download_rate_limit: Optional[int] = Field(None, alias="downloadLimit")
    upload_rate_limit: Optional[int] = Field(None, alias="uploadLimit")
    port: Optional[int] = Field(None)
    connections_limit: Optional[int] = Field(None, alias="connectionsLimit")
    torrent_connections_limit: Optional[int] = Field(
        None, alias="torrentConnectionsLimit"
    )
    enable_upnp_and_natpmp: Optional[bool] = Field(None, alias="enableUpnpAndNatpmp")
