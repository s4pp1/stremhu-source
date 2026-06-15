import asyncio

from fastapi import HTTPException, status

from app.common.logger import logger
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import (
    IndexerAccountCreate,
    IndexerAccountUpdate,
)
from app.modules.indexer_accounts.service import IndexerAccountsService
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    CredentialsRequiredException,
)
from app.modules.indexer_definitions.schemas.internal import IndexerDefinitionLogin
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.indexers.schemas.internal import (
    DownloadedTorrentFile,
    IndexerLogin,
    IndexerTorrent,
)
from app.modules.media_attributes.utils import resolve_attribute_ids
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

    async def login(
        self,
        payload: IndexerLogin,
    ) -> IndexerAccountModel:
        indexer_definition = self._indexer_definitions_service.get_by_id(
            payload.indexer_id
        )
        indexer_account = await asyncio.to_thread(
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
                )
            )

            indexer_account = await asyncio.to_thread(
                self._indexer_accounts_service.create,
                IndexerAccountCreate(
                    indexer_id=indexer_definition.id,
                    username=payload.username,
                    password=payload.password,
                    download_full_torrent=indexer_definition.requires_full_download,
                    cookies=indexer_definition.cookies,
                ),
            )

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
        except Exception as e:
            logger.error(e)
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
        self._torrents_service.delete_by_indexer_id(indexer_id)
        self._indexer_accounts_service.delete(indexer_id)

    async def get_torrents_by_torrent_id(
        self,
        torrent_id: str,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        indexer_accounts = await asyncio.to_thread(
            self._indexer_accounts_service.find_list
        )

        async def fetch_and_map(indexer_account: IndexerAccountModel) -> IndexerTorrent:
            indexer_definition = self._indexer_definitions_service.get_by_id(
                indexer_account.indexer_id
            )
            indexer_definition_torrent = await indexer_definition.find_torrent_by_id(
                torrent_id
            )

            return IndexerTorrent(
                indexer_account=indexer_account,
                torrent_id=indexer_definition_torrent.torrent_id,
                download_url=indexer_definition_torrent.download_url,
                imdb_id=indexer_definition_torrent.imdb_id,
                seeders=indexer_definition_torrent.seeders,
                attributes=[
                    *resolve_attribute_ids(indexer_definition_torrent.attribute_ids),
                    indexer_account.indexer_definition,
                ],
            )

        tasks = [fetch_and_map(indexer_account) for indexer_account in indexer_accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        indexer_torrents: list[IndexerTorrent] = []
        errors: list[str] = []

        for result in results:
            if isinstance(result, BaseException):
                errors.append(str(result))
            else:
                indexer_torrents.append(result)

        return indexer_torrents, errors

    async def get_torrent_by_torrent_id(
        self,
        indexer_id: str,
        torrent_id: str,
    ) -> IndexerTorrent:
        indexer_account = await asyncio.to_thread(
            self._indexer_accounts_service.get_by_id, indexer_id
        )

        indexer_definition = self._indexer_definitions_service.get_by_id(
            indexer_account.indexer_id
        )
        indexer_definition_torrent = await indexer_definition.find_torrent_by_id(
            torrent_id
        )
        return IndexerTorrent(
            indexer_account=indexer_account,
            torrent_id=indexer_definition_torrent.torrent_id,
            download_url=indexer_definition_torrent.download_url,
            imdb_id=indexer_definition_torrent.imdb_id,
            seeders=indexer_definition_torrent.seeders,
            attributes=[
                *resolve_attribute_ids(indexer_definition_torrent.attribute_ids),
                indexer_account.indexer_definition,
            ],
        )

    async def get_torrents_by_imdb_id(
        self,
        imdb_id: str,
    ) -> tuple[list[IndexerTorrent], list[str]]:
        indexer_accounts = await asyncio.to_thread(
            self._indexer_accounts_service.find_list
        )

        async def fetch_and_map(
            indexer_account: IndexerAccountModel,
        ) -> list[IndexerTorrent]:

            indexer_definition = self._indexer_definitions_service.get_by_id(
                indexer_account.indexer_id
            )
            indexer_definition_torrents = (
                await indexer_definition.find_torrents_by_imdb_id(imdb_id)
            )
            return [
                IndexerTorrent(
                    indexer_account=indexer_account,
                    torrent_id=indexer_definition_torrent.torrent_id,
                    download_url=indexer_definition_torrent.download_url,
                    imdb_id=indexer_definition_torrent.imdb_id,
                    seeders=indexer_definition_torrent.seeders,
                    attributes=[
                        *resolve_attribute_ids(
                            indexer_definition_torrent.attribute_ids
                        ),
                        indexer_account.indexer_definition,
                    ],
                )
                for indexer_definition_torrent in indexer_definition_torrents
            ]

        tasks = [fetch_and_map(indexer_account) for indexer_account in indexer_accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        indexer_torrents: list[IndexerTorrent] = []
        errors: list[str] = []

        for result in results:
            if isinstance(result, BaseException):
                errors.append(str(result))
            else:
                indexer_torrents.extend(result)

        return indexer_torrents, errors

    async def download_torrent(
        self,
        indexer_id: str,
        torrent_id: str,
        download_url: str,
    ) -> DownloadedTorrentFile:
        indexer_definition = self._indexer_definitions_service.get_by_id(indexer_id)
        torrent_bytes = await indexer_definition.download_torrent(download_url)

        return DownloadedTorrentFile(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
            torrent_bytes=torrent_bytes,
        )

    async def cleanup_torrents_by_rules(self) -> None:
        indexer_accounts = await asyncio.to_thread(
            self._indexer_accounts_service.find_list
        )
        system_settings = await asyncio.to_thread(self._settings_service.get_system)

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
                system_settings = await asyncio.to_thread(
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
            await asyncio.to_thread(
                self._torrents_service.cleanup_tracker_torrents,
                indexer_id=indexer_account.indexer_id,
                keep_seed_seconds=keep_seed_seconds,
                not_completed_torrent_ids=not_completed_torrent_ids,
            )
            logger.info(
                f"✅ Sikeres takarítás lefutott az indexerhez: {indexer_account.indexer_id}"
            )
        except Exception as ex:
            logger.error(
                f"🚨 Hiba történt a(z) '{indexer_account.indexer_id}' indexer takarítása során: {ex}",
                exc_info=ex,
            )
