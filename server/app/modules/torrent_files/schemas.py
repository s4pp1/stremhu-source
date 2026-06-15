from pydantic import BaseModel


class TorrentFileIdentifier(BaseModel):
    indexer_id: str
    torrent_id: str


class TorrentFilesFilter(BaseModel):
    indexer_id: str | None = None
    torrent_id: str | None = None
    identifiers: list[TorrentFileIdentifier] | None = None
    exclude_persisted: bool | None = None
