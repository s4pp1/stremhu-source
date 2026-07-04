from pydantic import BaseModel


class SystemStatus(BaseModel):
    configured: bool

    version: str

    app_url: str

    host_ip: str

    port: int

    is_reverse_proxy: bool
