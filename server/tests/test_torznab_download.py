from collections.abc import Iterator

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api import api_router
from app.exceptions import setup_exception_handlers
from app.modules.auth.dependencies import get_auth_service
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_source_provider.schemas import TorrentSource
from app.modules.torznab.constants import TORRENT_MEDIA_TYPE
from app.modules.torznab.dependencies import get_torznab_service
from app.modules.torznab.download_token import generate_download_token
from app.modules.torznab.schemas.download import TorznabDownloadToken
from app.modules.torznab.service import TorznabService
from tests.helpers import create_torrent_source

API_KEY = "9f8f3c2a-0b1d-4f5e-8a7b-6c5d4e3f2a1b"
OTHER_API_KEY = "00000000-0000-0000-0000-000000000000"
APP_URL = "https://stremhu.local"

INDEXER_ID = "ncore"
TORRENT_ID = "111"


class FakeUser:
    id = "user-id"
    api_key = API_KEY


class FakeAuthService:
    def verify_api_key(self, api_key: str | None, allowed_roles=None) -> FakeUser:
        _ = allowed_roles

        if api_key != API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return FakeUser()


class FakeSettingsService:
    def get_app_url(self) -> str:
        return APP_URL


class FakeIsolatedTorrentFilesService:
    def __init__(self, torrent_file: TorrentFileModel | None = None):
        self.torrent_file = torrent_file
        self.touched: list[object] = []

    def find_by_id(self, indexer_id: str, torrent_id: str):
        _ = (indexer_id, torrent_id)

        return self.torrent_file

    def touch(self, identifiers) -> None:
        self.touched.append(identifiers)


class FakeTorrentSourceProviderService:
    def __init__(self, sources: list[TorrentSource] | None = None):
        self._sources = sources or []

    async def find_by_imdb_id(self, imdb_id: str):
        _ = imdb_id

        return self._sources, []

    async def find_one_by_indexer(self, indexer_id: str, torrent_id: str):
        _ = (indexer_id, torrent_id)

        return self._sources[0] if self._sources else None


def create_source() -> TorrentSource:
    return create_torrent_source(
        indexer_id=INDEXER_ID,
        indexer_name="nCore",
        torrent_id=TORRENT_ID,
        name="Teszt.Film.2026.1080p.WEB-DL.H264-TESZTGROUP.mkv",
    )


def create_client(
    isolated_torrent_files_service: FakeIsolatedTorrentFilesService,
    sources: list[TorrentSource] | None = None,
) -> Iterator[TestClient]:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(api_router)

    app.dependency_overrides[get_auth_service] = FakeAuthService
    app.dependency_overrides[get_torznab_service] = lambda: TorznabService(
        settings_service=FakeSettingsService(),  # type: ignore[arg-type]
        torrent_source_provider_service=FakeTorrentSourceProviderService(sources),  # type: ignore[arg-type]
        isolated_torrent_files_service=isolated_torrent_files_service,  # type: ignore[arg-type]
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def source() -> TorrentSource:
    return create_source()


@pytest.fixture
def cached(source: TorrentSource) -> FakeIsolatedTorrentFilesService:
    return FakeIsolatedTorrentFilesService(source.torrent_file)


@pytest.fixture
def client(cached: FakeIsolatedTorrentFilesService) -> Iterator[TestClient]:
    yield from create_client(cached)


def download_url(api_key: str = API_KEY, token: str | None = None) -> str:
    if token is None:
        token = generate_download_token(
            TorznabDownloadToken(indexer_id=INDEXER_ID, torrent_id=TORRENT_ID)
        )

    return f"/api/{api_key}/torznab/download/{token}"


def test_valid_token_serves_the_stored_torrent(
    client: TestClient,
    source: TorrentSource,
    cached: FakeIsolatedTorrentFilesService,
):
    response = client.get(download_url())

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == TORRENT_MEDIA_TYPE
    assert response.content == source.torrent_file.torrent_bytes
    assert cached.touched


def test_tampered_token_is_rejected(client: TestClient):
    token = generate_download_token(
        TorznabDownloadToken(indexer_id=INDEXER_ID, torrent_id=TORRENT_ID)
    )

    response = client.get(download_url(token=f"{token[:-3]}xxx"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_another_api_key_cannot_download(client: TestClient):
    response = client.get(download_url(api_key=OTHER_API_KEY))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_missing_torrent_is_fetched_from_the_indexer():
    source = create_source()
    empty_cache = FakeIsolatedTorrentFilesService()

    for client in create_client(empty_cache, sources=[source]):
        response = client.get(download_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.content == source.torrent_file.torrent_bytes
