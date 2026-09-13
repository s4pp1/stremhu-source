import xml.etree.ElementTree as ElementTree
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.modules.torznab.enums import TorznabErrorCode
from app.modules.torznab.schemas.xml import (
    FeedItem,
    FeedItemEnclosure,
    FeedItemGuid,
    FeedItemIndexer,
    TorznabAttr,
    TorznabError,
)
from app.modules.torznab.service import TorznabService
from app.modules.torznab.utils import clean_xml_text, format_date_to_rfc822

APP_URL = "https://stremhu.local"
LINK = f"{APP_URL}/api/torznab/api"
INFO_HASH = "0123456789abcdef0123456789abcdef01234567"


class FakeSettingsService:
    def get_app_url(self) -> str:
        return APP_URL


def build_service() -> TorznabService:
    return TorznabService(settings_service=FakeSettingsService())  # type: ignore[arg-type]


def serialize(model) -> str:
    return model.to_xml(
        encoding="utf-8",
        xml_declaration=True,
        skip_empty=True,
    ).decode()


def build_item() -> FeedItem:
    return FeedItem(
        title="Valami.Film.2024.1080p.WEB-DL.H264.HUN-GROUP",
        guid=FeedItemGuid(value=INFO_HASH),
        indexer=FeedItemIndexer(id="indexer-id", name="Teszt Indexer"),
        type="private",
        pub_date=format_date_to_rfc822(datetime(2024, 6, 1, 12, 0, tzinfo=UTC)),
        size=8589934592,
        categories=[2000, 2040],
        enclosure=FeedItemEnclosure(
            url=f"magnet:?xt=urn:btih:{INFO_HASH}",
            length=8589934592,
        ),
        attributes=[
            TorznabAttr(name="size", value="8589934592"),
            TorznabAttr(name="category", value="2000"),
            TorznabAttr(name="category", value="2040"),
            TorznabAttr(name="infohash", value=INFO_HASH),
            TorznabAttr(name="seeders", value="12"),
        ],
    )


def test_capabilities(snapshot):
    assert serialize(build_service().capabilities()) == snapshot


def test_empty_feed(snapshot):
    assert serialize(build_service().feed(link=LINK)) == snapshot


def test_feed_with_item(snapshot):
    feed = build_service().feed(link=LINK, items=[build_item()])

    assert serialize(feed) == snapshot


def test_error_document(snapshot):
    error = TorznabError(
        code=int(TorznabErrorCode.INCORRECT_PARAMETER),
        description="Incorrect parameter (cat)",
    )

    assert serialize(error) == snapshot


def test_feed_reports_the_item_count():
    feed = build_service().feed(link=LINK, items=[build_item()], offset=25)

    assert (feed.channel.response.offset, feed.channel.response.total) == (25, 1)


def test_control_characters_are_stripped():
    assert clean_xml_text("Valami\x1aFilm\x00.2024") == "ValamiFilm.2024"


def test_item_sanitises_its_own_text():
    item = build_item()
    dirty = FeedItem(
        **{
            **item.model_dump(),
            "title": "Film & <Tarsai>\x1a 2024",
        }
    )

    assert dirty.title == "Film & <Tarsai> 2024"


def test_serialised_feed_stays_well_formed_with_dirty_titles():
    item = build_item()
    dirty = FeedItem(
        **{
            **item.model_dump(),
            "title": "Film & <Tarsai>\x1a 2024",
        }
    )

    xml = serialize(build_service().feed(link=LINK, items=[dirty]))

    assert ElementTree.fromstring(xml).find("./channel/item/title") is not None


def test_feed_link_uses_the_configured_app_url():
    assert build_service().feed_link("/api/torznab/api") == LINK


def test_total_can_differ_from_the_serialised_page():
    feed = build_service().feed(
        link=LINK,
        items=[build_item()],
        offset=100,
        total=250,
    )

    assert (feed.channel.response.offset, feed.channel.response.total) == (100, 250)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        datetime(2024, 6, 1, 14, 0, tzinfo=timezone(timedelta(hours=2))),
        datetime(2024, 6, 1, 12, 0),
    ],
)
def test_pub_date_accepts_naive_and_offset_datetimes(value: datetime):
    assert format_date_to_rfc822(value).endswith("GMT")


def test_lone_surrogates_are_stripped():
    dirty = FeedItem(
        **{
            **build_item().model_dump(),
            "title": "Film\ud800Name",
        }
    )

    xml = serialize(build_service().feed(link=LINK, items=[dirty]))

    assert ElementTree.fromstring(xml).findtext("./channel/item/title") == "FilmName"
