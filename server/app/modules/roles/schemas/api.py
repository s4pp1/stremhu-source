from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.roles.schemas.internal import Role


class RoleResponse(Role):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )
