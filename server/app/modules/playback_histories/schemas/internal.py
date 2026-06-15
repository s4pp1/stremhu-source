from app.common.schemas.internal import ImdbInfo
from pydantic import BaseModel


class PlaybackHistoryClientInfo(BaseModel):
    user_agent: str | None = None
    ip: str | None = None


class PlaybackHistoryCreate(BaseModel):
    playback_id: str
    user_id: str
    indexer_id: str
    torrent_id: str
    file_index: int
    torrent_name: str
    file_name: str
    imdb_info: ImdbInfo | None = None
    client: PlaybackHistoryClientInfo | None = None


class PlaybackHistoryUpdate(BaseModel):
    client: PlaybackHistoryClientInfo | None = None
