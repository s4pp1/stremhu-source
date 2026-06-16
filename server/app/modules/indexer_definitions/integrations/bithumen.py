from urllib.parse import parse_qs, urljoin, urlparse

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

_CATEGORY_MAP: dict[str, str] = {
    "23": "movie_sd_hun",
    "3": "movie_sd",
    "31": "movie_hd_hun",
    "28": "movie_hd",
    "32": "series_sd_hun",
    "33": "series_sd",
    "35": "series_hd_hun",
    "36": "series_hd",
}


class BithumenIndexerDefinition(BaseIndexerDefinition):
    def __init__(self, credentials_provider) -> None:
        super().__init__(credentials_provider)
        self._cached_user_id: str | None = None

    @property
    def id(self) -> str:
        return "bithumen"

    @property
    def name(self) -> str:
        return "BitHUmen"

    @property
    def requires_full_download(self) -> bool:
        return False

    @property
    def url(self) -> str:
        return "https://bithumen.be"

    @property
    def login_path(self) -> str:
        return "/takelogin.php"

    @property
    def details_path(self) -> str:
        return "/details.php?id={torrent_id}"

    def _detect_authentication_error(
        self, response: httpx.Response
    ) -> AuthenticationErrorEnum | None:
        if response.status_code == 401:
            return AuthenticationErrorEnum.CREDENTIAL_ERROR

        final_path = str(response.url.path)
        if "/login.php" in final_path:
            return AuthenticationErrorEnum.SESSION_ERROR

        return None

    async def _login(
        self,
        credential: IndexerDefinitionLogin,
    ) -> httpx.Response:
        return await self._client.post(
            self.login_path,
            data={
                "username": credential.username,
                "password": credential.password,
                "returnto": "/",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def _fetch_torrents(
        self,
        imdb_id: str,
        page: int | None = None,
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 0
        response = await self._client.get(
            "/browse.php",
            params={
                "genre": "0",
                "search": imdb_id,
                "page": str(current_page),
            },
        )

        html = response.text
        if not isinstance(html, str):
            return IndexerDefinitionFindTorrentsResult(torrents=[])

        tree = HTMLParser(html)
        torrent_rows = tree.css("#torrenttable tbody tr")[1:]
        torrents: list[IndexerDefinitionTorrent] = []

        for row in torrent_rows:
            cols = row.css("td")
            if len(cols) < 9:
                continue

            # Category
            category_node = cols[0].css_first("a")
            category_href = (
                category_node.attributes.get("href") if category_node else None
            )

            if not category_href:
                continue

            category_id = category_href.replace("?cat=", "")

            # Download
            download_node = cols[1].css_first('a[href*="download.php/"]')
            download_path = (
                download_node.attributes.get("href") if download_node else None
            )
            if not download_path:
                continue
            download_url = urljoin(self.url, download_path)

            # IMDB
            imdb_node = cols[1].css_first('a[href*="www.imdb.com/title/"]')
            imdb_url = imdb_node.attributes.get("href") if imdb_node else None

            if not imdb_url:
                continue

            imdb_id_parts = imdb_url.rstrip("/").split("/")
            imdb_id = imdb_id_parts[-1] if len(imdb_id_parts) >= 4 else ""

            # Torrent ID
            torrent_id_node = cols[1].css_first('a[href*="details.php?id="]')
            torrent_id_href = (
                torrent_id_node.attributes.get("href") if torrent_id_node else None
            )
            if not torrent_id_href:
                continue

            torrent_id = torrent_id_href.replace("details.php?id=", "")

            # Seeders
            seeders = cols[7].text(strip=True)

            torrents.append(
                IndexerDefinitionTorrent(
                    torrent_id=torrent_id,
                    download_url=download_url,
                    seeders=int(seeders) if seeders.isdigit() else 0,
                    imdb_id=imdb_id,
                    attribute_ids=[
                        self._resolve_language(category_id),
                        self._resolve_resolution(category_id),
                    ],
                )
            )

        next_link = None
        for b_node in tree.css("#pagertop b"):
            if "Tovább" in b_node.text(strip=True):
                next_link = b_node
                break

        has_next_page = False
        if next_link is not None:
            parent = next_link.parent
            if parent is not None and parent.tag == "a":
                has_next_page = True

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=current_page + 1 if has_next_page else None,
        )

    async def _fetch_torrent(
        self,
        torrent_id: str,
    ) -> IndexerDefinitionTorrent:
        response = await self._client.get(f"/details.php?id={torrent_id}")
        tree = HTMLParser(response.text)

        dl_node = tree.css_first(f'a[href*="download.php/{torrent_id}"]')
        download_path = dl_node.attributes.get("href") if dl_node else None

        imdb_node = tree.css_first('a[href*="www.imdb.com/title/"]')
        imdb_url = imdb_node.attributes.get("href") if imdb_node else ""
        imdb_id_parts = (imdb_url or "").rstrip("/").split("/")
        imdb_id = imdb_id_parts[-1] if len(imdb_id_parts) >= 4 else None

        if not download_path:
            raise Exception("A letöltési link nem található!")

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=urljoin(self.url, download_path),
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        user_id = await self._get_user_id()
        response = await self._client.get(
            "/hitnrun.php", params={"id": user_id, "hnr": "1"}
        )
        tree = HTMLParser(response.text)

        hrefs = [
            node.attributes.get("href")
            for node in tree.css('td a[href*="/details.php?id="]')
        ]

        ids = []
        for href in hrefs:
            if not href:
                continue

            full_url = urljoin(self.url, href)
            torrent_id = parse_qs(urlparse(full_url).query).get("id", [None])[0]
            if torrent_id:
                ids.append(torrent_id)

        return ids

    async def _get_user_id(self) -> str:
        if self._cached_user_id:
            return self._cached_user_id

        response = await self._client.get("/index.php")
        tree = HTMLParser(response.text)

        user_node = tree.css_first('#status a[href*="/userdetails.php?"]')
        user_detail_path = user_node.attributes.get("href") if user_node else None
        if not user_detail_path:
            raise Exception("A felhasználói adatlap elérési útja nem található!")

        user_detail_url = urljoin(self.url, user_detail_path)
        user_id = parse_qs(urlparse(user_detail_url).query).get("id", [None])[0]

        if not user_id:
            raise Exception("A felhasználói azonosító nem található!")

        self._cached_user_id = user_id
        return user_id

    def _resolve_resolution(self, category: str) -> str:
        cat_type = _CATEGORY_MAP.get(category, "none")
        if "hd" in cat_type:
            return MediaAttributeKey.R720P
        return MediaAttributeKey.R480P

    def _resolve_language(self, category: str) -> str:
        cat_type = _CATEGORY_MAP.get(category, "none")
        if "hun" in cat_type:
            return MediaAttributeKey.HUN
        return MediaAttributeKey.ENG
