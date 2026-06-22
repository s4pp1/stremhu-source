from pydantic import BaseModel, ConfigDict


class IndexerDefinition(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: str
    name: str
    url: str
    details_path: str
    requires_full_download: bool


class IndexerDefinitionLogin(BaseModel):
    username: str
    password: str
    cookies: dict[str, str] | None = None


class IndexerDefinitionTorrent(BaseModel):
    torrent_id: str
    download_url: str
    imdb_id: str | None = None
    seeders: int = 0
    attribute_ids: list[str] = []


class IndexerDefinitionFindTorrentsResult(BaseModel):
    torrents: list[IndexerDefinitionTorrent] = []
    next_page: int | None = None
