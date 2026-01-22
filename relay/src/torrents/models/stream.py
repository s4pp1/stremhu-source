from typing import List

from torrents.models.stream_piece import StreamPiece


class Stream:
    def __init__(self):
        self.stream_pieces: List[StreamPiece] = []

    def set_stream_pieces(
        self,
        pieces: List[StreamPiece],
    ):
        self.stream_pieces = pieces
        return self.stream_pieces
