import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

from app.modules.indexer_definitions.enums import AuthenticationErrorEnum
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    CredentialsRequiredException,
    TrackerException,
)
from app.modules.indexer_definitions.protocols import IndexerAccountStorage
from app.modules.indexer_definitions.schemas.internal import (
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionLogin,
    IndexerDefinitionTorrent,
)

_TORRENTS_LIMIT = 300
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/141.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
}


class IndexerClient(httpx.AsyncClient):
    def __init__(self, definition: "BaseIndexerDefinition", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._definition = definition

    async def request(
        self, method: str, url: httpx.URL | str, **kwargs
    ) -> httpx.Response:
        # Concurrency limit (szemafor) kezelése
        async with self._definition._semaphore:
            response = await super().request(method, url, **kwargs)
        # Hitelesítési hibák detektálása a kliens szintű válaszon
        auth_error = self._definition._detect_authentication_error(response)
        if auth_error == AuthenticationErrorEnum.CREDENTIAL_ERROR:
            raise AuthenticationException(
                f"Sikertelen bejelentkezés a(z) {self._definition.name} fiókba."
            )
        if auth_error == AuthenticationErrorEnum.SESSION_ERROR:
            # Újra-bejelentkezés (a cookie-k frissülnek a kliensben)
            await self._definition.relogin()

            # Kérés újraindítása (az új cookie-k automatikusan bekerülnek!)
            async with self._definition._semaphore:
                response = await super().request(method, url, **kwargs)
        return response


class BaseIndexerDefinition(ABC):
    def __init__(
        self,
        indexer_account_storage: IndexerAccountStorage | None = None,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._indexer_account_storage = indexer_account_storage

        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._login_in_progress: asyncio.Future | None = None

        self._client = IndexerClient(
            definition=self,
            base_url=self.url,
            follow_redirects=True,
            headers=_DEFAULT_HEADERS,
            timeout=20.0,
        )

        if indexer_account_storage:
            try:
                account = indexer_account_storage.get_credentials(self.id)
                if account and account.cookies:
                    self._client.cookies.update(account.cookies)
            except Exception as e:
                self.logger.error(
                    "Failed to load persisted cookies for %s: %s", self.name, e
                )

    @property
    def cookies(self) -> dict[str, str]:
        """A kliens jelenlegi session cookie-jai."""
        return dict(self._client.cookies)

    @property
    def max_concurrent(self) -> int:
        """Max egyidejű HTTP kérések száma."""
        return 5

    # --- Absztrakt tulajdonságok ---

    @property
    @abstractmethod
    def id(self) -> str:
        """Az indexer egyedi azonosítója (pl. 'ncore')."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A tracker megjelenített neve (pl. 'nCore')."""

    @property
    @abstractmethod
    def url(self) -> str:
        """A tracker alap URL-je (pl. 'https://ncore.pro')."""

    @property
    @abstractmethod
    def login_path(self) -> str:
        """A bejelentkezési útvonal (pl. '/login.php')."""

    @property
    @abstractmethod
    def details_path(self) -> str:
        """A torrent adatlap útvonala (pl. '/torrents.php?action=details&id={torrent_id}')."""

    @property
    @abstractmethod
    def requires_full_download(self) -> bool:
        """Szükséges-e a teljes .torrent letöltés a seedeléshez."""

    @property
    def disabled(self) -> bool:
        """Letiltott-e az indexer integráció (pl. törött működés miatt)."""
        return False

    # --- Absztrakt üzleti metódusok ---

    @abstractmethod
    def _detect_authentication_error(
        self, response: httpx.Response
    ) -> AuthenticationErrorEnum | None:
        """
        Kiszűri és detektálja a hitelesítési vagy munkamenet hibákat az httpx válasz alapján.

        Implementálandó:
        - Ha a kérés a login oldalra irányított és nem oda indítottuk: SESSION_ERROR
        - Ha a bejelentkezés közvetlenül meghiúsult: CREDENTIAL_ERROR
        - Egyéb esetben: None
        """

    @abstractmethod
    async def _login(self, credential: IndexerDefinitionLogin) -> httpx.Response:
        """Végrehajtja a tényleges POST bejelentkezési kérést a tracker felé."""

    @abstractmethod
    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        """
        Keresést hajt végre a trackeren és visszaadja a találatokat.

        Visszatér:
        - torrents: a talált torrentek listája IndexerDefinitionTorrent-ként
        - next_page: a következő oldal száma, ha van; egyébként None
        """

    @abstractmethod
    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent:
        """Lekéri egy konkrét torrent részletes adatait az azonosítója alapján."""

    @abstractmethod
    async def _fetch_hit_and_run_ids(self) -> list[str]:
        """Lekéri a Hit 'n' Run listán lévő torrent azonosítókat."""

    # --- Megvalósított publikus API ---

    async def login(
        self,
        credential: IndexerDefinitionLogin | None = None,
    ) -> None:
        """
        A NestJS login() megfelelője.

        Ha nem adunk meg hitelesítési adatot, az account_storage-ból olvassa ki.
        """
        is_first_login = credential is not None
        if not credential:
            if not self._indexer_account_storage:
                raise CredentialsRequiredException(
                    f"{self.name} hitelesítési információk nincsenek megadva."
                )
            credential = await asyncio.to_thread(
                self._indexer_account_storage.get_credentials, self.id
            )

        if not credential:
            raise CredentialsRequiredException(
                f"{self.name} hitelesítési információk nincsenek megadva."
            )

        self._client.cookies.clear()

        await self._login(credential)

        if not is_first_login and self._indexer_account_storage:
            try:
                await asyncio.to_thread(
                    self._indexer_account_storage.save_cookies,
                    self.id,
                    dict(self._client.cookies),
                )
            except Exception as e:
                self.logger.error(
                    "Failed to save persisted cookies for %s: %s", self.name, e
                )

    async def find_torrents_by_imdb_id(
        self, imdb_id: str
    ) -> list[IndexerDefinitionTorrent]:
        return await self._find_all(imdb_id, None, [])

    async def find_torrent_by_id(self, torrent_id: str) -> IndexerDefinitionTorrent:
        try:
            return await self._fetch_torrent(torrent_id)
        except Exception as e:
            error_msg = f"{self.name} nem érhető el vagy megváltozott a struktúrája."
            self.logger.error(error_msg, exc_info=e)
            raise TrackerException(error_msg) from e

    async def download_torrent(self, download_url: str) -> bytes:
        try:
            response = await self._client.get(download_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            self.logger.error(
                f'🚨 Hiba történt a(z) "[{self.name}] - {download_url}" torrent letöltése közben.',
                exc_info=e,
            )
            raise

    async def find_hit_and_run_ids(self) -> list[str]:
        try:
            return await self._fetch_hit_and_run_ids()
        except Exception as e:
            error_msg = f"{self.name} nem érhető el vagy megváltozott a struktúrája."
            self.logger.error(error_msg, exc_info=e)
            raise TrackerException(error_msg) from e

    # --- Belső folyamatkezelők ---

    async def _find_all(
        self,
        imdb_id: str,
        page: int | None,
        accumulator: list[IndexerDefinitionTorrent],
    ) -> list[IndexerDefinitionTorrent]:
        if len(accumulator) > _TORRENTS_LIMIT:
            return accumulator

        try:
            result = await self._fetch_torrents(imdb_id, page)
            accumulator.extend(result.torrents)

            if result.next_page is not None:
                return await self._find_all(imdb_id, result.next_page, accumulator)

            return [t for t in accumulator if t.imdb_id == imdb_id]
        except Exception as e:
            error_msg = f"{self.name} nem érhető el vagy megváltozott a struktúrája."
            self.logger.exception(error_msg)
            raise TrackerException(error_msg) from e

    async def relogin(self) -> None:
        """
        Kezeli a párhuzamos újra-bejelentkezések összevonását.

        Több egyidejű SESSION_ERROR esetén
        csak egyszer fut le a bejelentkezés, a többi kérés megvárja azt.
        """
        if self._login_in_progress is not None:
            await self._login_in_progress
            return

        loop = asyncio.get_running_loop()
        self._login_in_progress = loop.create_future()

        try:
            self.logger.info(f"🔄 {self.name} session frissítése.")
            await self.login()
            self._login_in_progress.set_result(None)
        except Exception as e:
            if not self._login_in_progress.done():
                self._login_in_progress.set_exception(e)
            raise
        finally:
            self._login_in_progress = None

    async def close(self) -> None:
        """Lezárja a HTTP hálózati kapcsolatokat (alkalmazás leállásakor)."""
        await self._client.aclose()
