from typing import AsyncIterator

from pydantic import BaseModel


class ParsedRangeHeader(BaseModel):
    start_byte: int
    end_byte: int
    content_length: int


class PieceOrFileAvailable(BaseModel):
    piece_available: bool
    file_available: bool


class PlaybackResponse:
    def __init__(
        self,
        iterator: AsyncIterator[bytes],
        start_byte: int,
        end_byte: int,
        file_size: int,
        file_name: str,
    ):
        self.iterator = iterator
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.file_size = file_size
        self.file_name = file_name
