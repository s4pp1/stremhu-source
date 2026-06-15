import re
import unicodedata
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
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
from selectolax.parser import HTMLParser

_CATEGORY_MAP: dict[str, str] = {
    "1": "movie_sd",
    "2": "movie_dvd",
    "4": "movie_hd",
    "6": "movie_uhd",
    "20": "movie_bluray",
    "26": "movie_uhd_bluray",
    "21": "series_hd",
    "23": "series_sd",
    "27": "series_uhd",
    "24": "anime_bluray",
}


class FilelistIndexerDefinition(BaseIndexerDefinition):
    @property
    def id(self) -> str:
        return "filelist"

    @property
    def disabled(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "FileList"

    @property
    def requires_full_download(self) -> bool:
        return False

    @property
    def url(self) -> str:
        return "https://filelist.io"

    @property
    def login_path(self) -> str:
        return "/login.php"

    @property
    def details_path(self) -> str:
        return "/details.php?id={torrent_id}"

    def _detect_authentication_error(
        self, response: httpx.Response
    ) -> AuthenticationErrorEnum | None:
        request_path = str(response.url.path)
        is_login_path = "/login.php" in request_path or "/takelogin.php" in request_path

        if not is_login_path:
            return None

        html = response.text if isinstance(response.text, str) else ""
        normalized = html.encode("ascii", "ignore").decode("ascii").lower()

        if (
            'name="username"' in html
            or "name='username'" in html
            or "login on any ip" in normalized
            or "numarul maxim permis de actiuni" in normalized
        ):
            return AuthenticationErrorEnum.SESSION_ERROR

        return None

    async def _login(self, credential: IndexerDefinitionLogin) -> httpx.Response:
        # Először lekérjük a login oldalt a CSRF validator token miatt
        res = await self._client.get(self.login_path)
        form_data = self._build_login_form(res.text)
        form_data["username"] = credential.username
        form_data["password"] = credential.password

        return await self._client.post(
            urljoin(self.url, "/takelogin.php"),
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        current_page = page or 0
        response = await self._client.get(
            "/browse.php",
            params={
                "search": imdb_id.replace("tt", ""),
                "searchin": "3",  # IMDB keresés
                "sort": "5",  # PEERS szerint
                "incldead": "0",
                "page": str(current_page),
            },
        )

        html = response.text
        if not isinstance(html, str):
            return IndexerDefinitionFindTorrentsResult(torrents=[])

        tree = HTMLParser(html)
        torrent_rows = tree.css(".torrentrow")
        torrents: list[IndexerDefinitionTorrent] = []

        for row in torrent_rows:
            cat_node = row.css_first(
                'a[href^="browse.php?cat="], a[href^="/browse.php?cat="]'
            )
            category_href = cat_node.attributes.get("href") if cat_node else ""
            try:
                cat_url = urlparse(urljoin("http://localhost", category_href))
                category = parse_qs(cat_url.query).get("cat", [""])[0]
            except Exception:
                category = ""

            self._resolve_resolution(category)

            det_node = row.css_first(
                'a[href^="details.php?id="], a[href^="/details.php?id="]'
            )
            details_path = det_node.attributes.get("href") if det_node else ""
            try:
                details_url = urlparse(urljoin("http://localhost", details_path))
                torrent_id = parse_qs(details_url.query).get("id", [""])[0]
            except Exception:
                torrent_id = ""

            dl_node = row.css_first(
                'a[href^="download.php?id="], a[href^="/download.php?id="]'
            )
            download_path = dl_node.attributes.get("href") if dl_node else ""
            download_url = urljoin(self.url, download_path) if download_path else ""

            imdb_node = row.css_first(
                'a[href*="www.imdb.com/title/"], a[href*="imdb.com/title/"]'
            )
            imdb_url = imdb_node.attributes.get("href") if imdb_node else ""
            imdb_id_val = self._resolve_imdb_id(imdb_url) or imdb_id

            cols = row.css("td, .torrenttable")
            if len(cols) < 9:
                continue
            seeders_text = cols[8].text(strip=True)

            if torrent_id and download_url:
                torrents.append(
                    IndexerDefinitionTorrent(
                        torrent_id=torrent_id,
                        download_url=download_url,
                        seeders=int(seeders_text) if seeders_text.isdigit() else 0,
                        imdb_id=imdb_id_val,
                    )
                )

        next_page_param = f"page={current_page + 1}"
        has_next_page = (
            len(
                [
                    node
                    for node in tree.css("a[href]")
                    if next_page_param in (node.attributes.get("href") or "")
                ]
            )
            > 0
        )

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=current_page + 1 if has_next_page else None,
        )

    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent:
        response = await self._client.get(f"/details.php?id={torrent_id}")
        tree = HTMLParser(response.text)

        dl_node = tree.css_first(f'a[href*="download.php?id={torrent_id}"]')
        download_path = dl_node.attributes.get("href") if dl_node else None

        imdb_node = tree.css_first(
            'a[href*="www.imdb.com/title/"], a[href*="imdb.com/title/"]'
        )
        imdb_url = imdb_node.attributes.get("href") if imdb_node else ""
        imdb_id = self._resolve_imdb_id(imdb_url)

        if not download_path:
            raise Exception('A "downloadPath" nem talalhato!')

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_id,
            download_url=urljoin(self.url, download_path),
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        response = await self._client.get("/snatchlist.php")
        html = response.text
        if not isinstance(html, str):
            raise Exception("A Filelist SnatchList nem talalhato.")

        tree = HTMLParser(html)
        body_node = tree.css_first("body")
        body_text = body_node.text() if body_node else ""
        page_text = self._normalize_hnr_text(body_text)

        has_snatch_marker = (
            "snatchlist" in page_text
            or "snatch list" in page_text
            or len(
                tree.css('a[href*="snatchlist.php"], form[action*="snatchlist.php"]')
            )
            > 0
        )

        if not has_snatch_marker:
            raise Exception("A Filelist SnatchList nem talalhato.")

        rows = [
            row
            for row in tree.css("tr")
            if len(row.css('a[href*="details.php?id="]')) > 0
        ]

        if not rows:
            if self._has_empty_hnr_state(page_text):
                return []
            raise Exception("A Filelist SnatchList torrent sorai nem talalhatok.")

        hnr_ids: set[str] = set()
        unknown_ids: list[str] = []

        for row in rows:
            details_node = row.css_first('a[href*="details.php?id="]')
            details_path = details_node.attributes.get("href") if details_node else None
            torrent_id = self._resolve_torrent_id(details_path or "")
            if not torrent_id:
                continue

            row_clone = HTMLParser(row.html or "")
            for node in row_clone.css('a[href*="details.php?id="]'):
                node.decompose()

            status_parts = [row_clone.body.text() if row_clone.body else ""]
            for el in row.css("[title], [alt], [aria-label], [class]"):
                href = el.attributes.get("href") or ""
                if "details.php?id=" in href:
                    continue
                status_parts.extend(
                    [
                        el.attributes.get("title") or "",
                        el.attributes.get("alt") or "",
                        el.attributes.get("aria-label") or "",
                        el.attributes.get("class") or "",
                    ]
                )

            status_text = self._normalize_hnr_text(" ".join(status_parts))

            if self._is_hnr_status(status_text):
                hnr_ids.add(torrent_id)
            elif not self._is_completed_seed_status(status_text):
                unknown_ids.append(torrent_id)

        if unknown_ids:
            raise Exception(
                f"A Filelist SnatchList statusza nem felismerheto: {', '.join(unknown_ids)}."
            )

        return list(hnr_ids)

    # --- Segédfüggvények ---

    def _build_login_form(self, html: str) -> dict[str, str]:
        tree = HTMLParser(html)
        form: dict[str, str] = {}
        for el in tree.css("form input[name]"):
            name = el.attributes.get("name")
            value = el.attributes.get("value") or ""
            if name:
                form[name] = value

        if "validator" not in form:
            raise Exception("A Filelist login validator nem talalhato.")

        return form

    def _resolve_imdb_id(self, imdb_url: str | None) -> str | None:
        if not imdb_url:
            return None
        match = re.search(r"/title/(tt\d+)", imdb_url)
        return match.group(1) if match else None

    def _resolve_torrent_id(self, details_path: str) -> str | None:
        try:
            details_url = urlparse(urljoin("http://localhost", details_path))
            return parse_qs(details_url.query).get("id", [None])[0]
        except Exception:
            return None

    def _normalize_hnr_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text)
        ascii_text = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", ascii_text.lower())).strip()

    def _has_empty_hnr_state(self, page_text: str) -> bool:
        patterns = [
            r"\bno\s+(?:torrents|results|snatches|records)\s*(?:found|available)?\b",
            r"\bnothing\s+found\b",
            r"\bempty\b",
            r"\bnu\s+(?:exista|sunt)\s+(?:torrente|rezultate|inregistrari)\b",
        ]
        return any(re.search(p, page_text) for p in patterns)

    def _is_hnr_status(self, text: str) -> bool:
        patterns = [
            r"\bhnr\b",
            r"h\s*&\s*r",
            r"hit\s*(?:and|&)\s*run",
            r"needs?\s+(?:seed|seeding|ratio|time)",
            r"(?:seed|seeding|ratio|time)\s+(?:needed|required|missing|left)",
            r"not\s+(?:completed|cleared|ok|seeded|satisfied|fulfilled)",
            r"\b(?:incomplete|unsatisfied|unfulfilled|warning|danger|pending)\b",
            r"\b(?:nefinalizat|neterminat|nesatisfacut|neindeplinit|avertizare|risc|restant)\b",
            r"(?:necesita|trebuie).*(?:seed|ratio|ratie|timp)",
        ]
        return any(re.search(p, text) for p in patterns)

    def _is_completed_seed_status(self, text: str) -> bool:
        patterns = [
            r"\b(?:complete|completed|cleared|ok|safe|done|satisfied|fulfilled)\b",
            r"\b(?:finalizat|completat|indeplinit|satisfacut)\b",
            r"\bseeded\b",
        ]
        return any(re.search(p, text) for p in patterns)

    def _resolve_resolution(self, category: str) -> str:
        cat_type = _CATEGORY_MAP.get(category, "none")
        if "uhd" in cat_type:
            return MediaAttributeKey.R2160P
        if "bluray" in cat_type:
            return MediaAttributeKey.R1080P
        if "hd" in cat_type:
            return MediaAttributeKey.R720P
        return MediaAttributeKey.R480P
