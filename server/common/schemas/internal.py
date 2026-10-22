from pydantic import BaseModel


class SeriesInfo(BaseModel):
    season: int
    episode: int


class ImdbInfo(BaseModel):
    imdb_id: str
    series_info: SeriesInfo | None = None


class Success(BaseModel):
    success: bool
    message: str | None = None
