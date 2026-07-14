import pytest

from app.modules.torrent_streams.schemas import TorrentStream
from tests.helpers import load_streams_from_json

streams_data = load_streams_from_json()

test_cases = []
test_ids = []
for test_id, data in streams_data.items():
    torrent_info = data["torrent_info"]
    for file in torrent_info.files:
        if not file.is_video:
            continue

        test_ids.append(f"{test_id}_{file.name}")
        test_cases.append(
            (
                torrent_info,
                file.name,
                data["external_fallbacks"],
            )
        )


@pytest.mark.parametrize(
    "torrent_info, file_name, external_fallbacks",
    test_cases,
    ids=test_ids,
)
def test_stream_attributes_resolution(
    torrent_info, file_name, external_fallbacks, snapshot
):
    parsed_attributes = TorrentStream.resolve_attributes(
        torrent_name=torrent_info.name,
        file_name=file_name,
        external_fallbacks=external_fallbacks,
    )

    actual_attribute_ids = sorted(
        [parsed_attribute.id for parsed_attribute in parsed_attributes]
    )

    assert actual_attribute_ids == snapshot
