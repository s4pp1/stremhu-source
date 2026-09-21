import xml.etree.ElementTree as ElementTree
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api import api_router
from app.exceptions import setup_exception_handlers
from app.modules.auth.dependencies import get_auth_service
from app.modules.torznab.constants import FEED_MEDIA_TYPE, XML_MEDIA_TYPE
from app.modules.torznab.dependencies import get_torznab_service
from app.modules.torznab.service import TorznabService

API_KEY = "9f8f3c2a-0b1d-4f5e-8a7b-6c5d4e3f2a1b"
APP_URL = "https://stremhu.local"


class FakeUser:
    id = "user-id"


class FakeAuthService:
    def verify_api_key(self, api_key: str | None, allowed_roles=None) -> FakeUser:
        _ = allowed_roles

        if api_key != API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A megadott API kulcs érvénytelen.",
            )

        return FakeUser()


class FakeSettingsService:
    def get_app_url(self) -> str:
        return APP_URL


class FakeTorrentSourceProviderService:
    async def find_by_imdb_id(self, imdb_id: str):
        _ = imdb_id

        return [], []


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(api_router)

    app.dependency_overrides[get_auth_service] = FakeAuthService
    app.dependency_overrides[get_torznab_service] = lambda: TorznabService(
        settings_service=FakeSettingsService(),  # type: ignore[arg-type]
        torrent_source_provider_service=FakeTorrentSourceProviderService(),  # type: ignore[arg-type]
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


def error_code(body: str) -> int:
    root = ElementTree.fromstring(body)

    assert root.tag == "error"

    return int(root.attrib["code"])


@pytest.mark.parametrize(
    "url",
    [
        f"/api/torznab?t=caps&apikey={API_KEY}",
        f"/api/torznab/api?t=caps&apikey={API_KEY}",
    ],
)
def test_capabilities_is_served_on_every_supported_route(client: TestClient, url: str):
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == XML_MEDIA_TYPE
    assert ElementTree.fromstring(response.text).tag == "caps"


def test_search_returns_an_empty_feed(client: TestClient):
    query = "t=tvsearch&imdbid=tt9999999"
    response = client.get(f"/api/torznab/api?{query}&apikey={API_KEY}")
    root = ElementTree.fromstring(response.text)

    assert response.headers["content-type"] == FEED_MEDIA_TYPE
    assert root.tag == "rss"
    assert root.findall("./channel/item") == []
    assert root.findtext("./channel/link") == f"{APP_URL}/api/torznab/api?{query}"


@pytest.mark.parametrize(
    "url",
    [
        "/api/torznab/api?t=caps",
        "/api/torznab/api?t=caps&apikey=wrong",
    ],
)
def test_missing_or_wrong_key_returns_a_protocol_error(client: TestClient, url: str):
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert error_code(response.text) == 100


def test_protocol_errors_keep_a_200_status(client: TestClient):
    response = client.get(f"/api/torznab/api?t=nonsense&apikey={API_KEY}")

    assert response.status_code == status.HTTP_200_OK
    assert error_code(response.text) == 202


def test_authentication_is_checked_before_the_query(client: TestClient):
    response = client.get("/api/torznab/api?t=details")

    assert error_code(response.text) == 100


def test_api_key_is_not_published_in_the_feed(client: TestClient):
    response = client.get(f"/api/torznab/api?t=movie&imdbid=tt9999999&apikey={API_KEY}")

    assert API_KEY not in response.text
