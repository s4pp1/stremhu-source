from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class UpdateSettings(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    download_limit: Optional[int] = None
    upload_limit: Optional[int] = None
    port: Optional[int] = None
    connections_limit: Optional[int] = None
    torrent_connections_limit: Optional[int] = None
    enable_upnp_and_natpmp: Optional[bool] = None
