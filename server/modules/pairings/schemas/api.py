from modules.pairings.schemas.internal import PairInit, PairStatus, PairVerify
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class PairInitResponse(PairInit):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class PairStatusResponse(PairStatus):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class PairVerifyRequest(PairVerify):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
