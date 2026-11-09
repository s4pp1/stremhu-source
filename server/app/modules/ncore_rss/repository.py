import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.ncore_rss.models import NcoreRssItemModel, NcoreRssSettingsModel
from app.modules.ncore_rss.schemas import NcoreRssEntry


class NcoreRssRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self) -> NcoreRssSettingsModel | None:
        return self.db.get(NcoreRssSettingsModel, "main")

    def set_feed_url(self, feed_url: str) -> NcoreRssSettingsModel:
        settings = self.get_settings()
        if settings is None:
            settings = NcoreRssSettingsModel(id="main", feed_url=feed_url)
            self.db.add(settings)
        else:
            settings.feed_url = feed_url
        self.db.flush()
        return settings

    def clear_feed_url(self) -> None:
        settings = self.get_settings()
        if settings:
            self.db.delete(settings)
            self.db.flush()

    def set_last_synced_at(self, value: datetime.datetime) -> None:
        settings = self.get_settings()
        if settings:
            settings.last_synced_at = value
            self.db.flush()

    def upsert_items(self, entries: list[NcoreRssEntry]) -> None:
        now = datetime.datetime.now()
        for entry in entries:
            item = self.db.get(NcoreRssItemModel, entry.torrent_id)
            if item is None:
                item = NcoreRssItemModel(
                    torrent_id=entry.torrent_id,
                    title=entry.title,
                    source_url=entry.source_url,
                    download_url=entry.download_url,
                    detected_imdb_id=entry.imdb_id,
                    last_detail_checked_at=entry.last_detail_checked_at,
                    seeders=entry.seeders,
                    last_seen_at=now,
                )
                self.db.add(item)
                continue

            item.title = entry.title or item.title
            item.source_url = entry.source_url or item.source_url
            item.download_url = entry.download_url or item.download_url
            item.detected_imdb_id = entry.imdb_id or item.detected_imdb_id
            if entry.last_detail_checked_at is not None:
                item.last_detail_checked_at = entry.last_detail_checked_at
            item.seeders = entry.seeders if entry.seeders is not None else item.seeders
            item.last_seen_at = now

        self.db.flush()

    def create_manual_item(self, entry: NcoreRssEntry) -> NcoreRssItemModel:
        item = self.db.get(NcoreRssItemModel, entry.torrent_id)
        if item is None:
            item = NcoreRssItemModel(
                torrent_id=entry.torrent_id,
                title=entry.title,
                source_url=entry.source_url,
                manual_download_url=entry.download_url,
                manual_imdb_id=entry.imdb_id,
                is_manual=True,
            )
            self.db.add(item)
        else:
            item.title = entry.title
            item.source_url = entry.source_url
            item.manual_download_url = entry.download_url
            item.manual_imdb_id = entry.imdb_id
            item.is_manual = True
        self.db.flush()
        return item

    def update_item(
        self,
        torrent_id: str,
        imdb_id: str | None,
        download_url: str | None = None,
        update_download_url: bool = False,
    ) -> NcoreRssItemModel | None:
        item = self.db.get(NcoreRssItemModel, torrent_id)
        if item is None:
            return None
        item.manual_imdb_id = imdb_id
        if update_download_url:
            item.manual_download_url = download_url
        self.db.flush()
        return item

    def find_list(self, limit: int = 500) -> list[NcoreRssItemModel]:
        return list(
            self.db.scalars(
                select(NcoreRssItemModel)
                .order_by(
                    NcoreRssItemModel.last_seen_at.desc(),
                    NcoreRssItemModel.created_at.desc(),
                )
                .limit(limit)
            ).all()
        )

    def find_torrent_ids_recently_checked(self) -> set[str]:
        retry_after = datetime.datetime.now() - datetime.timedelta(hours=24)
        rows = self.db.scalars(
            select(NcoreRssItemModel.torrent_id).where(
                NcoreRssItemModel.last_detail_checked_at.is_not(None),
                NcoreRssItemModel.last_detail_checked_at >= retry_after,
            )
        ).all()
        return set(rows)

    def find_by_torrent_id(self, torrent_id: str) -> NcoreRssItemModel | None:
        return self.db.get(NcoreRssItemModel, torrent_id)

    def find_by_imdb_id(self, imdb_id: str) -> list[NcoreRssItemModel]:
        return list(
            self.db.scalars(
                select(NcoreRssItemModel).where(
                    or_(
                        NcoreRssItemModel.manual_imdb_id == imdb_id,
                        and_(
                            NcoreRssItemModel.manual_imdb_id.is_(None),
                            NcoreRssItemModel.detected_imdb_id == imdb_id,
                        ),
                    )
                )
            ).all()
        )

    def get_counts(self) -> tuple[int, int]:
        total = self.db.scalar(select(func.count()).select_from(NcoreRssItemModel)) or 0
        unresolved = (
            self.db.scalar(
                select(func.count())
                .select_from(NcoreRssItemModel)
                .where(
                    and_(
                        NcoreRssItemModel.manual_imdb_id.is_(None),
                        NcoreRssItemModel.detected_imdb_id.is_(None),
                    )
                )
            )
            or 0
        )
        return total, unresolved
