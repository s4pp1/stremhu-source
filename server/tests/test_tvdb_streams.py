from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.torrent_streams.utils.series_parser import SeriesParser
from app.modules.torrent_streams.utils.stream_file_resolver import StreamFileResolver


def test_anime_series_parser_cases():
    # Naruto 3-jegyű számok
    s, e = SeriesParser("Naruto - 105.mkv").parse()
    assert s == []
    assert e == [105]

    s, e = SeriesParser("Naruto Shippuden - 215 [1080p].mkv").parse()
    assert s == []
    assert e == [215]

    # Attack on Titan Final Season & Arc
    s, e = SeriesParser(
        "[Erai-raws] Shingeki no Kyojin The Final Season - 01 [1080p].mkv"
    ).parse()
    assert s == [4]
    assert e == [1]

    s, e = SeriesParser("Attack.on.Titan.S04E17.1080p.mkv").parse()
    assert s == [4]
    assert e == [17]

    # Demon Slayer Arcs (arc nevek nincsenek beleégetve, epizódszámokat generikusan bontja ki)
    s, e = SeriesParser(
        "[SubsPlease] Kimetsu no Yaiba - Hashira Geiko-hen - 01 (1080p).mkv"
    ).parse()
    assert s == []
    assert e == [1]

    s, e = SeriesParser("Kimetsu no Yaiba - Yuukaku-hen 01.mkv").parse()
    assert s == []
    assert e == [1]

    s, e = SeriesParser("Demon.Slayer.Mugen.Train.Arc.E01.1080p.mkv").parse()
    assert s == []
    assert e == [1]


def test_anime_stream_file_resolver_matching():
    def make_file(name: str, index: int) -> TorrentFileInfo:
        return TorrentFileInfo(
            name=name,
            path=name,
            size=1000,
            offset=index * 1000,
            start_piece_index=index,
            end_piece_index=index,
            is_video=True,
            index=index,
        )

    # Demon Slayer S2E8 (Yuukaku ep 1)
    t_info_ds = TorrentInfo(
        info_hash="hash_ds",
        name="Kimetsu no Yaiba Yuukaku-hen",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Kimetsu no Yaiba - Yuukaku-hen - 01.mkv", 0),
            make_file("Kimetsu no Yaiba - Yuukaku-hen - 02.mkv", 1),
        ],
    )
    res_ds = StreamFileResolver(
        t_info_ds,
        series=SeriesInfo(season=2, episode=8, alternate_episodes=[1]),
    ).resolve()
    assert res_ds is not None
    assert res_ds.name == "Kimetsu no Yaiba - Yuukaku-hen - 01.mkv"

    # Attack on Titan S4E16 (abszolút ep 75)
    t_info_aot = TorrentInfo(
        info_hash="hash_aot",
        name="Shingeki no Kyojin Pack",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Shingeki no Kyojin - 74.mkv", 0),
            make_file("Shingeki no Kyojin - 75.mkv", 1),
        ],
    )
    res_aot = StreamFileResolver(
        t_info_aot,
        series=SeriesInfo(season=4, episode=16, alternate_episodes=[75]),
    ).resolve()
    assert res_aot is not None
    assert res_aot.name == "Shingeki no Kyojin - 75.mkv"

    # Naruto S1E5: nem keveri össze a 105. résszel!
    t_info_naruto = TorrentInfo(
        info_hash="hash_naruto",
        name="Naruto Pack",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Naruto - 005.mkv", 0),
            make_file("Naruto - 105.mkv", 1),
        ],
    )
    res_naruto = StreamFileResolver(
        t_info_naruto, series=SeriesInfo(season=1, episode=5)
    ).resolve()
    assert res_naruto is not None
    assert res_naruto.name == "Naruto - 005.mkv"


def test_one_piece_series_parser_and_resolver():
    # 1. SeriesParser generikus tesztek
    p1 = SeriesParser("[SubsPlease] One Piece - 1089 (1080p) [98E7B28B].mkv")
    _, e = p1.parse()
    assert e == [1089]

    p2 = SeriesParser("One Piece - Wano Kuni - 892.mkv")
    _, e = p2.parse()
    assert e == [892]

    p3 = SeriesParser("One Piece - Egghead Arc - 1089.mkv")
    _, e = p3.parse()
    assert e == [1089]

    p4 = SeriesParser("One Piece 890-895.mkv")
    _, e = p4.parse()
    assert e == [890, 891, 892, 893, 894, 895]

    def make_file(name: str, index: int) -> TorrentFileInfo:
        return TorrentFileInfo(
            name=name,
            path=name,
            size=1000,
            offset=index * 1000,
            start_piece_index=index,
            end_piece_index=index,
            is_video=True,
            index=index,
        )

    # 2. Generikus feloldás: S21E01 kérés alternate_episodes=[892]-vel feloldja a "One Piece - 892.mkv" fájlt
    t_info_op1 = TorrentInfo(
        info_hash="hash_op1",
        name="One Piece Batch",
        size=3000,
        piece_size=1000,
        files=[
            make_file("One Piece - 891.mkv", 0),
            make_file("One Piece - 892.mkv", 1),
            make_file("One Piece - 893.mkv", 2),
        ],
    )
    res_cinemeta = StreamFileResolver(
        t_info_op1,
        series=SeriesInfo(season=21, episode=1, alternate_episodes=[892]),
    ).resolve()
    assert res_cinemeta is not None
    assert res_cinemeta.name == "One Piece - 892.mkv"

    # 3. S22E04 kérés alternate_episodes=[1089]-vel feloldja az 1089. részt
    t_info_op2 = TorrentInfo(
        info_hash="hash_op2",
        name="[SubsPlease] One Piece - 1089 (1080p)",
        size=1000,
        piece_size=1000,
        files=[
            make_file("[SubsPlease] One Piece - 1089 (1080p) [98E7B28B].mkv", 0),
        ],
    )
    res_egghead = StreamFileResolver(
        t_info_op2,
        series=SeriesInfo(season=22, episode=4, alternate_episodes=[1089]),
    ).resolve()
    assert res_egghead is not None
    assert res_egghead.name == "[SubsPlease] One Piece - 1089 (1080p) [98E7B28B].mkv"

    # 4. Kitsu kérés S1 E892 feloldja a "One Piece - 892.mkv"-t ÉS a "One.Piece.S21E01.mkv"-t is
    t_info_op_season_name = TorrentInfo(
        info_hash="hash_op3",
        name="One Piece Season 21",
        size=2000,
        piece_size=1000,
        files=[
            make_file("One.Piece.S21E01.1080p.mkv", 0),
            make_file("One.Piece.S21E02.1080p.mkv", 1),
        ],
    )
    res_kitsu_mapped = StreamFileResolver(
        t_info_op_season_name,
        series=SeriesInfo(
            season=1,
            episode=892,
            alternate_seasons=[21],
            alternate_episodes=[1],
        ),
    ).resolve()
    assert res_kitsu_mapped is not None
    assert res_kitsu_mapped.name == "One.Piece.S21E01.1080p.mkv"

    # 5. One Piece S2E1 (Cinemeta) -> feloldás S01-nek elnevezett HorribleSubs pakkból (abszolút 9. rész)
    t_info_op_s01_pack = TorrentInfo(
        info_hash="hash_op_s1",
        name="One Piece S01 480p",
        size=5000,
        piece_size=1000,
        files=[
            make_file("One Piece S01 480p/[HorribleSubs] One Piece - 01 [480p].mkv", 0),
            make_file("One Piece S01 480p/[HorribleSubs] One Piece - 09 [480p].mkv", 1),
        ],
    )
    res_op_s2e1 = StreamFileResolver(
        t_info_op_s01_pack,
        series=SeriesInfo(season=2, episode=1, alternate_episodes=[9]),
    ).resolve()
    assert res_op_s2e1 is not None
    assert "[HorribleSubs] One Piece - 09 [480p].mkv" in res_op_s2e1.name

    # 6. One Piece S5E1 (Cinemeta) -> feloldás S02-nek elnevezett pakkból (abszolút 62. rész)
    t_info_op_s02_pack = TorrentInfo(
        info_hash="hash_op_s2",
        name="One Piece S02 720p",
        size=5000,
        piece_size=1000,
        files=[
            make_file("One Piece S02 720p/[HorribleSubs] One Piece - 62 [720p].mkv", 0),
            make_file("One Piece S02 720p/[HorribleSubs] One Piece - 63 [720p].mkv", 1),
        ],
    )
    res_op_s5e1 = StreamFileResolver(
        t_info_op_s02_pack,
        series=SeriesInfo(season=5, episode=1, alternate_episodes=[62]),
    ).resolve()
    assert res_op_s5e1 is not None
    assert "[HorribleSubs] One Piece - 62 [720p].mkv" in res_op_s5e1.name

    # 7. Naruto Shippuden abszolút ep 500 -> S22E42 feloldása
    t_info_shippuden = TorrentInfo(
        info_hash="hash_ns",
        name="Naruto Shippuden",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Naruto Shippuden - 499.mkv", 0),
            make_file("Naruto Shippuden - 500.mkv", 1),
        ],
    )
    res_ns = StreamFileResolver(
        t_info_shippuden,
        series=SeriesInfo(season=22, episode=42, alternate_episodes=[500]),
    ).resolve()
    assert res_ns is not None
    assert res_ns.name == "Naruto Shippuden - 500.mkv"

    # 8. Attack on Titan Season 3 Episode 2 - S01E02 és standalone "- 02" torrent kizárása, de S03E02 és "- 39" illesztése
    aot_s3_series = SeriesInfo(season=3, episode=2, alternate_episodes=[39])

    # S01E02 explicit 1. évad -> nem szabad illeszkednie!
    t_aot_s01 = TorrentInfo(
        info_hash="hash_aot_s01",
        name="Attack.on.Titan.S01E02.BDRIP.x264-Krissz.mkv",
        size=1000,
        piece_size=500,
        files=[make_file("Attack.on.Titan.S01E02.BDRIP.x264-Krissz.mkv", 0)],
    )
    assert StreamFileResolver(t_aot_s01, series=aot_s3_series).resolve() is None

    # Standalone "- 02" évad nélkül -> nem szabad S3E2-re illeszkednie!
    t_aot_standalone_02 = TorrentInfo(
        info_hash="hash_aot_02",
        name="Shingeki no Kyojin - 02 (BD 1280x720 x264 AAC).mkv",
        size=1000,
        piece_size=500,
        files=[make_file("Shingeki no Kyojin - 02 (BD 1280x720 x264 AAC).mkv", 0)],
    )
    assert (
        StreamFileResolver(t_aot_standalone_02, series=aot_s3_series).resolve() is None
    )

    # S03E02 -> egyeznie kell!
    t_aot_s03 = TorrentInfo(
        info_hash="hash_aot_s03",
        name="attack.on.titan.s03e02.dubbed.hdtv.x264-w4f.mkv",
        size=1000,
        piece_size=500,
        files=[make_file("attack.on.titan.s03e02.dubbed.hdtv.x264-w4f.mkv", 0)],
    )
    res_s03 = StreamFileResolver(t_aot_s03, series=aot_s3_series).resolve()
    assert res_s03 is not None
    assert "s03e02" in res_s03.name

    # Standalone "- 39" abszolút epizódszám -> egyeznie kell S3E2-re!
    t_aot_abs_39 = TorrentInfo(
        info_hash="hash_aot_39",
        name="[ReinForce] Shingeki no Kyojin - 39 (BDRip 1920x1080 x264 FLAC).mkv",
        size=1000,
        piece_size=500,
        files=[
            make_file(
                "[ReinForce] Shingeki no Kyojin - 39 (BDRip 1920x1080 x264 FLAC).mkv", 0
            )
        ],
    )
    res_abs_39 = StreamFileResolver(t_aot_abs_39, series=aot_s3_series).resolve()
    assert res_abs_39 is not None
    assert "- 39" in res_abs_39.name

    # 9. Code Geass R2 és Ordinal Season (pl. 2nd Season) felismerése és feloldása S2E2-re
    cg_s2_series = SeriesInfo(season=2, episode=2)

    # 720p BDRip S01-S02 pakk (ID 2137664)
    t_cg_720p_pack = TorrentInfo(
        info_hash="hash_cg_720p",
        name="Code Geass Lelouch of the Rebellion (BD_1280x720)",
        size=17000,
        piece_size=1000,
        files=[
            make_file(
                "Code Geass Lelouch of the Rebellion (BD_1280x720)/Code Geass Hangyaku no Lelouch - 02 (BD 1280x720 x264 AAC).mkv",
                0,
            ),
            make_file(
                "Code Geass Lelouch of the Rebellion (BD_1280x720)/Code Geass Hangyaku no Lelouch R2 - 02 (BD 1280x720 x264 AAC).mkv",
                1,
            ),
        ],
    )
    res_cg_720p = StreamFileResolver(t_cg_720p_pack, series=cg_s2_series).resolve()
    assert res_cg_720p is not None
    assert "R2 - 02" in res_cg_720p.name

    # 1080p BDRip S01-S02 pakk
    t_cg_1080p_pack = TorrentInfo(
        info_hash="hash_cg_1080p",
        name="Code Geass - Hangyaku no Lelouch S01-S02 (BD_1920x1080)",
        size=54000,
        piece_size=2000,
        files=[
            make_file(
                "Code Geass - Hangyaku no Lelouch S01-S02 (BD_1920x1080)/[Yousei-raws] Code Geass - Hangyaku no Lelouch 02 [BDrip 1920x1080 x264 FLAC].mkv",
                0,
            ),
            make_file(
                "Code Geass - Hangyaku no Lelouch S01-S02 (BD_1920x1080)/[Yousei-raws] Code Geass - Hangyaku no Lelouch R2 02 [BDrip 1920x1080 x264 FLAC].mkv",
                1,
            ),
        ],
    )
    res_cg_1080p = StreamFileResolver(t_cg_1080p_pack, series=cg_s2_series).resolve()
    assert res_cg_1080p is not None
    assert "R2 02" in res_cg_1080p.name

    # Ordinal season (2nd Season)
    t_mob_2nd = TorrentInfo(
        info_hash="hash_mob_2nd",
        name="Mob Psycho 100 2nd Season",
        size=5000,
        piece_size=1000,
        files=[
            make_file("Mob Psycho 100 2nd Season - 02.mkv", 0),
        ],
    )
    res_mob_2nd = StreamFileResolver(
        t_mob_2nd, series=SeriesInfo(season=2, episode=2)
    ).resolve()
    assert res_mob_2nd is not None
    assert "2nd Season - 02" in res_mob_2nd.name
