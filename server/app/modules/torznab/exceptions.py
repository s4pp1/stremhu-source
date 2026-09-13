from fastapi import Request, Response

from app.modules.torznab.enums import TorznabErrorCode
from app.modules.torznab.schemas.xml import TorznabError
from app.modules.torznab.utils import xml_response


class TorznabProtocolError(Exception):
    def __init__(self, code: TorznabErrorCode, description: str):
        super().__init__(description)
        self.code = code
        self.description = description


async def torznab_protocol_error_handler(
    request: Request,
    exc: TorznabProtocolError,
) -> Response:
    _ = request

    return xml_response(TorznabError(code=int(exc.code), description=exc.description))
