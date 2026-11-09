import asyncio
import datetime
import hashlib
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException, status

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.service import IndexerAccountsService
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.indexer_definitions.schemas.internal import IndexerDefinitionTorrent
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.ncore_rss.models import NcoreRssItemModel
from app.modules.ncore_rss.repository import NcoreRssRepository
from app.modules.ncore_rss.schemas import (
    NcoreRssEntry,
    NcoreRssFeedUpdate,
    NcoreRssItemResponse,
    NcoreRssItemUpdate,
    NcoreRssManualItemCreate,
    NcoreRssStatusResponse,
    is_ncore_download_url,
    torrent_id_from_url,
)

_ncore_rss_sync_lock = asyncio.Lock()


class NcoreRssService:
    def __init__(
        self,
        repository: NcoreRssRepository,
        indexer_accounts_service: IndexerAccountsService,
        indexer_definitions_service: IndexerDefinitionsService,
    ):
        self._repository = repository
        self._indexer_accounts_service = indexer_accounts_service
        self._indexer_definitions_service = indexer_definitions_service

    def get_status(self) -> NcoreRssStatusResponse:
        settings = self._repository.get_settings()
        total_items, unresolved_items = self._repository.get_counts()
        return NcoreRssStatusResponse(
            ncore_connected=(
                self._indexer_accounts_service.find_by_id("ncore") is not None
            ),
            configured=settings is not None,
            last_synced_at=settings.last_synced_at if settings else None,
            total_items=total_items,
            unresolved_items=unresolved_items,
        )

    def get_items(self) -> list[NcoreRssItemResponse]:
        return [
            NcoreRssItemResponse(
                torrent_id=item.torrent_id,
                title=item.title,
                source_url=item.source_url,
                download_url=item.manual_download_url or item.download_url,
                detected_imdb_id=item.detected_imdb_id,
                manual_imdb_id=item.manual_imdb_id,
                imdb_id=item.manual_imdb_id or item.detected_imdb_id,
                seeders=item.seeders,
                is_manual=item.is_manual,
                last_seen_at=item.last_seen_at,
            )
            for item in self._repository.find_list()
        ]

    async def configure_feed(
        self, payload: NcoreRssFeedUpdate
    ) -> NcoreRssStatusResponse:
        self._ensure_ncore_account()
        async with _ncore_rss_sync_lock:
            entries = await self._fetch_feed(payload.feed_url)
            self._repository.set_feed_url(payload.feed_url)
            self._repository.upsert_items(entries)
            self._repository.set_last_synced_at(datetime.datetime.now())
        return self.get_status()

    def clear_feed(self) -> NcoreRssStatusResponse:
        self._repository.clear_feed_url()
        return self.get_status()

    async def sync(self) -> NcoreRssStatusResponse:
        self._ensure_ncore_account()
        async with _ncore_rss_sync_lock:
            settings = self._repository.get_settings()
            if settings is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Előbb add meg az nCore RSS feed hivatkozását.",
                )
            entries = await self._fetch_feed(settings.feed_url)
            self._repository.upsert_items(entries)
            self._repository.set_last_synced_at(datetime.datetime.now())
        return self.get_status()

    async def update_item(
        self,
        torrent_id: str,
        payload: NcoreRssItemUpdate,
        update_imdb_id: bool,
        update_download_url: bool,
    ) -> NcoreRssItemResponse:
        item = self._repository.find_by_torrent_id(torrent_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A feed elem nem található.",
            )

        download_url = payload.download_url
        if download_url:
            query = parse_qs(urlparse(download_url).query)
            if query.get("action", [None])[0] == "details":
                details = await self._find_torrent(
                    torrent_id_from_url(download_url) or ""
                )
                if details is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="A torrent letöltési hivatkozása nem oldható fel.",
                    )
                download_url = details.download_url

        updated = self._repository.update_item(
            torrent_id=torrent_id,
            imdb_id=payload.imdb_id if update_imdb_id else item.manual_imdb_id,
            download_url=download_url,
            update_download_url=update_download_url,
        )
        assert updated is not None
        return self._to_response(updated)

    async def add_manual_item(
        self,
        payload: NcoreRssManualItemCreate,
    ) -> NcoreRssItemResponse:
        self._ensure_ncore_account()
        download_url = payload.download_url
        torrent_id = torrent_id_from_url(download_url)
        if torrent_id is None:
            if not is_ncore_download_url(download_url):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Érvényes nCore torrent letöltési link szükséges.",
                )
            torrent_id = (
                f"manual-{hashlib.sha256(download_url.encode()).hexdigest()[:32]}"
            )

        query = parse_qs(urlparse(download_url).query)
        if (
            torrent_id_from_url(download_url)
            and query.get("action", [None])[0] == "details"
        ):
            details = await self._find_torrent(torrent_id)
            if details is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="A megadott nCore torrent nem található.",
                )
            download_url = details.download_url

        item = self._repository.create_manual_item(
            NcoreRssEntry(
                torrent_id=torrent_id,
                title=payload.title,
                source_url=payload.download_url,
                download_url=download_url,
                imdb_id=payload.imdb_id,
            )
        )
        return self._to_response(item)

    async def _fetch_feed(self, feed_url: str) -> list[NcoreRssEntry]:
        try:
            checked_ids = self._repository.find_torrent_ids_recently_checked()
            return await self._ncore_definition().fetch_rss_items(
                feed_url,
                skip_detail_torrent_ids=checked_ids,
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Az nCore RSS feed letöltése vagy feldolgozása nem sikerült.",
            ) from None

    async def _find_torrent(
        self, torrent_id: str
    ) -> IndexerDefinitionTorrent | None:
        try:
            return await self._ncore_definition().find_torrent_by_id(torrent_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Az nCore torrent adatainak lekérése nem sikerült.",
            ) from None

    def _ensure_ncore_account(self) -> IndexerAccountModel:
        account = self._indexer_accounts_service.find_by_id("ncore")
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Előbb jelentkezz be egy nCore fiókkal.",
            )
        return account

    def _ncore_definition(self) -> NcoreIndexerDefinition:
        definition = self._indexer_definitions_service.get_by_id("ncore")
        if not isinstance(definition, NcoreIndexerDefinition):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Az nCore integráció jelenleg nem érhető el.",
            )
        return definition

    def _to_response(self, item: NcoreRssItemModel) -> NcoreRssItemResponse:
        return NcoreRssItemResponse(
            torrent_id=item.torrent_id,
            title=item.title,
            source_url=item.source_url,
            download_url=item.manual_download_url or item.download_url,
            detected_imdb_id=item.detected_imdb_id,
            manual_imdb_id=item.manual_imdb_id,
            imdb_id=item.manual_imdb_id or item.detected_imdb_id,
            seeders=item.seeders,
            is_manual=item.is_manual,
            last_seen_at=item.last_seen_at,
        )
