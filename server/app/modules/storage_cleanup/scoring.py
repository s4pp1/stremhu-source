from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.modules.storage_cleanup.enums import StorageCleanupScoreComponentKeyEnum

GIB = 1024**3

# A pontozás minden komponense 0 és a súlya között van, így a maximum 100 pont.
FIRST_PLAYED_MAX_POINTS = 30.0
LAST_PLAYED_MAX_POINTS = 25.0
DOWNLOADED_MAX_POINTS = 20.0
SEEDERS_MAX_POINTS = 10.0
LEECHERS_MAX_POINTS = 10.0
UPLOADED_MAX_POINTS = 5.0

PLAYED_WINDOW_DAYS = 30.0
DOWNLOADED_CAP_BYTES = 80 * GIB
SEEDERS_CAP = 50
LEECHERS_CAP = 20
UPLOADED_CAP_BYTES = 5 * GIB

MISSING_SWARM_POINTS = 5.0

COMPONENT_MAX_POINTS: Mapping[StorageCleanupScoreComponentKeyEnum, float] = {
    StorageCleanupScoreComponentKeyEnum.FIRST_PLAYED: FIRST_PLAYED_MAX_POINTS,
    StorageCleanupScoreComponentKeyEnum.LAST_PLAYED: LAST_PLAYED_MAX_POINTS,
    StorageCleanupScoreComponentKeyEnum.DOWNLOADED: DOWNLOADED_MAX_POINTS,
    StorageCleanupScoreComponentKeyEnum.SEEDERS: SEEDERS_MAX_POINTS,
    StorageCleanupScoreComponentKeyEnum.LEECHERS: LEECHERS_MAX_POINTS,
    StorageCleanupScoreComponentKeyEnum.UPLOADED: UPLOADED_MAX_POINTS,
}


@dataclass(frozen=True)
class TorrentMetrics:
    created_at: datetime
    last_played_at: datetime
    downloaded_bytes: int
    uploaded_bytes: int
    seeders: int
    leechers: int
    swarm_known: bool


def to_local_naive(value: datetime) -> datetime:
    """Az adatbázis időbélyegei időzónával jönnek vissza, a számítás helyi időben fut."""
    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


@dataclass(frozen=True)
class ScoreBreakdown:
    first_played: float
    last_played: float
    downloaded: float
    seeders: float
    leechers: float
    uploaded: float

    def points(self) -> dict[StorageCleanupScoreComponentKeyEnum, float]:
        return {
            StorageCleanupScoreComponentKeyEnum.FIRST_PLAYED: self.first_played,
            StorageCleanupScoreComponentKeyEnum.LAST_PLAYED: self.last_played,
            StorageCleanupScoreComponentKeyEnum.DOWNLOADED: self.downloaded,
            StorageCleanupScoreComponentKeyEnum.SEEDERS: self.seeders,
            StorageCleanupScoreComponentKeyEnum.LEECHERS: self.leechers,
            StorageCleanupScoreComponentKeyEnum.UPLOADED: self.uploaded,
        }

    @property
    def total(self) -> int:
        return min(100, max(0, int(sum(self.points().values()) + 0.5)))


def _age_days(value: datetime, now: datetime) -> float:
    return max(0.0, (now - to_local_naive(value)).total_seconds() / 86400)


def calculate_score(
    metrics: TorrentMetrics,
    now: datetime | None = None,
) -> ScoreBreakdown:
    reference = now or datetime.now()

    first_played = min(_age_days(metrics.created_at, reference) / PLAYED_WINDOW_DAYS, 1)
    last_played = min(
        _age_days(metrics.last_played_at, reference) / PLAYED_WINDOW_DAYS, 1
    )

    downloaded = min(max(metrics.downloaded_bytes, 0) / DOWNLOADED_CAP_BYTES, 1)

    if metrics.swarm_known:
        seeders = min(max(metrics.seeders, 0) / SEEDERS_CAP, 1) * SEEDERS_MAX_POINTS
        leechers = (
            1 - min(max(metrics.leechers, 0) / LEECHERS_CAP, 1)
        ) * LEECHERS_MAX_POINTS
    else:
        # Ismeretlen raj: mindkét komponens semleges, félsúlyos értéket kap.
        seeders = MISSING_SWARM_POINTS
        leechers = MISSING_SWARM_POINTS

    uploaded = 1 - min(max(metrics.uploaded_bytes, 0) / UPLOADED_CAP_BYTES, 1)

    return ScoreBreakdown(
        first_played=first_played * FIRST_PLAYED_MAX_POINTS,
        last_played=last_played * LAST_PLAYED_MAX_POINTS,
        downloaded=downloaded * DOWNLOADED_MAX_POINTS,
        seeders=seeders,
        leechers=leechers,
        uploaded=uploaded * UPLOADED_MAX_POINTS,
    )
