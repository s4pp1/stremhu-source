from pydantic import BaseModel


class TorznabDownloadToken(BaseModel):
    indexer_id: str
    torrent_id: str
