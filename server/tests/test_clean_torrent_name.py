import pytest

from app.modules.media_attributes.parser import clean_torrent_name
from tests.helpers import load_streams_from_json

streams_data = load_streams_from_json()

test_cases = []
test_ids = []
for test_id, data in streams_data.items():
    torrent_info = data["torrent_info"]
    test_ids.append(test_id)
    test_cases.append(torrent_info.name)


@pytest.mark.parametrize(
    "torrent_name",
    test_cases,
    ids=test_ids,
)
def test_clean_torrent_name(torrent_name: str, snapshot):
    cleaned = clean_torrent_name(torrent_name)

    assert {
        "original_name": torrent_name,
        "cleaned_name": cleaned,
    } == snapshot
