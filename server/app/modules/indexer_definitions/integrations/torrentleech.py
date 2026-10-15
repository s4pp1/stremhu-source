import asyncio
import re
from urllib.parse import quote, urljoin

import httpx
from selectolax.parser import HTMLParser, Node

from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
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

# A "newfilter/2" (0day és music bevonása) itt nem kell: IMDB-re keresünk,
# kategóriaszűrés nélkül. Seeders szerint rendezünk, hogy a _find_all 300-as
# limitjébe a használható találatok kerüljenek be először.
_SEARCH_PATH = (
    "/torrents/browse/list/imdbID/{imdb_id}/orderby/seeders/order/desc/page/{page}"
)
_DOWNLOAD_PATH = "/download/{torrent_id}/{filename}"
_HIT_AND_RUN_PATH = "/profile/{username}/hnr"
_SNATCHLIST_PATH = "/profile/{username}/snatchlist"

# 10 nap másodpercben: a legszigorúbb, Registered osztályra érvényes minimum
# seed idő (Power User 8, Super User 7, Extreme 6, TL God 4, VIP 0 nap). A
# fiók osztályát nem ismerjük, ezért a legszigorúbbal számolunk.
_MINIMUM_SEED_TIME = 864_000

# 10% letöltés alatt nem keletkezik kötelezettség (Rules → Hit and Run).
_HIT_AND_RUN_THRESHOLD = 0.10

# A DataTables "Showing 1 to 25 of 57 entries" felirata. Ha a szerver csak egy
# lapnyi sort küldött, ebből tudjuk meg, hogy nem látjuk a teljes listát.
_ENTRIES_PATTERN = re.compile(r"of\s+([\d,.]+)\s+entries", re.IGNORECASE)

# A kategóriából kiolvasható felbontás. Csak azok a kategóriák szerepelnek,
# ahol a besorolás egyértelmű — a "Movies WEBRip" vagy a boxsetek alatt SD és
# HD is van, ott inkább nem állítunk semmit.
#
# Ez fallback: ha a rendszer a release névből vagy a letöltött torrent fájlból
# kiszedi a valódi felbontást, az itteni értéket eldobja. Ezért kapnak a HD
# kategóriák 720p-t, hiába jelenthetnek 1080p-t is.
_CATEGORY_RESOLUTION: dict[str, str] = {
    "8": MediaAttributeKey.R480P,  # Movies Cam
    "9": MediaAttributeKey.R480P,  # Movies TS/TC
    "11": MediaAttributeKey.R480P,  # Movies DVDRip/DVDScreener
    "12": MediaAttributeKey.R480P,  # Movies DVD-R
    "26": MediaAttributeKey.R480P,  # TV Episodes (SD)
    "13": MediaAttributeKey.R720P,  # Movies Bluray
    "14": MediaAttributeKey.R720P,  # Movies BlurayRip
    "43": MediaAttributeKey.R720P,  # Movies HDRip
    "32": MediaAttributeKey.R720P,  # TV Episodes HD
    "47": MediaAttributeKey.R2160P,  # Movies 4K
}

# A kedvezmény attribútum azonosítója. SZÁNDÉKOSAN szövegkonstans és nem
# import: az upstream szerveren nem létezik ez az attribútum, egy import pedig
# a modul betöltését buktatná el — a discover_indexer_definitions() ilyenkor az
# ÖSSZES definíciót elveszítené.
_FREELEECH_ATTRIBUTE_ID = "freeleech"

# A Cloudflare challenge oldal ujjlenyomatai. A tracker normál böngésző
# User-Agenttel (amit a bázisosztály küld) jellemzően nem ad ilyet, de ha
# mégis, jobb azonnal beszédes hibát dobni, mint csendben hibás adatot adni.
_CLOUDFLARE_MARKERS = (
    "just a moment",
    "cf-chl",
    "cf_chl_opt",
    "attention required! | cloudflare",
    "checking your browser before accessing",
)


def _is_html(response: httpx.Response) -> bool:
    return "html" in response.headers.get("content-type", "").lower()


def _looks_like_cloudflare_challenge(response: httpx.Response) -> bool:
    server = response.headers.get("server", "").lower()
    if response.status_code in (403, 503) and "cloudflare" in server:
        return True

    # A challenge mindig HTML. A JSON keresési választ és a .torrent letöltés
    # bájtjait meg sem nézzük — a response.text ott felesleges dekódolás.
    if not _is_html(response):
        return False

    body_start = response.text[:2000].lower()

    return any(marker in body_start for marker in _CLOUDFLARE_MARKERS)


def _is_freeleech(row: dict) -> bool:
    """Igaz, ha a keresési találat FreeLeech.

    Elsődlegesen a `download_multiplier` mezőből (a Cardigann YAML is ezt
    olvassa: 0 = freeleech, 1 = normál), tartalékként a `tags` mezőből, amit a
    keresés `facets/tags:FREELEECH` szűrője is használ.

    A szabályzat két további szabályt is kimond — "all boxsets and packs will be
    marked FreeLeech" és "any torrent above 14GB will be FreeLeech" —, de MÉRET
    ALAPJÁN NEM TIPPELÜNK: egy tévesen freeleechnek jelölt torrent a felhasználó
    arányát viszi el. Ha a tracker megjelöli, a multiplier úgyis 0 lesz.
    """
    multiplier = row.get("download_multiplier")
    if multiplier is not None:
        try:
            return float(multiplier) == 0
        except (TypeError, ValueError):
            pass

    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    return any("freeleech" in str(tag).lower() for tag in tags)


def _parse_torrent_id(href: str | None) -> str | None:
    match = re.search(r"/torrent/(\d+)", href or "")

    return match.group(1) if match else None


def _parse_imdb_id(href: str | None) -> str | None:
    match = re.search(r"/title/(tt\d+)", href or "")

    return match.group(1) if match else None


def _parse_entry_total(text: str) -> int | None:
    """A snatchlist teljes sorszáma a DataTables feliratából, ha ott van."""
    match = _ENTRIES_PATTERN.search(text)
    if not match:
        return None

    digits = re.sub(r"\D", "", match.group(1))

    return int(digits) if digits else None


def _read_data_sort(node: Node | None) -> int | None:
    """A snatchlist celláinak data-sort attribútumát olvassa ki.

    A táblázat a megjelenített "1.31 GB" / "3 days" szövegek mellett gépileg
    olvasható értéket is tárol: bájtot, illetve másodpercet. None a válasz, ha
    a cella vagy az attribútum hiányzik, vagy nem szám — a hívó ilyenkor a
    biztonságos irányba dönt.
    """
    if node is None:
        return None

    raw = node.attributes.get("data-sort")
    if raw is None:
        return None

    try:
        return int(float(raw.strip()))
    except (TypeError, ValueError):
        return None


def _is_hit_and_run(
    size: int | None,
    downloaded: int,
    uploaded: int,
    seeding_time: int,
) -> bool:
    """Igaz, ha a torrenten még van H&R kötelezettség (nem törölhető).

    A tracker szabályzatának négy megállapítása, ebben a sorrendben:

    1. 10% letöltés alatt nem keletkezik kötelezettség.
    2. 1:1 arány a TÉNYLEGESEN letöltött adatra letudja — FreeLeech is.
    3. A minimum seed idő letudja, DE csak 100%-ban letöltött torrentnél:
       "Partial downloads never accrue seeding time".
    4. Ismeretlen méretnél nem tudjuk, teljes-e a letöltés, ezért sem a 10%-os
       mentesülést, sem az idő alapút nem alkalmazzuk — marad az 1:1.
    """
    if downloaded <= 0:
        return False

    has_size = size is not None and size > 0

    if has_size and downloaded < size * _HIT_AND_RUN_THRESHOLD:
        return False

    if uploaded >= downloaded:
        return False

    is_complete = has_size and downloaded >= size

    return not (is_complete and seeding_time >= _MINIMUM_SEED_TIME)


class TorrentleechIndexerDefinition(BaseIndexerDefinition):
    @property
    def id(self) -> str:
        return "torrentleech"

    @property
    def name(self) -> str:
        return "TorrentLeech"

    @property
    def url(self) -> str:
        return "https://www.torrentleech.org"

    @property
    def login_path(self) -> str:
        return "/user/account/login/"

    @property
    def details_path(self) -> str:
        return "/torrent/{torrent_id}"

    @property
    def supports_totp(self) -> bool:
        # A TL "Alt 2FA Token"-je statikus, nem TOTP — lásd a fájl fejlécét.
        return False

    @property
    def requires_full_download(self) -> bool:
        # Nem a letöltés módja, hanem a H&R szabály miatt True. A tracker
        # dokumentációja: "Every torrent of which you have downloaded at least
        # 10% will appear in your HNR list… Partial downloads never accrue
        # seeding time, so your only option is to seed the data you've
        # downloaded back to a 1:1 ratio."
        #
        # Streamelős módban a StremHU csak a lejátszáshoz kellő darabokat
        # tölti le, ami egy filmnél bőven 10% fölött van — H&R keletkezik, de
        # az időalapú mentesülés részleges letöltésre nem jár. Teljes
        # letöltésnél viszont életbe lép a minimum seed idő, és van is mit
        # felajánlani a peereknek. A felhasználó ezt felülírhatja az indexer
        # fiókjánál (download_full_torrent).
        return True

    @property
    def max_concurrent(self) -> int:
        # A Cardigann YAML `requestDelay: 4.1`-et ír elő (Jackett #13796): a
        # TorrentLeech sűrű kérésre 429-cel, tartós túlterhelésre tiltással
        # válaszol. A bázisosztály alapértéke (5) itt sok.
        return 2

    # -- Hitelesítés ---------------------------------------------------

    def _detect_authentication_error(self, response: httpx.Response) -> AuthError:
        if _looks_like_cloudflare_challenge(response):
            return AuthOtherError(
                message=(
                    f"A(z) {self.name} Cloudflare-ellenőrző oldalt adott vissza. "
                    "Ezt a beépített kliens nem tudja megoldani, mert JS "
                    "futtatás kellene hozzá."
                )
            )

        # FIGYELEM: nem URL alapon ismerjük fel a login oldalt. A TorrentLeech
        # lejárt munkamenetnél nem irányít át — a kért URL-en, 200-zal adja
        # vissza a login oldal HTML-jét. Az ncore.py mintája (response.url.path
        # vizsgálata) itt mindig None-t adna, a session soha nem újulna meg, és
        # a _fetch_torrents HTML-t kapna JSON helyett. A Cardigann YAML is
        # tartalom alapján dönt: `selector: form[name="login-form"]`.
        if not _is_html(response):
            # JSON keresési válasz vagy .torrent letöltés.
            return None

        tree = HTMLParser(response.text)
        if not tree.css_first('form[name="login-form"]'):
            return None

        # Innentől biztos, hogy a login oldalt kaptuk vissza.
        original_url = str(response.request.url)
        if response.history:
            original_url = str(response.history[0].url)

        if self.login_path not in original_url:
            # Nem ide indultunk — a munkamenet járt le. A bázisosztály újra
            # belép, és megismétli az eredeti kérést.
            return AuthSessionError()

        # Ide indultunk, tehát ez a bejelentkezés válasza, és nem sikerült.
        # A YAML login.error selectorai döntik el, hogy 2FA vagy hibás adat.
        otp_node = tree.css_first(".login-container h2")
        if otp_node and "One Time Password" in otp_node.text():
            return AuthCredentialError(
                message=(
                    "A TorrentLeech fiókon be van kapcsolva a 2FA, amit a "
                    "StremHU nem tud kiszolgálni: a tracker statikus Alt 2FA "
                    "Tokent vár, a fiókadatok között viszont csak TOTP kulcs "
                    "tárolható. Kapcsold ki a 2FA-t a TorrentLeech profilodban."
                )
            )

        error_node = tree.css_first("p.text-danger")
        error_text = error_node.text(strip=True) if error_node else None
        if error_text:
            return AuthCredentialError(message=error_text)

        # Konkrét hibaüzenet nélkül is biztos, hogy nem sikerült: a
        # bejelentkezés válaszaként megint a login űrlapot kaptuk. Sikeres
        # belépésnél a TorrentLeech a főoldalra visz.
        return AuthCredentialError()

    async def _login(
        self,
        payload: IndexerDefinitionLoginPayload,
    ) -> httpx.Response:
        # FIGYELEM: nem kérjük le előbb a login oldalt az űrlap mezőiért. Az
        # IndexerClient.request minden válaszon lefuttatja a
        # _detect_authentication_error-t, tehát a login oldal GET-je maga
        # váltana ki "sikertelen bejelentkezés" hibát (login űrlap a válaszban
        # + login útvonal az eredeti URL-ben) még a POST előtt.
        #
        # Nincs is rá szükség: az űrlap csak username és password mezőt
        # tartalmaz, rejtett/CSRF mező nélkül, a PHPSESSID pedig a POST
        # válaszában érkezik. Ha a tracker később CSRF mezőt vezetne be, a
        # lekérést a szülő httpx.AsyncClient.request-tel kell megkerülni, hogy
        # ne fusson rá a detektor.
        return await self._client.post(
            self.login_path,
            data={
                "username": payload.username,
                "password": payload.password,
                # A YAML is mindig küldi; 2FA nélküli fióknál üresen megy.
                "alt2FAToken": payload.totp_code or "",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    # -- Keresés -------------------------------------------------------

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 1

        # A quote() azért kell, mert az imdb_id a kérés útvonalába kerül: a
        # Stremio felől érkező azonosító nem feltétlenül tiszta "tt\d+".
        path = _SEARCH_PATH.format(
            imdb_id=quote(imdb_id, safe=""),
            page=current_page,
        )
        response = await self._client.get(path)

        try:
            data = response.json()
        except Exception as e:
            raise Exception(
                "A TorrentLeech nem JSON-t adott vissza — valószínűleg "
                "megszűnt munkamenet vagy megváltozott végpont."
            ) from e

        rows = data.get("torrentList", [])

        torrents: list[IndexerDefinitionTorrent] = []
        for row in rows:
            torrent_id = row.get("fid")
            filename = row.get("filename")
            row_imdb_id = (row.get("imdbID") or "").strip()

            # IMDB-s keresésnél a szervernek ki kellene töltenie az imdbID-t.
            # Ha mégsem tette, nem lehetünk biztosak benne, hogy a sor tényleg
            # a keresett filmhez tartozik — ilyenkor kihagyjuk. (A _find_all
            # amúgy is imdb_id egyezésre szűr a végén.)
            if not torrent_id or not filename or not row_imdb_id:
                continue

            torrents.append(
                IndexerDefinitionTorrent(
                    torrent_id=str(torrent_id),
                    imdb_id=row_imdb_id,
                    seeders=int(row.get("seeders") or 0),
                    download_url=urljoin(
                        self.url,
                        _DOWNLOAD_PATH.format(
                            torrent_id=torrent_id,
                            filename=quote(filename),
                        ),
                    ),
                    attribute_ids=self._resolve_attributes(
                        str(row.get("categoryID") or ""),
                        _is_freeleech(row),
                    ),
                )
            )

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=self._resolve_next_page(data, len(rows), current_page),
        )

    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent | None:
        details_url = self.details_path.replace("{torrent_id}", torrent_id)
        response = await self._client.get(details_url)

        if response.status_code == 404:
            return None

        tree = HTMLParser(response.text)

        # A szelektor a torrent AZONOSÍTÓJÁRA szűr, nem csak a /download/
        # előtagra: az adatlapon más torrent letöltés linkje is szerepelhet
        # (kapcsolódó release-ek), és rossz fájlt letölteni rosszabb, mint
        # nem találni linket. A `*=` az abszolút href-et is elviseli.
        download_node = tree.css_first(f'a[href*="/download/{torrent_id}/"]')
        download_path = download_node.attributes.get("href") if download_node else None

        if not download_path:
            # Törölt vagy nem létező torrent — a TL ilyenkor is 200-at ad,
            # csak nincs letöltés link a lapon. A hívó None-ként kezeli.
            return None

        imdb_node = tree.css_first('a[href*="imdb.com/title/"]')
        imdb_href = imdb_node.attributes.get("href") if imdb_node else None

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=_parse_imdb_id(imdb_href),
            download_url=urljoin(self.url, download_path),
        )

    # -- Hit & Run -----------------------------------------------------

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        """Összegyűjti azokat a torrenteket, amiket nem szabad letörölni.

        A mérvadó forrás a /profile/{user}/snatchlist, mert abból számolható
        ki, hogy MIBŐL LENNE H&R a törlés pillanatában. A tracker H&R füle erre
        nem alkalmas: az csak a már leállított torrenteket sorolja fel, tehát
        egy aktívan seedelt, de még nem teljesített torrent nincs rajta —
        letörölve viszont azonnal H&R lesz belőle. A H&R fül így csak ráadás.

        Ha a snatchlist nem olvasható, kivételt dobunk, NEM üres listát adunk. A
        hívó (indexers/service.py cleanup_torrent_by_rules) a visszakapott
        listát arra használja, hogy mit NE töröljön — üres lista tehát azt
        jelentené, hogy "nincs kötelezettséged", és a takarítás letörölné a
        H&R-es torrenteket is. Kivételnél viszont az `except Exception` ága
        kihagyja ezt az indexert, és nem töröl semmit.
        """
        if not self._indexer_account_storage:
            return []

        credential = await asyncio.to_thread(
            self._indexer_account_storage.get_credentials, self.id
        )
        if not credential or not credential.username:
            return []

        username = quote(credential.username)

        hit_and_run_ids = await self._fetch_snatchlist_obligations(username)

        # A tracker saját listája csak hozzáad: ami ott már meg van jelölve,
        # azt újra kell seedelni. Ha az oldal nem olvasható, az itt nem hiba —
        # a snatchlistes számolás ezt a halmazt is lefedi.
        for torrent_id in await self._fetch_hit_and_run_page(username):
            if torrent_id not in hit_and_run_ids:
                hit_and_run_ids.append(torrent_id)

        return hit_and_run_ids

    async def _fetch_snatchlist_obligations(self, username: str) -> list[str]:
        """A snatchlistből számolt kötelezettségek.

        Az értékeket a data-sort attribútumokból olvassuk ki, tényleges bájtban
        és másodpercben. A megjelenített arány (Rto oszlop) nem használható:
        FreeLeech torrentnél "inf.", mert a beszámított letöltés nulla, holott
        a szabályzat szerint "every torrent you download from TL including
        freeleech is expected to be seeded back fully".

        Kivételt dob, ha a táblázat nem olvasható vagy hiányosnak látszik.
        """
        path = _SNATCHLIST_PATH.format(username=username)
        response = await self._client.get(path)
        tree = HTMLParser(response.text)

        table = tree.css_first("table#profile-snatchListTable")
        if table is None:
            raise Exception(
                f"A TorrentLeech snatchlist táblázata nem található a {path} "
                "oldalon — elképzelhető, hogy a tracker JS-ből tölti be. A "
                "takarítás biztonságból kimarad."
            )

        if table.css_first("td.dataTables_empty"):
            # Üres snatchlist: a DataTables ilyenkor egyetlen "No data
            # available in table" cellát rajzol. Nincs mit megtartani.
            return []

        rows = table.css("tbody tr")
        if not rows:
            raise Exception(
                "A TorrentLeech snatchlist táblázatában egyetlen sor sincs a "
                f"{path} oldalon, és üresnek sincs jelölve. A takarítás "
                "biztonságból kimarad."
            )

        # Ha a szerver csak egy lapnyi sort küldött (szerver oldali lapozás), a
        # többi torrent kötelezettségéről semmit nem tudunk — az pedig pont a
        # régi, nehezen seedelhető torrenteket érintené.
        entry_total = _parse_entry_total(response.text)
        if entry_total is not None and entry_total > len(rows):
            raise Exception(
                f"A TorrentLeech snatchlistje {entry_total} tételt jelez, de "
                f"csak {len(rows)} sor jött vissza a {path} oldalon. A teljes "
                "lista nélkül a takarítás biztonságból kimarad."
            )

        hit_and_run_ids: list[str] = []
        unknown_size = 0

        for row in rows:
            link = row.css_first('a[href*="/torrent/"]')
            href = link.attributes.get("href") if link else None
            torrent_id = _parse_torrent_id(href)
            if not torrent_id:
                continue

            size = _read_data_sort(row.css_first('td[title="Size"]'))
            downloaded = _read_data_sort(row.css_first('td[title="Downloaded"]'))
            uploaded = _read_data_sort(row.css_first('td[title="Uploaded"]'))
            seeding_time = _read_data_sort(row.css_first('td[title="Seeding Time"]'))

            if downloaded is None or uploaded is None or seeding_time is None:
                # Ismeretlen szerkezet vagy formátum: a biztonságos irány a
                # megjelölés, mert abból legfeljebb egy meg nem törölt torrent
                # lesz, a fordítottjából viszont figyelmeztetés a fiókra.
                hit_and_run_ids.append(torrent_id)
                continue

            if size is None or size <= 0:
                unknown_size += 1

            if _is_hit_and_run(size, downloaded, uploaded, seeding_time):
                hit_and_run_ids.append(torrent_id)

        if unknown_size:
            self.logger.warning(
                "TorrentLeech: %s snatchlist sorból hiányzik a méret, ezeknél "
                "csak az 1:1 arány számít — a seed idő alapú mentesülés "
                "kimaradt. Ellenőrizd a snatchlist oszlopait.",
                unknown_size,
            )

        return hit_and_run_ids

    async def _fetch_hit_and_run_page(self, username: str) -> list[str]:
        """A tracker H&R füle: a MÁR megjelölt (leállított) torrentek.

        Csak kiegészítő forrás, ezért hiba helyett üres listával tér vissza, ha
        a táblázat nem olvasható — a döntést a snatchlistes számolás hozza.
        """
        response = await self._client.get(_HIT_AND_RUN_PATH.format(username=username))
        tree = HTMLParser(response.text)

        table = tree.css_first("#harsTable")
        if table is None:
            return []

        ids: list[str] = []
        for link in table.css('a[href*="/torrent/"]'):
            torrent_id = _parse_torrent_id(link.attributes.get("href"))
            if torrent_id and torrent_id not in ids:
                ids.append(torrent_id)

        return ids

    # -- Segédfüggvények -----------------------------------------------

    def _resolve_next_page(
        self,
        data: dict,
        row_count: int,
        current_page: int,
    ) -> int | None:
        # A TorrentLeech nem küldi vissza az oldalméretet (a fiókprofil
        # "Torrents per page" beállítása szabja meg, alapból 35), ezért a
        # kapott sorok számából dolgozunk. Ez a végén legfeljebb egy fölösleges
        # kérést jelent, viszont mindig terminál: a numFound véges, a szorzat
        # oldalanként nő.
        if row_count <= 0:
            return None

        num_found = int(data.get("numFound") or 0)
        if current_page * row_count >= num_found:
            return None

        return current_page + 1

    def _resolve_attributes(self, category_id: str, is_freeleech: bool) -> list[str]:
        # Csak az kerül ide, ami a kategóriából megállapítható, és amit a
        # release név nem feltétlenül tartalmaz. A többi jellemzőt (forrás,
        # kodek, HDR, hang) a rendszer a tényleges torrent fájlból dolgozza fel.
        #
        # Nyelv: a TorrentLeech angol nyelvű tracker (a Cardigann YAML
        # `language: en-US`), a kategóriák nem jelölnek nyelvet. Ha a release
        # névből más jön ki, a rendszer felülírja ezt az értéket.
        attributes = [MediaAttributeKey.ENG]

        resolution = _CATEGORY_RESOLUTION.get(category_id)
        if resolution:
            attributes.append(resolution)

        # A kedvezmény a release névből soha nem derül ki, csak a trackertől —
        # pont az az eset, amire az attribute_ids való.
        if is_freeleech:
            attributes.append(_FREELEECH_ATTRIBUTE_ID)

        return attributes
