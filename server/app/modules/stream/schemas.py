from pydantic import BaseModel

from app.common.schemas.internal import SeriesInfo


class StreamToken(BaseModel):
    indexer_id: str
    torrent_id: str
    file_index: int
    playback_id: str
    imdb_id: str | None = None
    series_info: SeriesInfo | None = None


class ParsedRangeHeader(BaseModel):
    start_byte: int
    end_byte: int
    content_length: int
