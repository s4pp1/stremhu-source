from unittest.mock import AsyncMock, Mock
from urllib.parse import quote

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.common.validators import validate_numeric_media_id
from app.main import app
from app.modules.auth.dependencies import get_auth_service
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.stremio.schemas import (
    KitsuStreamId,
    MalStreamId,
    TmdbStreamId,
    TvdbStreamId,
)
from app.modules.stremio.tvdb_resolver import TvdbResolver
from app.modules.stremio.utils import parse_stream_id
from app.modules.users.models import UserModel

BAD_IDS = ["123'", '123"', "1/2", " 123", "123 ", "²", "١٢٣", "1" * 33]


@pytest.mark.parametrize("value", BAD_IDS)
def test_numeric_media_policy_rejects_invalid_text(value):
    with pytest.raises(ValueError):
        validate_numeric_media_id(value)
    for schema, field in [(TvdbStreamId, "tvdb_id"), (KitsuStreamId, "kitsu_id"), (TmdbStreamId, "tmdb_id"), (MalStreamId, "mal_id")]:
        with pytest.raises(ValidationError):
            schema(**{field: value})


@pytest.mark.parametrize("prefix", ["tvdb:", "tvdb_", "tvdb", "kitsu:", "kitsu_", "tmdb:", "tmdb_", "mal:", "mal_", "anime:kitsu:", "anime:mal:"])
def test_legacy_numeric_prefixes_remain_accepted(prefix):
    parsed = parse_stream_id(prefix + "12345")
    assert "12345" in parsed.model_dump().values()


@pytest.mark.parametrize("value", BAD_IDS)
@pytest.mark.anyio
async def test_resolver_public_entries_do_not_request_for_invalid_ids(value):
    resolver = TvdbResolver()
    client_factory = Mock(side_effect=AssertionError("network must not be reached"))
    resolver._get_client = client_factory
    for resolve in [resolver.resolve_tvdb, resolver.resolve_tvdb_to_imdb, resolver.resolve_kitsu, resolver.resolve_kitsu_to_imdb, resolver.resolve_mal, resolver.resolve_tmdb]:
        with pytest.raises(ValueError):
            await resolve(value)
    client_factory.assert_not_called()


@pytest.mark.parametrize("value", BAD_IDS)
def test_malformed_ids_are_router_400(value):
    for prefix in ["tvdb:", "kitsu:", "tmdb:", "mal:"]:
        with pytest.raises(HTTPException) as error:
            parse_stream_id(prefix + value)
        assert error.value.status_code == 400


def test_invalid_id_http_does_not_start_stream_search():
    service = AsyncMock()
    auth = Mock()
    auth.verify_api_key.return_value = UserModel(id="fixture", username="fixture")
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_stremio_service] = lambda: service
    app.dependency_overrides[get_auth_service] = lambda: auth
    try:
        client = TestClient(app)
        for prefix in ["tvdb:", "kitsu:", "tmdb:", "mal:"]:
            response = client.get("/api/fixture/stremio/stream/series/" + quote(prefix + '123"', safe=":") + ".json")
            assert response.status_code == 400
        service.get_streams.assert_not_called()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
