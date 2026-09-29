import datetime
import math

from sqlalchemy import func as sqlalchemy_func

from app.modules.playback_histories.models import PlaybackHistoryModel

#: indexer_id → a legrövidebb megtartási idő másodpercben, amit a takarítás
#: ennél az indexernél alkalmazhat. A miértje az adott definíció fejlécében van
#: (integrations/seedpool.py).
STREMHU_KEEP_SEED_FLOOR: dict[str, int] = {
    "seedpool": 864_000,  # 240 óra = 10 nap — a tracker Unsatisfied szabálya
}

STREMHU_SEED_TIME_RULES: dict[str, str] = {
    "cinemaz": "72 óra + 2 óra/GB 50 GB alatt, e fölött 100*ln(GB) - 219.2023",
}

STREMHU_PARTIAL_DOWNLOAD_SECONDS = 60 * 24 * 3600


def _stremhu_required_seed_seconds(
    indexer_id: str, size_bytes: int, full_download: bool | None
) -> int | None:
    """A torrent mérete alapján kötelező megtartás másodpercben."""
    if indexer_id not in STREMHU_SEED_TIME_RULES:
        return None

    if full_download is not True:
        return STREMHU_PARTIAL_DOWNLOAD_SECONDS

    from app.modules.indexer_definitions.integrations.cinemaz import (
        _required_seed_hours,
    )

    size_gb = size_bytes / 1_000_000_000

    return int(math.ceil(_required_seed_hours(size_gb) * 3600))


def _stremhu_obligated_torrent_ids(service, indexer_id: str) -> list[str]:
    repository = service._torrent_repository
    db = repository.db
    now = datetime.datetime.now()

    torrents = (
        db.query(TorrentModel)
        .filter(
            TorrentModel.indexer_id == indexer_id,
            TorrentModel.is_persisted.is_(False),
        )
        .all()
    )

    obligated: list[str] = []
    for torrent in torrents:
        last_played = (
            db.query(sqlalchemy_func.max(PlaybackHistoryModel.created_at))
            .filter(
                PlaybackHistoryModel.indexer_id == torrent.indexer_id,
                PlaybackHistoryModel.torrent_id == torrent.torrent_id,
            )
            .scalar()
        )
        basis = last_played or torrent.created_at

        required = _stremhu_required_seed_seconds(
            indexer_id, torrent.torrent_file.info.size, torrent.full_download
        )
        if required is None:
            continue

        if (now - basis).total_seconds() < required:
            obligated.append(torrent.torrent_id)

    if obligated:
        logger.info(
            "🌱 %s: %s torrent még megtartási kötelezettség alatt áll "
            "(méret-alapú szabály), ezeket a takarítás kihagyja.",
            indexer_id,
            len(obligated),
        )

    return obligated


_stremhu_original_cleanup_tracker_torrents = TorrentsService.cleanup_tracker_torrents

_stremhu_floor_logged: set[str] = set()


def _stremhu_cleanup_tracker_torrents(
    self,
    indexer_id: str,
    keep_seed_seconds: int | None,
    not_completed_torrent_ids: list[str] | None,
) -> None:
    floor = STREMHU_KEEP_SEED_FLOOR.get(indexer_id)

    if floor is not None and (keep_seed_seconds is None or keep_seed_seconds < floor):
        if indexer_id not in _stremhu_floor_logged:
            _stremhu_floor_logged.add(indexer_id)
            logger.warning(
                "🔒 %s: a megtartási idő %s óra a tracker szabálya miatt "
                "(a beállított érték: %s). Ez a stremhu patch; a részletek az "
                "indexer definíció fejlécében.",
                indexer_id,
                floor // 3600,
                "nincs"
                if keep_seed_seconds is None
                else f"{keep_seed_seconds // 3600} óra",
            )

        keep_seed_seconds = floor

    if indexer_id in STREMHU_SEED_TIME_RULES:
        obligated = _stremhu_obligated_torrent_ids(self, indexer_id)
        if obligated:
            not_completed_torrent_ids = sorted(
                set(not_completed_torrent_ids or []) | set(obligated)
            )

    return _stremhu_original_cleanup_tracker_torrents(
        self,
        indexer_id,
        keep_seed_seconds,
        not_completed_torrent_ids,
    )


TorrentsService.cleanup_tracker_torrents = _stremhu_cleanup_tracker_torrents
