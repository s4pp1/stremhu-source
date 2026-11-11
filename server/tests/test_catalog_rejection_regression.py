from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.stremio.catalogs_service import StremioCatalogsService
from app.modules.stremio.constants import SEARCH_ID
from app.modules.stremio.enums import MediaType
from app.modules.stremio.schemas import ParsedExtra


@pytest.mark.anyio
async def test_movie_catalog_does_not_restore_rejected_episode_sources():
    provider = AsyncMock()
    source = MagicMock()
    source.torrent_file.info.name = "Example.S01E01.1080p"
    source.torrent_file.info.files = []
    provider.find_by_query.return_value = ([source], [])
    service = StremioCatalogsService(MagicMock(), provider, MagicMock())

    result = await service.get_catalog(
        MediaType.MOVIE, SEARCH_ID, ParsedExtra(search="Example")
    )

    assert result.metas == []
