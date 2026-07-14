import pytest

from app.modules.torrent_streams.utils.series_parser import SeriesParser
from tests.helpers import load_streams_from_json

streams_data = load_streams_from_json()

test_cases = []
test_ids = []
for test_id, data in streams_data.items():
    is_series = any(
        query.get("series") is not None for query in data.get("queries", [])
    )
    if not is_series:
        continue

    torrent_info = data["torrent_info"]
    test_ids.append(test_id)
    test_cases.append(torrent_info.name)


@pytest.mark.parametrize(
    "torrent_name",
    test_cases,
    ids=test_ids,
)
def test_series_parser_torrent_name(torrent_name: str, snapshot):
    parser = SeriesParser(torrent_name)
    seasons, episodes = parser.parse()

    assert {
        "torrent_name": torrent_name,
        "seasons": seasons,
        "episodes": episodes,
    } == snapshot
