"""
TorrentLeech indexer definíció a StremHU Source-hoz.

Elhelyezés a szerver kódbázisában:
    app/modules/indexer_definitions/integrations/torrentleech.py

A Jackett Cardigann YAML-jéből származtatva (torrentleech.yml), de NEM gépi
fordítás: a StremHU adatmodellje lényegesen szűkebb, mint a Jacketté. A YAML
`fields` blokkjának nagy része (size, date, leechers, grabs, download_multiplier,
minimumseedtime) itt egyszerűen nem létezik — az IndexerDefinitionTorrent öt
mezőt ismer. Ami átjött a YAML-ből:

    login.path / login.form / login.inputs   → _login
    login.error selectorok                   → _detect_authentication_error
    search.paths (JSON mód)                  → _fetch_torrents
    fields.fid / .filename / .imdbID         → torrent_id / download_url / imdb_id
    requestDelay: 4.1                        → max_concurrent

Miért JSON és nem HTML scraping?
--------------------------------
A /torrents/browse/list/... végpont natívan JSON-t ad (a YAML-ben is
`response: {type: json}`), a sorok a `torrentList` tömbben vannak. Ez stabilabb,
mint a HTML szerkezetére támaszkodni, és a keresés IMDB-azonosítóval közvetlenül
szűrhető — ami azért létfontosságú, mert a StremHU KIZÁRÓLAG IMDB alapján keres
(lásd BaseIndexerDefinition._find_all, ami a végén imdb_id egyezésre szűr).

Ismert korlát: Hit'n'Run
------------------------
A TorrentLeech-nek nincs gépileg olvasható H&R listaoldala, és a Cardigann
YAML sem ismer ilyet (a Jackett csak a `minimumseedtime: 864000` — 10 nap —
metaadatot tárolja). A _fetch_hit_and_run_ids ezért üres listát ad: a H&R
figyelés ezen a trackeren nem működik. Ez tudatos, nem hiányzó implementáció.
"""

import asyncio
import re
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.schemas.internal import (
    AuthCredentialError,
    AuthError,
    AuthSessionError,
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionLogin,
    IndexerDefinitionTorrent,
)
from app.modules.media_attributes.constants import MediaAttributeKey

# A release-névből kiolvasható jellemzők. A sorrend számít: az első találat nyer,
# ezért a bővebb minta előzi a szűkebbet (2160p a 720p előtt, DTS-HD MA a DTS
# előtt, HDR10+ a HDR10 előtt). Enélkül a "DTS-HD.MA.5.1" DTS-ként jönne be.
_RESOLUTION_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:2160p|4k|uhd)\b", MediaAttributeKey.R2160P),
    (r"\b1080[pi]\b", MediaAttributeKey.R1080P),
    (r"\b720p\b", MediaAttributeKey.R720P),
    (r"\b576[pi]\b", MediaAttributeKey.R576P),
    (r"\b540p\b", MediaAttributeKey.R540P),
    (r"\b480[pi]\b", MediaAttributeKey.R480P),
]

_SOURCE_PATTERNS: list[tuple[str, str]] = [
    (r"\bremux\b", MediaAttributeKey.REMUX),
    (r"\b(?:uhd[.\s_-]?bluray|uhdbd)\b", MediaAttributeKey.UHD),
    (r"\b(?:bluray|blu-ray|bdremux)\b", MediaAttributeKey.BLURAY),
    (r"\b(?:bdrip|brrip)\b", MediaAttributeKey.BDRIP),
    (r"\bweb[.\s_-]?dl\b", MediaAttributeKey.WEB_DL),
    (r"\bweb[.\s_-]?rip\b", MediaAttributeKey.WEB_RIP),
    (r"\bhdtv\b", MediaAttributeKey.HDTV),
    (r"\bdvd[.\s_-]?rip\b", MediaAttributeKey.DVD_RIP),
    (r"\b(?:cam|ts|tc|telesync)\b", MediaAttributeKey.CAM),
]

_CODEC_PATTERNS: list[tuple[str, str]] = [
    (r"\bav1\b", MediaAttributeKey.AV1),
    (r"\b(?:x265|h[.\s_-]?265|hevc)\b", MediaAttributeKey.X265),
    (r"\b(?:x264|h[.\s_-]?264|avc)\b", MediaAttributeKey.X264),
]

_HDR_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:dv|dovi|dolby[.\s_-]?vision)\b", MediaAttributeKey.DV),
    (r"\bhdr10\+|hdr10p\b", MediaAttributeKey.HDR10P),
    (r"\bhdr10\b", MediaAttributeKey.HDR10),
    (r"\bhlg\b", MediaAttributeKey.HLG),
    (r"\bsdr\b", MediaAttributeKey.SDR),
]

# A hangformátum és a térhangzás a MediaAttributeKey-ben KÜLÖN csoport (Audio
# Quality vs Audio Spatial), ezért itt is külön lista kell. Egy listában az
# "TrueHD.7.1.Atmos" névből csak az Atmos maradna meg, a TrueHD elveszne.
_AUDIO_QUALITY_PATTERNS: list[tuple[str, str]] = [
    (r"\bdts[.\s_-]?hd[.\s_-]?ma\b", MediaAttributeKey.DTS_HD_MA),
    (r"\btrue[.\s_-]?hd\b", MediaAttributeKey.TRUEHD),
    (r"\bflac\b", MediaAttributeKey.FLAC),
    # Trailing \b nélkül, mert a gyakori írásmód "DDP5.1" — ott a "ddp" után
    # rögtön számjegy jön, és a \b nem illeszkedne.
    (r"\b(?:eac3|e[.\s_-]?ac[.\s_-]?3|ddp|dd\+)", MediaAttributeKey.DD_PLUS),
    (r"\bdts\b", MediaAttributeKey.DTS),
    (r"\b(?:ac3|dd)\d", MediaAttributeKey.DD),
    (r"\bac3\b", MediaAttributeKey.DD),
    # Szintén trailing \b nélkül: az "AAC2.0" írásmód gyakori.
    (r"\baac", MediaAttributeKey.AAC),
]

_AUDIO_SPATIAL_PATTERNS: list[tuple[str, str]] = [
    (r"\bdts[.\s_-]?x\b", MediaAttributeKey.DTS_X),
    (r"\batmos\b", MediaAttributeKey.DOLBY_ATMOS),
]

# Vezető \b helyett negatív lookbehind: a "DDP5.1" esetén az "5" előtt "P" áll,
# ami szóhatár nélküli — a \b ott nem illeszkedne. A számjegy-kizárás viszont
# megakadályozza, hogy a "15.1"-ből 5.1 legyen.
_CHANNEL_PATTERNS: list[tuple[str, str]] = [
    (r"(?<!\d)7[.\s_]1(?!\d)", MediaAttributeKey.CH_7_1),
    (r"(?<!\d)5[.\s_]1(?!\d)", MediaAttributeKey.CH_5_1),
    (r"(?<!\d)2[.\s_]0(?!\d)", MediaAttributeKey.CH_2_0),
]

# A YAML categorymappings-ből csak az, ami felbontásra utal — akkor használjuk,
# ha a release-névből nem jött ki semmi. A többi kategória (játék, könyv, zene)
# a StremHU szempontjából érdektelen, mert IMDB-re keresünk.
_CATEGORY_RESOLUTION: dict[str, str] = {
    "47": MediaAttributeKey.R2160P,  # Movies 4K
    "13": MediaAttributeKey.R1080P,  # Movies Bluray
    "14": MediaAttributeKey.R1080P,  # Movies BlurayRip
    "43": MediaAttributeKey.R1080P,  # Movies HDRip
    "32": MediaAttributeKey.R1080P,  # TV Episodes HD
    "8": MediaAttributeKey.R480P,  # Movies Cam
    "9": MediaAttributeKey.R480P,  # Movies TS/TC
    "11": MediaAttributeKey.R480P,  # Movies DVDRip
    "26": MediaAttributeKey.R480P,  # TV Episodes (SD)
}


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
    def requires_full_download(self) -> bool:
        # A TorrentLeech nem ad magnetet, viszont a .torrent letöltés közvetlen
        # (/download/{id}/{filename}), ugyanúgy, ahogy az nCore-nál — ezért False.
        return False

    @property
    def max_concurrent(self) -> int:
        # A Cardigann YAML `requestDelay: 4.1`-et ír elő (Jackett #13796): a
        # TorrentLeech sűrű kérésre 429-cel, tartós túlterhelésre tiltással
        # válaszol. A bázisosztály alapértéke 5 párhuzamos kérés — az itt sok.
        return 2

    # ── Hitelesítés ──────────────────────────────────────────────────────────

    def _detect_authentication_error(self, response: httpx.Response) -> AuthError:
        # FIGYELEM: NE URL-alapon próbáld felismerni a login oldalt. A
        # TorrentLeech lejárt munkamenetnél NEM irányít át — a kért URL-en,
        # 200-zal adja vissza a login oldal HTML-jét. Az ncore.py mintája (a
        # response.url.path vizsgálata) itt mindig None-t adna, a session soha
        # nem újulna meg, és a _fetch_torrents HTML-t kapna JSON helyett.
        # A Cardigann YAML is tartalom alapján dönt: `selector: form[name="login-form"]`.
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            # JSON keresési válasz vagy .torrent letöltés — hitelesítési hiba kizárva.
            return None

        tree = HTMLParser(response.text)
        if not tree.css_first('form[name="login-form"]'):
            return None

        # Innentől biztos, hogy a login oldalt kaptuk vissza.
        original_url = str(response.request.url)
        if response.history:
            original_url = str(response.history[0].url)

        if self.login_path not in original_url:
            # Nem ide indultunk → a munkamenet járt le. A bázisosztály újra
            # belép, és megismétli az eredeti kérést.
            return AuthSessionError()

        # Ide indultunk, tehát ez a bejelentkezés válasza, és nem sikerült.
        # A YAML login.error selectorai döntik el, hogy hibás adat vagy 2FA az ok.

        otp_node = tree.css_first(".login-container h2")
        if otp_node and "One Time Password" in otp_node.text():
            return AuthCredentialError(
                message=(
                    "A TorrentLeech fiókon be van kapcsolva a 2FA. Add meg az "
                    "Alt 2FA Tokent a profilodból (Site Profile → Alt 2FA Token)."
                )
            )

        error_node = tree.css_first("p.text-danger")
        error_text = error_node.text(strip=True) if error_node else None
        if error_text:
            return AuthCredentialError(message=error_text)

        # Konkrét hibaüzenet nélkül is biztos, hogy nem sikerült: a bejelentkezés
        # válaszaként megint a login űrlapot kaptuk (ezt a metódus eleje már
        # ellenőrizte). Sikeres belépésnél a TorrentLeech a főoldalra visz.
        return AuthCredentialError()

    async def _login(self, credential: IndexerDefinitionLogin) -> httpx.Response:
        # FIGYELEM: NE kérd le előbb a login oldalt az űrlap mezőiért. Az
        # IndexerClient.request MINDEN válaszon lefuttatja a
        # _detect_authentication_error-t — a login oldal GET-je tehát saját maga
        # váltana ki "a bejelentkezés nem sikerült" hibát (login űrlap a
        # válaszban + a login útvonal az eredeti URL-ben), még a POST előtt.
        # A belépés így soha nem tudna sikerülni.
        #
        # Szerencsére nincs is rá szükség: a TorrentLeech űrlapja mindössze
        # <input name="username"> és <input name="password"> mezőket tartalmaz,
        # rejtett/CSRF mező nélkül. Ha a tracker később bevezetne ilyet, a
        # lekérést a szülő httpx.AsyncClient.request-tel kell megkerülni, hogy
        # ne fusson rá a detektor.
        return await self._client.post(
            self.login_path,
            data={
                "username": credential.username,
                "password": credential.password,
                # A YAML is mindig küldi; 2FA nélküli fióknál üresen kell menjen.
                "alt2FAToken": "",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    # ── Keresés ──────────────────────────────────────────────────────────────

    async def _fetch_torrents(
        self, imdb_id: str, page: int | None = None
    ) -> IndexerDefinitionFindTorrentsResult:
        # A `page` paramétert nem használjuk (lásd lentebb) — a bázisosztály
        # _find_all-ja csak akkor hívna 1-nél nagyobb értékkel, ha next_page-et
        # adnánk vissza, amit sosem teszünk.
        del page

        # A YAML search.paths sablonjából az IMDB-s ág, kategóriaszűrés nélkül:
        #   torrents/browse/list/imdbID/{imdb}/newfilter/2/orderby/{sort}/order/{type}
        # A "newfilter/2" a YAML kommentje szerint a 0day és music kategóriákat
        # is bevonja — nálunk ez ártalmatlan, mert IMDB-re szűrünk.
        # Seeders szerint rendezünk, hogy a _find_all 300-as limitjébe a
        # használható találatok kerüljenek be először.
        # Lapozás NINCS: a Cardigann YAML sem lapoz, és a /page/{n} szegmenst a
        # TorrentLeech böngésző-végpontja nem dokumentálja. Egy IMDB-keresés
        # amúgy is jóval a lapméret alatt marad (a YAML a fiókprofilban 100-as
        # "Torrents per page" beállítást javasol). Inkább egy lap biztosan
        # jó adattal, mint kettő bizonytalan URL-lel.
        path = (
            f"/torrents/browse/list/imdbID/{imdb_id}"
            f"/newfilter/2/orderby/seeders/order/desc"
        )

        response = await self._client.get(path)

        try:
            data = response.json()
        except Exception as e:
            raise Exception(
                "A TorrentLeech nem JSON-t adott vissza — valószínűleg "
                "Cloudflare-ellenőrzés vagy megszűnt munkamenet."
            ) from e

        rows = data.get("torrentList") or []

        torrents: list[IndexerDefinitionTorrent] = []
        for row in rows:
            torrent_id = row.get("fid")
            filename = row.get("filename")
            if not torrent_id or not filename:
                continue

            # A sor imdbID-ja lehet üres vagy null (#13736 a YAML-ben a title-re
            # ugyanezt jelzi). Mivel IMDB-re kerestünk, ilyenkor a keresett
            # azonosító a helyes érték — enélkül a _find_all végén kiesne a sor.
            row_imdb = (row.get("imdbID") or "").strip() or imdb_id

            torrents.append(
                IndexerDefinitionTorrent(
                    torrent_id=str(torrent_id),
                    imdb_id=row_imdb,
                    seeders=int(row.get("seeders") or 0),
                    download_url=urljoin(
                        self.url, f"/download/{torrent_id}/{filename}"
                    ),
                    attribute_ids=self._resolve_attributes(
                        row.get("name") or filename,
                        str(row.get("categoryID") or ""),
                    ),
                )
            )

        # next_page mindig None — lásd a path fenti megjegyzését. Ha a numFound
        # rendszeresen meghaladná a kapott sorok számát, itt lehet lapozást
        # bevezetni, de csak a végpont tényleges ellenőrzése után.
        num_found = int(data.get("numFound") or 0)
        if num_found > len(rows):
            self.logger.info(
                "TorrentLeech: %s találatból %s jött vissza az első lapon "
                "(imdb_id=%s). Növeld a 'Torrents per page' értéket a "
                "fiókprofilodban, ha hiányoznak találatok.",
                num_found,
                len(rows),
                imdb_id,
            )

        return IndexerDefinitionFindTorrentsResult(
            torrents=torrents,
            next_page=None,
        )

    async def _fetch_torrent(self, torrent_id: str) -> IndexerDefinitionTorrent | None:
        details_url = self.details_path.replace("{torrent_id}", torrent_id)
        response = await self._client.get(details_url)

        tree = HTMLParser(response.text)

        download_node = tree.css_first(f'a[href^="/download/{torrent_id}/"]')
        download_path = download_node.attributes.get("href") if download_node else None

        if not download_path:
            # Nem létező vagy törölt torrent — a hívó None-ként kezeli.
            return None

        imdb_node = tree.css_first('a[href*="imdb.com/title/"]')
        imdb_href = imdb_node.attributes.get("href") if imdb_node else None
        imdb_match = re.search(r"/title/(tt\d+)", imdb_href or "")

        return IndexerDefinitionTorrent(
            torrent_id=torrent_id,
            imdb_id=imdb_match.group(1) if imdb_match else None,
            download_url=urljoin(self.url, download_path),
        )

    async def _fetch_hit_and_run_ids(self) -> list[str]:
        """
        A profil snatchlistjéből gyűjti a H&R-t, KIZÁRÓLAG az 1:1 arány alapján.

        A TorrentLeech két feltétel bármelyikével letudja a kötelezettséget:
        1:1 arány VAGY az osztályhoz tartozó minimum seed idő (Registered 10 nap,
        Power User 8, Super User 7, Extreme 6, TL God 4, VIP 0). A snatchlist
        oszlopai — Name, Size, Dld, Uld, Rto, Ann, Co, Act — viszont NEM
        tartalmaznak seed időt, csak arányt.

        Ezért ez a lista TÚLBECSÜL: rajta marad az is, ami az időt már letöltötte,
        csak az arányt nem érte el. Ez tudatos választás. A fordított hiba lenne
        veszélyes: ha "teljesítve"-nek mondanánk valamit, amit a tracker még
        H&R-nek számol, a felhasználó annak alapján törölné le, és warningot kapna.

        A seed időt a StremHU saját torrents.created_at mezőjéből sem lehet
        kiváltani: az a felvétel ideje (a seed óra a letöltés BEFEJEZÉSEKOR indul),
        a fali óra pedig akkor is ketyeg, amikor a kliens áll és a tracker nem
        számol időt. Ráadásul a definíciók nem is érik el az adatbázist — az
        IndexerAccountStorage csak hitelesítési adatot és cookie-t ad.
        """
        if not self._indexer_account_storage:
            return []

        credential = await asyncio.to_thread(
            self._indexer_account_storage.get_credentials, self.id
        )
        if not credential or not credential.username:
            return []

        response = await self._client.get(f"/profile/{credential.username}")
        tree = HTMLParser(response.text)

        # A snatchlist sorait a névcella osztálya azonosítja:
        #   <td class="snatchlistName"><a href="/torrent/241811750">…</a></td>
        name_cells = tree.css("td.snatchlistName")

        if not name_cells:
            # KIVÉTELT dobunk, NEM üres listát adunk. A hívó
            # (indexers/service.py cleanup_torrent_by_rules) a visszakapott
            # listát arra használja, hogy MIT NE töröljön:
            #
            #   not_completed_torrent_ids = await find_hit_and_run_ids()
            #   cleanup_tracker_torrents(..., not_completed_torrent_ids=...)
            #
            # Üres lista tehát azt jelenti: "nincs H&R kötelezettséged" — és
            # ilyenkor a takarítás letörli azokat a torrenteket is, amikre
            # valójában H&R jár. Kivételnél viszont a hívó `except Exception`
            # ága elkapja, kihagyja EZT az indexert, és nem töröl semmit.
            # Bizonytalanságban ez a helyes irány.
            #
            # Nem tudjuk megkülönböztetni az üres snatchlistet a sikertelen
            # elemzéstől, mert a táblát a TorrentLeech JS-ből tölti be — a
            # szerver által küldött HTML-ben nincs benne (Ctrl+U → nincs
            # "snatchlistName"). Amíg az XHR végpontra át nem áll, ez az ág
            # mindig lefut, és a TorrentLeech takarítása kimarad. Ez szándékos:
            # inkább ne töröljön, mint hogy warningot hozzon a fiókra.
            raise Exception(
                "A TorrentLeech snatchlist nem olvasható a /profile/"
                f"{credential.username} oldalról. A táblát a tracker JS-ből "
                "tölti be, ezért a H&R lista nem állapítható meg — a takarítás "
                "biztonságból kimarad."
            )

        hit_and_run_ids: list[str] = []
        unparsed_ratios = 0

        for name_cell in name_cells:
            row = name_cell.parent
            if row is None:
                continue

            link = name_cell.css_first('a[href^="/torrent/"]')
            href = link.attributes.get("href") if link else None
            match = re.search(r"/torrent/(\d+)", href or "")
            if not match:
                continue
            torrent_id = match.group(1)

            # Oszlopsorrend: Name(0) Size(1) Dld(2) Uld(3) Rto(4) Ann(5) Co(6) Act(7)
            cells = row.css("td")
            if len(cells) <= 3:
                continue

            downloaded = self._parse_size(cells[2].text(strip=True))
            uploaded = self._parse_size(cells[3].text(strip=True))

            if downloaded is None or uploaded is None:
                # Ismeretlen formátum → a biztonságos irány a megjelölés.
                unparsed_ratios += 1
                hit_and_run_ids.append(torrent_id)
                continue

            # 1:1 a TÉNYLEGES bájtokon. Nem a Rto oszlopot használjuk: a
            # TorrentLeech ott "inf."-et ír, ha a BESZÁMÍTOTT letöltés nulla
            # (freeleech), holott a kötelezettség ilyenkor is fennáll. A
            # tracker doksija egyértelmű: "every torrent you download from TL
            # including freeleech is expected to be seeded back fully".
            # A Rto-ra hagyatkozva minden freeleech torrent teljesítettnek
            # látszana 0 bájt feltöltéssel is — épp a veszélyes irányba.
            if downloaded <= 0:
                continue  # nem töltöttünk le semmit → nincs mit visszaadni
            if uploaded < downloaded:
                hit_and_run_ids.append(torrent_id)

        if unparsed_ratios:
            self.logger.warning(
                "TorrentLeech: %s sor Dld/Uld értéke nem volt értelmezhető, "
                "ezek biztonságból H&R-ként szerepelnek.",
                unparsed_ratios,
            )

        return hit_and_run_ids

    def _parse_size(self, size_text: str) -> float | None:
        """
        "17.27 GB" → bájt. None, ha nem értelmezhető.

        A TorrentLeech 1024-es nagyságrendeket használ B/KB/MB/GB/TB
        jelöléssel. Mivel a Dld és az Uld ugyanabban a mértékegység-rendszerben
        van, az összehasonlításra a pontos szorzó amúgy sem kritikus.
        """
        text = size_text.strip().replace(",", ".").replace("\xa0", " ")
        match = re.match(r"^([0-9]*\.?[0-9]+)\s*([kmgtp]?i?b)$", text, re.IGNORECASE)
        if not match:
            return None

        try:
            value = float(match.group(1))
        except ValueError:
            return None

        multipliers = {
            "b": 1,
            "kb": 1024,
            "kib": 1024,
            "mb": 1024**2,
            "mib": 1024**2,
            "gb": 1024**3,
            "gib": 1024**3,
            "tb": 1024**4,
            "tib": 1024**4,
            "pb": 1024**5,
            "pib": 1024**5,
        }
        unit = match.group(2).lower()
        if unit not in multipliers:
            return None

        return value * multipliers[unit]

    # ── Segédfüggvények ──────────────────────────────────────────────────────

    def _resolve_attributes(self, release_name: str, category_id: str) -> list[str]:
        """
        A release-névből olvassa ki a média-jellemzőket.

        A TorrentLeech kategóriái ehhez túl durvák (a "Movies Bluray" alatt
        720p és 1080p is van), a scene/p2p release-nevek viszont szabványosak.
        A kategória csak tartalék, ha a névből nem jött ki felbontás.
        """
        name = release_name.lower()
        attributes: list[str] = []

        for patterns in (
            _RESOLUTION_PATTERNS,
            _SOURCE_PATTERNS,
            _CODEC_PATTERNS,
            _HDR_PATTERNS,
            _AUDIO_QUALITY_PATTERNS,
            _AUDIO_SPATIAL_PATTERNS,
            _CHANNEL_PATTERNS,
        ):
            for pattern, attribute in patterns:
                if re.search(pattern, name):
                    attributes.append(attribute)
                    break

        # Felbontás tartalék a kategóriából.
        has_resolution = any(
            attribute in {resolution for _, resolution in _RESOLUTION_PATTERNS}
            for attribute in attributes
        )
        if not has_resolution:
            fallback = _CATEGORY_RESOLUTION.get(category_id)
            if fallback:
                attributes.append(fallback)

        # Nyelv: a TorrentLeech angol nyelvű tracker (a YAML `language: en-US`),
        # magyar szinkron csak elvétve és mindig jelölve fordul elő.
        if re.search(r"\b(?:hun|hungarian|magyar)\b", name):
            attributes.append(MediaAttributeKey.HUN)
        else:
            attributes.append(MediaAttributeKey.ENG)

        return attributes
