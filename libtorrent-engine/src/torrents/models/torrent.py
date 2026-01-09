from typing import Dict, List, Optional

from torrents.models.file import File


class Torrent:
    files: Dict[int, File] = {}

    def __init__(
        self,
        current_priorities: List[int],
        default_priorities: List[int],
    ):
        self.current_priorities = current_priorities
        self.default_priorities = default_priorities

    def get_file(
        self,
        file_index: int,
    ) -> Optional[File]:
        if file_index not in self.files:
            return None
        return self.files[file_index]

    def get_or_raise_file(
        self,
        file_index: int,
    ) -> File:
        file = self.get_file(file_index)
        if not file:
            raise KeyError(f'A(z) "{file_index}" nem létezik.')
        return file

    def get_or_create_file(
        self,
        file_index: int,
        start_piece_index: int,
        end_piece_index: int,
    ) -> File:
        file = self.get_file(file_index)

        if file:
            return file

        file_state = File(
            start_piece_index=start_piece_index,
            end_piece_index=end_piece_index,
        )
        self.files[file_index] = file_state
        return self.files[file_index]

    def set_current_priorities(
        self,
        priorities: List[int],
    ) -> None:
        self.current_priorities = priorities
