"""
@author Sappi <https://github.com/s4pp1/stremhu-source>
@website https://stremhu.hu
"""

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


class NcoreIndexerDefinition(BaseIndexerDefinition):
    @property
    def id(self) -> str:
        return "ncore"

    @property
    def name(self) -> str:
        return "nCore"

    @property
    def requires_full_download(self) -> bool:
        return False

    @property
    def url(self) -> str:
        return "https://ncore.pro"

    @property
    def login_path(self) -> str:
        return "/login.php"

    @property
    def details_path(self) -> str:
        return "/torrents.php?action=details&id={torrent_id}"

    def _detect_authentication_error(
        self, response: httpx.Response
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

    async def _login(self, credential: IndexerDefinitionLogin) -> httpx.Response:
        return await self._client.post(
            self.login_path,
            data={"nev": credential.username, "pass": credential.password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 1
        response = await self._client.get(
            "/torrents.php",
            params={
                "oldal": str(current_page),
                "miben": "imdb",
                "mire": imdb_id,
                "miszerint": "seeders",
                "hogyan": "DESC",
                "jsons": True,
            },
        )

        try:
            data = response.json()
        except Exception:
            tree = HTMLParser(response.text)
            error_node = tree.css_first(".lista_mini_error")
            error_text = error_node.text(strip=True) if error_node else None
            if error_text == "Nincs találat!":
                return IndexerDefinitionFindTorrentsResult(torrents=[])
            raise Exception(error_text or "Ismeretlen nCore hiba.")

        torrents: list[IndexerDefinitionTorrent] = []

        for torrent in data.get("results", []):
            category = torrent.get("category", "")
            torrents.append(
                IndexerDefinitionTorrent(
                    imdb_id=torrent.get("imdb_id"),
                    torrent_id=str(torrent["torrent_id"]),
                    seeders=int(torrent.get("seeders", 0)),
                    download_url=torrent["download_url"],
                    attribute_ids=[
                        self._resolve_language(category),
                        self._resolve_resolution(category),
                    ],
                )
            )

        total = int(data.get("total_results", 0))
        limit = int(data.get("perpage", 1)) or 1
        on_page = int(data.get("onpage", current_page))
        last_page = -(-total // limit)  # math.ceil

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=current_page + 1 if last_page > on_page else None,
        )

    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent:
        details_url = self.details_path.replace("{torrent_id}", torrent_id)
        response = await self._client.get(details_url)

        tree = HTMLParser(response.text)

        download_node = tree.css_first(
            f'.download a[href*="torrents.php?action=download&id={torrent_id}"]'
        )
        download_path = download_node.attributes.get("href") if download_node else None

        imdb_node = tree.css_first('a[href*="imdb.com/title/"]')
        imdb_anchor_href = imdb_node.attributes.get("href") if imdb_node else None
        imdb_id = (
            imdb_anchor_href.rstrip("/").split("/")[-1] if imdb_anchor_href else None
        )

        if not download_path:
            raise Exception('A "downloadPath" nem található!')

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=urljoin(self.url, download_path),
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        response = await self._client.get("/hitnrun.php", params={"showall": "false"})
        tree = HTMLParser(response.text)

        content = tree.css_first("#main_tartalom")
        if not content:
            raise Exception("A tartalom nem található.")

        hrefs = [
            node.attributes.get("href")
            for node in content.css('a[href*="torrents.php?action=details&id="]')
        ]

        ids = []
        for href in hrefs:
            if not href:
                continue
            full_url = urljoin(self.url, href)
            id_val = parse_qs(urlparse(full_url).query).get("id", [None])[0]
            if id_val:
                ids.append(id_val)

        return ids

    def _resolve_resolution(self, category: str) -> str:
        if "hd" in category:
            return MediaAttributeKey.R720P
        return MediaAttributeKey.R480P

    def _resolve_language(self, category: str) -> str:
        if "hun" in category:
            return MediaAttributeKey.HUN
        return MediaAttributeKey.ENG
