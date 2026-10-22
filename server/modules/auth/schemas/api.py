from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    username: str
    password: str


class RegisterRequest(LoginRequest):
    pass
