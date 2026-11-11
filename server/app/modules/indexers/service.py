import asyncio

from fastapi import HTTPException, status

from app.common.async_utils import owned_to_thread
from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import (
    IndexerAccountCreate,
    IndexerAccountUpdate,
)
from app.modules.indexer_accounts.service import IndexerAccountsService
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    AuthenticationOtherException,
    CredentialsRequiredException,
)
from app.modules.indexer_definitions.schemas.internal import IndexerDefinitionLogin
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.indexers.schemas.internal import (
    DownloadedTorrentFile,
    IndexerLogin,
    IndexerTorrent,
)
from app.modules.indexers.search import IndexerSearchService, invalidate_indexer_cache
from app.modules.settings.schemas.internal import SystemSettings
from app.modules.settings.service import SettingsService
from app.modules.torrents.schemas.internal import TorrentUpdate
from app.modules.torrents.service import TorrentsService


class IndexersService:
    def __init__(
        self,
        indexer_definitions_service: IndexerDefinitionsService,
        indexer_accounts_service: IndexerAccountsService,
        torrents_service: TorrentsService,
        settings_service: SettingsService,
    ):
        self._indexer_definitions_service = indexer_definitions_service
        self._indexer_accounts_service = indexer_accounts_service
        self._torrents_service = torrents_service
        self._settings_service = settings_service
        self._search = IndexerSearchService(indexer_definitions_service)

    async def login(
        self,
        payload: IndexerLogin,
    ) -> IndexerAccountModel:
        indexer_definition = self._indexer_definitions_service.get_by_id(
            payload.indexer_id
        )
        indexer_account = await owned_to_thread(
            self._indexer_accounts_service.find_by_id,
            indexer_definition.id,
        )

        if indexer_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A megadott '{indexer_definition.name}' már be van jelentkezve!",
            )

        try:
            await indexer_definition.login(
                IndexerDefinitionLogin(
                    username=payload.username,
                    password=payload.password,
                    totp_secret=payload.totp_secret,
                )
            )

            indexer_account = await owned_to_thread(
                self._indexer_accounts_service.create,
                IndexerAccountCreate(
                    indexer_id=indexer_definition.id,
                    username=payload.username,
                    password=payload.password,
                    totp_secret=payload.totp_secret,
                    download_full_torrent=indexer_definition.requires_full_download,
                    cookies=indexer_definition.cookies,
                ),
            )

            invalidate_indexer_cache(indexer_definition.id)
            return indexer_account
        except CredentialsRequiredException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except AuthenticationException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except AuthenticationOtherException as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            )
        except Exception as e:
            logger.error("operation=indexer-login %s", network_error_fields(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bejelentkezés közben hiba történt, próbáld újra!",
            )

    async def update(
        self,
        indexer_id: str,
        payload: IndexerAccountUpdate,
    ) -> IndexerAccountModel:
        indexer_definition = self._indexer_definitions_service.get_by_id(indexer_id)

        if (
            "download_full_torrent" in payload.model_fields_set
            and payload.download_full_torrent
            != indexer_definition.requires_full_download
        ):
            if (
                indexer_definition.requires_full_download
                and payload.download_full_torrent is not True
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Nem lehetséges a '{indexer_definition.name}' letöltési beállításának módosítása!",
                )

            full_download = indexer_definition.requires_full_download

            if payload.download_full_torrent is not None:
                full_download = payload.download_full_torrent

            self._torrents_service.bulk_update_by_indexer_id(
                indexer_id=indexer_id,
                payload=TorrentUpdate(
                    full_download=full_download,
                ),
            )

        return self._indexer_accounts_service.update(indexer_id, payload)

    async def delete(
        self,
        indexer_id: str,
    ) -> None:
        invalidate_indexer_cache(indexer_id)
        self._torrents_service.delete_by_indexer_id(indexer_id)
        self._indexer_accounts_service.delete(indexer_id)

    async def get_torrents_by_torrent_id(
        self,
        torrent_id: str,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        return await self._search.get_torrents_by_torrent_id(torrent_id)

    async def get_torrent_by_torrent_id(
        self,
        indexer_id: str,
        torrent_id: str,
    ) -> IndexerTorrent:
        return await self._search.get_torrent_by_torrent_id(indexer_id, torrent_id)

    async def get_torrents_by_imdb_id(
        self,
        imdb_id: str,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        return await self._search.get_torrents_by_imdb_id(imdb_id)

    async def get_torrents_by_query(
        self,
        query: str,
        media_type: str | None = None,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        return await self._search.get_torrents_by_query(query, media_type=media_type)

    async def download_torrent(
        self,
        indexer_id: str,
        torrent_id: str,
        download_url: str,
    ) -> DownloadedTorrentFile:
        return await self._search.download_torrent(indexer_id, torrent_id, download_url)

    async def cleanup_torrents_by_rules(self) -> None:
        indexer_accounts = await owned_to_thread(
            self._indexer_accounts_service.find_list
        )
        system_settings = await owned_to_thread(self._settings_service.get_system)

        tasks = [
            self.cleanup_torrent_by_rules(indexer_account, system_settings)
            for indexer_account in indexer_accounts
        ]
        await asyncio.gather(*tasks)

    async def cleanup_torrent_by_rules(
        self,
        indexer_account: IndexerAccountModel,
        system_settings: SystemSettings | None = None,
    ) -> None:
        try:
            if system_settings is None:
                system_settings = await owned_to_thread(
                    self._settings_service.get_system
                )

            indexer_definition = self._indexer_definitions_service.get_by_id(
                indexer_account.indexer_id
            )

            # Hit and Run beállítás
            enabled_hit_and_run = system_settings.hit_and_run
            if indexer_account.hit_and_run is not None:
                enabled_hit_and_run = indexer_account.hit_and_run

            not_completed_torrent_ids: list[str] | None = None
            if enabled_hit_and_run:
                # Meghívjuk az adapter hit and run listáját
                not_completed_torrent_ids = (
                    await indexer_definition.find_hit_and_run_ids()
                )

            # Keep Seed beállítás
            keep_seed_seconds: int | None = (
                system_settings.keep_seed_seconds
                if system_settings.keep_seed_seconds > 0
                else None
            )
            if indexer_account.keep_seed_seconds is not None:
                keep_seed_seconds = indexer_account.keep_seed_seconds

            if not_completed_torrent_ids is None and keep_seed_seconds is None:
                return

            # Futtatjuk a letöltött torrentek takarítását
            await owned_to_thread(
                self._torrents_service.cleanup_tracker_torrents,
                indexer_id=indexer_account.indexer_id,
                keep_seed_seconds=keep_seed_seconds,
                not_completed_torrent_ids=not_completed_torrent_ids,
            )
            logger.info(
                f"✅ Sikeres takarítás lefutott az indexerhez: {indexer_account.indexer_id}"
            )
        except Exception as exc:
            logger.error("operation=indexer-cleanup provider=%s %s", indexer_account.indexer_id, network_error_fields(exc))
