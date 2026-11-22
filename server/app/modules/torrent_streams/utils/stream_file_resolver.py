from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.torrent_streams.utils.resolver_helpers import (
    is_extra_file,
    is_extra_folder,
    is_sample_or_trash,
)
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
        imdb_id: str | None = None,
    ):
        self.torrent_info = torrent_info
        self.series = series
        self.imdb_id = imdb_id

        self.valid_files = [
            file for file in torrent_info.files if not is_sample_or_trash(file.name)
        ]

        self.target_seasons: set[int] = set()
        self.target_episodes: set[int] = set()
        self.alt_episodes_set: set[int] = set()
        self.alt_seasons_set: set[int] = set()
        if self.series:
            self.target_seasons.add(self.series.season)
            if self.series.alternate_seasons:
                self.target_seasons.update(self.series.alternate_seasons)
                self.alt_seasons_set.update(self.series.alternate_seasons)
            if self.series.episode is not None:
                self.target_episodes.add(self.series.episode)
            if self.series.alternate_episodes:
                self.target_episodes.update(self.series.alternate_episodes)
                self.alt_episodes_set.update(self.series.alternate_episodes)

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

    def _get_target_seasons(self) -> set[int]:
        return self.target_seasons

    def _get_target_episodes(self) -> set[int]:
        return self.target_episodes

    def _traverse_tree(
        self,
        node: FolderNode | FileNode,
        inherited_season: int | None,
    ) -> list[TorrentFileInfo]:
        if self.series is None:
            return []

        if isinstance(node, FileNode):
            # Extrák/minta fájlok szűrése, kivéve ha kifejezetten a 0. évadot keressük
            if 0 not in self.target_seasons and is_extra_file(node.name):
                return []

            parser = SeriesParser(node.name)
            seasons, episodes = parser.parse(
                context_seasons=[inherited_season] if inherited_season else None
            )

            file_season = inherited_season

            if seasons and len(seasons) == 1:
                file_season = seasons[0]

            if self._is_episode_match(
                file_info=node.file_info,
                file_season=file_season,
                seasons=seasons,
                episodes=episodes,
            ):
                return [node.file_info]
            return []

        elif isinstance(node, FolderNode):
            seasons: list[int] = []
            episodes: list[int] = []

            # Ha a mappa neve extrákra/különkiadásokra utal (pl. Extras, Specials, Bonus, NCED...)
            if is_extra_folder(node.name):
                if 0 not in self.target_seasons:
                    return []
                folder_season = 0
            else:
                parser = SeriesParser(node.name)
                seasons, episodes = parser.parse(allow_standalone_episode=False)

                folder_season = inherited_season

                if seasons and len(seasons) == 1:
                    folder_season = seasons[0]
                elif not seasons:
                    # Számozott évadmappa felismerése (pl. "01. Noragami" -> 1. évad, "02. Noragami Aragoto" -> 2. évad)
                    lead_match = re.match(r"^0*([1-9]\d?)[ ._\-]+", node.name.strip())
                    if lead_match:
                        folder_season = int(lead_match.group(1))

            if folder_season is not None and folder_season not in self.target_seasons:
                if 0 in self.target_seasons:
                    # Különkiadások (0. évad) keresésekor az évadmappákban is lehetnek Extrák almappák
                    pass
                elif folder_season == 0 or not self.alt_episodes_set:
                    # Ha a mappa kifejezetten a 0. évad (extrák/specials), vagy nincs alternatív számozás,
                    # akkor azonnal elvetjük (a különkiadások sosem kapnak abszolút TV anime számozást!)
                    return []

            # Először megnézzük, hogy az almappákban/fájlokban van-e közvetlen találat
            matches: list[TorrentFileInfo] = []
            for child in node.children.values():
                matches.extend(
                    self._traverse_tree(
                        child,
                        folder_season,
                    )
                )

            if matches:
                return matches

            # Csak ha a gyermekelemek nem adtak konkrét találatot, akkor vizsgáljuk,
            # hogy maga a mappa képviseli-e a keresett epizódot (pl. S01E01 nevű mappa egy videóval)
            folder_season_ok = (
                folder_season in self.target_seasons
                if folder_season is not None
                else (self.series.season == 1 or 1 in self.target_seasons)
            )
            if (
                folder_season_ok
                and episodes
                and len(episodes) == 1
                and (
                    episodes[0] in self.alt_episodes_set
                    or (episodes[0] == self.series.episode and folder_season_ok)
                )
            ):
                return self._get_all_files_in_folder(node)

            return []

    def _is_episode_match(
        self,
        file_info: TorrentFileInfo,
        file_season: int | None,
        seasons: list[int],
        episodes: list[int],
    ) -> bool:
        if not self.series or not episodes:
            return False

        # 1. Relatív epizód közvetlen egyezése a megfelelő évadban (pl. S02E01 vagy Season 2 mappában "01.mkv")
        if self.series.episode in episodes:
            if file_season is not None:
                if file_season in self.target_seasons:
                    return True
            elif seasons:
                if any(s in self.target_seasons for s in seasons):
                    return True
            else:
                # Nincs megadva évad sehol (pl. "Anime - 02.mkv") -> csak akkor egyezhet,
                # ha az 1. évadot keressük!
                if self.series.season == 1 or 1 in self.target_seasons:
                    return True

        # 2. Abszolút epizódszámozás egyezése (pl. anime: Ep 39 vagy flat pakkban Ep 13 ami S02E01)
        # Csak akkor engedjük, ha nincsenek alternatív évadpárok (azokat a 3. pont kezeli)
        # És ha a fájl egyértelműen egy későbbi évad (évad > 1) mappájában van, ott a számozás relatív,
        # ezért a fájl 13. része nem lehet az 1. rész!
        if (
            not self.alt_seasons_set
            and self.alt_episodes_set
            and any(alt in self.alt_episodes_set for alt in episodes)
        ):
            if (
                file_season is not None
                and file_season > 1
                and file_season in self.target_seasons
            ):
                return False
            return True

        # 3. Alternatív évad és epizód párok egyezése (pl. One Piece S21E01 amikor S1E892 a kérés)
        if self.alt_seasons_set and self.alt_episodes_set:
            if any(e in self.alt_episodes_set for e in episodes):
                if file_season is not None:
                    if file_season in self.alt_seasons_set:
                        return True
                elif seasons:
                    if any(s in self.alt_seasons_set for s in seasons):
                        return True
                else:
                    if 1 in self.alt_seasons_set:
                        return True

        return False

    def resolve(self) -> TorrentFileInfo | None:
        if not self.valid_files:
            return None

        # Filmek esetén: csak visszaadjuk a legnagyobbat
        if not self.series:
            return self._get_largest_video_file(self.valid_files)

        # Torrent root feldolgozása (gyökér kontextus) egyszer
        torrent_seasons, torrent_episodes = SeriesParser(self.torrent_info.name).parse(
            allow_standalone_episode=False
        )

        if torrent_seasons:
            season_allowed = any(s in self.target_seasons for s in torrent_seasons)
            # Ha a torrent évada nem egyezik a célévaddal, de a torrent neve konkrétan egy abszolút
            # epizódot jelöl, vagy egy teljes pakk (nincs konkrét epizód a torrent nevében), engedélyezzük.
            # DE ha a torrent címében explicit más évad és más epizód van (pl. S01E02 mikor S03E02-t keresünk),
            # akkor nem engedélyezzük!
            if not season_allowed and self.alt_episodes_set:
                if torrent_episodes and any(
                    ep in self.alt_episodes_set for ep in torrent_episodes
                ):
                    season_allowed = True
                elif not torrent_episodes:
                    season_allowed = True
            if not season_allowed and 0 in self.target_seasons and not torrent_episodes:
                season_allowed = True
            if not season_allowed:
                return None

        # Early optimization: Ha a torrent címe maga egyetlen konkrét epizódot jelöl és egyetlen fájl
        if (
            len(self.valid_files) == 1
            and torrent_episodes
            and len(torrent_episodes) == 1
        ):
            ep = torrent_episodes[0]
            is_absolute_match = ep in self.alt_episodes_set
            season_ok = (
                any(s in self.target_seasons for s in torrent_seasons)
                if torrent_seasons
                else (self.series.season == 1 or 1 in self.target_seasons)
            )
            is_relative_match = ep == self.series.episode and season_ok

            is_alt_pair_match = False
            if self.alt_seasons_set and self.alt_episodes_set:
                alt_season_ok = (
                    any(s in self.alt_seasons_set for s in torrent_seasons)
                    if torrent_seasons
                    else (1 in self.alt_seasons_set)
                )
                if ep in self.alt_episodes_set and alt_season_ok:
                    is_alt_pair_match = True

            if is_absolute_match or is_relative_match or is_alt_pair_match:
                return self._get_largest_video_file(self.valid_files)
            else:
                return None

        # Fa felépítése
        root_node = self._build_tree()

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
