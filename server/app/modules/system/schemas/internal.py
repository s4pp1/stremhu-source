from pydantic import BaseModel


class SystemStatus(BaseModel):
    configured: bool
    app_url: str
    version: str
