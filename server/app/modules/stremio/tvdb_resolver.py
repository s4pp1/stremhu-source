import html
import re
from collections import defaultdict
from typing import Any
from urllib.parse import quote

import httpx

from app.common.keyed_lock import KeyedLock
from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.common.validators import validate_numeric_media_id
from app.config import config

_MAX_CACHE_ENTRIES = 10000
_MAX_SERIES_CACHE = 2000

# Gyakori anime és sorozatok ismert alternatív / iker IMDb azonosítói (pl. eredeti japán TV sugárzás vs nemzetközi/angol premier)
# nCore-on és egyéb indexereken a feltöltők gyakran az egyikre vagy másikra töltik fel a torrenteket.
_IMDB_ALIASES: dict[str, list[str]] = {
    # Dragon Ball Z (1989 eredeti japán: tt0121220 <-> 1996 nemzetközi/angol: tt0214341)
    "tt0121220": ["tt0214341"],
    "tt0214341": ["tt0121220"],
    # Dragon Ball (1986: tt0133290 <-> 1995: tt0214340)
    "tt0133290": ["tt0214340"],
    "tt0214340": ["tt0133290"],
    # Dragon Ball GT (1996: tt0140739 <-> 2003: tt0280249)
    "tt0140739": ["tt0280249"],
    "tt0280249": ["tt0140739"],
    # Sailor Moon (1992: tt0103533 <-> 1995: tt0214361)
    "tt0103533": ["tt0214361"],
    "tt0214361": ["tt0103533"],
    # Pokémon (Pocket Monsters 1997: tt0168366 <-> Indigo League 1998: tt0176385)
    "tt0168366": ["tt0176385"],
    "tt0176385": ["tt0168366"],
    # Yu-Gi-Oh! (Duel Monsters 2000: tt0283732 <-> English 2001: tt0286386)
    "tt0283732": ["tt0286386"],
    "tt0286386": ["tt0283732"],
    # Digimon Adventure (1999: tt0210423 <-> English: tt0227907)
    "tt0210423": ["tt0227907"],
    "tt0227907": ["tt0210423"],
    # Shaman King (2001: tt0366085 <-> 2003: tt0380131)
    "tt0366085": ["tt0380131"],
    "tt0380131": ["tt0366085"],
    # Rurouni Kenshin (1996: tt0115341 <-> 2000 Samurai X: tt0348924)
    "tt0115341": ["tt0348924"],
    "tt0348924": ["tt0115341"],
    # Naruto (2002: tt0409591 <-> 2005 angol/nemzetközi: tt0371408)
    "tt0409591": ["tt0371408"],
    "tt0371408": ["tt0409591"],
    # Bleach (2004: tt0434665 <-> 2006 angol/nemzetközi: tt0831290)
    "tt0434665": ["tt0831290"],
    "tt0831290": ["tt0434665"],
    # Death Note (2006: tt0877057 <-> 2007 angol/nemzetközi: tt1049513)
    "tt0877057": ["tt1049513"],
    "tt1049513": ["tt0877057"],
}


class TvdbResolver:
    def __init__(self):
        self._cache: dict[str, str | tuple | list | None] = {}
        # Teljes sorozat szintű gyorsítótár: imdb_id -> {(season, episode): (alt_eps, alt_seasons)}
        self._series_epmap: dict[str, dict[tuple[int, int], tuple[list[int], list[int]]]] = {}
        # Cinemeta kumulatív évad-epizódszám gyorsítótár: imdb_id -> {season: episode_count}
        self._cinemeta_counts: dict[str, dict[int, int]] = {}
        self._animation_ids: set[str] = set()
        self._lock = KeyedLock()
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed is True:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
            self._client = httpx.AsyncClient(
                timeout=8.0,
                follow_redirects=True,
                limits=limits,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StremHU/1.0",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def aclose(self) -> None:
        try:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
        finally:
            self._client = None
            self._cache.clear()
            self._series_epmap.clear()
            self._cinemeta_counts.clear()
            self._animation_ids.clear()

    def _set_cache(self, key: str, value: str | tuple | list | None) -> None:
        if len(self._cache) >= _MAX_CACHE_ENTRIES:
            # Régi bejegyzések törlése (egyszerű memóriavédelem hetekig tartó futás esetére)
            keys_to_remove = list(self._cache.keys())[:1000]
            for k in keys_to_remove:
                self._cache.pop(k, None)
        self._cache[key] = value

    async def resolve_tvdb(
        self, tvdb_id: str, is_series: bool = True
    ) -> tuple[str | None, str | None]:
        """
        TVDB azonosító feloldása (imdb_id, title) párra kulcs nélkül vagy TMDB kulccsal.
        1. TVMaze API (sorozatokhoz, kulcs nélkül, visszaadja az IMDb ID-t és a címet)
        2. Wikidata SPARQL API (kulcs nélkül, P4835 sorozathoz, P12196 filmhez)
        3. TMDB API (ha van beállítva TMDB API kulcs)
        """
        if not tvdb_id:
            return None, None

        clean_id = validate_numeric_media_id(tvdb_id)
        cache_key = f"tvdb_{clean_id}_{is_series}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, tuple):
                return cached

        async with self._lock(cache_key):
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if isinstance(cached, tuple):
                    return cached

            # 1. Próbálkozás: TVMaze API (ingyenes, nem igényel API kulcsot, adja a címet és IMDb ID-t)
            if is_series:
                tvmaze_res = await self._resolve_from_tvmaze_full(clean_id)
                if tvmaze_res[0] or tvmaze_res[1]:
                    self._set_cache(cache_key, tvmaze_res)
                    if tvmaze_res[0] and tvmaze_res[1]:
                        self._set_cache(f"title_{tvmaze_res[0]}", tvmaze_res[1])
                    return tvmaze_res

            # 2. Próbálkozás: Wikidata SPARQL API (ingyenes, pontos IMDb ID + hu/en cím)
            try:
                prop = "P4835" if is_series else "P12196"
                sparql = (
                    f"SELECT ?imdb ?labelHu ?labelEn WHERE {{ "
                    f'{{ ?item wdt:{prop} "{clean_id}". }} '
                    f"OPTIONAL {{ ?item wdt:P345 ?imdb. }} "
                    f'OPTIONAL {{ ?item rdfs:label ?labelHu FILTER(LANG(?labelHu)="hu") }} '
                    f'OPTIONAL {{ ?item rdfs:label ?labelEn FILTER(LANG(?labelEn)="en") }} '
                    f"}} LIMIT 1"
                )
                sparql_url = f"https://query.wikidata.org/sparql?format=json&query={quote(sparql)}"
                client = self._get_client()
                wiki_resp = await client.get(
                    sparql_url,
                    headers={
                        "User-Agent": "StremHUSource/1.0 (https://github.com/s4pp1/stremhu-source; admin@stremhu.local) httpx/0.28.1",
                        "Accept": "application/json",
                    },
                    timeout=5.0,
                )
                if wiki_resp.status_code == 200:
                    wiki_data = wiki_resp.json()
                    bindings = wiki_data.get("results", {}).get("bindings", [])
                    if bindings:
                        row = bindings[0]
                        w_imdb = row.get("imdb", {}).get("value")
                        w_label_hu = row.get("labelHu", {}).get("value")
                        w_label_en = row.get("labelEn", {}).get("value")
                        found_imdb = (
                            w_imdb
                            if isinstance(w_imdb, str) and w_imdb.startswith("tt")
                            else None
                        )
                        raw_title = w_label_hu or w_label_en
                        found_title = html.unescape(raw_title) if raw_title else None
                        if found_imdb or found_title:
                            res = (found_imdb, found_title)
                            self._set_cache(cache_key, res)
                            if found_imdb and found_title:
                                self._set_cache(f"title_{found_imdb}", found_title)
                            return res
            except Exception as e:
                logger.debug(f"[TvdbResolver] Wikidata SPARQL hiba TVDB-re ({clean_id}): {network_error_fields(e)}")

            # 3. Próbálkozás: TMDB API (ha van beállítva TMDB API kulcs)
            if config.tmdb_api_key:
                imdb_id = await self._resolve_from_tmdb(clean_id)
                if imdb_id:
                    res = (imdb_id, None)
                    self._set_cache(cache_key, res)
                    return res

            return None, None

    async def resolve_tvdb_to_imdb(self, tvdb_id: str) -> str | None:
        """
        TVDB azonosító feloldása IMDb (tt...) azonosítóra (kompatibilitási wrapper).
        """
        if not tvdb_id:
            return None
        clean_id = validate_numeric_media_id(tvdb_id)
        if clean_id in self._cache:
            val = self._cache[clean_id]
            if isinstance(val, str):
                return val
        imdb_id, _ = await self.resolve_tvdb(tvdb_id, is_series=True)
        if imdb_id:
            self._set_cache(clean_id, imdb_id)
        return imdb_id

    async def _resolve_from_tvmaze_full(
        self, tvdb_id: str
    ) -> tuple[str | None, str | None]:
        url = f"https://api.tvmaze.com/lookup/shows?thetvdb={tvdb_id}"
        client = self._get_client()
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                externals = data.get("externals", {})
                imdb = externals.get("imdb")
                name = data.get("name")
                clean_imdb = (
                    imdb if isinstance(imdb, str) and imdb.startswith("tt") else None
                )
                clean_title = str(name).strip() if name else None
                if clean_imdb or clean_title:
                    logger.info(
                        f"[TvdbResolver] TVDB {tvdb_id} feloldva: IMDb={clean_imdb}, Cím={clean_title} (TVMaze)"
                    )
                    return clean_imdb, clean_title
        except Exception as e:
            logger.debug(f"[TvdbResolver] TVMaze feloldási hiba ({tvdb_id}): {network_error_fields(e)}")

        return None, None

    async def _resolve_from_tvmaze(self, tvdb_id: str) -> str | None:
        url = f"https://api.tvmaze.com/lookup/shows?thetvdb={tvdb_id}"
        client = self._get_client()
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                externals = data.get("externals", {})
                imdb = externals.get("imdb")
                if imdb and isinstance(imdb, str) and imdb.startswith("tt"):
                    logger.info(
                        f"[TvdbResolver] TVDB {tvdb_id} sikeresen feloldva IMDb-re: {imdb} (TVMaze)"
                    )
                    return imdb
        except Exception as e:
            logger.debug(f"[TvdbResolver] TVMaze feloldási hiba ({tvdb_id}): {network_error_fields(e)}")

        return None

    async def _resolve_from_tmdb(self, tvdb_id: str) -> str | None:
        if not config.tmdb_api_key:
            return None

        client = self._get_client()
        find_url = (
            f"https://api.themoviedb.org/3/find/{tvdb_id}"
            f"?api_key={config.tmdb_api_key}&external_source=tvdb_id"
        )
        try:
            response = await client.get(find_url)
            if response.status_code == 200:
                data = response.json()
                tv_results = data.get("tv_results", [])
                if tv_results:
                    tmdb_id = tv_results[0].get("id")
                    ext_url = (
                        f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids"
                        f"?api_key={config.tmdb_api_key}"
                    )
                    ext_resp = await client.get(ext_url)
                    if ext_resp.status_code == 200:
                        imdb = ext_resp.json().get("imdb_id")
                        if imdb and isinstance(imdb, str) and imdb.startswith("tt"):
                            logger.info(
                                f"[TvdbResolver] TVDB {tvdb_id} feloldva IMDb-re: {imdb} (TMDB)"
                            )
                            return imdb

                movie_results = data.get("movie_results", [])
                if movie_results:
                    tmdb_id = movie_results[0].get("id")
                    ext_url = (
                        f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids"
                        f"?api_key={config.tmdb_api_key}"
                    )
                    ext_resp = await client.get(ext_url)
                    if ext_resp.status_code == 200:
                        imdb = ext_resp.json().get("imdb_id")
                        if imdb and isinstance(imdb, str) and imdb.startswith("tt"):
                            logger.info(
                                f"[TvdbResolver] TVDB {tvdb_id} feloldva IMDb-re: {imdb} (TMDB)"
                            )
                            return imdb
        except Exception as e:
            logger.debug(f"[TvdbResolver] TMDB feloldási hiba ({tvdb_id}): {network_error_fields(e)}")

        return None

    async def resolve_kitsu(
        self, kitsu_id: str | int, episode: int | None = None
    ) -> tuple[str | None, int | None, int | None, list[int], list[int], str | None]:
        """
        Kitsu azonosító feloldása IMDb azonosítóra, évad/epizód számra, valamint címre.
        """
        if not kitsu_id:
            return None, None, None, [], [], None

        clean_id = validate_numeric_media_id(str(kitsu_id))
        cache_key = f"kitsu_{clean_id}_{episode}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, tuple) and len(cached) == 6:
                return cached

        async with self._lock(cache_key):
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if isinstance(cached, tuple) and len(cached) == 6:
                    return cached

            # 1. Próbálkozás: Anime Kitsu (strem.fun) - pontos IMDb ID és évad/epizód leképzés
            res = await self._resolve_from_anime_kitsu(clean_id, episode)
            if res[0]:
                self._set_cache(cache_key, res)
                return res

            # 2. Próbálkozás: Kitsu API -> TVMaze
            res2 = await self._resolve_from_kitsu_tvmaze(clean_id, episode)
            if res2[0] or res2[5]:
                self._set_cache(cache_key, res2)
                return res2

            logger.warning(
                f"[TvdbResolver] Nem sikerült IMDb azonosítót vagy címet találni a Kitsu ID-hoz: {clean_id}"
            )
            return None, None, None, [], [], None

    async def resolve_kitsu_to_imdb(
        self, kitsu_id: str | int, episode: int | None = None
    ) -> tuple[Any, ...]:
        """
        Kompatibilitási wrapper az 5 vagy 3 elemű visszatérési értéket váró hívóknak.
        """
        clean_id = validate_numeric_media_id(str(kitsu_id)) if kitsu_id else ""
        cache_key = f"kitsu_{clean_id}_{episode}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, tuple):
                if len(cached) in (3, 5):
                    return cached
                if len(cached) == 6:
                    return cached[0], cached[1], cached[2], cached[3], cached[4]
        res = await self.resolve_kitsu(kitsu_id, episode)
        return res[0], res[1], res[2], res[3], res[4]

    async def _resolve_from_anime_kitsu(
        self, kitsu_id: str, episode: int | None
    ) -> tuple[str | None, int | None, int | None, list[int], list[int], str | None]:
        client = self._get_client()
        for endpoint in [
            f"https://anime-kitsu.strem.fun/meta/series/kitsu:{kitsu_id}.json",
            f"https://anime-kitsu.strem.fun/meta/anime/kitsu:{kitsu_id}.json",
        ]:
            try:
                resp = await client.get(endpoint)
                if resp.status_code == 200:
                    data = resp.json()
                    meta = data.get("meta", {})
                    imdb_id = meta.get("imdb_id")
                    anime_name = meta.get("name")
                    if imdb_id and isinstance(imdb_id, str) and imdb_id.startswith("tt"):
                        season = 1
                        ep = episode
                        alt_eps: list[int] = []
                        alt_seasons: list[int] = []
                        if episode is not None:
                            videos = meta.get("videos", [])
                            for v in videos:
                                if v.get("episode") == episode or str(v.get("id", "")).endswith(f":{episode}"):
                                    season = v.get("imdbSeason") or v.get("season") or 1
                                    ep = v.get("imdbEpisode") or v.get("episode") or episode
                                    abs_ep = v.get("absoluteEpisode")
                                    if abs_ep and abs_ep != ep and abs_ep not in alt_eps:
                                        alt_eps.append(abs_ep)
                                    if episode and episode != ep and episode not in alt_eps:
                                        alt_eps.append(episode)
                                    v_s = v.get("season")
                                    if v_s and v_s != season and v_s not in alt_seasons:
                                        if not (v_s == 1 and season > 1):
                                            alt_seasons.append(v_s)
                                    break
                        logger.info(
                            f"[TvdbResolver] Kitsu {kitsu_id} feloldva: {imdb_id} S{season}E{ep} alt_eps={alt_eps} (Anime-Kitsu)"
                        )
                        return imdb_id, season, ep, alt_eps, alt_seasons, anime_name
            except Exception as e:
                logger.debug(f"[TvdbResolver] Anime-Kitsu hiba ({kitsu_id}): {network_error_fields(e)}")

        return None, None, None, [], [], None

    async def _resolve_from_kitsu_tvmaze(
        self, kitsu_id: str, episode: int | None
    ) -> tuple[str | None, int | None, int | None, list[int], list[int], str | None]:
        url = f"https://kitsu.io/api/edge/anime/{kitsu_id}"
        client = self._get_client()
        try:
            resp = await client.get(url, headers={"Accept": "application/vnd.api+json"})
            if resp.status_code == 200:
                data = resp.json()
                attr = data.get("data", {}).get("attributes", {})
                canonical = attr.get("canonicalTitle")
                candidates = [
                    canonical,
                    attr.get("titles", {}).get("en"),
                    attr.get("titles", {}).get("en_jp"),
                ]
                for c in list(candidates):
                    if c and ":" in c:
                        candidates.append(c.split(":")[0].strip())

                # Duplikációk szűrése sorrendmegőrzéssel
                unique_candidates = list(dict.fromkeys(filter(None, candidates)))

                for title in unique_candidates:
                    tvmaze_url = f"https://api.tvmaze.com/singlesearch/shows?q={title}"
                    try:
                        tvmaze_resp = await client.get(tvmaze_url)
                        if tvmaze_resp.status_code == 200:
                            tvmaze_data = tvmaze_resp.json()
                            imdb = tvmaze_data.get("externals", {}).get("imdb")
                            if imdb and isinstance(imdb, str) and imdb.startswith("tt"):
                                logger.info(
                                    f"[TvdbResolver] Kitsu {kitsu_id} ({title}) feloldva IMDb-re: {imdb} (TVMaze)"
                                )
                                return imdb, 1, episode, [], [], canonical or title
                    except Exception:
                        continue

                # Ha nem találtunk IMDb ID-t, a canonicalTitle mentőövként szolgál a szöveges kereséshez
                if canonical:
                    logger.info(
                        f"[TvdbResolver] Kitsu {kitsu_id} cím kinyerve (IMDb nélkül): '{canonical}'"
                    )
                    return None, 1, episode, [], [], canonical
        except Exception as e:
            logger.debug(f"[TvdbResolver] Kitsu TVMaze feloldási hiba ({kitsu_id}): {network_error_fields(e)}")

        return None, None, None, [], [], None

    async def resolve_mal(
        self, mal_id: str, episode: int | None = None
    ) -> tuple[str | None, int | None, int | None, list[int], list[int], str | None]:
        """
        MyAnimeList azonosító feloldása (imdb_id, season, episode, alt_eps, alt_seasons, title).
        1. Kitsu Mapping API: /mappings?filter[external_site]=myanimelist/anime&filter[external_id]={mal_id}
           -> Kitsu ID kinyerése és delegálás a resolve_kitsu-nak (így teljes TVDB/Cinemeta leképzés jár hozzá!)
        2. Wikidata SPARQL API (P4086 MyAnimeList ID) -> IMDb ID (P345) és hu/en cím
        """
        if not mal_id:
            return None, None, None, [], [], None

        clean_id = validate_numeric_media_id(mal_id)
        cache_key = f"mal_{clean_id}_{episode}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, tuple) and len(cached) == 6:
                return cached

        async with self._lock(cache_key):
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if isinstance(cached, tuple) and len(cached) == 6:
                    return cached

            # 1. Próbálkozás: Kitsu Mapping API (MyAnimeList -> Kitsu -> IMDb + pontos évad/epizód leképezés!)
            try:
                kitsu_map_url = (
                    f"https://kitsu.io/api/edge/mappings?"
                    f"filter[external_site]=myanimelist/anime&filter[external_id]={clean_id}&include=item"
                )
                client = self._get_client()
                resp = await client.get(
                    kitsu_map_url,
                    headers={"Accept": "application/vnd.api+json"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    included = data.get("included", [])
                    kitsu_id = None
                    for item in included:
                        if item.get("type") == "anime":
                            kitsu_id = str(item.get("id"))
                            break
                    if not kitsu_id:
                        data_items = data.get("data", [])
                        if data_items:
                            rel = (
                                data_items[0]
                                .get("relationships", {})
                                .get("item", {})
                                .get("data", {})
                            )
                            if rel.get("type") == "anime":
                                kitsu_id = str(rel.get("id"))

                    if kitsu_id:
                        kitsu_res = await self.resolve_kitsu(kitsu_id, episode)
                        if kitsu_res[0] or kitsu_res[5]:
                            self._set_cache(cache_key, kitsu_res)
                            return kitsu_res
            except Exception as e:
                logger.debug(f"[TvdbResolver] Kitsu MAL mapping hiba ({clean_id}): {network_error_fields(e)}")

            # 2. Próbálkozás: Wikidata SPARQL API (P4086 MyAnimeList ID)
            try:
                sparql = (
                    f"SELECT ?imdb ?labelHu ?labelEn WHERE {{ "
                    f'?item wdt:P4086 "{clean_id}". '
                    f"OPTIONAL {{ ?item wdt:P345 ?imdb. }} "
                    f'OPTIONAL {{ ?item rdfs:label ?labelHu FILTER(LANG(?labelHu)="hu") }} '
                    f'OPTIONAL {{ ?item rdfs:label ?labelEn FILTER(LANG(?labelEn)="en") }} '
                    f"}} LIMIT 1"
                )
                sparql_url = f"https://query.wikidata.org/sparql?format=json&query={quote(sparql)}"
                client = self._get_client()
                wiki_resp = await client.get(
                    sparql_url,
                    headers={
                        "User-Agent": "StremHUSource/1.0 (https://github.com/s4pp1/stremhu-source; admin@stremhu.local) httpx/0.28.1",
                        "Accept": "application/json",
                    },
                    timeout=5.0,
                )
                if wiki_resp.status_code == 200:
                    wiki_data = wiki_resp.json()
                    bindings = wiki_data.get("results", {}).get("bindings", [])
                    if bindings:
                        row = bindings[0]
                        w_imdb = row.get("imdb", {}).get("value")
                        w_label_hu = row.get("labelHu", {}).get("value")
                        w_label_en = row.get("labelEn", {}).get("value")
                        found_imdb = (
                            w_imdb
                            if isinstance(w_imdb, str) and w_imdb.startswith("tt")
                            else None
                        )
                        raw_title = w_label_hu or w_label_en
                        found_title = html.unescape(raw_title) if raw_title else None
                        if found_imdb or found_title:
                            res = (found_imdb, 1, episode, [], [], found_title)
                            self._set_cache(cache_key, res)
                            if found_imdb and found_title:
                                self._set_cache(f"title_{found_imdb}", found_title)
                            return res
            except Exception as e:
                logger.debug(f"[TvdbResolver] Wikidata SPARQL hiba MAL-ra ({clean_id}): {network_error_fields(e)}")

            return None, None, None, [], [], None

    async def get_title_by_imdb(
        self, imdb_id: str, is_series: bool | None = None
    ) -> str | None:
        """Lekéri a média címét IMDb ID alapján Cinemeta API-n keresztül (másodlagos kereséshez)."""
        if not imdb_id:
            return None
        if not imdb_id.startswith("tt"):
            # Ha nem 'tt' azonosító (pl. közvetlenül átadott cím vagy slug), használjuk címként
            return imdb_id
        cache_key = f"title_{imdb_id}"
        if cache_key in self._cache:
            val = self._cache[cache_key]
            return val if isinstance(val, str) else None

        client = self._get_client()
        if is_series is False:
            c_types = ["movie", "series"]
        elif is_series is True:
            c_types = ["series", "movie"]
        else:
            c_types = ["series", "movie"]

        for c_type in c_types:
            url = f"https://v3-cinemeta.strem.io/meta/{c_type}/{imdb_id}.json"
            try:
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    name = data.get("meta", {}).get("name")
                    if name:
                        self._set_cache(cache_key, name)
                        return name
            except Exception:
                pass
        return None

    async def resolve_tmdb(
        self, tmdb_id: str, is_series: bool = False
    ) -> tuple[str | None, str | None]:
        """
        TMDB azonosító feloldása (imdb_id, title) párra.
        Amennyiben elérhető IMDb ID, azt adja vissza. Ha nincs IMDb ID (pl. hazai reality / magyar műsorok),
        akkor a cím alapján történő másodlagos kereséshez biztosítja a címet.
        """
        if not tmdb_id:
            return None, None

        clean_id = validate_numeric_media_id(tmdb_id)
        cache_key = f"tmdb_{clean_id}_{is_series}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, tuple):
                return cached

        async with self._lock(cache_key):
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if isinstance(cached, tuple):
                    return cached

            # 1. Próbálkozás: TMDB API, ha be van állítva API kulcs
            if config.tmdb_api_key:
                endpoints = (
                    [
                        (
                            "tv",
                            f"https://api.themoviedb.org/3/tv/{clean_id}?api_key={config.tmdb_api_key}&append_to_response=external_ids&language=hu-HU",
                        ),
                        (
                            "movie",
                            f"https://api.themoviedb.org/3/movie/{clean_id}?api_key={config.tmdb_api_key}&append_to_response=external_ids&language=hu-HU",
                        ),
                    ]
                    if is_series
                    else [
                        (
                            "movie",
                            f"https://api.themoviedb.org/3/movie/{clean_id}?api_key={config.tmdb_api_key}&append_to_response=external_ids&language=hu-HU",
                        ),
                        (
                            "tv",
                            f"https://api.themoviedb.org/3/tv/{clean_id}?api_key={config.tmdb_api_key}&append_to_response=external_ids&language=hu-HU",
                        ),
                    ]
                )
                client = self._get_client()
                for _, url in endpoints:
                    try:
                        resp = await client.get(url, timeout=5.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            ext_imdb = data.get("external_ids", {}).get("imdb_id")
                            ext_imdb_clean = (
                                ext_imdb
                                if isinstance(ext_imdb, str) and ext_imdb.startswith("tt")
                                else None
                            )
                            title = (
                                data.get("name")
                                or data.get("title")
                                or data.get("original_name")
                                or data.get("original_title")
                            )
                            if ext_imdb_clean or title:
                                res = (ext_imdb_clean, str(title) if title else None)
                                self._set_cache(cache_key, res)
                                if ext_imdb_clean and title:
                                    self._set_cache(f"title_{ext_imdb_clean}", str(title))
                                return res
                    except Exception as e:
                        logger.debug(f"[TvdbResolver] TMDB API hiba ({clean_id}): {network_error_fields(e)}")

            # 2. Próbálkozás: Wikidata SPARQL API (ingyenes, gyors, pontos IMDb ID + hu/en cím)
            # Mind a film (P4947), mind a sorozat (P4983) azonosítót ellenőrizzük UNION-nal,
            # így az anime OVA-k, minisorozatok vagy kategória-eltérések is hibátlanul feloldódnak.
            try:
                prop_filter = (
                    f'{{ ?item wdt:P4983 "{clean_id}". }} UNION '
                    f'{{ ?item wdt:P4947 "{clean_id}". }}'
                )

                sparql = (
                    f"SELECT ?imdb ?labelHu ?labelEn WHERE {{ "
                    f"{prop_filter} "
                    f"OPTIONAL {{ ?item wdt:P345 ?imdb. }} "
                    f'OPTIONAL {{ ?item rdfs:label ?labelHu FILTER(LANG(?labelHu)="hu") }} '
                    f'OPTIONAL {{ ?item rdfs:label ?labelEn FILTER(LANG(?labelEn)="en") }} '
                    f"}} LIMIT 1"
                )
                sparql_url = f"https://query.wikidata.org/sparql?format=json&query={quote(sparql)}"
                client = self._get_client()
                wiki_resp = await client.get(
                    sparql_url,
                    headers={
                        "User-Agent": "StremHUSource/1.0 (https://github.com/s4pp1/stremhu-source; admin@stremhu.local) httpx/0.28.1",
                        "Accept": "application/json",
                    },
                    timeout=5.0,
                )
                if wiki_resp.status_code == 200:
                    wiki_data = wiki_resp.json()
                    bindings = wiki_data.get("results", {}).get("bindings", [])
                    if bindings:
                        row = bindings[0]
                        w_imdb = row.get("imdb", {}).get("value")
                        w_label_hu = row.get("labelHu", {}).get("value")
                        w_label_en = row.get("labelEn", {}).get("value")
                        found_imdb = (
                            w_imdb
                            if isinstance(w_imdb, str) and w_imdb.startswith("tt")
                            else None
                        )
                        raw_title = w_label_hu or w_label_en
                        found_title = html.unescape(raw_title) if raw_title else None
                        if found_imdb or found_title:
                            res = (found_imdb, found_title)
                            self._set_cache(cache_key, res)
                            if found_imdb and found_title:
                                self._set_cache(f"title_{found_imdb}", found_title)
                            return res
            except Exception as e:
                logger.debug(f"[TvdbResolver] Wikidata SPARQL hiba ({clean_id}): {network_error_fields(e)}")

            # 3. Próbálkozás: Publikus TMDB oldal lekérése és elemzése (curl UA-val Cloudflare védelem kikerüléséhez)
            client = self._get_client()
            url_types = ["tv", "movie"] if is_series else ["movie", "tv"]
            for u_type in url_types:
                url = f"https://www.themoviedb.org/{u_type}/{clean_id}"
                try:
                    resp = await client.get(
                        url,
                        headers={
                            "User-Agent": "curl/8.5.0",
                            "Accept": "text/html,*/*",
                            "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
                        },
                        timeout=5.0,
                    )
                    if resp.status_code == 200:
                        text = resp.text
                        imdb_match = re.search(
                            r'href=["\']https?://(?:www\.)?imdb\.com/title/(tt\d+)', text
                        )
                        found_imdb = imdb_match.group(1) if imdb_match else None

                        og_match = re.search(
                            r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
                            text,
                            re.I,
                        )
                        found_title = None
                        if og_match:
                            found_title = og_match.group(1).strip()
                        else:
                            title_tag = re.search(r"<title>(.*?)<\/title>", text, re.I)
                            if title_tag:
                                clean_t = (
                                    title_tag.group(1)
                                    .split("—")[0]
                                    .split("&#8212;")[0]
                                    .strip()
                                )
                                clean_t = re.sub(r"\s*\([^)]*\)$", "", clean_t).strip()
                                if clean_t:
                                    found_title = clean_t

                        orig_m = re.search(
                            r"(?:Eredeti\s+cím|Eredeti\s+név|Original\s+Title|Original\s+Name)\s*</strong>\s*([^<]+)</p>",
                            text,
                            re.I,
                        )
                        orig_title = orig_m.group(1).strip() if orig_m else None
                        raw_chosen = found_title or orig_title
                        chosen_title = html.unescape(raw_chosen) if raw_chosen else None

                        if found_imdb or chosen_title:
                            res = (found_imdb, chosen_title)
                            self._set_cache(cache_key, res)
                            if found_imdb and chosen_title:
                                self._set_cache(f"title_{found_imdb}", chosen_title)
                            return res
                except Exception as e:
                    logger.debug(
                        f"[TvdbResolver] TMDB web scraping hiba ({clean_id}, {u_type}): {network_error_fields(e)}"
                    )

            # Ne mérgezzük a gyorsítótárat sikertelen hálózati kérés esetén
            return (None, None)

    async def get_episode_mappings(
        self,
        imdb_id: str,
        season: int,
        episode: int,
    ) -> tuple[list[int], list[int]]:
        """
        Dinamikusan lekéri egy adott (imdb_id, season, episode) alternatív epizódszámait
        és évadait Anime-Kitsu és Cinemeta metaadatokból.
        A letöltött metaadatokat sorozat-szinten indexeli és gyorsítótárazza, így a későbbi
        epizódok lekérése hálózati forgalom nélkül, azonnal történik.
        """
        if not imdb_id or not imdb_id.startswith("tt"):
            return [], []

        cache_key = f"epmap_{imdb_id}_{season}_{episode}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, tuple):
                return cached

        # 0. Sorozat-szintű in-memory gyorsítótár ellenőrzése
        if imdb_id in self._series_epmap:
            series_map = self._series_epmap[imdb_id]
            if (season, episode) in series_map:
                res = series_map[(season, episode)]
                self._set_cache(cache_key, res)
                return res

        alt_eps: set[int] = set()
        alt_seasons: set[int] = set()

        client = self._get_client()

        # Ha az azonosító ismert anime az _IMDB_ALIASES szótárban, akkor az Anime-Kitsu az elsődleges forrás
        is_known_anime = imdb_id in _IMDB_ALIASES

        if is_known_anime:
            # 1. Anime Kitsu API az IMDb ID vagy ismert aliasok alapján
            candidate_imdb_ids = [imdb_id]
            for alt in _IMDB_ALIASES[imdb_id]:
                if alt not in candidate_imdb_ids:
                    candidate_imdb_ids.append(alt)

            for c_imdb in candidate_imdb_ids:
                if c_imdb in self._series_epmap:
                    if (season, episode) in self._series_epmap[c_imdb]:
                        res = self._series_epmap[c_imdb][(season, episode)]
                        self._set_cache(cache_key, res)
                        return res

                kitsu_url = f"https://anime-kitsu.strem.fun/meta/series/{c_imdb}.json"
                try:
                    resp = await client.get(kitsu_url, timeout=6.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        meta = data.get("meta", {})
                        if meta.get("name"):
                            self._set_cache(f"title_{c_imdb}", meta["name"])
                        self._set_cache(f"alt_imdb_{c_imdb}", [])
                        videos = meta.get("videos", [])

                        if c_imdb not in self._series_epmap:
                            if len(self._series_epmap) >= _MAX_SERIES_CACHE:
                                for old_k in list(self._series_epmap.keys())[:200]:
                                    self._series_epmap.pop(old_k, None)
                            self._series_epmap[c_imdb] = {}

                        for v in videos:
                            v_s = v.get("imdbSeason") or v.get("season")
                            v_e = v.get("imdbEpisode") or v.get("episode")
                            v_abs = v.get("absoluteEpisode") or v.get("kitsuEpisode")

                            if v_s is not None and v_e is not None:
                                entry_alt_eps: set[int] = set()
                                entry_alt_seasons: set[int] = set()
                                if v_abs and v_abs != v_e:
                                    entry_alt_eps.add(v_abs)
                                k_ep = v.get("kitsuEpisode")
                                if k_ep and k_ep != v_e:
                                    entry_alt_eps.add(k_ep)
                                if v_s == 1 and v_e > 20 and v_abs == v_e:
                                    orig_s = v.get("season")
                                    if orig_s and orig_s != 1:
                                        entry_alt_seasons.add(orig_s)

                                existing = self._series_epmap[c_imdb].get((v_s, v_e), ([], []))
                                merged_eps = sorted(list(set(existing[0]) | entry_alt_eps))
                                merged_seasons = sorted(list(set(existing[1]) | entry_alt_seasons))
                                self._series_epmap[c_imdb][(v_s, v_e)] = (merged_eps, merged_seasons)

                        if (season, episode) in self._series_epmap[c_imdb]:
                            res = self._series_epmap[c_imdb][(season, episode)]
                            if res[0] or res[1]:
                                self._set_cache(cache_key, res)
                                return res
                except Exception as e:
                    logger.debug(f"[TvdbResolver] Anime Kitsu epmap lekérési hiba ({c_imdb}): {network_error_fields(e)}")

        # 2. Cinemeta kumulatív számítás (nyugati sorozatoknál azonnal ez fut le 404-es Kitsu probe nélkül!)
        is_animation = imdb_id in self._animation_ids
        s_counts = self._cinemeta_counts.get(imdb_id)
        if s_counts is None:
            cinemeta_url = f"https://v3-cinemeta.strem.io/meta/series/{imdb_id}.json"
            try:
                resp = await client.get(cinemeta_url, timeout=6.0)
                if resp.status_code == 200:
                    data = resp.json()
                    meta = data.get("meta", {})
                    if meta.get("name"):
                        self._set_cache(f"title_{imdb_id}", meta["name"])
                    genres = [str(g).lower() for g in (meta.get("genres") or [])]
                    is_animation = "anime" in genres or "animation" in genres
                    if is_animation:
                        self._animation_ids.add(imdb_id)
                    else:
                        self._animation_ids.discard(imdb_id)
                    if genres and not is_animation:
                        # Élőszereplős sorozat esetén azonnal negatív gyorsítótárazzuk a Kitsu alias keresést
                        self._set_cache(f"alt_imdb_{imdb_id}", [])
                    vids = [
                        v for v in meta.get("videos", [])
                        if v.get("season", 0) > 0
                    ]
                    s_counts = defaultdict(int)
                    for v in vids:
                        s_counts[v.get("season")] += 1
                    if len(self._cinemeta_counts) >= _MAX_SERIES_CACHE:
                        for old_k in list(self._cinemeta_counts.keys())[:200]:
                            self._cinemeta_counts.pop(old_k, None)
                            self._animation_ids.discard(old_k)
                    self._cinemeta_counts[imdb_id] = s_counts
            except Exception as e:
                logger.debug(f"[TvdbResolver] Cinemeta epmap lekérési hiba ({imdb_id}): {network_error_fields(e)}")

        if s_counts and len(s_counts) > 1:
            if season in s_counts:
                cum = sum(s_counts[s] for s in range(1, season))
                calc_abs = cum + episode
                if calc_abs != episode:
                    alt_eps.add(calc_abs)
            elif season == 1 and episode > 20:
                cum = 0
                for s_num in sorted(s_counts.keys()):
                    if cum < episode <= cum + s_counts[s_num]:
                        alt_seasons.add(s_num)
                        alt_eps.add(episode - cum)
                        break
                    cum += s_counts[s_num]

        # 3. Ha nem volt ismert anime, de a Cinemeta szerint animáció (és a Cinemeta nem adott eredményt),
        # pótlólagosan megpróbáljuk az Anime-Kitsu lekérdezést
        if not is_known_anime and is_animation and not alt_eps:
            kitsu_url = f"https://anime-kitsu.strem.fun/meta/series/{imdb_id}.json"
            try:
                resp = await client.get(kitsu_url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    meta = data.get("meta", {})
                    videos = meta.get("videos", [])
                    for v in videos:
                        v_s = v.get("imdbSeason") or v.get("season")
                        v_e = v.get("imdbEpisode") or v.get("episode")
                        v_abs = v.get("absoluteEpisode") or v.get("kitsuEpisode")
                        if v_s == season and v_e == episode and v_abs and v_abs != episode:
                            alt_eps.add(v_abs)
            except Exception as e:
                logger.debug(f"[TvdbResolver] Fallback Anime Kitsu hiba ({imdb_id}): {network_error_fields(e)}")

        result = (sorted(list(alt_eps)), sorted(list(alt_seasons)))
        self._set_cache(cache_key, result)
        return result

    async def get_alternate_imdb_ids(
        self,
        imdb_id: str,
        is_series: bool | None = None,
        allow_dynamic_search: bool = False,
    ) -> list[str]:
        """
        Lekéri egy médium alternatív/iker IMDb azonosítóit (pl. anime nemzetközi vs japán IMDb bejegyzések).
        Először a statikus alias szótárból olvas, majd szükség esetén dinamikusan keres a Kitsu API-n keresztül.
        Ha allow_dynamic_search=False (alapértelmezett a stream kéréseknél), csak a statikus és a memóriában
        lévő aliasokat adja vissza külső hálózati késleltetés nélkül (0 ms).
        """
        if not imdb_id or not imdb_id.startswith("tt"):
            return []

        static_aliases = _IMDB_ALIASES.get(imdb_id, [])
        if static_aliases:
            return list(static_aliases)

        cache_key = f"alt_imdb_{imdb_id}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, list):
                return list(dict.fromkeys(static_aliases + cached))

        # Ha nincs engedélyezve a dinamikus külső hálózati keresés, vagy egyértelműen filmről van szó:
        if not allow_dynamic_search or is_series is False:
            return list(static_aliases)

        async with self._lock(cache_key):
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if isinstance(cached, list):
                    return list(dict.fromkeys(static_aliases + cached))

            dynamic_aliases: list[str] = []
            try:
                title = await self.get_title_by_imdb(imdb_id, is_series=is_series)
                if title:
                    cleaned_title = title.split(":")[0].strip()
                    client = self._get_client()
                    kitsu_search_url = (
                        f"https://kitsu.io/api/edge/anime?filter[text]={quote(cleaned_title)}"
                    )
                    resp = await client.get(
                        kitsu_search_url,
                        headers={"Accept": "application/vnd.api+json"},
                        timeout=5.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        anime_list = data.get("data", [])
                        if anime_list:
                            top_anime = anime_list[0]
                            attributes = top_anime.get("attributes", {})
                            canonical_title = (attributes.get("canonicalTitle") or "").strip().lower()
                            en_title = (attributes.get("titles", {}).get("en") or "").strip().lower()
                            en_jp_title = (attributes.get("titles", {}).get("en_jp") or "").strip().lower()

                            search_norm = cleaned_title.lower()
                            candidate_titles = {t for t in (canonical_title, en_title, en_jp_title) if t}
                            title_matches = any(
                                t == search_norm or t.startswith(search_norm + " ") or search_norm in t
                                for t in candidate_titles
                            )
                            # Kizárjuk a téves alcímeket (pl. "Inception" vs "Inception: The Cobol Job")
                            if search_norm and canonical_title and search_norm != canonical_title:
                                if canonical_title.startswith(f"{search_norm}:"):
                                    title_matches = False

                            top_kitsu_id = top_anime.get("id")
                            if top_kitsu_id and title_matches:
                                ak_url = f"https://anime-kitsu.strem.fun/meta/series/kitsu:{top_kitsu_id}.json"
                                ak_resp = await client.get(ak_url, timeout=5.0)
                                if ak_resp.status_code == 200:
                                    ak_meta = ak_resp.json().get("meta", {})
                                    discovered_imdb = ak_meta.get("imdb_id")
                                    if (
                                        discovered_imdb
                                        and isinstance(discovered_imdb, str)
                                        and discovered_imdb.startswith("tt")
                                        and discovered_imdb != imdb_id
                                        and discovered_imdb not in static_aliases
                                    ):
                                        dynamic_aliases.append(discovered_imdb)
            except Exception as e:
                logger.debug(
                    f"[TvdbResolver] Dinamikus IMDb alias keresési hiba ({imdb_id}): {network_error_fields(e)}"
                )

            self._set_cache(cache_key, dynamic_aliases)
            return list(dict.fromkeys(static_aliases + dynamic_aliases))



tvdb_resolver = TvdbResolver()
