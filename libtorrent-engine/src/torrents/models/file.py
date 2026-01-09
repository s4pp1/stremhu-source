from typing import Dict

from torrents.models.stream import Stream


class File:
    streams: Dict[str, Stream] = {}

    def __init__(
        self,
        start_piece_index: int,
        end_piece_index: int,
    ):
        self.start_piece_index = start_piece_index
        self.end_piece_index = end_piece_index

    def get_stream(
        self,
        stream_id: str,
    ) -> Stream | None:
        if stream_id not in self.streams:
            return None
        return self.streams[stream_id]

    def get_or_raise_stream(self, stream_id: str) -> Stream:
        stream = self.get_stream(stream_id)
        if not stream:
            raise KeyError(f'A(z) "{stream}" nem létezik.')
        return stream

    def get_or_create_stream(
        self,
        stream_id: str,
    ):
        stream = self.get_stream(stream_id)

        if stream:
            return stream

        stream_state = Stream()
        self.streams[stream_id] = stream_state
        return self.streams[stream_id]
