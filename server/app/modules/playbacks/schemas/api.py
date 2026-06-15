from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.indexer_definitions.schemas.api import IndexerDefinitionResponse
from app.modules.playback_histories.schemas.api import PlaybackHistoryResponse
from app.modules.playbacks.schemas.internal import Playback
from app.modules.users.schemas.api import UserResponse


class PlaybackResponse(PlaybackHistoryResponse):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    progress: float

    @classmethod
    def from_playback(
        cls,
        playback: Playback,
    ) -> "PlaybackResponse":
        progress = (
            playback.stream.current_stream_byte / playback.stream.file.size
        ) * 100

        return cls(
            playback_id=playback.playback_history_model.playback_id,
            user=UserResponse.model_validate(playback.playback_history_model.user),
            indexer_definition=IndexerDefinitionResponse.model_validate(
                playback.playback_history_model.indexer_definition
            ),
            torrent_name=playback.playback_history_model.torrent_name,
            file_name=playback.playback_history_model.file_name,
            created_at=playback.playback_history_model.created_at,
            progress=progress,
        )
