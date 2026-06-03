from modules.settings.schemas.internal import (
    RelaySettings,
    RelaySettingsUpdate,
    SystemSettings,
    SystemSettingsUpdate,
)
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class SystemSettingsResponse(SystemSettings):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class SystemSettingsUpdateRequest(SystemSettingsUpdate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class RelaySettingsResponse(RelaySettings):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class RelaySettingsUpdateRequest(RelaySettingsUpdate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
