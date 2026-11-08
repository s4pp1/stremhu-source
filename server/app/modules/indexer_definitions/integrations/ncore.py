"""
@author Sappi <https://github.com/s4pp1/stremhu-source>
@website https://stremhu.hu
"""

from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from selectolax.lexbor import LexborHTMLParser

from app.common.log_safety import network_error_fields
from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.schemas.internal import (
    AuthCredentialError,
    AuthError,
    AuthSessionError,
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionLoginPayload,
    IndexerDefinitionTorrent,
)
from app.modules.media_attributes.constants import MediaAttributeKey

_NCORE_MOVIE_CATEGORIES: list[str] = [
    "xvid_hun",
    "xvid",
    "dvd_hun",
    "dvd",
    "dvd9_hun",
    "dvd9",
    "hd_hun",
    "hd",
]

_NCORE_SERIES_CATEGORIES: list[str] = [
    "xvidser_hun",
    "xvidser",
    "dvdser_hun",
    "dvdser",
    "hdser_hun",
    "hdser",
]


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
    def supports_totp(self) -> bool:
        return True

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
        self,
        response: httpx.Response,
    ) -> AuthError:
        final_path = str(response.url.path)
        original_url = str(response.request.url)
        if response.history:
            original_url = str(response.history[0].url)

        ended_up_at_login = self.login_path in final_path

        if ended_up_at_login:
            if self.login_path in original_url:
                return AuthCredentialError()
            return AuthSessionError()

        return None

    async def _login(
        self,
        payload: IndexerDefinitionLoginPayload,
    ) -> httpx.Response:
        data = {"nev": payload.username, "pass": payload.password}
        if payload.totp_code:
            data["2factor"] = payload.totp_code

        return await self._client.post(
            self.login_path,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        return await self._query_torrents(mire=imdb_id, miben="imdb", page=page)

    async def _fetch_torrents_by_query(
        self,
        query: str,
        page: int | None = None,
        media_type: str | None = None,
    ) -> IndexerDefinitionFindTorrentsResult:
        return await self._query_torrents(
            mire=query, miben="nev", page=page, media_type=media_type
        )

    async def _query_torrents(
        self,
        mire: str,
        miben: str,
        page: int | None = None,
        media_type: str | None = None,
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 1
        params: Any = [
            ("oldal", str(current_page)),
            ("miben", miben),
            ("mire", mire),
            ("miszerint", "seeders"),
            ("hogyan", "DESC"),
            ("jsons", "true"),
        ]

        if media_type == "movie":
            params.append(("tipus", "kivalasztottak_kozott"))
            for cat in _NCORE_MOVIE_CATEGORIES:
                params.append(("kivalasztott_tipus[]", cat))
        elif media_type == "series":
            params.append(("tipus", "kivalasztottak_kozott"))
            for cat in _NCORE_SERIES_CATEGORIES:
                params.append(("kivalasztott_tipus[]", cat))
        else:
            params.append(("tipus", "kivalasztottak_kozott"))
            for cat in _NCORE_MOVIE_CATEGORIES + _NCORE_SERIES_CATEGORIES:
                params.append(("kivalasztott_tipus[]", cat))

        response = await self._client.get(
            "/torrents.php",
            params=params,
        )

        try:
            data = response.json()
        except Exception:
            tree = LexborHTMLParser(response.text)
            error_node = tree.css_first(".lista_mini_error")
            error_text = error_node.text(strip=True) if error_node else None
            if error_text == "Nincs találat!":
                return IndexerDefinitionFindTorrentsResult(torrents=[])
            raise Exception(error_text or "Ismeretlen nCore hiba.")

        torrents: list[IndexerDefinitionTorrent] = []

        for torrent in data.get("results", []):
            category = torrent.get("category", "")
            raw_imdb = torrent.get("imdb_id")
            imdb_id = (
                raw_imdb
                if isinstance(raw_imdb, str) and raw_imdb.strip()
                else None
            )
            torrents.append(
                IndexerDefinitionTorrent(
                    imdb_id=imdb_id,
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
        last_page = -(-total // limit)  # math.ceil

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=current_page + 1 if current_page < last_page else None,
        )

    async def _fetch_torrent(
        self,
        torrent_id: str,
    ) -> IndexerDefinitionTorrent | None:
        details_url = self.details_path.replace("{torrent_id}", torrent_id)
        response = await self._client.get(details_url)

        tree = LexborHTMLParser(response.text)

        html_node = tree.css_first("html")
        if html_node and "Nem található az adatbázisunkban" in html_node.text():
            return None

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
            raise Exception("A letöltési link nem található!")

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=urljoin(self.url, download_path),
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        response = await self._client.get("/hitnrun.php", params={"showall": "false"})
        tree = LexborHTMLParser(response.text)

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

    async def fetch_tech_info(self, torrent_id: str) -> tuple[str | None, str | None]:
        nfo_text: str | None = None
        drop_text: str | None = None

        try:
            r_nfo = await self._client.get(
                "/ajax.php",
                params={"action": "nfo", "id": torrent_id},
                timeout=1.5,
            )
            if r_nfo.status_code == 200 and r_nfo.text.strip():
                nfo_text = r_nfo.text

            # Ha van NFO, és az tartalmaz MediaInfo blokkot (Video/Audio/General) vagy magyar feliratot,
            # a technikai adatok már teljesek, nem szükséges egy második lassú webes kérés:
            need_drop = True
            if nfo_text:
                lower_nfo = nfo_text.lower()
                has_mediainfo = any(
                    k in lower_nfo
                    for k in (
                        "unique id",
                        "general",
                        "video #",
                        "audio #",
                        "hang #",
                        "szöveg #",
                        "text #",
                        "format :",
                    )
                )
                has_hun = "hungarian" in lower_nfo or "magyar" in lower_nfo
                if has_mediainfo or has_hun:
                    need_drop = False

            if need_drop:
                r_drop = await self._client.get(
                    "/ajax.php",
                    params={"action": "torrent_drop", "id": torrent_id},
                    timeout=1.5,
                )
                if r_drop.status_code == 200 and r_drop.text.strip():
                    drop_text = r_drop.text
        except Exception as e:
            self.logger.debug(f"[nCore] fetch_tech_info hiba ({torrent_id}): {network_error_fields(e)}")

        return nfo_text, drop_text

