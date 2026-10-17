from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from core.modules.system.schemas.internal import SystemStatus


class SystemStatusResponse(SystemStatus):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
