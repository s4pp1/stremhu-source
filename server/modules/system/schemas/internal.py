from pathlib import Path

from pydantic import BaseModel


class SystemStatus(BaseModel):
    configured: bool

    version: str

    app_url: str

    host_ip: str

    port: int

    downloads_dir: Path

    is_reverse_proxy: bool
    is_downloads_dir_overridden: bool
