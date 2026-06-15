from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.media_attributes.parser import clean_torrent_name
from app.modules.torrent_streams.utils.resolver_helpers import is_sample_or_trash
from app.modules.torrent_streams.utils.series_parser import parse_season_episode


class StreamFileResolver:
    @staticmethod
    def get_largest_video_file(
        valid_files: list[TorrentFileInfo],
    ) -> TorrentFileInfo:
        return max(valid_files, key=lambda f: f.size)

    @staticmethod
    def resolve_file(
        torrent_info: TorrentInfo,
        series: SeriesInfo | None,
    ) -> TorrentFileInfo | None:
        valid_files = [
            file for file in torrent_info.files if not is_sample_or_trash(file.name)
        ]

        if not valid_files:
            return None

        if not series:
            return StreamFileResolver.get_largest_video_file(valid_files)

        torrent_name_cleaned = clean_torrent_name(torrent_info.name)
        torrent_seasons, torrent_episodes = parse_season_episode(torrent_name_cleaned)

        # Case 2: Torrent root explicitly names exactly this season and exactly this single episode
        if (
            torrent_seasons
            and series.season in torrent_seasons
            and torrent_episodes
            and len(torrent_episodes) == 1
            and series.episode in torrent_episodes
        ):
            return StreamFileResolver.get_largest_video_file(valid_files)

        # Case 3: Search inside the files (Season pack & Multi-season pack)
        best_match: TorrentFileInfo | None = None
        for file in valid_files:
            file_name_cleaned = clean_torrent_name(file.name)
            file_seasons, file_episodes = parse_season_episode(file_name_cleaned)

            if not file_episodes or series.episode not in file_episodes:
                continue

            if file_seasons:
                if series.season in file_seasons:
                    return file
            else:
                if (
                    torrent_seasons
                    and len(torrent_seasons) == 1
                    and series.season in torrent_seasons
                ):
                    if best_match is None or file.size > best_match.size:
                        best_match = file

        return best_match
