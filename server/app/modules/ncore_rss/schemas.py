import datetime
import re
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


def validate_ncore_url(value: str) -> str:
    try:
        parsed = urlparse(value.strip())
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as error:
        raise ValueError("Érvénytelen nCore hivatkozás.") from error

    if (
        parsed.scheme != "https"
        or hostname not in {"ncore.pro", "www.ncore.pro"}
        or port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Csak HTTPS-es nCore hivatkozás adható meg.")
    return value.strip()


def torrent_id_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.path.rstrip("/").split("/")[-1] != "torrents.php":
        return None
    query = parse_qs(parsed.query)
    torrent_id = query.get("id", [None])[0]
    action = query.get("action", [None])[0]
    if torrent_id and torrent_id.isdigit() and action in {"details", "download"}:
        return torrent_id
    return None


def is_ncore_download_url(value: str) -> bool:
    try:
        validate_ncore_url(value)
    except ValueError:
        return False
    parsed = urlparse(value)
    return (
        torrent_id_from_url(value) is not None
        and parse_qs(parsed.query).get("action", [None])[0] == "download"
    ) or parsed.path.lower().endswith(".torrent")


class NcoreRssFeedUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    feed_url: str = Field(min_length=1, max_length=2048)

    @field_validator("feed_url")
    @classmethod
    def validate_feed_url(cls, value: str) -> str:
        return validate_ncore_url(value)


class NcoreRssItemUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    imdb_id: str | None = None
    download_url: str | None = Field(default=None, max_length=2048)

    @field_validator("imdb_id")
    @classmethod
    def validate_imdb_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if not re.fullmatch(r"tt\d{7,10}", normalized):
            raise ValueError("Érvényes IMDb azonosító szükséges (például tt1234567).")
        return normalized

    @field_validator("download_url")
    @classmethod
    def validate_download_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return value
        value = validate_ncore_url(value)
        if torrent_id_from_url(value) is None and not value.lower().split(
            "?", 1
        )[0].endswith(".torrent"):
            raise ValueError("A linknek nCore torrent letöltési linknek kell lennie.")
        return value


class NcoreRssManualItemCreate(NcoreRssItemUpdate):
    imdb_id: str
    download_url: str
    title: str = Field(min_length=1, max_length=500)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("A torrent címe nem lehet üres.")
        return title


class NcoreRssEntry(BaseModel):
    torrent_id: str
    title: str
    source_url: str | None = None
    download_url: str | None = None
    imdb_id: str | None = None
    seeders: int | None = None
    last_detail_checked_at: datetime.datetime | None = None


class NcoreRssItemResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    torrent_id: str
    title: str
    source_url: str | None
    download_url: str | None
    detected_imdb_id: str | None
    manual_imdb_id: str | None
    imdb_id: str | None
    seeders: int | None
    is_manual: bool
    last_seen_at: datetime.datetime


class NcoreRssStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    ncore_connected: bool
    configured: bool
    last_synced_at: datetime.datetime | None
    total_items: int
    unresolved_items: int
