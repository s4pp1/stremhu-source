from pydantic import BaseModel


class DDNSIpUpdate(BaseModel):
    provider_token: str
    host: str
    ip: str


class DDNSTxtUpdate(BaseModel):
    provider_token: str
    host: str
    txt: str
    clear_txt: bool = False
