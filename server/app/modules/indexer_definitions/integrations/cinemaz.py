
import asyncio
import math
import re
from typing import Any
from urllib.parse import urljoin

import httpx

from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.exceptions import (
    AuthenticationException,
    CredentialsRequiredException,
    IndexerDefinitionException,
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
from app.modules.media_attributes.constants import MediaAttributeKey

_AUTH_PATH = "/api/v1/jackett/auth"
_SEARCH_PATH = "/api/v1/jackett/torrents"

# A Jackett is ezt küldi: in=1 (a hálózat saját "hol keressen" kapcsolója),
# type=0 (kategóriaszűrés nélkül), limit=50 (a lapméret felső határa).
_PAGE_LIMIT = 50

# A hálózat 429-cel válaszol a sűrű kérésre, a Jackett is késleltetéssel megy.
# A max_concurrent=1 mellett ez legfeljebb egy kérés másodpercenként.
_MIN_REQUEST_INTERVAL_SECONDS = 1.0

# AvistaZ/CinemaZ: /torrent/12345-slug, AnimeZ: /torrents/12345-slug
_TORRENT_ID_PATTERN = re.compile(r"/torrents?/(\d+)")
_IMDB_ID_PATTERN = re.compile(r"(\d+)")

# Csak az egyértelmű értékek. Ismeretlen video_quality esetén nem állítunk be
# felbontást — a release névből kiolvasott érték pontosabb a tippnél.
_RESOLUTION_MAP: dict[str, str] = {
    "2160p": MediaAttributeKey.R2160P,
    "1080p": MediaAttributeKey.R1080P,
    "1080i": MediaAttributeKey.R1080P,
    "720p": MediaAttributeKey.R720P,
    "576p": MediaAttributeKey.R576P,
    "540p": MediaAttributeKey.R540P,
    "480p": MediaAttributeKey.R480P,
}

# A Cloudflare challenge oldal ujjlenyomatai. A JSON API-tól ilyet nem várunk,
# de ha mégis jön, beszédes hibát kell dobni: enélkül a válasz "nem JSON"
# hibaként jelenne meg, és a felhasználó a saját fiókját hibáztatná.
_CLOUDFLARE_MARKERS = (
    "just a moment",
    "cf-chl",
    "cf_chl_opt",
    "attention required! | cloudflare",
    "checking your browser before accessing",
)

# A H&R üzenetben mutatott példaméretek (GB).
_SEED_TIME_EXAMPLES = (5, 20, 50, 100)

# A kedvezmény attribútumai. Ezeket a stremhu/patches/ teszi a StremHU
# attribútum-katalógusába; patch nélküli image-en a resolve_attribute_ids()
# némán eldobja őket — a definíció ettől még hibátlanul működik.
_FREELEECH_ATTRIBUTE = "freeleech"
_HALFLEECH_ATTRIBUTE = "halfleech"

# Az API audio[].language értékei (kisbetűsítve, részleges egyezéssel) →
# attribútum azonosító. A SORREND SZÁMÍT: a StremHU kategóriánként egyetlen
# attribútumot vesz át az indexertől, ezért a magyar és az angol elöl van, a
# többi a lista sorrendjében dönt. A részleges egyezés szándékos: a tracker
# "Mandarin Chinese" vagy "Brazilian Portuguese" alakot is ad.
_LANGUAGE_ATTRIBUTES: tuple[tuple[str, str], ...] = (
    ("hungarian", MediaAttributeKey.HUN),
    ("english", MediaAttributeKey.ENG),
    ("french", "fra"),
    ("german", "ger"),
    ("italian", "ita"),
    ("spanish", "spa"),
    ("portuguese", "por"),
    ("russian", "rus"),
    ("polish", "pol"),
    ("czech", "cze"),
    ("romanian", "rom"),
    ("turkish", "tur"),
    ("greek", "gre"),
    ("dutch", "nld"),
    ("flemish", "nld"),
    ("swedish", "swe"),
    ("danish", "dan"),
    ("norwegian", "nor"),
    ("japanese", "jpn"),
    ("korean", "kor"),
    ("mandarin", "zho"),
    ("cantonese", "zho"),
    ("chinese", "zho"),
)


def _required_seed_hours(size_gb: float) -> float:
    """A CinemaZ kötelező seed ideje órában, a szabályzat képlete szerint.

    A tracker H&R táblázatának mind a 30 sorával egyezik (kerekítve): 5 GB → 82,
    20 GB → 112, 50 GB → 172, 100 GB → 241, 500 GB → 402, 1000 GB → 472 óra.

    Egyetlen eltérés a táblázat első sora: 1 GB-ra 74 órát ír, a képlet viszont
    ott már a 72 órás ágon van. Két óra a szabályzat két saját megfogalmazása
    között — a képletet követjük, mert az az egzakt megfogalmazás.
    """
    if size_gb <= 1:
        return 72.0

    if size_gb < 50:
        return 72.0 + 2.0 * size_gb

    return 100.0 * math.log(size_gb) - 219.2023


def _is_html(response: httpx.Response) -> bool:
    return "html" in response.headers.get("content-type", "").lower()


def _looks_like_cloudflare_challenge(response: httpx.Response) -> bool:
    server = response.headers.get("server", "").lower()
    if response.status_code in (403, 503) and "cloudflare" in server:
        return True

    # A challenge mindig HTML. A JSON válaszokat és a .torrent letöltés
    # bájtjait meg sem nézzük — ott a response.text felesleges dekódolás.
    if not _is_html(response):
        return False

    return any(marker in response.text[:2000].lower() for marker in _CLOUDFLARE_MARKERS)


class CinemazIndexerDefinition(BaseIndexerDefinition):
    def __init__(
        self,
        indexer_account_storage: IndexerAccountStorage | None = None,
    ) -> None:
        super().__init__(indexer_account_storage)

        # A PID-et a login() teszi ide, a _login onnan veszi. A két hívás
        # között nincs másik: az egyidejű újra-bejelentkezéseket a bázisosztály
        # relogin()-ja egyetlen future mögé sorolja.
        self._pid: str = ""

        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0

    @property
    def id(self) -> str:
        return "cinemaz"

    @property
    def name(self) -> str:
        return "CinemaZ"

    @property
    def url(self) -> str:
        return "https://cinemaz.to"

    @property
    def login_path(self) -> str:
        return _AUTH_PATH

    @property
    def details_path(self) -> str:
        return "/torrent/{torrent_id}"

    @property
    def supports_totp(self) -> bool:
        # Nem TOTP: ez a mező hordozza a PID-et — lásd a fájl fejlécét.
        return True

    @property
    def requires_full_download(self) -> bool:
        # A H&R szabály miatt True, nem a letöltés módja miatt. A tracker
        # dokumentációja: "Seeding time is only counted after you have 100% of
        # the files. Partial downloads don't count as seeding (no hours
        # counted)." Streamelős módban a StremHU csak a lejátszáshoz kellő
        # darabokat tölti le — az egy filmnél bőven a 10%-os küszöb fölött van,
        # tehát keletkezik kötelezettség, az időalapú mentesülés viszont nem
        # jár rá. A felhasználó ezt felülírhatja az indexer fiókjánál
        # (download_full_torrent).
        return True

    @property
    def max_concurrent(self) -> int:
        # A hálózat rate limitel (429). A bázisosztály alapértéke (5) itt sok.
        return 1

    # -- Hitelesítés ---------------------------------------------------

    async def login(self, credential: IndexerDefinitionLogin | None = None) -> None:
        """A bázisosztály login()-ja, a pyotp lépés kikerülésével.

        A PID a totp_secret mezőben érkezik (lásd a fájl fejlécét), a
        bázisosztály viszont base32 TOTP kulcsként dekódolná. Ezért kivesszük a
        credentialból, eltesszük a _login számára, és a maradékkal hívjuk a
        szülőt — a cookie-törlés, a payload összeállítása és a hibakezelés így
        marad a bázisosztályé, és egy jövőbeli upstream változás sem esik ki
        alóla.

        A fiókadatok kiolvasását meg kell ismételni: relogin()-nál a szülő
        magától is elvégezné, csakhogy akkor már a nyers totp_secret-tel futna
        neki a pyotp-nek. Az egyetlen mellékhatás, hogy a szülő ilyenkor "első
        bejelentkezésnek" látja a hívást, és nem menti el a cookie-kat — itt
        nincs is mit menteni, a munkamenet Bearer token.
        """
        if credential is None:
            if not self._indexer_account_storage:
                raise CredentialsRequiredException(
                    f"A(z) {self.name} hitelesítési információk nincsenek megadva."
                )

            credential = await asyncio.to_thread(
                self._indexer_account_storage.get_credentials, self.id
            )

        if credential is None:
            raise CredentialsRequiredException(
                f"A(z) {self.name} hitelesítési információk nincsenek megadva."
            )

        pid = (credential.totp_secret or "").strip()
        if not pid:
            raise CredentialsRequiredException(
                f"A(z) {self.name} API-ja a felhasználónév és jelszó mellett a "
                "PID-et is megköveteli. Pipáld be a 'Kétlépcsős azonosítás "
                "(2FA / TOTP) használata' jelölőt, és a '2FA titkos kulcs "
                "(TOTP)' mezőbe a PID-et írd — nem 2FA kulcsot. A PID a "
                "tracker profilodban, a My Account oldalon található."
            )

        self._pid = pid

        await super().login(credential.model_copy(update={"totp_secret": None}))

    async def _login(
        self,
        payload: IndexerDefinitionLoginPayload,
    ) -> httpx.Response:
        # A régi token eldobása: sikertelen bejelentkezés után se maradjon élő
        # Authorization fejléc a kliensen.
        self._client.headers.pop("Authorization", None)

        await self._throttle()

        # Űrlapként megy, nem JSON-ként — a Jackett is így küldi, és a működő
        # kliens a mérvadó minta. (A payload.totp_code itt mindig None: a PID-et
        # a login() vette ki a credentialból.)
        response = await self._client.post(
            _AUTH_PATH,
            data={
                "username": payload.username.strip(),
                "password": payload.password.strip(),
                "pid": self._pid,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )

        body = self._json_body(response)
        token = body.get("token") if isinstance(body, dict) else None

        if not token:
            raise AuthenticationException(
                self._api_message(response)
                or f"A(z) {self.name} nem adott vissza tokent a bejelentkezésre."
            )

        self._client.headers["Authorization"] = f"Bearer {token}"

        return response

    def _detect_authentication_error(self, response: httpx.Response) -> AuthError:
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", "").strip()

            retry_hint = (
                f" Újrapróbálható {retry_after} másodperc múlva." if retry_after else ""
            )

            return AuthOtherError(
                message=(
                    f"A(z) {self.name} átmenetileg letiltotta a kéréseket "
                    f"(429 — túl sok kérés).{retry_hint}"
                )
            )

        if _looks_like_cloudflare_challenge(response):
            return AuthOtherError(
                message=(
                    f"A(z) {self.name} Cloudflare-ellenőrző oldalt adott vissza. "
                    "Ezt a beépített kliens nem tudja megoldani, mert JS "
                    "futtatás kellene hozzá."
                )
            )

        if str(response.url.path).endswith(_AUTH_PATH):
            # A bejelentkezés válaszára SOHA nem adhatunk AuthSessionError-t:
            # az újra-bejelentkezést indítana a bejelentkezés közben.
            if response.status_code >= 400:
                return AuthCredentialError(message=self._api_message(response))

            return None

        # Lejárt vagy hiányzó Bearer token. A Jackett a 401-re és a 403-ra is
        # tokent újít; a 412-t a hálózat a hiányzó fejlécre adja.
        if response.status_code in (401, 403, 412):
            return AuthSessionError()

        return None

    # -- Keresés -------------------------------------------------------

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 1
        response = await self._api_get({"imdb": imdb_id, "page": str(current_page)})

        # Találat nélküli keresésre a tracker 404-et ad, nem üres listát.
        if response.status_code == 404:
            return IndexerDefinitionFindTorrentsResult(torrents=[])

        body = self._require_body(response)
        rows = body.get("data") or []

        torrents = [
            torrent
            for torrent in (self._map_row(row, imdb_id) for row in rows)
            if torrent is not None
        ]

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=self._resolve_next_page(body, len(rows), current_page),
        )

    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent | None:
        # Az API-nak nincs "egy torrent azonosító alapján" végpontja, az adatlap
        # HTML-je pedig bejelentkezés nélkül nem érhető el. Az "id" szűrőt ezért
        # csak megpróbáljuk, a sorokat viszont tételesen ellenőrizzük: ha a
        # tracker nem ismeri a paramétert, szűretlen listát kapunk vissza.
        response = await self._api_get({"id": torrent_id})

        if response.status_code == 404:
            return None

        for row in self._require_body(response).get("data") or []:
            torrent = self._map_row(row)
            if torrent and torrent.torrent_id == torrent_id:
                return torrent

        return None

    # -- Hit & Run -----------------------------------------------------

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        """Üres lista, HA a méret-alapú megtartási szabály él — különben kivétel.

        A trackertől LISTÁT nem tudunk kérni: a Jackett API csak keresést tud, a
        snatchlist és a H&R fül HTML-je pedig a captchás bejelentkezés mögött
        van, oda a Bearer token nem jó. A kötelezettség viszont nem is
        egyedi-kivétel jellegű, hanem KISZÁMÍTHATÓ: a szabályzat képlete a
        torrent méretéből adja a kötelező seed időt (_required_seed_hours), és
        ezt a torrent saját adataiból ki tudjuk számolni — a trackert meg sem
        kell kérdezni hozzá.

        Ezt a számítást a stremhu/patches/torrents_service.append.py végzi el a
        takarítás pillanatában (STREMHU_SEED_TIME_RULES): torrentenként
        kiszámolja a méretéhez tartozó kötelező időt, és a még kötelezettség
        alatt állókat ugyanúgy kihagyatja a törlésből, mintha a tracker H&R
        listáján lennének. Ha a szabály a helyén van, az üres lista pontosan azt
        jelenti, amit kell: "ezen felül nincs egyedi kivétel".

        Ha a szabály HIÁNYZIK (gyári image, patch nélkül), visszaáll a kivétel:
        az üres lista ott azt jelentené a takarítónak, hogy egyetlen torrenten
        sincs kötelezettség, és letörölné a még seedelendőket is. A kivételtől
        viszont ez az indexer kimarad a takarításból, tehát semmi nem törlődik.
        """
        if self._seed_time_rule_active():
            return []

        examples = ", ".join(
            f"{size_gb} GB → {round(_required_seed_hours(size_gb))} óra"
            for size_gb in _SEED_TIME_EXAMPLES
        )

        raise IndexerDefinitionException(
            f"A(z) {self.name} API-ja nem ad vissza Hit & Run listát (csak "
            "keresést tud, a snatchlist pedig captchás bejelentkezés mögött "
            "van), a méret-alapú megtartási szabályt kikényszerítő cinemaz.py "
            "patch pedig nincs a helyén — ezért a takarítás biztonságból "
            "kimarad. Vagy építsd újra az image-et a patchcsel (docker compose "
            "build stremhu-source), vagy kapcsold ki a Hit & Run-t ennél az "
            "indexernél, és állíts be helyette keep seed időt. A tracker "
            f"elvárása: 72 óra + 2 óra/GB 50 GB alatt, e fölött "
            f"100*ln(GB) - 219.2 óra, vagy 0.90 arány ({examples})."
        )

    def _seed_time_rule_active(self) -> bool:
        """Él-e a cinemaz.py méret-alapú megtartási szabály erre az indexerre.

        Az import SZÁNDÉKOSAN a metóduson belül van, és minden hibát elnyel: a
        modul fejlécében ugyanez az import a gyári (patch nélküli) image-en a
        definíció betöltését buktatná el, azzal pedig a
        discover_indexer_definitions() az ÖSSZES definíciót elveszítené.
        """
        try:
            from app.modules.torrents.service import STREMHU_SEED_TIME_RULES

            return self.id in STREMHU_SEED_TIME_RULES

        except Exception:
            return False

    # -- Segédfüggvények -----------------------------------------------

    async def _api_get(self, params: dict[str, str]) -> httpx.Response:
        await self._throttle()

        return await self._client.get(
            _SEARCH_PATH,
            params={"in": "1", "type": "0", "limit": str(_PAGE_LIMIT), **params},
            headers={"Accept": "application/json"},
        )

    async def _throttle(self) -> None:
        """Minimális kérésköz a 429-es tiltás elkerülésére."""
        async with self._request_lock:
            loop = asyncio.get_running_loop()
            elapsed = loop.time() - self._last_request_at

            if 0 <= elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
                await asyncio.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)

            self._last_request_at = loop.time()

    def _require_body(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            message = self._api_message(response) or ""

            raise IndexerDefinitionException(
                f"A(z) {self.name} API hibát adott vissza: "
                f"{response.status_code} {message}".strip()
            )

        body = self._json_body(response)
        if not isinstance(body, dict):
            raise IndexerDefinitionException(
                f"A(z) {self.name} API válasza nem értelmezhető — valószínűleg "
                "megváltozott a végpont."
            )

        return body

    def _json_body(self, response: httpx.Response) -> Any:
        if "json" not in response.headers.get("content-type", "").lower():
            return None

        try:
            return response.json()
        except Exception:
            # A _detect_authentication_error is hív ide, minden válaszra: onnan
            # kivételt dobni azt jelentené, hogy egy csonka válasz elfedi a
            # valódi hibát.
            return None

    def _api_message(self, response: httpx.Response) -> str | None:
        body = self._json_body(response)

        if isinstance(body, dict):
            message = body.get("message")

            return message if isinstance(message, str) and message else None

        return body if isinstance(body, str) and body else None

    def _resolve_next_page(
        self,
        body: dict[str, Any],
        row_count: int,
        current_page: int,
    ) -> int | None:
        if row_count <= 0:
            return None

        # A hálózat Laravel-lapozót ad vissza (current_page, last_page,
        # next_page_url, total). Ha megvan, abból dolgozunk; ez terminál akkor
        # is, ha a lapméret nem a kértnek megfelelő.
        last_page = body.get("last_page")
        if isinstance(last_page, int):
            return current_page + 1 if current_page < last_page else None

        if body.get("next_page_url"):
            return current_page + 1

        # Fallback: tele lap = valószínűleg van folytatás.
        return current_page + 1 if row_count >= _PAGE_LIMIT else None

    def _map_row(
        self,
        row: Any,
        requested_imdb_id: str | None = None,
    ) -> IndexerDefinitionTorrent | None:
        if not isinstance(row, dict):
            return None

        match = _TORRENT_ID_PATTERN.search(str(row.get("url") or ""))
        download_url = str(row.get("download") or "").strip()

        # Azonosító vagy letöltési link nélkül a sor használhatatlan.
        if not match or not download_url:
            return None

        return IndexerDefinitionTorrent(
            torrent_id=match.group(1),
            download_url=urljoin(self.url, download_url),
            imdb_id=self._resolve_imdb_id(row, requested_imdb_id),
            seeders=self._resolve_seeders(row),
            attribute_ids=self._resolve_attribute_ids(row),
        )

    def _resolve_imdb_id(
        self,
        row: dict[str, Any],
        requested_imdb_id: str | None,
    ) -> str | None:
        movie_tv = row.get("movie_tv")
        raw_imdb_id = movie_tv.get("imdb") if isinstance(movie_tv, dict) else None
        imdb_id = self._normalize_imdb_id(raw_imdb_id)

        if not imdb_id:
            # IMDB szerinti keresésnél a találat a keresett filmhez tartozik.
            return requested_imdb_id

        # A bázisosztály _find_all-ja nyers string egyezésre szűr a végén, ezért
        # egyezésnél a KÉRT alakot adjuk vissza (tt0058083 vs. 58083).
        if requested_imdb_id and self._normalize_imdb_id(requested_imdb_id) == imdb_id:
            return requested_imdb_id

        return imdb_id

    def _normalize_imdb_id(self, value: Any) -> str | None:
        match = _IMDB_ID_PATTERN.search(str(value)) if value else None

        return f"tt{match.group(1).zfill(7)}" if match else None

    def _resolve_seeders(self, row: dict[str, Any]) -> int:
        try:
            return int(row.get("seed"))
        except (TypeError, ValueError):
            return 0

    def _resolve_attribute_ids(self, row: dict[str, Any]) -> list[str]:
        # Csak az kerül ide, ami a sorból biztosan megállapítható. A forrást,
        # kodeket, HDR-t és hangot a rendszer a release névből és a letöltött
        # torrent fájlból dolgozza fel — a tippelés itt csak rontana rajta.
        attribute_ids = [
            _RESOLUTION_MAP.get(str(row.get("video_quality") or "").strip().lower()),
            self._resolve_language(row),
            self._resolve_discount(row),
        ]

        return [attribute_id for attribute_id in attribute_ids if attribute_id]

    def _resolve_discount(self, row: dict[str, Any]) -> str | None:
        """FreeLeech / Half-leech a download_multiply mezőből.

        A hálózat mérethez köti a kedvezményt (10-20 GB között half-leech, e
        fölött freeleech), plusz akciók is vannak — a méretből visszafejteni
        tehát fölösleges és pontatlan is lenne, a tracker megmondja.

        Hiányzó vagy értelmezhetetlen értéknél nem állítunk semmit: a hamis
        "ingyenes" címke rosszabb, mint a hiányzó — az arány bánná.
        """
        try:
            multiply = float(row.get("download_multiply"))
        except (TypeError, ValueError):
            return None

        if multiply <= 0:
            return _FREELEECH_ATTRIBUTE

        if multiply < 1:
            return _HALFLEECH_ATTRIBUTE

        return None

    def _resolve_language(self, row: dict[str, Any]) -> str | None:
        languages = [
            str(item.get("language") or "").lower()
            for item in (row.get("audio") or [])
            if isinstance(item, dict)
        ]

        for needle, attribute_id in _LANGUAGE_ATTRIBUTES:
            if any(needle in language for language in languages):
                return attribute_id

        # A CinemaZ világmozis tracker: a listán kívüli nyelvekre nincs
        # attribútum. Semmit nem állítunk — a rendszer a release névből még
        # kiszedheti.
        return None
