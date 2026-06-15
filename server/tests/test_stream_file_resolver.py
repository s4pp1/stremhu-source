from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.torrent_streams.utils.stream_file_resolver import StreamFileResolver


def create_file(path: str, size: int, is_video: bool = True) -> TorrentFileInfo:
    return TorrentFileInfo(
        name=path.split("/")[-1],
        path=path,
        index=0,
        size=size,
        offset=0,
        start_piece_index=0,
        end_piece_index=0,
        is_video=is_video,
    )


def test_resolve_movie_largest_file():
    torrent_info = TorrentInfo(
        info_hash="hash",
        name="A.Movie.2023.1080p",
        size=1000,
        piece_size=10,
        files=[
            create_file("sample.mkv", 50, is_video=True),
            create_file("movie.mkv", 800, is_video=True),
            create_file("movie.srt", 10, is_video=False),
        ],
    )
    result = StreamFileResolver.resolve_file(torrent_info, None)
    assert result is not None
    assert result.name == "movie.mkv"


def test_resolve_series_single_episode_torrent():
    torrent_info = TorrentInfo(
        info_hash="hash",
        name="The.Show.S02E04.1080p",
        size=1000,
        piece_size=10,
        files=[
            create_file("random_weird_name_123.mkv", 800, is_video=True),
            create_file("sample.mkv", 50, is_video=True),
        ],
    )
    series = SeriesInfo(season=2, episode=4)
    result = StreamFileResolver.resolve_file(torrent_info, series)
    assert result is not None
    assert result.name == "random_weird_name_123.mkv"


def test_resolve_series_season_pack():
    torrent_info = TorrentInfo(
        info_hash="hash",
        name="The.Show.S02.1080p",
        size=1000,
        piece_size=10,
        files=[
            create_file("03.mkv", 800, is_video=True),
            create_file("04.mkv", 850, is_video=True),
            create_file("05.mkv", 800, is_video=True),
        ],
    )
    series = SeriesInfo(season=2, episode=4)
    result = StreamFileResolver.resolve_file(torrent_info, series)
    assert result is not None
    assert result.name == "04.mkv"


def test_resolve_series_season_pack_with_explicit_season_in_file():
    torrent_info = TorrentInfo(
        info_hash="hash",
        name="The.Show.S02.1080p",
        size=1000,
        piece_size=10,
        files=[
            create_file("The.Show.S02E03.mkv", 800, is_video=True),
            create_file("The.Show.S02E04.mkv", 850, is_video=True),
        ],
    )
    series = SeriesInfo(season=2, episode=4)
    result = StreamFileResolver.resolve_file(torrent_info, series)
    assert result is not None
    assert result.name == "The.Show.S02E04.mkv"


def test_resolve_series_multi_season_pack():
    torrent_info = TorrentInfo(
        info_hash="hash",
        name="The.Show.S01-S03.1080p",
        size=1000,
        piece_size=10,
        files=[
            create_file(
                "04.mkv", 800, is_video=True
            ),  # Has no season in filename, should be skipped
            create_file("S02/The.Show.S02E04.mkv", 850, is_video=True),  # Perfect match
            create_file("S03/The.Show.S03E04.mkv", 850, is_video=True),
        ],
    )
    series = SeriesInfo(season=2, episode=4)
    result = StreamFileResolver.resolve_file(torrent_info, series)
    assert result is not None
    assert result.path == "S02/The.Show.S02E04.mkv"


def test_resolve_series_complete_pack_without_season_in_torrent_name():
    torrent_info = TorrentInfo(
        info_hash="hash",
        name="The.Show.Complete.Series",
        size=1000,
        piece_size=10,
        files=[
            create_file("S02E04.mkv", 850, is_video=True),
            create_file("S03E04.mkv", 850, is_video=True),
        ],
    )
    series = SeriesInfo(season=2, episode=4)
    result = StreamFileResolver.resolve_file(torrent_info, series)
    assert result is not None
    assert result.name == "S02E04.mkv"
