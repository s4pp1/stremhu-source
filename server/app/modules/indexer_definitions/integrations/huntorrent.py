"""
@author ntamas94 <https://github.com/ntamas94>
@website https://huntorrent.org
"""

from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser, Node

from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.enums import AuthenticationErrorEnum
from app.modules.indexer_definitions.schemas.internal import (
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionLogin,
    IndexerDefinitionTorrent,
)
from app.modules.media_attributes.constants import MediaAttributeKey

_LOGIN_API_PATH = "/login/api/login"
_BROWSE_PATH = "/browse/"

# A kategória-ikon alt szövegéből (pl. "HD/Magyar") a nyelvet és a felbontást
# vesszük át. Ezek fallbackként működnek: ha a parse_torrent_name() kiszedi őket
# a release névből, akkor a rendszer az itteni értéket eldobja. Ezért adunk a HD
# kategóriákra 720p-t is, hiába jelenthet 1080p-t: van olyan torrent, aminek a
# nevében sehol nem szerepel a felbontás.
_CATEGORY_ATTRIBUTES: dict[str, list[str]] = {
    "hd/magyar": [MediaAttributeKey.HUN, MediaAttributeKey.R720P],
    "hd/külföldi": [MediaAttributeKey.ENG, MediaAttributeKey.R720P],
    "xvid/magyar": [MediaAttributeKey.HUN, MediaAttributeKey.R480P],
    "xvid/külföldi": [MediaAttributeKey.ENG, MediaAttributeKey.R480P],
    "dvdr/magyar": [MediaAttributeKey.HUN, MediaAttributeKey.R480P],
    "dvdr/külföldi": [MediaAttributeKey.ENG, MediaAttributeKey.R480P],
    "cam/magyar": [MediaAttributeKey.HUN, MediaAttributeKey.CAM],
    "cam/külföldi": [MediaAttributeKey.ENG, MediaAttributeKey.CAM],
    "sorozat/hd/magyar": [MediaAttributeKey.HUN, MediaAttributeKey.R720P],
    "sorozat/hd/külföldi": [MediaAttributeKey.ENG, MediaAttributeKey.R720P],
    "sorozat/magyar": [MediaAttributeKey.HUN, MediaAttributeKey.R480P],
    "sorozat/külföldi": [MediaAttributeKey.ENG, MediaAttributeKey.R480P],
}


def _get_attribute(node: Node | None, name: str) -> str | None:
    if node is None:
        return None

    return node.attributes.get(name)


def _parse_imdb_id(href: str | None) -> str | None:
    if not href:
        return None

    segments = [segment for segment in urlparse(href).path.split("/") if segment]
    if segments and segments[-1].startswith("tt"):
        return segments[-1]

    return None


def _parse_torrent_id(href: str | None) -> str | None:
    if not href:
        return None

    parsed = urlparse(href)

    query_id = parse_qs(parsed.query).get("id", [None])[0]
    if query_id and query_id.isdigit():
        return query_id

    segments = [segment for segment in parsed.path.split("/") if segment]
    if segments and segments[-1].isdigit():
        return segments[-1]

    return None


def _parse_poster_id(poster_id: str | None) -> str | None:
    # A sor azonosítója az id attribútumban van, "poster-" előtaggal:
    # id="poster-53357".
    if not poster_id:
        return None

    prefix, _, torrent_id = poster_id.partition("poster-")
    if prefix or not torrent_id.isdigit():
        return None

    return torrent_id


def _parse_seeders(item: Node) -> int:
    # A seed érték a "Seed" feliratú .poster-stat blokkban van; az értéket egy
    # <a> csomagolja, ezért csak a számjegyeket olvassuk ki.
    for stat in item.css(".poster-stat"):
        label = stat.css_first(".poster-stat-label")
        if label is None or "seed" not in label.text().lower():
            continue

        value = stat.css_first(".poster-stat-value")
        digits = "".join(ch for ch in value.text() if ch.isdigit()) if value else ""
        return int(digits) if digits else 0

    return 0


class HunTorrentIndexerDefinition(BaseIndexerDefinition):
    @property
    def id(self) -> str:
        return "huntorrent"

    @property
    def name(self) -> str:
        return "HunTorrent"

    @property
    def url(self) -> str:
        return "https://huntorrent.org"

    @property
    def login_path(self) -> str:
        # A /login.php ide irányít át, és a munkamenet lejárta is erre épül.
        return "/login/"

    @property
    def details_path(self) -> str:
        return "/torrent/huntorrent/{torrent_id}"

    @property
    def requires_full_download(self) -> bool:
        return True

    @property
    def max_concurrent(self) -> int:
        return 3

    def _detect_authentication_error(
        self, response: httpx.Response
    ) -> AuthenticationErrorEnum | None:
        request_path = urlparse(str(response.request.url)).path

        # A bejelentkezés JSON-nal válaszol: hibás adatoknál {"wrong": true, ...}
        # és HTTP 400, sikernél a "text" mezőben jön az átirányítás célja.
        if request_path.startswith(_LOGIN_API_PATH):
            try:
                if response.json().get("wrong") is True:
                    return AuthenticationErrorEnum.CREDENTIAL_ERROR
            except ValueError:
                return AuthenticationErrorEnum.CREDENTIAL_ERROR

            return None

        # A CSRF tokent mi magunk kérjük le a /login/ oldalról, ez nem munkamenet
        # hiba. Enélkül a kliens újra-bejelentkezést indítana, ami ismét ide
        # vezetne: végtelen bejelentkezési hurok.
        if request_path.startswith(self.login_path):
            return None

        # Bármely más kérés a /login/-ra fut ki: lejárt a munkamenet.
        if urlparse(str(response.url)).path.startswith("/login"):
            return AuthenticationErrorEnum.SESSION_ERROR

        # Az oldal nem mindig irányít át: előfordulhat, hogy a kért útvonalon
        # szolgálja ki a bejelentkező űrlapot. Ilyenkor az URL alapján semmi nem
        # látszik, a keresés viszont némán nulla találatot adna vissza, és el
        # sem indulna az újra-bejelentkezés. Ezért a törzsben is megnézzük az
        # űrlapot. A loginForm azonosító csak a bejelentkező oldalon fordul elő,
        # belépett állapotú oldalakon nem, így nem ad hamis riasztást.
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("text/html") and "loginForm" in response.text:
            return AuthenticationErrorEnum.SESSION_ERROR

        return None

    async def _login(
        self,
        credential: IndexerDefinitionLogin,
    ) -> httpx.Response:
        # Az oldal reCAPTCHA-t kapcsol be, ha a szerver oldali loginattempts
        # számláló nagyobb nullánál, azaz volt már sikertelen próbálkozás.
        # Olyankor egyszer kézzel, böngészőből kell belépni.
        form = await self._client.get(self.login_path)
        form_tree = HTMLParser(form.text)
        csrf_node = form_tree.css_first('input[name="csrf_token"]')

        # A reCAPTCHA-t az automata bejelentkezés nem tudja megoldani (nem megy
        # g-recaptcha-response a kérésben), ezért a belépés biztosan elbukik.
        # Ezt külön jelezzük: a sima "sikertelen bejelentkezés" alapján nagyon
        # nehéz kideríteni, hogy valójában captcha-zár van.
        if form_tree.css_first(".g-recaptcha, [data-sitekey]") is not None:
            self.logger.warning(
                "%s: a bejelentkező oldal reCAPTCHA-t kér, az automata "
                "bejelentkezés így nem fog sikerülni. Lépj be egyszer kézzel, "
                "böngészőből, ugyanazzal a fiókkal és ugyanarról az IP-ről.",
                self.name,
            )

        response = await self._client.post(
            _LOGIN_API_PATH,
            data={
                "action": "login",
                "return_url": "/index.php",
                "csrf_token": _get_attribute(csrf_node, "value") or "",
                "username": credential.username,
                "password": credential.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # A bejelentkezés eredményének naplózása. A hibát warning szinten írjuk,
        # mert prod módban csak az látszik; a jelszó soha nem kerül logba.
        try:
            wrong = response.json().get("wrong") is True
        except ValueError:
            wrong = True

        if wrong:
            self.logger.warning(
                "%s: sikertelen bejelentkezés (felhasználó: %s) – az oldal "
                "elutasította a hitelesítő adatokat.",
                self.name,
                credential.username,
            )
        else:
            self.logger.info(
                "%s: sikeres bejelentkezés (felhasználó: %s).",
                self.name,
                credential.username,
            )

        return response

    async def _fetch_torrents(
        self,
        imdb_id: str,
        page: int | None = None,
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 1
        response = await self._client.get(
            _BROWSE_PATH,
            params={
                "xyz": "yes",
                # A kereső "Név, vagy iMDB link alapján" keres. A csupasz tt
                # azonosító része a tárolt IMDB linknek, így ez a biztos forma.
                "search": imdb_id,
                "incldead": "1",
                "sort": "7",
                "type": "desc",
                "page": str(current_page),
            },
        )

        tree = HTMLParser(response.text)

        # A böngésző oldal fiókfüggő nézetet ad: van táblázatos (tr.torrent-row)
        # és poszter-rács (div.poster-item) elrendezés is. Mindkettőt kezeljük,
        # így a keresés akkor is működik, ha a fiók bármelyik nézeten van.
        torrents = self._parse_table_rows(tree) or self._parse_poster_items(tree)

        # Ha a lapon vannak torrentek, de egyik parser sem illeszkedett, akkor
        # az oldal markupja megváltozott. Enélkül a keresés némán nulla
        # találatot adna: se hiba, se log, csak "nincs találat" — ezt nagyon
        # nehéz kideríteni.
        if not torrents and "/download/" in response.text:
            self.logger.warning(
                "%s: a böngésző oldal torrenteket tartalmaz, de egyik parser "
                "sem illeszkedett – valószínűleg megváltozott a markup.",
                self.name,
            )

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=self._resolve_next_page(tree, current_page),
        )

    def _parse_table_rows(self, tree: HTMLParser) -> list[IndexerDefinitionTorrent]:
        # Táblázatos nézet: soronként egy tr.torrent-row, az adatok data-*
        # attribútumokban (data-torrent-id, data-seeders), a kategória a
        # .torrent-category img alt szövegében.
        torrents: list[IndexerDefinitionTorrent] = []

        for row in tree.css("tr.torrent-row"):
            torrent_id = row.attributes.get("data-torrent-id")
            if not torrent_id:
                continue

            # A letöltési link már tartalmazza a felhasználó torrent_pass-át.
            download_node = row.css_first('.torrent-meta a[href*="/download/"]')
            download_path = _get_attribute(download_node, "href")
            if not download_path:
                continue

            category_node = row.css_first(".torrent-category img")
            category = (_get_attribute(category_node, "alt") or "").strip().lower()

            imdb_node = row.css_first('a[href*="imdb.com/title/"]')
            row_imdb_id = _parse_imdb_id(_get_attribute(imdb_node, "href"))
            seeders = row.attributes.get("data-seeders") or ""

            torrents.append(
                IndexerDefinitionTorrent(
                    torrent_id=torrent_id,
                    download_url=urljoin(self.url, download_path),
                    imdb_id=row_imdb_id,
                    seeders=int(seeders) if seeders.isdigit() else 0,
                    attribute_ids=_CATEGORY_ATTRIBUTES.get(category, []),
                )
            )

        return torrents

    def _parse_poster_items(self, tree: HTMLParser) -> list[IndexerDefinitionTorrent]:
        # Poszter-rács nézet: minden torrent egy div.poster-item, az azonosító
        # az id="poster-<id>" attribútumban, a kategória a .poster-category span
        # szövegében, a seed a "Seed" feliratú .poster-stat blokkban.
        torrents: list[IndexerDefinitionTorrent] = []

        for item in tree.css("div.poster-item"):
            torrent_id = _parse_poster_id(item.attributes.get("id"))
            if not torrent_id:
                continue

            # A letöltési link már tartalmazza a felhasználó torrent_pass-át.
            download_node = item.css_first('.poster-actions a[href*="/download/"]')
            download_path = _get_attribute(download_node, "href")
            if not download_path:
                continue

            category_node = item.css_first(".poster-category span")
            category = (category_node.text() if category_node else "").strip().lower()

            imdb_node = item.css_first('a[href*="imdb.com/title/"]')
            row_imdb_id = _parse_imdb_id(_get_attribute(imdb_node, "href"))

            torrents.append(
                IndexerDefinitionTorrent(
                    torrent_id=torrent_id,
                    download_url=urljoin(self.url, download_path),
                    imdb_id=row_imdb_id,
                    seeders=_parse_seeders(item),
                    attribute_ids=_CATEGORY_ATTRIBUTES.get(category, []),
                )
            )

        return torrents

    async def _fetch_torrent(
        self,
        torrent_id: str,
    ) -> IndexerDefinitionTorrent | None:
        response = await self._client.get(
            self.details_path.format(torrent_id=torrent_id)
        )
        tree = HTMLParser(response.text)

        download_node = tree.css_first('a[href*="/download/"]')
        download_path = _get_attribute(download_node, "href")
        if not download_path:
            # Törölt vagy nem létező torrent.
            return None

        imdb_node = tree.css_first('a[href*="imdb.com/title/"]')

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            download_url=urljoin(self.url, download_path),
            imdb_id=_parse_imdb_id(_get_attribute(imdb_node, "href")),
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        # Az id paraméter nélkül a belépett felhasználó saját listája jön.
        response = await self._client.get("/seedkotelezettseg.php")
        tree = HTMLParser(response.text)

        # A "/" a details.php előtt fontos: enélkül a fejléc
        # userdetails.php?id=<uid> linkje is illeszkedne, és a felhasználó
        # azonosítója kerülne a listába torrent azonosítóként.
        selector = 'a[href*="/torrent/"], a[href*="/details.php?id="]'

        ids: list[str] = []
        for link in tree.css(selector):
            torrent_id = _parse_torrent_id(link.attributes.get("href"))
            if torrent_id and torrent_id not in ids:
                ids.append(torrent_id)

        return ids

    def _resolve_next_page(self, tree: HTMLParser, current_page: int) -> int | None:
        for link in tree.css("a.ht-pager-btn"):
            href = link.attributes.get("href")
            if not href:
                continue

            page = parse_qs(urlparse(href).query).get("page", [None])[0]
            if page and page.isdigit() and int(page) > current_page:
                return current_page + 1

        return None
