import re
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

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


# ─── Kategória → attribute_id mapping ────────────────────────────────────────
# Kulcs: img src fájlnév stem (/img/cats/TV-Pack.png → "TV-Pack")
# vagy img alt szöveg ("TV/Packs") — mindkettőt kezeljük.
_CATEGORY_MAP: dict[str, list[str]] = {
    # ── src stem alapú kulcsok ──────────────────────────────────────────────
    "4K":                      [MediaAttributeKey.R2160P],
    "Movies-BluRayBDRip":      [MediaAttributeKey.R1080P, MediaAttributeKey.BLURAY],
    "Movie-BD-R":              [MediaAttributeKey.R1080P, MediaAttributeKey.BLURAY],
    "Movie-BD-Rip":            [MediaAttributeKey.R1080P, MediaAttributeKey.BDRIP],
    "Movie-Web-DL":            [MediaAttributeKey.R1080P, MediaAttributeKey.WEB_DL],
    "Movie-x265":              [MediaAttributeKey.R1080P, MediaAttributeKey.X265],
    "Movie-480p":              [MediaAttributeKey.R480P],
    "Movie-DVD-R":             [MediaAttributeKey.R480P, MediaAttributeKey.DVD_RIP],
    "Movie-Xvid":              [MediaAttributeKey.R480P],
    "Movie-MP4":               [MediaAttributeKey.R480P],
    "Movie-Cam":               [MediaAttributeKey.CAM],
    "Movie-3D":                [MediaAttributeKey.R1080P],
    "Movie-Kids":              [MediaAttributeKey.R480P],
    "Movie-Non-English":       [],
    "Movie-Packs":             [],
    "Movie":                   [],
    "Movies":                  [],
    "TV-Web-DL":               [MediaAttributeKey.R1080P, MediaAttributeKey.WEB_DL],
    "TV-x265":                 [MediaAttributeKey.R1080P, MediaAttributeKey.X265],
    "TV-x264":                 [MediaAttributeKey.R720P, MediaAttributeKey.X264],
    "TV-BD":                   [MediaAttributeKey.R1080P, MediaAttributeKey.BLURAY],
    "TV-480p":                 [MediaAttributeKey.R480P],
    "TV-SD-x264":              [MediaAttributeKey.R480P],
    "TV-DVD-R":                [MediaAttributeKey.R480P, MediaAttributeKey.DVD_RIP],
    "TV-DVD-Rip":              [MediaAttributeKey.R480P, MediaAttributeKey.DVD_RIP],
    "TV-Xvid":                 [MediaAttributeKey.R480P],
    "TV-Mobile":               [MediaAttributeKey.R480P],
    "TV-Non-English":          [],
    "TV-Pack":                 [],   # TV/Packs — src: TV-Pack.png
    "TV-Packs":                [],
    "TV-Packs-Non-English":    [],
    "TV":                      [],
    "Documentaries":           [],
    "Sports":                  [],
    # ── alt szöveg alapú kulcsok (cím-keresés esetén az alt ki van töltve) ──
    "Movie/4K":                [MediaAttributeKey.R2160P],
    "Movie/HD/Bluray":         [MediaAttributeKey.R1080P, MediaAttributeKey.BLURAY],
    "Movie/BD-R":              [MediaAttributeKey.R1080P, MediaAttributeKey.BLURAY],
    "Movie/BD-Rip":            [MediaAttributeKey.R1080P, MediaAttributeKey.BDRIP],
    "Movie/Web-DL":            [MediaAttributeKey.R1080P, MediaAttributeKey.WEB_DL],
    "Movie/x265":              [MediaAttributeKey.R1080P, MediaAttributeKey.X265],
    "Movie/480p":              [MediaAttributeKey.R480P],
    "Movie/DVD-R":             [MediaAttributeKey.R480P, MediaAttributeKey.DVD_RIP],
    "Movie/Xvid":              [MediaAttributeKey.R480P],
    "Movie/MP4":               [MediaAttributeKey.R480P],
    "Movie/Cam":               [MediaAttributeKey.CAM],
    "Movie/3D":                [MediaAttributeKey.R1080P],
    "Movie/Kids":              [MediaAttributeKey.R480P],
    "Movie/Non-English":       [],
    "Movie/Packs":             [],
    "Movies":                  [],
    "TV/Web-DL":               [MediaAttributeKey.R1080P, MediaAttributeKey.WEB_DL],
    "TV/x265":                 [MediaAttributeKey.R1080P, MediaAttributeKey.X265],
    "TV/x264":                 [MediaAttributeKey.R720P, MediaAttributeKey.X264],
    "TV/BD":                   [MediaAttributeKey.R1080P, MediaAttributeKey.BLURAY],
    "TV/480p":                 [MediaAttributeKey.R480P],
    "TV/SD/x264":              [MediaAttributeKey.R480P],
    "TV/DVD-R":                [MediaAttributeKey.R480P, MediaAttributeKey.DVD_RIP],
    "TV/DVD-Rip":              [MediaAttributeKey.R480P, MediaAttributeKey.DVD_RIP],
    "TV/Xvid":                 [MediaAttributeKey.R480P],
    "TV/Mobile":               [MediaAttributeKey.R480P],
    "TV/Non-English":          [],
    "TV/Packs":                [],
    "TV/Packs/Non-English":    [],
    "TV":                      [],
    "Documentaries":           [],
    "Sports":                  [],
}


# TV kategória checkbox ID-k (a movie listával együtt mind be van jelölve)
_TV_CATEGORY_IDS = [
    "73", "26", "55", "78", "23", "24", "25", "66", "82",
    "65", "83", "79", "22", "5", "99", "4",
]

_ALL_CATEGORY_IDS = [
    "72", "87", "77", "101", "89", "90", "96", "6",
    "48", "54", "62", "38", "68", "20", "100", "7",
    "73", "26", "55", "78", "23", "24", "25", "66", "82",
    "65", "83", "79", "22", "5", "99", "4",
]


def _category_key(img_node) -> str:
    """
    Kategória kulcs kinyerése img node-ból.
    Előnyt ad az alt attribútumnak (pl. "TV/Packs"), fallback az src stemre
    (pl. "TV-Pack" a TV-Pack.png-ből). Mindkettő szerepel a _CATEGORY_MAP-ban.
    """
    alt = (img_node.attributes.get("alt") or "").strip()
    if alt:
        return alt
    src = img_node.attributes.get("src", "")
    basename = src.rsplit("/", 1)[-1]
    return basename.rsplit(".", 1)[0]


def _attribute_ids_from_category_and_name(
    category: str, name: str
) -> list[str]:
    base_attrs = list(_CATEGORY_MAP.get(category, []))
    name_lower = name.lower()

    if not any(
        a in base_attrs
        for a in [
            MediaAttributeKey.R2160P, MediaAttributeKey.R1080P,
            MediaAttributeKey.R720P, MediaAttributeKey.R576P,
            MediaAttributeKey.R480P,
        ]
    ):
        if "2160" in name_lower or "4k" in name_lower or "uhd" in name_lower:
            base_attrs.append(MediaAttributeKey.R2160P)
        elif "1080" in name_lower or "fhd" in name_lower:
            base_attrs.append(MediaAttributeKey.R1080P)
        elif "720" in name_lower:
            base_attrs.append(MediaAttributeKey.R720P)
        elif "480" in name_lower or "sd" in name_lower:
            base_attrs.append(MediaAttributeKey.R480P)

    if MediaAttributeKey.X265 not in base_attrs:
        if "x265" in name_lower or "hevc" in name_lower or "h265" in name_lower or "h 265" in name_lower:
            base_attrs.append(MediaAttributeKey.X265)

    if MediaAttributeKey.X264 not in base_attrs:
        if "x264" in name_lower or "h264" in name_lower or "h 264" in name_lower or "avc" in name_lower:
            base_attrs.append(MediaAttributeKey.X264)

    if MediaAttributeKey.WEB_DL not in base_attrs:
        if "web-dl" in name_lower or "webdl" in name_lower:
            base_attrs.append(MediaAttributeKey.WEB_DL)

    if MediaAttributeKey.WEB_RIP not in base_attrs:
        if "webrip" in name_lower or "web rip" in name_lower:
            base_attrs.append(MediaAttributeKey.WEB_RIP)

    return base_attrs


def _parse_torrent_rows(
    tree, imdb_id: str
) -> list:
    """HTML tree-ből kinyeri a torrent listát."""
    torrent_table = tree.css_first("table#torrents")
    if not torrent_table:
        return []

    rows = torrent_table.css("tbody tr")
    torrents = []
    seen_ids: set[str] = set()

    for row in rows:
        # ── Kategória ──
        cat_img = row.css_first("td.i img")
        if not cat_img:
            continue
        category = _category_key(cat_img)

        if category not in _CATEGORY_MAP:
            continue

        # ── Torrent cím és ID ──
        title_node = row.css_first('td.al a[href^="/t/"]')
        if not title_node:
            continue

        torrent_title = title_node.text(strip=True)
        detail_href = title_node.attributes.get("href", "")
        torrent_id_match = re.search(r"/t/(\d+)", detail_href)
        if not torrent_id_match:
            continue
        torrent_id = torrent_id_match.group(1)

        if torrent_id in seen_ids:
            continue
        seen_ids.add(torrent_id)

        # ── Download URL ──
        dl_node = row.css_first('a[href*="download.php/"]')
        if not dl_node:
            continue
        download_path = dl_node.attributes.get("href", "")
        if download_path.startswith("http"):
            download_url = download_path
        else:
            download_url = urljoin("https://iptorrents.com", "/" + download_path.lstrip("/"))

        # ── Seeders: utolsó előtti <td> ──
        tds = row.css("td")
        if len(tds) < 2:
            continue
        seeders_text = tds[-2].text(strip=True)
        seeders = int(seeders_text) if seeders_text.isdigit() else 0

        attribute_ids = _attribute_ids_from_category_and_name(category, torrent_title)

        torrents.append(
            IndexerDefinitionTorrent(
                torrent_id=torrent_id,
                imdb_id=imdb_id,
                seeders=seeders,
                download_url=download_url,
                attribute_ids=attribute_ids,
            )
        )

    return torrents


class IptorrentsIndexerDefinition(BaseIndexerDefinition):

    @property
    def id(self) -> str:
        return "iptorrents"

    @property
    def name(self) -> str:
        return "IPTorrents"

    @property
    def requires_full_download(self) -> bool:
        return False

    @property
    def url(self) -> str:
        return "https://iptorrents.com"

    @property
    def login_path(self) -> str:
        return "/do-login.php"

    @property
    def details_path(self) -> str:
        return "/t/{torrent_id}"

    def _detect_authentication_error(
        self, response: httpx.Response
    ) -> AuthenticationErrorEnum | None:
        final_path = str(response.url.path)
        original_url = str(response.request.url)
        if response.history:
            original_url = str(response.history[0].url)

        ended_up_at_login = (
            "/do-login.php" in final_path
            or "/login.php" in final_path
        )
        if ended_up_at_login:
            if self.login_path in original_url or "/login.php" in original_url:
                return AuthenticationErrorEnum.CREDENTIAL_ERROR
            return AuthenticationErrorEnum.SESSION_ERROR

        return None

    async def _login(self, credential: IndexerDefinitionLogin) -> httpx.Response:
        return await self._client.post(
            self.login_path,
            data={
                "username": credential.username,
                "password": credential.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def _build_params(self, query: str, qf: str, page: int) -> dict[str, str]:
        params: dict[str, str] = {
            "q": query,
            "qf": qf,
            "o": "seeders",
        }
        if page > 1:
            params["p"] = str(page)
        for cat_id in _ALL_CATEGORY_IDS:
            params[cat_id] = ""
        return params

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 1

        print(f"[IPT] searching imdb={imdb_id} page={current_page}")

        # 1. kísérlet: keresés az összes mezőben (leírásban is) az IMDb ID-ra.
        # Ez filmeknél jól működik, sorozatoknál kevésbé.
        params_all = self._build_params(imdb_id, "all", current_page)
        response = await self._client.get("/t", params=params_all)
        tree = HTMLParser(response.text)
        torrents = _parse_torrent_rows(tree, imdb_id)
        print(f"[IPT] first search returned {len(torrents)} torrents")

        # 2. kísérlet: ha nincs találat, próbálj cím+tag alapú keresést
        # az IMDb ID rövid szám részével (pl. "tt0944947" → "0944947").
        # Az IPT tag mezőjébe néha bekerül az IMDb ID, de a tt-prefix nélkül.
        if not torrents:
            numeric_id = imdb_id.lstrip("t")  # "tt0944947" → "0944947"
            params_ti = self._build_params(numeric_id, "all", current_page)
            response2 = await self._client.get("/t", params=params_ti)
            tree2 = HTMLParser(response2.text)
            torrents = _parse_torrent_rows(tree2, imdb_id)

        # Pagination ellenőrzés az utolsó lekért tree-ből
        active_tree = tree2 if not _parse_torrent_rows(tree, imdb_id) else tree
        has_next = any(
            f";p={current_page + 1}" in (node.attributes.get("href") or "")
            or f"p={current_page + 1}" in (node.attributes.get("href") or "")
            for node in active_tree.css("a[href]")
        )

        # Rendezés seederek szerint és csak a legjobb 20 találat megtartása
        torrents.sort(key=lambda t: t.seeders, reverse=True)
        torrents = torrents[:20]

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=current_page + 1 if has_next else None,
        )

    async def _fetch_torrent(
        self, torrent_id: str
    ) -> IndexerDefinitionTorrent | None:
        detail_url = self.details_path.replace("{torrent_id}", torrent_id)
        response = await self._client.get(detail_url)
        tree = HTMLParser(response.text)

        title_node = tree.css_first("title")
        if title_node and "not found" in title_node.text().lower():
            return None

        dl_node = tree.css_first(f'a[href*="download.php/{torrent_id}/"]')
        if not dl_node:
            dl_node = tree.css_first('a[href*="download.php/"]')
        download_path = dl_node.attributes.get("href") if dl_node else None

        if not download_path:
            raise Exception("A letöltési link nem található!")

        imdb_node = tree.css_first('a[href*="imdb.com/title/"]')
        imdb_href = imdb_node.attributes.get("href") if imdb_node else None
        imdb_id = self._resolve_imdb_id(imdb_href)

        if download_path.startswith("http"):
            full_download_url = download_path
        else:
            full_download_url = urljoin(self.url, "/" + download_path.lstrip("/"))

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=full_download_url,
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        """
        Lekéri a H&R kötelezettség alatt álló torrentek azonosítóit.

        Az IPT /seeding_required.php oldala pontosan azokat a torrenteket
        listázza, amelyek még nem teljesítették az 1:1 arányt VAGY a 336 óra
        seedelési időt. A lista sorai <tr id="lineXXXXX"> formátumban tartalmazzák
        a torrent ID-t, így egyszerűen kinyerhető.

        Ha az oldal nem érhető el vagy nem tartalmaz listát, kivételt dobunk
        (nem üres listát), hogy a takarítás biztonságból kimaradjon — jobb
        nem törölni, mint véletlenül H&R warningot kockáztatni.
        """
        response = await self._client.get("/seeding_required.php")
        tree = HTMLParser(response.text)

        # Az oldal csak akkor tartalmaz táblát, ha van H&R kötelezettség.
        # Ha nincs egyetlen <tr id="lineXXX"> sem, az oldal üres → nincs H&R.
        rows = tree.css("tr[id^='line']")

        hit_and_run_ids: list[str] = []
        for row in rows:
            row_id = row.attributes.get("id", "")
            # "line5005189" → "5005189"
            torrent_id = row_id.removeprefix("line")
            if torrent_id.isdigit():
                hit_and_run_ids.append(torrent_id)

        return hit_and_run_ids

    def _resolve_imdb_id(self, imdb_url: str | None) -> str | None:
        if not imdb_url:
            return None
        match = re.search(r"/title/(tt\d+)", imdb_url)
        return match.group(1) if match else None
