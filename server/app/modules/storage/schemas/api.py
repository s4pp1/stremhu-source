from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.storage.schemas.internal import StorageStatus


class StorageStatusResponse(StorageStatus):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
