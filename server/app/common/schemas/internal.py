from pydantic import BaseModel, Field


class SeriesInfo(BaseModel):
    season: int
    episode: int
    alternate_episodes: list[int] = Field(default_factory=list)
    alternate_seasons: list[int] = Field(default_factory=list)


class ImdbInfo(BaseModel):
    imdb_id: str
    series_info: SeriesInfo | None = None


class Success(BaseModel):
    success: bool
    message: str | None = None
