from urllib.parse import urljoin

import httpx
import pydash
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
    "6": "movie_cam_hun",
    "5": "movie_cam",
    "14": "movie_sd_hun",
    "13": "movie_sd",
    "12": "movie_hd_hun",
    "11": "movie_hd",
    "18": "series_sd_hun",
    "17": "series_sd",
    "19": "series_hd_hun",
    "20": "series_hd",
}

_DOWNLOAD_URL_PREFIX = "/download/"
_CATEGORY_URL_PREFIX = "/torrents/?action=search&categories[]="


class MajomparadeIndexerDefinition(BaseIndexerDefinition):
    @property
    def id(self) -> str:
        return "majomparade"

    @property
    def name(self) -> str:
        return "Majomparádé"

    @property
    def requires_full_download(self) -> bool:
        return True

    @property
    def url(self) -> str:
        return "https://majomparade.eu"

    @property
    def login_path(self) -> str:
        return "/login"

    @property
    def details_path(self) -> str:
        return "/torrent/{torrent_id}"

    def _detect_authentication_error(
        self,
        response: httpx.Response,
    ) -> AuthenticationErrorEnum | None:
        original_url = str(response.request.url)

        if self.login_path in original_url and response.request.method == "POST":
            success = None
            try:
                data = response.json()
                success = pydash.get(data, "success")
            except Exception:
                success = False

            if success is False:
                return AuthenticationErrorEnum.CREDENTIAL_ERROR

            return None

        final_path = str(response.url.path)
        if self.login_path in final_path:
            return AuthenticationErrorEnum.SESSION_ERROR

        return None

    async def _login(
        self,
        credential: IndexerDefinitionLogin,
    ) -> httpx.Response:
        return await self._client.post(
            "/login/do",
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
            "/torrents/",
            params={
                "action": "search",
                "search_text": imdb_id,
                "sort": "5",
                "order_by": "0",
                "page": str(current_page),
            },
        )

        html = response.text
        if not isinstance(html, str):
            return IndexerDefinitionFindTorrentsResult(torrents=[])

        tree = HTMLParser(html)
        torrent_rows = tree.css("article.torrent-card")
        torrents: list[IndexerDefinitionTorrent] = []

        for row in torrent_rows:
            # Category
            category_node = row.css_first(f'a[href*="{_CATEGORY_URL_PREFIX}"]')
            category_href = (
                category_node.attributes.get("href") if category_node else None
            )
            category_id = (
                category_href.replace(_CATEGORY_URL_PREFIX, "")
                if category_href
                else None
            )

            if not category_id:
                continue

            # Download
            download_node = row.css_first(f'a[href*="{_DOWNLOAD_URL_PREFIX}"]')
            download_path = (
                download_node.attributes.get("href") if download_node else None
            )
            download_url = urljoin(self.url, download_path) if download_path else None

            if not download_url:
                continue

            # Torrent ID
            torrent_id = (
                download_path.replace(_DOWNLOAD_URL_PREFIX, "")
                if download_path
                else None
            )

            if not torrent_id:
                continue

            # IMDB
            imdb_node = row.css_first('a[href*="www.imdb.com/title/"]')
            imdb_url = imdb_node.attributes.get("href") if imdb_node else None
            imdb_parts = imdb_url.rstrip("/").split("/") if imdb_url else []
            imdb_id = imdb_parts[-1] if len(imdb_parts) >= 4 else ""

            # Seeders
            seeders_node = row.css_first(".torrent-card__side .t-stats a")
            seeders = seeders_node.text(strip=True) if seeders_node else ""

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

        pagination = tree.css_first(".pagination")
        if pagination:
            # eq(-1) direct child:
            child_nodes = [
                n
                for n in pagination.iter()
                if n.tag == "a" or n.tag == "span" or n.tag == "li"
            ]
            next_button = child_nodes[-1] if child_nodes else None
        else:
            next_button = None

        is_disabled = False
        if next_button:
            classes = next_button.attributes.get("class") or ""
            is_disabled = "disabled" in classes

        has_next_page = next_button is not None and not is_disabled

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=current_page + 1 if has_next_page else None,
        )

    async def _fetch_torrent(
        self,
        torrent_id: str,
    ) -> IndexerDefinitionTorrent | None:
        response = await self._client.get(f"/torrent/{torrent_id}")
        tree = HTMLParser(response.text)

        html_node = tree.css_first("html")
        if html_node and "Ez a torrent nem létezik!" in html_node.text():
            return None

        # Download
        download_node = tree.css_first(f'form[action*="/download/{torrent_id}"]')
        download_path = (
            download_node.attributes.get("action") if download_node else None
        )

        # IMDB
        imdb_node = tree.css_first('a[href*="www.imdb.com/title/"]')
        imdb_url = imdb_node.attributes.get("href") if imdb_node else None
        imdb_parts = imdb_url.rstrip("/").split("/") if imdb_url else []
        imdb_id = imdb_parts[-1] if len(imdb_parts) >= 4 else None

        if not download_path:
            raise Exception("A letöltési link nem található!")

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=urljoin(self.url, download_path),
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        response = await self._client.get("/hitnrun/")
        tree = HTMLParser(response.text)

        content = tree.css_first("#main-section")
        if not content:
            raise Exception("Az elvárt tartalom nem érhető el.")

        hrefs = [
            node.attributes.get("href")
            for node in content.css('table a[href*="/torrent/"]')
        ]

        return [href.replace("/torrent/", "") for href in hrefs if href]

    def _resolve_resolution(self, category: str) -> str:
        cat_type = _CATEGORY_MAP.get(category, "")
        if "hd" in cat_type:
            return MediaAttributeKey.R720P
        return MediaAttributeKey.R480P

    def _resolve_language(self, category: str) -> str:
        cat_type = _CATEGORY_MAP.get(category, "")
        if "hun" in cat_type:
            return MediaAttributeKey.HUN
        return MediaAttributeKey.ENG
