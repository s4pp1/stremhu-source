import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from http.cookiejar import Cookie

import httpx
import pydash
import pyotp

from app.common.async_utils import owned_to_thread
from app.common.log_safety import network_error_fields, safe_endpoint_label
from app.common.singleflight import Singleflight
from app.config import config
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    AuthenticationOtherException,
    CredentialsRequiredException,
    IndexerDefinitionException,
    IndexerDownloadHostNotAllowedException,
    IndexerResponseTooLargeException,
)
from app.modules.indexer_definitions.protocols import IndexerAccountStorage
from app.modules.indexer_definitions.schemas.internal import (
    AuthCredentialError,
    AuthError,
    AuthOtherError,
    AuthSessionError,
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionLogin,
    IndexerDefinitionLoginPayload,
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


# CR15/b: korlátos letöltésnél követett átirányítások felső határa (terv: legfeljebb 10).
_MAX_BOUNDED_REDIRECTS = 10


class _CappedStream(httpx.AsyncByteStream):
    """Nyers válaszfolyam burka: a korlát átlépésekor azonnal megáll, a zárást továbbadja."""

    def __init__(self, stream: httpx.SyncByteStream | httpx.AsyncByteStream, max_bytes: int) -> None:
        if not isinstance(stream, httpx.AsyncByteStream):
            raise TypeError("async byte stream expected")
        self._stream = stream
        self._max_bytes = max_bytes

    async def __aiter__(self) -> AsyncIterator[bytes]:
        size = 0
        async for chunk in self._stream:
            size += len(chunk)
            if size > self._max_bytes:
                raise IndexerResponseTooLargeException
            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


class IndexerClient(httpx.AsyncClient):
    def __init__(self, definition: "BaseIndexerDefinition", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._definition = definition

    async def request(
        self, method: str, url: httpx.URL | str, **kwargs
    ) -> httpx.Response:
        return await self._guarded(
            lambda: super(IndexerClient, self).request(method, url, **kwargs)
        )

    async def get_bounded(
        self, url: httpx.URL | str, *, max_bytes: int
    ) -> httpx.Response:
        """GET, amelynek dekódolt törzse legfeljebb ``max_bytes`` bájt lehet.

        A szemafort és a hitelesítési újrapróbát ugyanúgy kezeli, mint a
        ``request()``; a szemafor a teljes törzsolvasás alatt foglalt.
        Átirányításnál legfeljebb ``_MAX_BOUNDED_REDIRECTS`` lépést követ, a
        közbülső válaszok törzsét nem olvassa be, csak lezárja.
        """
        return await self._guarded(lambda: self._read_bounded(url, max_bytes))

    def _check_download_host(self, url: httpx.URL) -> None:
        """CR15/b (26b), felhasználói döntés 2026-11-07: letöltés csak a tracker saját
        domainjére vagy aldomainjére mehet, a tracker sémájával (élesben HTTPS).

        A horgony a kliens base URL-je, ami élesben az adapter ``url``-je; ha nincs
        beállítva, maga az adapter ``url``-je.
        """
        base = self.base_url if self.base_url.host else httpx.URL(self._definition.url)
        base_host = base.host.lower()
        host = url.host.lower()
        if not base_host or url.scheme != base.scheme or not (host == base_host or host.endswith("." + base_host)):
            # Csak a host kerül az üzenetbe; a letöltési URL kulcsot tartalmazhat.
            raise IndexerDownloadHostNotAllowedException(f"A letöltési cél nem a tracker saját domainje: {host or '-'}")

    async def _send_following_unread(self, url: httpx.URL | str) -> httpx.Response:
        """Kézi átirányítás-követés: a HTTPX a követett redirect törzsét korlát nélkül olvasná.

        A következő kérést a HTTPX publikus ``next_request`` mezője adja (relatív Location,
        metódus, cookie- és fejlécszabályok változatlanul); a history megmarad. Minden lépés
        célját a küldés előtt ellenőrzi (``_check_download_host``).
        """
        request = self.build_request("GET", url)
        history: list[httpx.Response] = []
        while True:
            self._check_download_host(request.url)
            response = await self.send(request, stream=True, follow_redirects=False)
            next_request = response.next_request if self.follow_redirects else None
            if next_request is None:
                response.history = history
                return response
            await response.aclose()
            history.append(response)
            if len(history) > _MAX_BOUNDED_REDIRECTS:
                raise httpx.TooManyRedirects("Exceeded maximum allowed redirects.", request=next_request)
            request = next_request

    async def _read_bounded(
        self, url: httpx.URL | str, max_bytes: int
    ) -> httpx.Response:
        response = await self._send_following_unread(url)
        try:
            if "content-encoding" not in response.headers:
                declared = response.headers.get("content-length", "")
                if declared.isdigit() and int(declared) > max_bytes:
                    raise IndexerResponseTooLargeException
                # Tömörítetlen törzs: a HTTPX saját aread()-je fut (azonos memóriaút a sima
                # get()-tel), csak a nyers folyamot számoljuk. A cr15a-after-v1/v2 saját
                # pufferelése egymás utáni nagy letöltéseknél ismételhetően lassabb volt.
                response.stream = _CappedStream(response.stream, max_bytes)
                await response.aread()
                # A HTTPX folyamburka visszahivatkozik a válaszra; ciklusként a törzs csak a
                # ciklikus GC-vel szabadulna fel (cr15a-after-v4). A beolvasott törzs után a
                # válasz már nem olvas a hálózatról, a folyamot a meglévő bájtokra cseréljük.
                response.stream = httpx.ByteStream(response.content)
                return response
            # Tömörített törzs: a dekódolt bájtokat számoljuk (tömörítési bomba ellen).
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise IndexerResponseTooLargeException
                chunks.append(chunk)
        finally:
            await response.aclose()
        # A törzs már dekódolt: a kódolási/hossz fejléc a pufferelt válaszon nem érvényes.
        headers = [
            (key, value)
            for key, value in response.headers.multi_items()
            if key.lower() not in ("content-encoding", "content-length")
        ]
        return httpx.Response(
            response.status_code,
            headers=headers,
            content=b"".join(chunks),
            request=response.request,
            history=response.history,
        )

    async def _guarded(
        self, send: Callable[[], Awaitable[httpx.Response]]
    ) -> httpx.Response:
        if self._definition._closing:
            raise IndexerDefinitionException("Az indexer leállítás alatt áll.")
        # Concurrency limit (szemafor) kezelése
        async with self._definition._semaphore:
            response = await send()
        # Hitelesítési hibák detektálása a kliens szintű válaszon
        auth_error = self._definition._detect_authentication_error(response)

        match auth_error:
            case AuthSessionError():
                # Újra-bejelentkezés (a cookie-k frissülnek a kliensben)
                await self._definition.relogin()

                # Kérés újraindítása (az új cookie-k automatikusan bekerülnek!)
                async with self._definition._semaphore:
                    response = await send()
            case AuthCredentialError(message=message):
                raise AuthenticationException(
                    message
                    or f"Sikertelen bejelentkezés a(z) {self._definition.name} fiókba."
                )
            case AuthOtherError(message=message):
                raise AuthenticationOtherException(message)
            case None:
                pass

        return response


class BaseIndexerDefinition(ABC):
    def __init__(
        self,
        indexer_account_storage: IndexerAccountStorage | None = None,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._indexer_account_storage = indexer_account_storage

        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._login_singleflight: Singleflight[None] = Singleflight()
        self._closing = False

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
                    self._restore_cookies(account.cookies)
            except Exception as e:
                self.logger.error(
                    "Failed to load persisted cookies for %s: %s", self.id, network_error_fields(e)
                )

    def _restore_cookies(self, cookies: dict[str, str]) -> None:
        """Mentett (csak név-érték) cookie-k visszatöltése az indexer saját hosztjára kötve.

        Domain nélkül a cookie-jar minden célhoz elküldené őket (idegen hosztra és
        HTTP-re lefokozott átirányításnál is). Itt a hoszt és aldomainjei kapják,
        https-indexernél csak titkosított kapcsolaton — mint egy friss, domain-széles
        bejelentkezési cookie-t.
        """
        base = httpx.URL(self.url)
        for name, value in cookies.items():
            self._client.cookies.jar.set_cookie(
                Cookie(
                    version=0,
                    name=name,
                    value=value,
                    port=None,
                    port_specified=False,
                    domain="." + base.host,
                    domain_specified=True,
                    domain_initial_dot=True,
                    path="/",
                    path_specified=True,
                    secure=base.scheme == "https",
                    expires=None,
                    discard=True,
                    comment=None,
                    comment_url=None,
                    rest={},
                )
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
        """A indexer megjelenített neve (pl. 'nCore')."""

    @property
    @abstractmethod
    def url(self) -> str:
        """A indexer alap URL-je (pl. 'https://ncore.pro')."""

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

    @property
    def supports_totp(self) -> bool:
        """Támogatja-e az indexer a TOTP (2FA) bejelentkezést."""
        return False

    @property
    def provides_tech_info(self) -> bool:
        """Ad-e az indexer Tech Info-t (``fetch_tech_info`` felülírva).

        Az SP06/b előtöltés csak ezeknek a találatait kéri le; aki felülírja a
        ``fetch_tech_info``-t, ezt is igazra állítja.
        """
        return False

    # --- Absztrakt üzleti metódusok ---

    @abstractmethod
    def _detect_authentication_error(self, response: httpx.Response) -> AuthError:
        """
        Kiszűri és detektálja a hitelesítési vagy munkamenet hibákat az httpx válasz alapján.

        Implementálandó:
        - Ha a kérés a login oldalra irányított és nem oda indítottuk: SESSION_ERROR
        - Ha a bejelentkezés közvetlenül meghiúsult: CREDENTIAL_ERROR
        - Egyéb esetben: None
        """

    @abstractmethod
    async def _login(self, payload: IndexerDefinitionLoginPayload) -> httpx.Response:
        """Végrehajtja a tényleges POST bejelentkezési kérést a indexer felé."""

    @abstractmethod
    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        """
        Keresést hajt végre a indexer-en és visszaadja a találatokat.

        Visszatér:
        - torrents: a talált torrentek listája IndexerDefinitionTorrent-ként
        - next_page: a következő oldal száma, ha van; egyébként None
        """

    @abstractmethod
    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent | None:
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
        if self._closing:
            raise IndexerDefinitionException("Az indexer leállítás alatt áll.")
        is_first_login = credential is not None
        if not credential:
            if not self._indexer_account_storage:
                raise CredentialsRequiredException(
                    f"{self.name} hitelesítési információk nincsenek megadva."
                )
            credential = await owned_to_thread(
                self._indexer_account_storage.get_credentials, self.id
            )

        if not credential:
            raise CredentialsRequiredException(
                f"{self.name} hitelesítési információk nincsenek megadva."
            )

        self._client.cookies.clear()

        totp_code: str | None = None
        if credential.totp_secret:
            try:
                totp_code = pyotp.TOTP(credential.totp_secret).now()
            except Exception:
                raise AuthenticationException(
                    "Érvénytelen 2FA titkos kulcs (TOTP) formátum."
                )

        try:
            await self._login(
                IndexerDefinitionLoginPayload(
                    username=credential.username,
                    password=credential.password,
                    totp_code=totp_code,
                )
            )
        except httpx.HTTPError as exc:
            summary = network_error_fields(exc)
            self.logger.error("%s %s", safe_endpoint_label(self.id, "login"), summary)
            raise IndexerDefinitionException(f"{self.name} hálózati bejelentkezési hiba ({summary.kind}).") from None

        if not is_first_login and self._indexer_account_storage:
            try:
                await owned_to_thread(
                    self._indexer_account_storage.save_cookies,
                    self.id,
                    dict(self._client.cookies),
                )
            except Exception as e:
                self.logger.error(
                    "Failed to save persisted cookies for %s: %s", self.id, network_error_fields(e)
                )

    async def find_torrents_by_imdb_id(
        self, imdb_id: str
    ) -> list[IndexerDefinitionTorrent]:
        return await self._find_all(imdb_id, None, [])

    async def find_torrents_by_query(
        self, query: str, media_type: str | None = None
    ) -> list[IndexerDefinitionTorrent]:
        return await self._find_all_by_query(
            query, None, [], media_type=media_type
        )

    async def _fetch_torrents_by_query(
        self,
        query: str,
        page: int | None = None,
        media_type: str | None = None,
    ) -> IndexerDefinitionFindTorrentsResult:
        """Alapértelmezett megvalósítás: üres lista, ha az indexer nem támogatja a név szerinti keresést."""
        return IndexerDefinitionFindTorrentsResult(torrents=[])

    async def find_torrent_by_id(
        self, torrent_id: str
    ) -> IndexerDefinitionTorrent | None:
        try:
            return await self._fetch_torrent(torrent_id)
        except Exception as e:
            error_msg = f"{self.name} nem érhető el vagy megváltozott a struktúrája."
            self.logger.error("%s %s", safe_endpoint_label(self.id, "details"), network_error_fields(e))
            raise IndexerDefinitionException(error_msg) from None

    async def download_torrent(self, download_url: str) -> bytes:
        try:
            response = await self._client.get_bounded(
                download_url, max_bytes=config.indexer_torrent_max_bytes
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            summary = network_error_fields(e)
            self.logger.error("%s %s", safe_endpoint_label(self.id, "download"), summary)
            raise IndexerDefinitionException(f"{self.name} torrent letöltése sikertelen ({summary.kind}).") from None

    async def find_hit_and_run_ids(self) -> list[str]:
        try:
            return await self._fetch_hit_and_run_ids()
        except Exception as e:
            error_msg = f"{self.name} nem érhető el vagy megváltozott a struktúrája."
            self.logger.error("%s %s", safe_endpoint_label(self.id, "hit-and-run"), network_error_fields(e))
            raise IndexerDefinitionException(error_msg) from None

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

            return pydash.uniq_by(
                (torrent for torrent in accumulator if torrent.imdb_id == imdb_id),
                lambda torrent: torrent.torrent_id,
            )
        except Exception as e:
            error_msg = f"{self.name} nem érhető el vagy megváltozott a struktúrája."
            self.logger.error("%s %s", safe_endpoint_label(self.id, "search"), network_error_fields(e))
            raise IndexerDefinitionException(error_msg) from None

    async def _find_all_by_query(
        self,
        query: str,
        page: int | None,
        accumulator: list[IndexerDefinitionTorrent],
        media_type: str | None = None,
    ) -> list[IndexerDefinitionTorrent]:
        if len(accumulator) >= 50:
            return pydash.uniq_by(
                accumulator,
                lambda torrent: torrent.torrent_id,
            )

        try:
            result = await self._fetch_torrents_by_query(
                query, page, media_type=media_type
            )
            accumulator.extend(result.torrents)

            if result.next_page is not None:
                return await self._find_all_by_query(
                    query, result.next_page, accumulator, media_type=media_type
                )

            return pydash.uniq_by(
                accumulator,
                lambda torrent: torrent.torrent_id,
            )
        except Exception as e:
            error_msg = f"{self.name} nem érhető el vagy megváltozott a struktúrája."
            self.logger.error("%s %s", safe_endpoint_label(self.id, "search-query"), network_error_fields(e))
            raise IndexerDefinitionException(error_msg) from None

    async def fetch_tech_info(self, torrent_id: str) -> tuple[str | None, str | None]:
        """
        Opcionális Tech Info / NFO és leírás lekérés a torrenthez.
        Alapértelmezésben (None, None).
        """
        return None, None

    async def relogin(self) -> None:
        """
        Kezeli a párhuzamos újra-bejelentkezések összevonását.

        Több egyidejű SESSION_ERROR esetén
        csak egyszer fut le a bejelentkezés, a többi kérés megvárja azt.
        """
        if self._closing:
            raise IndexerDefinitionException("Az indexer leállítás alatt áll.")

        async def perform_login() -> None:
            self.logger.info(f"🔄 {self.name} session frissítése.")
            await self.login()

        await self._login_singleflight.run("login", perform_login)

    def stop_admission(self) -> None:
        self._closing = True

    async def close_logins(self) -> None:
        self.stop_admission()
        await self._login_singleflight.aclose()

    async def close(self) -> None:
        """Lezárja a HTTP hálózati kapcsolatokat (alkalmazás leállásakor)."""
        self._closing = True
        try:
            await self._login_singleflight.aclose()
        finally:
            await self._client.aclose()
