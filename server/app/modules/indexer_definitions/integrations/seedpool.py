import asyncio
import re
from typing import Any, NamedTuple
from urllib.parse import quote, urljoin

import httpx

from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    IndexerDefinitionException,
)
from app.modules.indexer_definitions.protocols import IndexerAccountStorage
from app.modules.indexer_definitions.schemas.internal import (
    AuthCredentialError,
    AuthError,
    AuthOtherError,
    AuthSessionError,
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionLoginPayload,
    IndexerDefinitionTorrent,
)
from app.modules.media_attributes.constants import MediaAttributeKey

_LOGIN_TEST_PATH = "/api/torrents"
_SEARCH_PATH = "/api/torrents/filter"
_TORRENT_PATH = "/api/torrents/{torrent_id}"
_AUTH_HEADER = "Authorization"

# A UNIT3D a perPage-et 100-nál elvágja (TorrentController::filter:
# min($request->integer('perPage') ?: 25, 100)), tehát ennél többet kérni
# fölösleges.
_PER_PAGE = 100

# Seederek szerint csökkenő sorrend, hogy a bázisosztály 300-as korlátjába a
# használható találatok kerüljenek be először. A sortField engedélyezett
# értékeit a controller validálja: name, size, seeders, leechers,
# times_completed, created_at, bumped_at.
_SORT_FIELD = "seeders"
_SORT_DIRECTION = "desc"

# Menetenkénti lapkorlát — lásd az "Ismert korlátok" 1. pontját.
_MAX_PAGES = 5

# ── A tracker forgalomkorlátja ───────────────────────────────────────────────
# A UNIT3D két külön vödröt tart (RouteServiceProvider), mindkettő FELHASZNÁLÓRA
# és PERCRE szól:
#     api  → Limit::perMinute(30)   a keresés (/api/torrents/filter)
#     rss  → Limit::perMinute(30)   a .torrent letöltés (a rsskey-s útvonal)
#
# A keresésnél ez bőven elég (menetenként legfeljebb _MAX_PAGES kérés). A
# LETÖLTÉSNÉL viszont nem: a StremHU egy találati listára EGYSZERRE indítja el az
# összes .torrent letöltését (torrent_source_provider/service.py:
# `asyncio.gather(*download_tasks)`), tehát 30 fölött garantált a 429.
_DOWNLOAD_MIN_INTERVAL = 60.0 / 30 + 0.1

# Meddig várhat egy letöltés a saját időrésére. Ennél tovább nem sorbanállunk:
# a Stremio a stream-kérésre vár, és egy sok kiadású sorozatnál a teljes lista
# ütemezése percekig tartana. Aki nem fér bele, beszédes hibát kap, a hívó
# `gather(return_exceptions=True)`-ja naplózza, a többi stream pedig megjön.
#
# Nem vész el semmi: a letöltött .torrent fájlok a torrent_files táblába
# kerülnek, tehát a cím következő megnyitásakor a már meglévőket meg sem
# kérdezzük, és a sor következő adagja jut időréshez. A keresés seederek szerint
# csökkenő sorrendben jön, a sorbanállás pedig FIFO — így a legtöbb seederrel
# rendelkező kiadások kapnak elsőként helyet.
_DOWNLOAD_MAX_QUEUE_WAIT = 45.0

# 429 esetén ennyiszer próbálkozunk újra, a szerver Retry-After fejlécét követve.
_RATE_LIMIT_MAX_ATTEMPTS = 3
_RATE_LIMIT_FALLBACK_WAIT = 10.0
_RATE_LIMIT_MAX_WAIT = 70.0

# A UNIT3D lapozása 1-ről indul (Laravel simplePaginate).
_FIRST_PAGE = 1

# A második menet (tmdbId) lapszámai ezzel az eltolással utaznak. A bázisosztály
# csak egy egész számot ad vissza a next_page-ben, más állapotot nem tud átvinni
# a lapok között — ezért a MENET is a lapszámban van kódolva. Példányváltozó
# nem jó erre: egyszerre több keresés is futhat ugyanezen a definíción.
_TMDB_PAGE_OFFSET = 1_000

# 10 nap másodpercben: a kötelező minimum seed idő, freeleech torrentre is.
_MINIMUM_SEED_TIME = 864_000

# A tracker mozgóképes kategóriái a Jackett definíciójából. A "Deprecated"
# jelölésűek is bent vannak: a régi feltöltések még azokban ülnek.
#
# Az anime (6) MINDKÉT halmazban szerepel, mert alatta anime film és anime
# sorozat is van — a Jackett is két Torznab kategóriára képezi le.
_MOVIE_CATEGORIES = ("1", "10", "6")
_SERIES_CATEGORIES = ("2", "13", "20", "6")

# Az API `resolution` mezője a felbontás NEVE. Csak fallback: a release névből
# kiolvasott érték erősebb nála.
_RESOLUTION_ATTRIBUTES: dict[str, str] = {
    "4320p": MediaAttributeKey.R2160P,
    "2160p": MediaAttributeKey.R2160P,
    "1080p": MediaAttributeKey.R1080P,
    "1080i": MediaAttributeKey.R1080P,
    "720p": MediaAttributeKey.R720P,
    "576p": MediaAttributeKey.R576P,
    "576i": MediaAttributeKey.R576P,
    "480p": MediaAttributeKey.R480P,
    "480i": MediaAttributeKey.R480P,
}

# A Stremio saját metaadat addonja. Csak a tmdb menethez kell.
# A SORREND SZÁMÍT: a movie végpont sorozat-azonosítóra a cinemeta-live-ra megy
# át, és ott ROSSZ rekordot ad (mérve 2026-09-02: tt0903747 → "Mirror", 1975),
# míg a series végpont film-azonosítóra üres metát ad.
_CINEMETA_URL = "https://v3-cinemeta.strem.io/meta/{media_type}/{imdb_id}.json"
_CINEMETA_TYPES = ("series", "movie")
_CINEMETA_TIMEOUT = 10.0

# Az imdb_id → TMDB feloldás folyamaton belüli gyorsítótára. A felső korlát azért
# kell, mert a szótár különben a szerver élettartama alatt korlátlanul nőne.
_METADATA_CACHE_LIMIT = 512

# A kedvezmény attribútumai. SZÁNDÉKOSAN szövegkonstansok és nem importok: az
# upstream szerveren nem léteznek ezek az attribútumok, egy import pedig a modul
# betöltését buktatná el — a discover_indexer_definitions() ilyenkor az ÖSSZES
# definíciót elveszítené.
_FREELEECH_ATTRIBUTE_ID = "freeleech"
_HALFLEECH_ATTRIBUTE_ID = "halfleech"

# A tracker Cloudflare mögött van (a válaszok `server: cloudflare` fejlécet
# adnak). Az API normál klienssel átmegy rajta, de ha egyszer challenge-et kap,
# jobb azonnal beszédes hibát dobni, mint "nem JSON a válasz" üzenettel a
# felhasználót a saját kulcsát hibáztatni.
_CLOUDFLARE_MARKERS = (
    "just a moment",
    "cf-chl",
    "cf_chl_opt",
    "attention required! | cloudflare",
    "checking your browser before accessing",
)

_IMDB_DIGITS = re.compile(r"(\d+)")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)")


class _TitleMetadata(NamedTuple):
    """Az IMDB azonosítóból feloldott TMDB azonosító és médiatípus."""

    tmdb_id: int
    is_series: bool


def _is_html(response: httpx.Response) -> bool:
    return "html" in response.headers.get("content-type", "").lower()


def _looks_like_cloudflare_challenge(response: httpx.Response) -> bool:
    server = response.headers.get("server", "").lower()
    if response.status_code in (403, 503) and "cloudflare" in server:
        return True

    # A challenge mindig HTML. A JSON válasz törzsét meg sem nézzük — ott a
    # response.text felesleges dekódolás.
    if not _is_html(response):
        return False

    return any(marker in response.text[:2000].lower() for marker in _CLOUDFLARE_MARKERS)


def _looks_like_login_page(response: httpx.Response) -> bool:
    """Igaz, ha a válasz a bejelentkezési oldal, vagy oda tart.

    A UNIT3D érvénytelen (vagy hiányzó) API tokennél nem 401-et ad, hanem a
    /login oldalra irányít — ezt mértük ki a trackeren, és a Jackett definíció
    login.error szelektora is erre épül (`a[href*="/login"]`).
    """
    if "/login" in str(response.url).lower():
        return True

    # Ha a kliens nem követné az átirányítást, a Location fejlécből látszik.
    if 300 <= response.status_code < 400:
        return "/login" in response.headers.get("location", "").lower()

    return False


def _numeric_imdb_id(imdb_id: str | None) -> int | None:
    """A "tt0111161" alakból 111161.

    A tracker az `imdb` oszlopot egész számként tárolja, a szűrő pedig
    `$request->integer('imdbId')`-vel olvassa be — a vezető nullák és a "tt"
    előtag tehát nem érdekesek, de a szám igen.
    """
    match = _IMDB_DIGITS.search(imdb_id or "")

    return int(match.group(1)) if match else None


def _clean_api_key(raw: str) -> str:
    """A jelszó mezőbe írt API kulcs megtisztítása.

    Elviseli, ha a felhasználó a fejléccel együtt másolta be
    ("Authorization: Bearer abc123", vagy csak "Bearer abc123").
    """
    key = (raw or "").strip()

    if key.lower().startswith("authorization:"):
        key = key.split(":", 1)[1].strip()

    if key.lower().startswith("bearer "):
        key = key[len("bearer ") :].strip()

    return key


class SeedpoolIndexerDefinition(BaseIndexerDefinition):
    def __init__(
        self,
        indexer_account_storage: IndexerAccountStorage | None = None,
    ) -> None:
        super().__init__(indexer_account_storage)

        # A kulcs ELLENŐRZŐ kérése is átmegy az IndexerClient.request-en, tehát
        # lefut rá a _detect_authentication_error. Enélkül egy rossz kulcs
        # hibáját a detektor dobná el a _login beszédes üzenete helyett — sőt,
        # az ellenőrző kérés újra-bejelentkezést kérne, ami a már futó
        # relogin() befejezésére várna, vagyis önmagára.
        self._verifying_key = False

        # imdb_id → TMDB azonosító. None érték is kerülhet bele: azt jelenti,
        # hogy a Cinemeta ismeri a kérdést, de nincs rá adata.
        self._metadata_cache: dict[str, _TitleMetadata | None] = {}

        # A már kiírt, egyszeri figyelmeztetések kulcsai. Ezek a metódusok
        # keresésenként futnak — a naplót nem szabad ugyanazzal a mondattal
        # teleírni.
        self._warned: set[str] = set()

        # A .torrent letöltések ütemezése. Az asyncio.Lock a 3.10 óta nem köt
        # eseményhurkot a létrehozásakor, tehát itt biztonságos létrehozni.
        self._download_lock = asyncio.Lock()
        self._next_download_at = 0.0

    @property
    def id(self) -> str:
        return "seedpool"

    @property
    def name(self) -> str:
        return "seedpool"

    @property
    def url(self) -> str:
        return "https://seedpool.org"

    @property
    def login_path(self) -> str:
        # Nincs űrlapos bejelentkezés: a hitelesítés az Authorization fejléc. Ez
        # az az útvonal, amin a kulcsot ellenőrizzük — a Jackett definíció is
        # ezt használja login.path-ként.
        return _LOGIN_TEST_PATH

    @property
    def details_path(self) -> str:
        # A UNIT3D `torrents.show` route-ja.
        return "/torrents/{torrent_id}"

    @property
    def supports_totp(self) -> bool:
        # Az API kulcs mellett nincs értelme: a kulcs a már befejezett (2FA-t is
        # tartalmazó) bejelentkezés eredménye.
        return False

    @property
    def requires_full_download(self) -> bool:
        # Nem a letöltés módja, hanem az Unsatisfied szabály miatt True.
        #
        # A tracker 10 nap SEED IDŐT vár el minden kiadásra, és — a
        # TorrentLeechtől eltérően — az arány itt nem kiút ("torrents must be
        # seeded for 10 days regardless of ratio"). Mentesülni csak 10% alatti
        # letöltéssel lehet, amit egy filmnél a streamelés bőven túllép.
        #
        # Seed időt viszont seederként lehet gyűjteni, seeder pedig az, akinél
        # `left == 0` (UNIT3D ProcessAnnounce.php és unit3d-announce:
        # `is_seeder = queries.left == 0`). Részlegesen letöltött torrentnél
        # tehát keletkezik kötelezettség, de nem telik az idő — és a peereknek
        # sem lenne mit felajánlani. Teljes letöltésnél mindkettő rendben.
        #
        # A felhasználó ezt felülírhatja az indexer fiókjánál
        # (download_full_torrent), de ezen a trackeren nem érdemes.
        return True

    @property
    def max_concurrent(self) -> int:
        # Az API Cloudflare mögött van, és a kulcs egyetlen fiókot jelent. Egy
        # keresés két menetet és több lapot is kérhet, ezért a bázisosztály
        # alapértéke (5) itt fölösleges kockázat.
        return 2

    # -- Hitelesítés ---------------------------------------------------

    async def _login(
        self,
        payload: IndexerDefinitionLoginPayload,
    ) -> httpx.Response:
        """Nem belép, hanem beteszi az API kulcsot a kliensbe és ellenőrzi."""
        api_key = _clean_api_key(payload.password)
        if not api_key:
            raise AuthenticationException(
                f"A(z) {self.name} nem felhasználónév/jelszó párral hitelesít, "
                "hanem API kulccsal. A JELSZÓ mezőbe a tracker beállításaiban "
                "(My Settings → API Key) generált kulcsot kell beírni."
            )

        self._client.headers[_AUTH_HEADER] = f"Bearer {api_key}"

        self._verifying_key = True
        try:
            response = await self._client.get(
                _LOGIN_TEST_PATH,
                headers={"Accept": "application/json"},
            )
        finally:
            self._verifying_key = False

        if _looks_like_cloudflare_challenge(response):
            self._client.headers.pop(_AUTH_HEADER, None)
            raise AuthenticationException(
                f"A(z) {self.name} Cloudflare-ellenőrző oldalt adott vissza. Ezt "
                "a beépített kliens nem tudja megoldani, mert JS futtatás "
                "kellene hozzá."
            )

        if _looks_like_login_page(response) or response.status_code in (401, 403):
            # A kulcsot NEM hagyjuk bent a kliensben: a következő kérés így
            # AuthSessionError-t vált ki, és újra idejut a hibaüzenettel,
            # ahelyett hogy csendben ismételgetné az érvénytelen kérést.
            self._client.headers.pop(_AUTH_HEADER, None)
            raise AuthenticationException(
                f"A(z) {self.name} nem fogadta el az API kulcsot "
                f"(HTTP {response.status_code}, a bejelentkezési oldalra "
                "irányított). Generálj újat a tracker beállításaiban "
                "(My Settings → API Key), és azt írd a jelszó mezőbe."
            )

        if self._json_payload(response) is None:
            raise AuthenticationException(
                f"A(z) {self.name} nem JSON-t adott vissza az ellenőrző kérésre "
                f"(HTTP {response.status_code}). Vagy karbantartás van, vagy "
                "megváltozott az API."
            )

        return response

    def _detect_authentication_error(self, response: httpx.Response) -> AuthError:
        if self._verifying_key:
            # A _login maga értékeli ki a választ, beszédesebb üzenettel.
            return None

        if _looks_like_cloudflare_challenge(response):
            return AuthOtherError(
                message=(
                    f"A(z) {self.name} Cloudflare-ellenőrző oldalt adott vissza. "
                    "Ezt a beépített kliens nem tudja megoldani, mert JS "
                    "futtatás kellene hozzá."
                )
            )

        if not _looks_like_login_page(response) and response.status_code not in (
            401,
            403,
        ):
            return None

        if _AUTH_HEADER not in self._client.headers:
            # Friss folyamat: a kulcs még nincs a kliensben (nem süti, tehát a
            # bázisosztály sem tudja betölteni a tárolt fiókból). A bázisosztály
            # erre bejelentkezik és megismétli a kérést.
            return AuthSessionError()

        # A kulcs bent van, mégis elutasít: visszavonták, hibás, vagy a fiók
        # tiltott. SZÁNDÉKOSAN nem AuthSessionError — az újra-bejelentkezés
        # ugyanazt a kulcsot tenné vissza, tehát körbe-körbe járnánk.
        return AuthCredentialError(
            message=(
                f"A(z) {self.name} elutasította az API kulcsot (a bejelentkezési "
                "oldalra irányított). Elképzelhető, hogy visszavontad, vagy hogy "
                "a fiók tiltott. Generálj újat a tracker beállításaiban "
                "(My Settings → API Key), és írd be az indexer fiók jelszó "
                "mezőjébe."
            )
        )

    # -- Keresés -------------------------------------------------------

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        numeric_imdb_id = _numeric_imdb_id(imdb_id)
        if numeric_imdb_id is None:
            # Nem IMDB azonosító — a tracker mindkét szűrője számot vár.
            return IndexerDefinitionFindTorrentsResult(torrents=[], next_page=None)

        current_page = page if page is not None else _FIRST_PAGE
        is_tmdb_pass = current_page >= _TMDB_PAGE_OFFSET

        if is_tmdb_pass:
            return await self._fetch_tmdb_pass(
                imdb_id=imdb_id,
                numeric_imdb_id=numeric_imdb_id,
                page=current_page - _TMDB_PAGE_OFFSET,
            )

        return await self._fetch_imdb_pass(
            imdb_id=imdb_id,
            numeric_imdb_id=numeric_imdb_id,
            page=current_page,
        )

    async def _fetch_imdb_pass(
        self,
        imdb_id: str,
        numeric_imdb_id: int,
        page: int,
    ) -> IndexerDefinitionFindTorrentsResult:
        """Első menet: szűrés a tracker imdb oszlopára.

        Kategóriát nem küldünk: az IMDB azonosító önmagában egyedi, nincs mit
        szétválasztani.
        """
        data, rows = await self._search({"imdbId": numeric_imdb_id}, page)

        next_page = self._resolve_next_page(data, page)

        if not rows and page == _FIRST_PAGE:
            # A trackeren vagy nincs meg a film, vagy — a gyakoribb eset — a
            # sorokban nincs kitöltve az imdb oszlop. Átváltunk a tmdb menetre.
            next_page = _TMDB_PAGE_OFFSET + _FIRST_PAGE

        return IndexerDefinitionFindTorrentsResult(
            torrents=self._map_rows(rows, imdb_id, numeric_imdb_id),
            next_page=next_page,
        )

    async def _fetch_tmdb_pass(
        self,
        imdb_id: str,
        numeric_imdb_id: int,
        page: int,
    ) -> IndexerDefinitionFindTorrentsResult:
        """Második menet: szűrés a TMDB azonosítóra, a Cinemeta segítségével."""
        metadata = await self._resolve_metadata(imdb_id)
        if metadata is None:
            # Nincs TMDB azonosító — nincs mivel keresni. Nem hiba: az első
            # menet már lefutott, ez csak a ráadás lett volna.
            # Egyetlen kulcs, nem címenkénti: a _warned halmaz különben a
            # szerver élettartama alatt korlátlanul nőne.
            self._warn_once(
                "no-tmdb",
                "seedpool: a(z) %s azonosítóhoz nincs TMDB azonosító a "
                "Cinemetában, a második keresési menet kimarad. (Ez a "
                "figyelmeztetés csak egyszer jelenik meg.)",
                imdb_id,
            )

            return IndexerDefinitionFindTorrentsResult(torrents=[], next_page=None)

        categories = _SERIES_CATEGORIES if metadata.is_series else _MOVIE_CATEGORIES

        data, rows = await self._search(
            {"tmdbId": metadata.tmdb_id, "categories[]": list(categories)},
            page,
        )

        next_page = self._resolve_next_page(data, page)

        return IndexerDefinitionFindTorrentsResult(
            torrents=self._map_rows(rows, imdb_id, numeric_imdb_id),
            next_page=(
                next_page + _TMDB_PAGE_OFFSET if next_page is not None else None
            ),
        )

    async def _search(
        self,
        filters: dict[str, Any],
        page: int,
    ) -> tuple[dict[str, Any], list[Any]]:
        params: dict[str, Any] = {
            "perPage": _PER_PAGE,
            "sortField": _SORT_FIELD,
            "sortDirection": _SORT_DIRECTION,
            **filters,
        }
        if page > _FIRST_PAGE:
            params["page"] = page

        response = await self._get_with_retry(_SEARCH_PATH, params=params)

        data = self._json_payload(response)
        if data is None:
            raise IndexerDefinitionException(
                f"A(z) {self.name} nem JSON-t adott vissza a keresésre "
                f"(HTTP {response.status_code}) — valószínűleg karbantartás "
                "vagy megváltozott végpont."
            )

        rows = data.get("data")
        if not isinstance(rows, list):
            raise IndexerDefinitionException(
                f"A(z) {self.name} válaszában nincs 'data' lista — megváltozott "
                "az API."
            )

        return data, rows

    # -- Forgalomkorlát (429) ------------------------------------------

    async def _get_with_retry(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """API kérés, a tracker percenkénti korlátjához igazodva.

        A UNIT3D 429-re a Laravel throttle-jának JSON válaszát adja
        ({"message": "Too Many Attempts."}) — az ELLENŐRZÉS NÉLKÜL úgy nézne ki,
        mint egy értelmezhető, csak épp üres válasz, és a hívó "megváltozott az
        API" hibát írna ki egy múló forgalomkorlátra.
        """
        for attempt in range(1, _RATE_LIMIT_MAX_ATTEMPTS + 1):
            response = await self._client.get(
                path,
                params=params,
                headers={"Accept": "application/json"},
            )

            if response.status_code != 429:
                return response

            if attempt == _RATE_LIMIT_MAX_ATTEMPTS:
                break

            await asyncio.sleep(self._retry_after_seconds(response))

        raise IndexerDefinitionException(
            f"A(z) {self.name} forgalomkorlátja nem engedett át (HTTP 429) "
            f"{_RATE_LIMIT_MAX_ATTEMPTS} próbálkozás után sem. A tracker "
            "percenként 30 API kérést enged fiókonként; várj egy percet, vagy "
            "nézd meg, nem használja-e más is ugyanezt a kulcsot."
        )

    async def download_torrent(self, download_url: str) -> bytes:
        """A .torrent letöltése, a percenkénti korláthoz ütemezve.

        A bázisosztály változatát azért írjuk felül, mert az egyetlen kérést
        küld, ütemezés és újrapróbálkozás nélkül — a hívó viszont egy címre az
        ÖSSZES találat letöltését egyszerre indítja el
        (torrent_source_provider/service.py), ami a 30/perc korlátba ütközik.

        Két dolog van benne: időrés-foglalás (_reserve_download_slot) és 429-re
        újrapróbálkozás a szerver Retry-After fejléce szerint.
        """
        for attempt in range(1, _RATE_LIMIT_MAX_ATTEMPTS + 1):
            await self._reserve_download_slot()

            response = await self._client.get(download_url)

            if response.status_code != 429:
                try:
                    response.raise_for_status()
                except Exception as e:
                    self.logger.error(
                        '‼️ Hiba történt a(z) "[%s] - %s" torrent letöltése '
                        "közben.",
                        self.name,
                        download_url,
                        exc_info=e,
                    )
                    raise

                return response.content

            if attempt == _RATE_LIMIT_MAX_ATTEMPTS:
                break

            await asyncio.sleep(self._retry_after_seconds(response))

        raise IndexerDefinitionException(
            f"A(z) {self.name} forgalomkorlátja nem engedte a .torrent "
            f"letöltését (HTTP 429) {_RATE_LIMIT_MAX_ATTEMPTS} próbálkozás után "
            "sem. A tracker percenként 30 letöltést enged fiókonként. Nyisd meg "
            "a címet újra: a már letöltött .torrent fájlok megmaradnak, a "
            "hiányzók pedig a következő körben sorra kerülnek."
        )

    async def _reserve_download_slot(self) -> None:
        """Foglal egy időrést, és megvárja, amíg az elérkezik.

        A foglalás a zár alatt történik, a VÁRAKOZÁS viszont már nem: így a
        sorban állók egyszerre várnak a saját idejükre, nem egymás után
        sorosítva. A sorrend a zár FIFO viselkedéséből adódik — a keresés
        seederek szerint csökkenő sorrendben adja a találatokat, tehát a
        legjobbak kapnak elsőként helyet.
        """
        loop = asyncio.get_running_loop()

        async with self._download_lock:
            now = loop.time()
            slot = max(now, self._next_download_at)
            wait = slot - now

            if wait > _DOWNLOAD_MAX_QUEUE_WAIT:
                raise IndexerDefinitionException(
                    f"A(z) {self.name} letöltési sora túl hosszú "
                    f"({wait:.0f} másodperc várakozás), ezért ez a .torrent "
                    "kimarad. A tracker percenként 30 letöltést enged "
                    "fiókonként. Nyisd meg a címet újra: a már letöltöttek "
                    "megmaradnak, a hiányzók a következő körben jönnek."
                )

            self._next_download_at = slot + _DOWNLOAD_MIN_INTERVAL

        if wait > 0:
            await asyncio.sleep(wait)

    def _retry_after_seconds(self, response: httpx.Response) -> float:
        """A Retry-After fejléc másodpercben, ésszerű határok közé szorítva.

        A Laravel throttle-ja másodpercet küld. Ha hiányzik vagy értelmezhetetlen,
        a tartalék várakozással megyünk tovább.
        """
        try:
            seconds = float(response.headers.get("retry-after", ""))
        except (TypeError, ValueError):
            seconds = _RATE_LIMIT_FALLBACK_WAIT

        return min(max(seconds, _RATE_LIMIT_FALLBACK_WAIT), _RATE_LIMIT_MAX_WAIT)

    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent | None:
        if not torrent_id.isdigit():
            # A UNIT3D route-ja `[0-9]+`-ra van kötve (routes/api.php), és a
            # hívó (indexers/service.py get_torrents_by_torrent_id) minden
            # indexert végigkérdez ugyanazzal az azonosítóval — a nem számjegyű
            # biztosan másik trackeré.
            return None

        response = await self._get_with_retry(
            _TORRENT_PATH.format(torrent_id=quote(torrent_id, safe=""))
        )

        if response.status_code == 404:
            return None

        payload = self._json_payload(response)
        if payload is None:
            return None

        # A show() a TorrentResource-t burkolás NÉLKÜL adja vissza
        # (`TorrentResource::withoutWrapping()`), a többi végpont viszont
        # "data" alatt — mindkettőt elfogadjuk.
        row = payload.get("data") if isinstance(payload.get("data"), dict) else payload

        attributes = row.get("attributes")
        if not isinstance(attributes, dict):
            return None

        download_url = str(attributes.get("download_link") or "").strip()
        if not download_url:
            return None

        row_imdb_id = self._row_imdb_id(attributes)

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=f"tt{row_imdb_id:07d}" if row_imdb_id else None,
            seeders=self._resolve_seeders(attributes),
            download_url=download_url,
            attribute_ids=self._resolve_attribute_ids(attributes),
        )

    # -- Hit & Run -----------------------------------------------------

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        """Üres lista, HA a 240 órás megtartási padló él — különben kivétel.

        A tracker kötelezettsége tisztán IDŐ alapú (10 nap minden kiadásra, az
        arány nem kiút), egyedi kivételek listája pedig nincs — a UNIT3D API-ja
        nem ad Unsatisfied végpontot. Ezért itt nincs értelmes torrent-lista:
        a helyes válasz az, hogy MINDEN torrentet meg kell tartani 240 óráig,
        utána egyiket sem kell.

        Ezt a megtartási időt a stremhu/patches/torrents_service.append.py
        kényszeríti ki (a takarítás keep seed értékét emeli a minimumra), tehát
        ha a padló a helyén van, az üres lista pontosan azt jelenti, amit kell:
        "nincs egyedi kivétel". A felhasználónak nem kell semmit beállítania.

        Ha a padló HIÁNYZIK (gyári image, patch nélkül), akkor az üres lista azt
        jelentené a takarítónak, hogy egyetlen torrenten sincs kötelezettség, és
        keep seed nélkül azonnal törölné őket. Ilyenkor visszaáll a kivétel: a
        takarítás kimarad, és semmi nem törlődik.
        """
        floor = self._keep_seed_floor_seconds()

        if floor is None or floor < _MINIMUM_SEED_TIME:
            raise IndexerDefinitionException(
                f"A(z) {self.name} nem ad lekérdezhető Unsatisfied (Hit & Run) "
                "listát: a UNIT3D API-ja csak torrenteket, kéréseket és a saját "
                "profilt ismeri, a webes Unsatisfied oldal pedig "
                "munkamenet-sütit kíván, amit az API kulcs nem ad meg. A "
                f"kötelező {_MINIMUM_SEED_TIME // 3600} órás megtartást "
                "rendszerint a seedpool patch kényszeríti ki "
                "(patches/torrents_service.append.py), de az most nincs a "
                "helyén — a takarítás ezért biztonságból kimarad. Vagy építsd "
                "újra az image-et a patchcsel, vagy kapcsold ki a Hit & Run-t "
                "ennél az indexernél, és állíts be legalább "
                f"{_MINIMUM_SEED_TIME // 3600} óra keep seed időt. A tracker "
                "elvárása: minden kiadást — a freeleecheket is — legalább "
                f"{_MINIMUM_SEED_TIME // 86400} napig seedelni kell, az arány "
                "itt nem kiút; enélkül Unsatisfied lesz belőle, és fogynak a "
                "letöltési sávjaid."
            )

        return []

    def _keep_seed_floor_seconds(self) -> int | None:
        """A seedpool patch által kikényszerített megtartási idő, ha van.

        Az import SZÁNDÉKOSAN a metóduson belül van, és minden hibát elnyel: a
        modul fejlécében ugyanez az import a gyári (patch nélküli) image-en a
        definíció betöltését buktatná el, azzal pedig a
        discover_indexer_definitions() az ÖSSZES definíciót elveszítené.
        """
        try:
            from app.modules.torrents.service import STREMHU_KEEP_SEED_FLOOR

            return STREMHU_KEEP_SEED_FLOOR.get(self.id)
        except Exception:
            return None

    # -- Metaadat (IMDB → TMDB) ----------------------------------------

    async def _resolve_metadata(self, imdb_id: str) -> _TitleMetadata | None:
        if imdb_id in self._metadata_cache:
            return self._metadata_cache[imdb_id]

        metadata = await self._fetch_metadata(imdb_id)

        # A hibás lekérés kivételt dob, tehát a gyorsítótárba csak érvényes
        # (akár "nincs ilyen") válasz kerül.
        if len(self._metadata_cache) >= _METADATA_CACHE_LIMIT:
            self._metadata_cache.pop(next(iter(self._metadata_cache)))
        self._metadata_cache[imdb_id] = metadata

        return metadata

    async def _fetch_metadata(self, imdb_id: str) -> _TitleMetadata | None:
        """Az IMDB azonosító TMDB párja a Cinemetából.

        Külön httpx klienssel, NEM a self._client-tel: annak a base_url-je a
        trackerre mutat, és minden válaszán lefutna a
        _detect_authentication_error. Kérésenként új kliens: a hívás a
        gyorsítótár miatt címenként egyszer fut le.

        Hiba esetén NEM dob kivételt, hanem None-t ad: ez a MÁSODIK menet, az
        első (imdbId) már lefutott. Egy Cinemeta-kiesés így nem viszi magával az
        egész keresést.
        """
        try:
            async with httpx.AsyncClient(
                timeout=_CINEMETA_TIMEOUT,
                follow_redirects=True,
            ) as client:
                for media_type in _CINEMETA_TYPES:
                    url = _CINEMETA_URL.format(
                        media_type=media_type,
                        imdb_id=quote(imdb_id, safe=""),
                    )
                    response = await client.get(
                        url, headers={"Accept": "application/json"}
                    )

                    if response.status_code != 200:
                        continue

                    metadata = self._parse_cinemeta_meta(
                        response, imdb_id, media_type
                    )
                    if metadata is not None:
                        return metadata
        except httpx.HTTPError as e:
            self._warn_once(
                "cinemeta-unreachable",
                "seedpool: a Cinemeta nem érhető el (%s), ezért a TMDB alapú "
                "második keresési menet kimarad. A találatok csak azokból a "
                "sorokból jönnek, ahol a tracker kitöltötte az IMDB "
                "azonosítót.",
                e,
            )

        return None

    def _parse_cinemeta_meta(
        self,
        response: httpx.Response,
        imdb_id: str,
        media_type: str,
    ) -> _TitleMetadata | None:
        payload = self._json_payload(response)
        meta = (payload or {}).get("meta")
        if not isinstance(meta, dict):
            return None

        # Az azonosító egyezését ellenőrizzük: a cinemeta-live tartalék néha
        # MÁSIK címet ad vissza (lásd a fájl fejlécét).
        if imdb_id not in (meta.get("id"), meta.get("imdb_id")):
            return None

        if not str(meta.get("name") or "").strip():
            # Név nélküli rekord: csonka válasz, nem támaszkodunk rá.
            return None

        try:
            tmdb_id = int(meta.get("moviedb_id"))
        except (TypeError, ValueError):
            return None

        if tmdb_id <= 0:
            return None

        return _TitleMetadata(tmdb_id=tmdb_id, is_series=media_type == "series")

    # -- Segédfüggvények -----------------------------------------------

    def _map_rows(
        self,
        rows: list[Any],
        imdb_id: str,
        numeric_imdb_id: int,
    ) -> list[IndexerDefinitionTorrent]:
        torrents: list[IndexerDefinitionTorrent] = []

        for row in rows:
            torrent = self._map_row(row, imdb_id, numeric_imdb_id)
            if torrent is not None:
                torrents.append(torrent)

        return torrents

    def _map_row(
        self,
        row: Any,
        imdb_id: str,
        numeric_imdb_id: int,
    ) -> IndexerDefinitionTorrent | None:
        if not isinstance(row, dict):
            return None

        torrent_id = str(row.get("id") or "").strip()
        attributes = row.get("attributes")

        if not torrent_id or not isinstance(attributes, dict):
            return None

        if not self._row_matches_imdb_id(attributes, numeric_imdb_id):
            return None

        download_url = str(attributes.get("download_link") or "").strip()
        if not download_url:
            # A letöltési link a válaszból jön (rsskey-jel a végén), nem
            # számoljuk ki — enélkül a sor használhatatlan.
            return None

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            # A KÉRT azonosítót adjuk vissza: a bázisosztály _find_all-ja nyers
            # string egyezésre szűr, a soron viszont szám (vagy 0) áll.
            imdb_id=imdb_id,
            seeders=self._resolve_seeders(attributes),
            download_url=urljoin(self.url, download_url),
            attribute_ids=self._resolve_attribute_ids(attributes),
        )

    def _row_matches_imdb_id(
        self,
        attributes: dict[str, Any],
        numeric_imdb_id: int,
    ) -> bool:
        """Igaz, ha a sor nem mond ellent a kért IMDB azonosítónak.

        A hiányzó (0) azonosítót elfogadjuk: a tmdb menetben pont az ilyen sorok
        miatt keresünk. A KITÖLTÖTT, de eltérő azonosító viszont biztos jel,
        hogy a sor másik műsorhoz tartozik — ez fogja ki a TMDB szám-ütközést
        (film és sorozat külön számozás).
        """
        row_imdb_id = self._row_imdb_id(attributes)

        return row_imdb_id is None or row_imdb_id == numeric_imdb_id

    def _row_imdb_id(self, attributes: dict[str, Any]) -> int | None:
        try:
            row_imdb_id = int(attributes.get("imdb_id"))
        except (TypeError, ValueError):
            return None

        # A UNIT3D a "nincs megadva" esetet 0-val jelöli.
        return row_imdb_id or None

    def _resolve_seeders(self, attributes: dict[str, Any]) -> int:
        try:
            return int(attributes.get("seeders"))
        except (TypeError, ValueError):
            return 0

    def _resolve_next_page(self, data: dict[str, Any], page: int) -> int | None:
        """A következő lap száma a válasz `links.next` mezőjéből.

        A UNIT3D a nem-modo ágon kézzel állítja össze a linkeket
        (TorrentController::filter): a `next` akkor és csak akkor URL, ha van
        még lap, egyébként null. Ez pontosabb, mint a sorok számából
        következtetni.
        """
        if page - _FIRST_PAGE + 1 >= _MAX_PAGES:
            return None

        links = data.get("links")
        if not isinstance(links, dict) or not links.get("next"):
            return None

        return page + 1

    def _resolve_attribute_ids(self, attributes: dict[str, Any]) -> list[str]:
        # Nyelv: a tracker angol nyelvű (a Jackett definíciója `language:
        # en-US`). Ez FALLBACK: ha a release névből más jön ki, a rendszer azt
        # használja helyette (media_attributes/parser.py, external_fallbacks).
        attribute_ids = [MediaAttributeKey.ENG]

        resolution = _RESOLUTION_ATTRIBUTES.get(
            str(attributes.get("resolution") or "").strip().lower()
        )
        if resolution:
            attribute_ids.append(resolution)

        discount = self._resolve_discount(attributes)
        if discount:
            attribute_ids.append(discount)

        return attribute_ids

    def _resolve_discount(self, attributes: dict[str, Any]) -> str | None:
        """FreeLeech / Half-leech az API `freeleech` és `featured` mezőjéből.

        A `freeleech` a kedvezmény SZÁZALÉKA szövegként ("0%" … "100%", a
        forrásban `$this->free.'%'`), a `featured` pedig önmagában ingyenessé
        tesz (a Jackett definíciója is így számol:
        `downloadvolumefactor: {{ if featured }}0{{ else }}…`).

        Nem tippelünk se méretből, se release névből: amit a tracker nem mond
        meg, azt nem állítjuk.
        """
        if attributes.get("featured") is True:
            return _FREELEECH_ATTRIBUTE_ID

        match = _PERCENT.search(str(attributes.get("freeleech") or ""))
        if not match:
            return None

        try:
            percent = float(match.group(1))
        except ValueError:
            return None

        if percent >= 100:
            return _FREELEECH_ATTRIBUTE_ID

        if percent > 0:
            # A katalógusban csak teljes és fél kedvezmény van; a 25% és a 75%
            # is ide esik. Kevesebbet ígérni pontatlan, de biztonságos.
            return _HALFLEECH_ATTRIBUTE_ID

        return None

    def _json_payload(self, response: httpx.Response) -> dict[str, Any] | None:
        """A válasz JSON objektuma, vagy None, ha nem az."""
        try:
            data = response.json()
        except Exception:
            return None

        return data if isinstance(data, dict) else None

    def _warn_once(self, key: str, message: str, *args: Any) -> None:
        if key in self._warned:
            return

        self._warned.add(key)
        # WARNING, nem INFO: éles naplószinten az INFO néma lenne.
        self.logger.warning(message, *args)
