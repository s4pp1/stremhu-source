import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PairInit(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    user_code: str
    device_code: str
    expires_at: datetime.datetime


class PairStatusRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    device_code: str


class PairStatus(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    status: str
    token: str | None = None


class PairVerifyRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    user_code: str


class PairVerify(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    success: bool
