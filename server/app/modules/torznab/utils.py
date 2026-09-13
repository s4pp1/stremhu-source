import re
from datetime import UTC, datetime
from email.utils import format_datetime

from fastapi import Response
from pydantic_xml import BaseXmlModel

from app.modules.torznab.constants import XML_MEDIA_TYPE

# A film nevek tudnak olyan karaktereket tartalmazni,
# ami az XML-el nincsenek jóban és eltörik a parser-eket.
_ILLEGAL_XML_CHARACTERS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff\ufeff\ufffe\uffff]"
)


def clean_xml_text(value: str) -> str:
    return _ILLEGAL_XML_CHARACTERS.sub("", value)


def format_date_to_rfc822(value: datetime) -> str:
    return format_datetime(value.astimezone(UTC), usegmt=True)


def xml_response(
    model: BaseXmlModel,
    media_type: str = XML_MEDIA_TYPE,
) -> Response:
    return Response(
        content=model.to_xml(
            encoding="utf-8",
            xml_declaration=True,
            skip_empty=True,
        ),
        media_type=media_type,
    )
