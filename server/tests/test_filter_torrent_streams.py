from unittest.mock import Mock

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.media_attributes.constants import MediaAttributeKey
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.preferences.constants import PreferenceKey
from app.modules.torrent_streams.schemas import TorrentStream
from app.modules.torrent_streams.service import TorrentStreamsService


def create_mock_service():
    return TorrentStreamsService(
        db=Mock(),
        torrent_source_provider_service=Mock(),
        torrents_service=Mock(),
        settings_service=Mock(),
        preferences_service=Mock(),
    )


def test_is_torrent_stream_excluded():
    service = create_mock_service()

    attr_hun = MediaAttributeModel(
        id=MediaAttributeKey.HUN, preference_id=PreferenceKey.LANGUAGE, name="magyar"
    )
    attr_eng = MediaAttributeModel(
        id=MediaAttributeKey.ENG, preference_id=PreferenceKey.LANGUAGE, name="angol"
    )
    attr_ncore = IndexerDefinitionModel(
        id="ncore", name="ncore", url="https://ncore.pro", details_path=""
    )

    dummy_indexer_account = IndexerAccountModel(
        indexer_id="ncore", username="test", password="pwd"
    )

    torrent = TorrentStream(
        indexer_account=dummy_indexer_account,
        torrent_id="1",
        info_hash="hash",
        torrent_name="test",
        file_name="test",
        file_size=1,
        file_index=1,
        play_url="",
        attributes=[attr_hun, attr_eng],
        is_persisted_torrent=False,
    )

    excluded_attribute_ids = {MediaAttributeKey.ENG}
    preference_multiple_map = {PreferenceKey.LANGUAGE: True}
    assert not service._is_torrent_stream_excluded(
        torrent, excluded_attribute_ids, preference_multiple_map
    )

    excluded_attribute_ids = {MediaAttributeKey.ENG, MediaAttributeKey.HUN}
    assert service._is_torrent_stream_excluded(
        torrent, excluded_attribute_ids, preference_multiple_map
    )

    excluded_attribute_ids = {MediaAttributeKey.ENG}
    preference_multiple_map = {PreferenceKey.LANGUAGE: False}
    assert service._is_torrent_stream_excluded(
        torrent, excluded_attribute_ids, preference_multiple_map
    )

    torrent_with_indexer = TorrentStream(
        indexer_account=dummy_indexer_account,
        torrent_id="1",
        info_hash="hash",
        torrent_name="test",
        file_name="test",
        file_size=1,
        file_index=1,
        play_url="",
        attributes=[attr_ncore],
        is_persisted_torrent=False,
    )
    excluded_attribute_ids = {"ncore"}
    preference_multiple_map = {}
    assert service._is_torrent_stream_excluded(
        torrent_with_indexer, excluded_attribute_ids, preference_multiple_map
    )

    excluded_attribute_ids = {"something_else"}
    assert not service._is_torrent_stream_excluded(
        torrent_with_indexer, excluded_attribute_ids, preference_multiple_map
    )
