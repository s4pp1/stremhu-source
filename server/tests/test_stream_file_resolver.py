import pytest

from app.common.schemas.internal import SeriesInfo
from app.modules.torrent_streams.utils.stream_file_resolver import StreamFileResolver
from tests.helpers import load_streams_from_json

streams_data = load_streams_from_json()

test_cases = []
test_ids = []
for test_id, data in streams_data.items():
    for i, query in enumerate(data["queries"]):
        test_ids.append(f"{test_id}_{i}")
        test_cases.append((data["torrent_info"], query))


@pytest.mark.parametrize(
    "torrent_info, query",
    test_cases,
    ids=test_ids,
)
def test_stream_file_resolver_resolves_expected_file(torrent_info, query):
    series_data = query.get("series")
    series = SeriesInfo(**series_data) if series_data else None

    resolved_file = StreamFileResolver(torrent_info, series).resolve()

    assert resolved_file is not None
    assert resolved_file.path == query["expected_file"]
