from datetime import datetime

from pydantic import BaseModel


class PairInit(BaseModel):
    user_code: str
    device_code: str
    expires_at: datetime


class PairStatus(BaseModel):
    status: str
    token: str | None = None


class PairVerify(BaseModel):
    user_code: str
