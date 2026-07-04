import re


def validate_domain(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        raise ValueError("A protokoll (http/https) nem szerepelhet a domainben")

    if re.match(r"^\d{1,3}(\.\d{1,3}){3}", value):
        raise ValueError("IP cím nem engedélyezett, csak domain")

    if ":" in value:
        raise ValueError("A port megadása nem engedélyezett")

    if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$", value):
        raise ValueError("Érvénytelen domain formátum")

    return value
