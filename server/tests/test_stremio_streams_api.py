from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.stremio.schemas import BehaviorHints, StremioStream
from app.modules.stremio.service import StremioService
from app.modules.users.models import UserModel


@pytest.fixture
def client():
    return TestClient(app)


def test_stremio_streams_api_returns_error_streams(client):
    """
    Test hogy a Stremio streams végpont megfelelően visszaadja-e a hiba streameket (is).
    """
    mock_stremio_service = AsyncMock(spec=StremioService)

    mock_stremio_service.get_streams.return_value = [
        StremioStream(
            name="⚠️ [StremHU] Hiba",
            description="TimeoutError: A(z) 'nCore' indexer nem válaszolt időben.",
            external_url="http://localhost:8000",
            behavior_hints=None,
        ),
        StremioStream(
            name="Normal Stream",
            description="A normal working stream",
            url="http://localhost/play",
            behavior_hints=BehaviorHints(not_web_ready=True),
        ),
    ]

    mock_auth_service = AsyncMock(spec=AuthService)
    mock_auth_service.verify_api_key.return_value = UserModel(
        id="user123", username="testuser"
    )

    # Felülírjuk a dependency-ket
    app.dependency_overrides[get_stremio_service] = lambda: mock_stremio_service
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    try:
        response = client.get("/api/dummy_api_key/stremio/stream/movie/tt1234567.json")

        assert response.status_code == 200
        data = response.json()

        assert "streams" in data
        streams = data["streams"]
        assert len(streams) == 2

        # Első stream a hiba stream
        error_stream = streams[0]
        assert error_stream["name"] == "⚠️ [StremHU] Hiba"
        assert (
            error_stream["description"]
            == "TimeoutError: A(z) 'nCore' indexer nem válaszolt időben."
        )
        assert error_stream.get("externalUrl") == "http://localhost:8000"
        assert error_stream.get("url") is None

        # Második stream a normál stream
        normal_stream = streams[1]
        assert normal_stream["name"] == "Normal Stream"
        assert normal_stream["description"] == "A normal working stream"
        assert normal_stream.get("url") == "http://localhost/play"

    finally:
        # Kitakarítjuk az override-okat a teszt végén
        app.dependency_overrides.clear()
