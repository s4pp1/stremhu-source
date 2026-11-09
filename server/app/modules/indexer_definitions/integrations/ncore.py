"""
@author Sappi <https://github.com/s4pp1/stremhu-source>
@website https://stremhu.hu
"""

import asyncio
import datetime
import hashlib
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from selectolax.lexbor import LexborHTMLParser

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
from app.modules.ncore_rss.schemas import (
    NcoreRssEntry,
    is_ncore_download_url,
    torrent_id_from_url,
    validate_ncore_url,
)


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
                "tipus": "all",
            },
        )
        response.raise_for_status()

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
        response.raise_for_status()

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
        imdb_match = (
            re.search(r"\btt\d{7,10}\b", imdb_anchor_href, re.IGNORECASE)
            if imdb_anchor_href
            else None
        )
        imdb_id = imdb_match.group(0).lower() if imdb_match else None

        if not download_path:
            raise Exception("A letöltési link nem található!")

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=urljoin(self.url, download_path),
        )

    async def fetch_rss_items(
        self,
        feed_url: str,
        skip_detail_torrent_ids: set[str] | None = None,
    ) -> list[NcoreRssEntry]:
        """Fetch a user's nCore feed and resolve each entry to a tracker torrent."""
        response = await self._get_ncore_response(feed_url)

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as error:
            raise ValueError("Az nCore RSS-válasz nem érvényes XML.") from error

        if root.tag.rsplit("}", 1)[-1].lower() not in {"rss", "feed", "rdf"}:
            raise ValueError("Az nCore válasza nem RSS vagy Atom feed.")

        feed_nodes = [
            node
            for node in root.iter()
            if node.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}
        ][:300]
        semaphore = asyncio.Semaphore(5)

        async def resolve_entry(node: ET.Element) -> NcoreRssEntry | None:
            def child_value(name: str) -> str | None:
                for child in node.iter():
                    if child is node or child.tag.rsplit("}", 1)[-1].lower() != name:
                        continue
                    text = " ".join(child.itertext()).strip()
                    if text:
                        return text
                    href = child.attrib.get("href") or child.attrib.get("url")
                    if href:
                        return href.strip()
                return None

            title = child_value("title") or "nCore torrent"
            link = child_value("link")
            guid = child_value("guid") or child_value("id")
            enclosure = next(
                (
                    element.attrib.get("url")
                    for element in node.iter()
                    if element.tag.rsplit("}", 1)[-1].lower() == "enclosure"
                    and element.attrib.get("url")
                ),
                None,
            )
            candidates = [
                urljoin(self.url, value)
                for value in (link, guid, enclosure)
                if value
            ]
            source_url = next(
                (
                    candidate
                    for candidate in candidates
                    if self._is_ncore_url(candidate)
                ),
                None,
            )
            torrent_id = next(
                (
                    parsed_id
                    for candidate in candidates
                    if self._is_ncore_url(candidate)
                    and (parsed_id := torrent_id_from_url(candidate))
                ),
                None,
            ) or (guid if guid and guid.isdigit() else None)

            description = child_value("description") or child_value("summary") or ""
            text_to_scan = " ".join([title, description, guid or "", link or ""])
            match = re.search(r"\btt\d{7,10}\b", text_to_scan, re.IGNORECASE)
            imdb_id = match.group(0).lower() if match else None
            download_url = None
            last_detail_checked_at = None
            has_direct_download = any(
                is_ncore_download_url(candidate) for candidate in candidates
            )

            if torrent_id and (not imdb_id or not has_direct_download) and (
                skip_detail_torrent_ids is None
                or torrent_id not in skip_detail_torrent_ids
            ):
                last_detail_checked_at = datetime.datetime.now()
                try:
                    async with semaphore:
                        details = await self._fetch_torrent(torrent_id)
                    if details:
                        download_url = details.download_url
                        imdb_id = details.imdb_id or imdb_id
                except Exception:
                    self.logger.debug(
                        "An nCore RSS entry could not be resolved from its details page."
                    )

            if not download_url:
                for candidate in candidates:
                    if is_ncore_download_url(candidate):
                        download_url = candidate
                        break

            stable_value = guid or link or enclosure or title
            stable_id = torrent_id or (
                f"rss-{hashlib.sha256(stable_value.encode()).hexdigest()[:32]}"
            )
            return NcoreRssEntry(
                torrent_id=stable_id,
                title=title[:500],
                source_url=source_url,
                download_url=download_url,
                imdb_id=imdb_id,
                last_detail_checked_at=last_detail_checked_at,
            )

        return [
            entry
            for entry in await asyncio.gather(
                *(resolve_entry(node) for node in feed_nodes)
            )
            if entry is not None
        ]

    async def _get_ncore_response(self, url: str) -> httpx.Response:
        original_url = validate_ncore_url(url)
        current_url = original_url
        retried_login = False

        for _ in range(6):
            response = await self._client.get(current_url, follow_redirects=False)
            if not 300 <= response.status_code < 400:
                response.raise_for_status()
                return response

            location = response.headers.get("location")
            if not location:
                response.raise_for_status()

            redirected_url = urljoin(str(response.url), location)
            validate_ncore_url(redirected_url)
            if self.login_path in urlparse(redirected_url).path:
                if retried_login:
                    response.raise_for_status()
                await self.relogin()
                retried_login = True
                current_url = original_url
                continue

            current_url = redirected_url

        raise httpx.TooManyRedirects(
            "The nCore response redirected too many times.",
            request=httpx.Request("GET", original_url),
        )

    def _is_ncore_url(self, url: str) -> bool:
        try:
            validate_ncore_url(url)
        except ValueError:
            return False
        return True

    async def download_torrent(self, download_url: str) -> bytes:
        """Download only nCore-hosted torrent URLs; do not follow redirects."""
        download_url = validate_ncore_url(download_url)
        if not is_ncore_download_url(download_url):
            raise ValueError("Érvénytelen nCore letöltési hivatkozás.")
        response = await self._get_ncore_response(download_url)
        return response.content

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
