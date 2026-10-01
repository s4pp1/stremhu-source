from itsdangerous import BadSignature, URLSafeSerializer

from app.config import config
from app.modules.torznab.schemas.download import TorznabDownloadToken

serializer = URLSafeSerializer(
    config.session_secret,
    salt="torznab-download-token",
)


def generate_download_token(payload: TorznabDownloadToken) -> str:
    return serializer.dumps(payload.model_dump())


def parse_download_token(token: str) -> TorznabDownloadToken | None:
    try:
        payload = serializer.loads(token)
    except BadSignature:
        return None

    return TorznabDownloadToken.model_validate(payload)
