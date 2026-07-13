from __future__ import annotations

from dataclasses import dataclass, field

from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.torrent_streams.utils.resolver_helpers import is_sample_or_trash
from app.modules.torrent_streams.utils.series_parser import SeriesParser


@dataclass
class FileNode:
    name: str
    file_info: TorrentFileInfo


@dataclass
class FolderNode:
    name: str
    children: dict[str, FileNode | FolderNode] = field(default_factory=dict)


class StreamFileResolver:
    def __init__(
        self,
        torrent_info: TorrentInfo,
        series: SeriesInfo | None = None,
    ):
        self.torrent_info = torrent_info
        self.series = series

        self.valid_files = [
            file for file in torrent_info.files if not is_sample_or_trash(file.name)
        ]

    @staticmethod
    def _get_largest_video_file(
        valid_files: list[TorrentFileInfo],
    ) -> TorrentFileInfo:
        return max(valid_files, key=lambda f: f.size)

    def _build_tree(self) -> FolderNode:
        root = FolderNode(
            name=self.torrent_info.name,
        )

        for file in self.valid_files:
            parts = file.path.split("/")
            current_node = root

            for index, part in enumerate(parts):
                if index == len(parts) - 1:
                    current_node.children[part] = FileNode(
                        name=part,
                        file_info=file,
                    )
                else:
                    if part not in current_node.children:
                        current_node.children[part] = FolderNode(name=part)

                    next_node = current_node.children[part]

                    if isinstance(next_node, FolderNode):
                        current_node = next_node
        return root

    def _get_all_files_in_folder(self, folder: FolderNode) -> list[TorrentFileInfo]:
        files: list[TorrentFileInfo] = []
        for child in folder.children.values():
            if isinstance(child, FileNode):
                files.append(child.file_info)
            elif isinstance(child, FolderNode):
                files.extend(self._get_all_files_in_folder(child))
        return files

    def _traverse_tree(
        self,
        node: FolderNode | FileNode,
        inherited_season: int | None,
    ) -> list[TorrentFileInfo]:
        if self.series is None:
            return []

        if isinstance(node, FileNode):
            parser = SeriesParser(node.name)
            seasons, episodes = parser.parse(
                context_seasons=[inherited_season] if inherited_season else None
            )

            file_season = inherited_season

            if seasons and len(seasons) == 1:
                file_season = seasons[0]

            effective_file_season = file_season if file_season is not None else 1

            if (
                effective_file_season == self.series.season
                and episodes
                and self.series.episode in episodes
            ):
                return [node.file_info]
            return []

        elif isinstance(node, FolderNode):
            parser = SeriesParser(node.name)
            seasons, episodes = parser.parse()

            folder_season = inherited_season

            if seasons and len(seasons) == 1:
                folder_season = seasons[0]

            if folder_season is not None and folder_season != self.series.season:
                return []

            effective_folder_season = folder_season if folder_season is not None else 1

            if (
                effective_folder_season == self.series.season
                and episodes
                and len(episodes) == 1
                and self.series.episode in episodes
            ):
                return self._get_all_files_in_folder(node)

            matches: list[TorrentFileInfo] = []

            for child in node.children.values():
                matches.extend(
                    self._traverse_tree(
                        child,
                        folder_season,
                    )
                )

            return matches

    def resolve(self) -> TorrentFileInfo | None:
        if not self.valid_files:
            return None

        # Filmek esetén: csak visszaadjuk a legnagyobbat
        if not self.series:
            return self._get_largest_video_file(self.valid_files)

        # Torrent root feldolgozása (gyökér kontextus) egyszer
        torrent_seasons, torrent_episodes = SeriesParser(self.torrent_info.name).parse()

        if torrent_seasons and self.series.season not in torrent_seasons:
            return None

        # Early optimization 1: Exact episode match in torrent name
        if torrent_episodes:
            exact_episode = len(torrent_episodes) == 1
            if exact_episode:
                if self.series.episode in torrent_episodes:
                    return self._get_largest_video_file(self.valid_files)
                else:
                    return None

        # Fa felépítése
        root_node = self._build_tree()

        # A root node nevének (torrent_info.name) feldolgozása már megtörtént feljebb.
        inherited_season = torrent_seasons[0] if len(torrent_seasons) == 1 else None

        exact_matches: list[TorrentFileInfo] = []

        for child in root_node.children.values():
            exact_matches.extend(
                self._traverse_tree(
                    child,
                    inherited_season,
                )
            )

        if exact_matches:
            return self._get_largest_video_file(exact_matches)

        return None
