from itsdangerous import URLSafeSerializer

from app.config import (
    config,
)
from app.modules.stream.schemas import StreamToken

serializer = URLSafeSerializer(
    config.session_secret,
    salt="stream-token",
)


def generate_stream_token(
    payload: StreamToken,
) -> str:
    return serializer.dumps(payload.model_dump())


def parse_stream_token(token: str) -> StreamToken:
    payload = serializer.loads(token)
    return StreamToken.model_validate(payload)
