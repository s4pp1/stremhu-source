from itsdangerous import URLSafeSerializer

from server.common.session import get_session_secret
from server.modules.stream.schemas import StreamToken


def get_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(
        get_session_secret(),
        salt="stream-token",
    )


def generate_stream_token(
    payload: StreamToken,
) -> str:
    return get_serializer().dumps(payload.model_dump())


def parse_stream_token(token: str) -> StreamToken:
    payload = get_serializer().loads(token)
    return StreamToken.model_validate(payload)
