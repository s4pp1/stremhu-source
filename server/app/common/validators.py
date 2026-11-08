import re
from urllib.parse import urlsplit


def normalize_browser_origin(value: str) -> tuple[str, str, int]:
    """Parse an origin without paths, credentials, wildcards or URL guessing."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (
            parsed.scheme not in {"http", "https"}
            or not host
            or not host.isascii()
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value)
            or any(character in host for character in "*%\\,;\"'<>")
            or "?" in value
            or "#" in value
        ):
            raise ValueError
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if not 0 < port <= 65535:
            raise ValueError
        # Origin headers use ASCII serialization. Accept explicit A-labels;
        # avoid silently mapping Unicode names with a different IDNA version.
        return parsed.scheme, host.lower(), port
    except (ValueError, UnicodeError):
        raise ValueError("Érvénytelen böngésző-origin.") from None


def validate_numeric_media_id(value: str) -> str:
    """Application input policy, not a claim about provider ID limits."""
    if not value or len(value) > 32 or not value.isascii() or not value.isdecimal():
        raise ValueError("A médiaazonosító 1–32 ASCII számjegyből állhat.")
    return value


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
