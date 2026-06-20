"""
@author Sappi <https://github.com/s4pp1/stremhu-source>
@website https://stremhu.hu
"""

from urllib.parse import parse_qs, urlparse

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
    "41": "movie_sd_hun",
    "42": "movie_sd",
    "27": "movie_hd_hun",
    "25": "movie_hd",
    "44": "movie_uhd_hun",
    "45": "movie_uhd",
    "8": "series_sd_hun",
    "7": "series_sd",
    "40": "series_hd_hun",
    "39": "series_hd",
    "47": "series_uhd_hun",
    "46": "series_uhd",
}


class InsaneIndexerDefinition(BaseIndexerDefinition):
    @property
    def id(self) -> str:
        return "insane"

    @property
    def name(self) -> str:
        return "iNSANE"

    @property
    def requires_full_download(self) -> bool:
        return False

    @property
    def url(self) -> str:
        return "https://newinsane.info"

    @property
    def login_path(self) -> str:
        return "/login.php"

    @property
    def details_path(self) -> str:
        return "/details.php?id={torrent_id}"

    def _detect_authentication_error(
        self,
        response: httpx.Response,
    ) -> AuthenticationErrorEnum | None:
        final_path = str(response.url.path)
        original_url = str(response.request.url)
        if response.history:
            original_url = str(response.history[0].url)

        ended_up_at_login = self.login_path in final_path

        if ended_up_at_login:
            if self.login_path in original_url:
                return AuthenticationErrorEnum.CREDENTIAL_ERROR
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
                "search": imdb_id,
                "page": str(current_page),
                "torart": "tor",
                "incldead": "1",
                "sort": "7",
                "type": "desc",
            },
        )

        html = response.text
        if not isinstance(html, str):
            return IndexerDefinitionFindTorrentsResult(torrents=[])

        tree = HTMLParser(html)
        torrent_rows = tree.css(".torrenttable tbody .torrentrow")
        torrents: list[IndexerDefinitionTorrent] = []

        for row in torrent_rows:
            # Category
            category_node = row.css_first('a[href*="browse.php?cat="]')
            category_href = (
                category_node.attributes.get("href") if category_node else None
            )
            category_id = (
                category_href.replace("browse.php?cat=", "") if category_href else None
            )

            if not category_id:
                continue

            # Torrent ID
            torrent_id_node = row.css_first(".torrentmain a[href*='details.php?id=']")
            torrent_id_href = (
                torrent_id_node.attributes.get("href") if torrent_id_node else None
            )
            torrent_id = (
                torrent_id_href.replace("details.php?id=", "")
                if torrent_id_href
                else None
            )

            if not torrent_id:
                continue

            # Download
            download_node = row.css_first(
                f'.downloadlink a[href*="{self.url}/download.php/{torrent_id}/"]'
            )
            download_url = (
                download_node.attributes.get("href") if download_node else None
            )

            if not download_url:
                continue

            # IMDB
            imdb_node = row.css_first('a[href*="www.imdb.com/title/"]')
            imdb_url = imdb_node.attributes.get("href") if imdb_node else None

            if not imdb_url:
                continue

            imdb_parts = imdb_url.rstrip("/").split("/")
            imdb_id = imdb_parts[-1] if len(imdb_parts) >= 4 else ""

            # Seeders
            seed_node = row.css_first(".data .leftborder")
            seeders_text = seed_node.text(strip=True) if seed_node else ""

            torrents.append(
                IndexerDefinitionTorrent(
                    torrent_id=torrent_id,
                    download_url=download_url,
                    seeders=int(seeders_text) if seeders_text.isdigit() else 0,
                    imdb_id=imdb_id,
                    attribute_ids=[
                        self._resolve_language(category_id),
                        self._resolve_resolution(category_id),
                    ],
                )
            )

        has_next_page = len(tree.css(".top.pager.center a.pagernextlink")) > 0

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=current_page + 1 if has_next_page else None,
        )

    async def _fetch_torrent(
        self,
        torrent_id: str,
    ) -> IndexerDefinitionTorrent | None:
        response = await self._client.get(f"/details.php?id={torrent_id}")
        tree = HTMLParser(response.text)

        html_node = tree.css_first("html")
        if html_node and "Torrent nem létezik" in html_node.text():
            return None

        download_node = tree.css_first(
            f'a[href*="{self.url}/download.php/{torrent_id}/"]'
        )
        download_url = download_node.attributes.get("href") if download_node else None

        imdb_node = tree.css_first('a[href*="www.imdb.com/title/"]')
        imdb_url = imdb_node.attributes.get("href") if imdb_node else None
        imdb_parts = imdb_url.rstrip("/").split("/") if imdb_url else []
        imdb_id = imdb_parts[-1] if len(imdb_parts) >= 4 else None

        if not download_url:
            raise Exception("A letöltési link nem található!")

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=download_url,
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        response = await self._client.get("/hitnrun.php")
        tree = HTMLParser(response.text)

        hrefs = [
            node.attributes.get("href")
            for node in tree.css('td a[href*="details.php?id="]')
        ]

        ids = []
        for href in hrefs:
            if not href:
                continue
            try:
                parsed = urlparse(href)
                torrent_id = parse_qs(parsed.query).get("id", [None])[0]
                if torrent_id:
                    ids.append(torrent_id)
            except Exception:
                continue

        return ids

    def _resolve_resolution(self, category: str) -> str:
        category_type = _CATEGORY_MAP.get(category, "")
        if "uhd" in category_type:
            return MediaAttributeKey.R2160P
        if "hd" in category_type:
            return MediaAttributeKey.R720P
        return MediaAttributeKey.R480P

    def _resolve_language(self, category: str) -> str:
        category_type = _CATEGORY_MAP.get(category, "")
        if "hun" in category_type:
            return MediaAttributeKey.HUN
        return MediaAttributeKey.ENG
