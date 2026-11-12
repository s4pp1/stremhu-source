import datetime

from app.modules.storage_cleanup.scoring import (
    COMPONENT_MAX_POINTS,
    ScoreBreakdown,
    TorrentMetrics,
    calculate_score,
    to_local_naive,
)

GIB = 1024**3
NOW = datetime.datetime(2026, 1, 31, 12, 0, 0)


def build_metrics(**overrides: object) -> TorrentMetrics:
    values: dict[str, object] = {
        "created_at": NOW - datetime.timedelta(days=15),
        "last_played_at": NOW - datetime.timedelta(days=30),
        "downloaded_bytes": 40 * GIB,
        "uploaded_bytes": int(2.5 * GIB),
        "seeders": 25,
        "leechers": 10,
        "swarm_known": True,
    }
    values.update(overrides)
    return TorrentMetrics(**values)  # pyright: ignore[reportArgumentType]


def test_components_are_linear_and_total_rounds_half_up():
    breakdown = calculate_score(build_metrics(), NOW)

    assert breakdown.first_played == 15.0
    assert breakdown.last_played == 25.0
    assert breakdown.downloaded == 10.0
    assert breakdown.seeders == 5.0
    assert breakdown.leechers == 5.0
    assert breakdown.uploaded == 2.5
    assert breakdown.total == 63


def test_components_are_capped_and_reversed_where_needed():
    breakdown = calculate_score(
        build_metrics(
            created_at=NOW - datetime.timedelta(days=60),
            last_played_at=NOW - datetime.timedelta(days=60),
            downloaded_bytes=100 * GIB,
            uploaded_bytes=0,
            seeders=100,
            leechers=0,
        ),
        NOW,
    )

    assert breakdown.first_played == 30.0
    assert breakdown.last_played == 25.0
    assert breakdown.downloaded == 20.0
    assert breakdown.seeders == 10.0
    assert breakdown.leechers == 10.0
    assert breakdown.uploaded == 5.0
    assert breakdown.total == 100


def test_missing_swarm_gives_neutral_half_points():
    breakdown = calculate_score(build_metrics(swarm_known=False), NOW)

    assert breakdown.seeders == 5.0
    assert breakdown.leechers == 5.0


def test_future_timestamps_score_zero_for_age_components():
    future = NOW + datetime.timedelta(days=10)

    breakdown = calculate_score(
        build_metrics(created_at=future, last_played_at=future),
        NOW,
    )

    assert breakdown.first_played == 0.0
    assert breakdown.last_played == 0.0
    assert 0 <= breakdown.total <= 100


def test_component_max_points_match_the_weights():
    assert sum(COMPONENT_MAX_POINTS.values()) == 100.0


def test_aware_timestamps_are_converted_to_local_time():
    aware = datetime.datetime.now(datetime.timezone.utc)
    naive = to_local_naive(aware)

    assert naive.tzinfo is None
    assert naive == aware.astimezone().replace(tzinfo=None)


def test_score_breakdown_points_are_ordered_by_component():
    breakdown = ScoreBreakdown(
        first_played=1.0,
        last_played=2.0,
        downloaded=3.0,
        seeders=4.0,
        leechers=5.0,
        uploaded=6.0,
    )

    assert list(breakdown.points().values()) == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert breakdown.total == 21
