from collections.abc import Iterator

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from app.api import api_router
from app.exceptions import setup_exception_handlers
from app.modules.auth.dependencies import get_auth_service
from app.modules.media_attributes.constants import MediaAttributeKey
from app.modules.torrent_source_provider.schemas import TorrentSource
from app.modules.torznab.dependencies import get_torznab_service
from app.modules.torznab.service import TorznabService
from tests.helpers import create_torrent_source

API_KEY = "9f8f3c2a-0b1d-4f5e-8a7b-6c5d4e3f2a1b"
APP_URL = "https://stremhu.local"
IMDB_ID = "tt9999999"


class FakeUser:
    id = "user-id"


class FakeAuthService:
    def verify_api_key(self, api_key: str | None, allowed_roles=None) -> FakeUser:
        _ = allowed_roles

        if api_key != API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return FakeUser()


class FakeSettingsService:
    def get_app_url(self) -> str:
        return APP_URL


class FakeTorrentSourceProviderService:
    def __init__(self, sources: list[TorrentSource]):
        self._sources = sources

    async def find_by_imdb_id(self, imdb_id: str):
        _ = imdb_id

        return self._sources, []


def create_client(sources: list[TorrentSource]) -> Iterator[TestClient]:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(api_router)

    app.dependency_overrides[get_auth_service] = FakeAuthService
    app.dependency_overrides[get_torznab_service] = lambda: TorznabService(
        settings_service=FakeSettingsService(),  # type: ignore[arg-type]
        torrent_source_provider_service=FakeTorrentSourceProviderService(sources),  # type: ignore[arg-type]
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def movie_client() -> Iterator[TestClient]:
    sources = [
        create_torrent_source(
            indexer_id="bithumen",
            indexer_name="BitHUmen",
            torrent_id="222",
            name="Teszt.Film.2026.720p.WEB-DL.H264-TESZTGROUP.mkv",
            seeders=14,
            imdb_id=IMDB_ID,
            attribute_ids=[MediaAttributeKey.ENG],
        ),
        create_torrent_source(
            indexer_id="ncore",
            indexer_name="nCore",
            torrent_id="111",
            name="Teszt.Film.2026.1080p.WEB-DL.H264.HUN-TESZTGROUP.mkv",
            seeders=91,
            imdb_id=IMDB_ID,
            attribute_ids=[MediaAttributeKey.HUN],
        ),
    ]

    yield from create_client(sources)


@pytest.fixture
def series_client() -> Iterator[TestClient]:
    sources = [
        create_torrent_source(
            indexer_id="ncore",
            indexer_name="nCore",
            torrent_id="333",
            name="Teszt.Sorozat.S02.1080p.WEB-DL.H264-TESZTGROUP",
            files=[f"Teszt.Sorozat.S02E0{episode}.1080p.mkv" for episode in (1, 2, 3)],
            seeders=120,
            imdb_id=IMDB_ID,
            attribute_ids=[MediaAttributeKey.HUN],
        ),
        create_torrent_source(
            indexer_id="bithumen",
            indexer_name="BitHUmen",
            torrent_id="444",
            name="Teszt.Sorozat.S02E02.1080p.WEB-DL.H264-TESZTGROUP.mkv",
            seeders=7,
            imdb_id=IMDB_ID,
            attribute_ids=[MediaAttributeKey.HUN],
        ),
        # Teljesen másik évad, a keresett epizódot nem tartalmazza.
        create_torrent_source(
            indexer_id="ncore",
            indexer_name="nCore",
            torrent_id="555",
            name="Teszt.Sorozat.S03E01.1080p.WEB-DL.H264-TESZTGROUP.mkv",
            seeders=999,
            imdb_id=IMDB_ID,
            attribute_ids=[MediaAttributeKey.HUN],
        ),
    ]

    yield from create_client(sources)


def test_movie_search_feed(movie_client: TestClient, snapshot: SnapshotAssertion):
    response = movie_client.get(
        f"/api/torznab/api?t=movie&imdbid={IMDB_ID}&apikey={API_KEY}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.text == snapshot


def test_tv_search_feed(series_client: TestClient, snapshot: SnapshotAssertion):
    response = series_client.get(
        f"/api/torznab/api?t=tvsearch&imdbid={IMDB_ID}&season=2&ep=2&apikey={API_KEY}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.text == snapshot
