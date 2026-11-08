---
doc_id: "feature-stremio-catalog-search"
title: "Fejlesztői Dokumentáció: feature/stremio-catalog-search"
kind: "feature-reference"
status: "historical-reference"
audience: ["developer", "ai-agent"]
tags: ["stremio", "catalog", "meta", "movie", "series", "search"]
source_commit: null
baseline: "8c99c7d"
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/feature/README.md", "docs/feature/search-filter-tmdb-tvdb.md"]
source_paths: ["server/app/modules/stremio/catalogs_service.py", "server/app/modules/torrent_source_provider/service.py"]
---

# Fejlesztői Dokumentáció: `feature/stremio-catalog-search`

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../README.md) · [AI-index](../AI-INDEX.md)

> **Státusz:** Korábbi feature technikai referenciája. A tartalom és a mérések nem kaptak most új runtime-verifikációt; aktuális működéshez kövesd a forráskódot.

**Kapcsolódó:** [README.md](README.md) · [search-filter-tmdb-tvdb.md](search-filter-tmdb-tvdb.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [1. A Branch Célja és Motivációja](#doc-1-a-branch-celja-es-motivacioja)
- [2. Módosított és Új Fájlok Áttekintése (Diff Mátrix s4pp1/stremhu-source vs feature/stremio-catalog-search)](#doc-2-modositott-es-uj-fajlok-attekintese-diff-matrix-s4pp1stremhu-source-vs-featurestremio-catalog-search)
- [3. Architektúra és Működési Folyamatábrák](#doc-3-architektura-es-mukodesi-folyamatabrak)
- [4. Tesztelési és Ellenőrzési Referencia](#doc-4-tesztelesi-es-ellenorzesi-referencia)

</details>

<!-- doc-nav:end -->

> **Viszonyítási alap (Baseline):** Eredeti upstream [`s4pp1/stremhu-source`](https://github.com/s4pp1/stremhu-source) (`8c99c7d` commit).
> Ez a dokumentum a `feature/stremio-catalog-search` branch által bevezetett közvetlen katalógus-keresési, kategória szerinti szétválasztási (Filmek vs Sorozatok), borítókép/IMDb integrációs és sorozat-epizódfelbontási fejlesztéseit részletezi.

---

<!-- doc-anchor:doc-1-a-branch-celja-es-motivacioja -->
<a id="doc-1-a-branch-celja-es-motivacioja"></a>
## 1. A Branch Célja és Motivációja

Az eredeti upstream `s4pp1/stremhu-source` két keresési katalógust regisztrál a Stremio manifestben:
- `🔍 Torrent - StremHU • Filmek` (`id="search"`, `type=ContentType.MOVIE`)
- `🔍 Torrent - StremHU • Sorozatok` (`id="search"`, `type=ContentType.SERIES`)

Azonban az upstream megvalósításban a `StremioCatalogsService.get_catalog` kódja **kizárólag** a konkrét numerikus torrent ID-s kereséseket engedélyezte (`t-<torrent_id>`):
```python
parts = extra.search.split("-", 1)
if len(parts) < 2 or parts[0] != "t":
    return StremioCatalogResponse(metas=[])  # ❌ Minden szöveges keresésre üres választ adott!
```

Ez a gyakorlatban azt jelentette, hogy:
1. Ha a felhasználó a Stremio felső keresősávjába beírta bármilyen film vagy sorozat címét (pl. *Lupin*, *A mi kis falunk*, *Inception*), a StremHU **nulla találatot** adott vissza a két sorában.
2. Csak akkor lehetett tartalmat lejátszani, ha a Stremio beépített Cinemeta (IMDb) katalógusában már létezett a műsor. Ha egy tartalom nem szerepelt az IMDb-n (pl. hazai vetélkedők, televíziós közvetítések), azt a Stremio felületéről egyáltalán nem lehetett elérni.
3. Sorozatok esetén hiányzott a torrenten belüli fájlok automatikus epizódlistává (`MetaVideo`) alakítása, így a Stremio UI nem tudott epizódválasztót renderelni közvetlen torrent metaadatokból.
4. **Kategória-keveredés és fekete kártyák:** A kezdeti közvetlen keresés mindkét katalógusban azonos listát adott vissza (filmeknél sorozatok, sorozatoknál filmek jelentek meg), és hiányoztak a poszterek.

<!-- doc-anchor:doc-a-megoldott-fejlesztesek -->
<a id="doc-a-megoldott-fejlesztesek"></a>
### A megoldott fejlesztések:
- **Közvetlen szabadszavas tracker keresés (`find_by_query`):** Bármilyen szöveges keresőkifejezésre azonnal lekéri a beállított indexerek (nCore, HunTorrent, stb.) találatait, seederek szerint csökkenő sorrendben.
- **Kategória szerinti szétválasztás (Filmek vs Sorozatok):**
  - **Filmek katalógus:** Kizárólag magyar és külföldi filmkategóriák (`xvid_hun`, `hd_hun`, `dvd_hun`, `hd`, stb.).
  - **Sorozatok katalógus:** Kizárólag magyar és külföldi sorozatkategóriák (`xvidser_hun`, `hdser_hun`, `dvdser_hun`, `hdser`, stb.).
  - **Kettős védelem (`SeriesParser`):** A katalógus szerviz tartalomelemzéssel kiszűri a sorozat-epizódokat a filmek közül, és az önálló filmeket a sorozatok közül.
- **Hivatalos borítóképek & IMDb pontszám:** Az indexerek által visszaadott `imdb_id` továbbításával a kártyák automatikusan megkapják a nagyfelbontású Metahub borítóképet (`https://images.metahub.space/poster/medium/{imdb_id}/img`) és az IMDb értékelést a sötét dobozok helyett.
- **Automatikus sorozat- és epizódfelbontás (`MetaDetail.videos`):** A sorozatkiadásokban és évadpakkokban lévő videofájlokat a `SeriesParser` segítségével automatikusan felbontja évadokra és epizódokra (`S04E01`, `S04E02`, stb.).
- **Fájlszintű közvetlen streaming (`file_index`):** A generált stream azonosító (`stremhu-source:{indexer_id}:{torrent_id}:{file_index}`) révén a Stremio epizódonként tudja elindítani a lejátszást évadcsomagokból is.
- **Felhasználónkénti beállítás és UI kapcsoló (`enable_catalog_search`):**
  - Ha a felhasználó nem szeretné, hogy a Stremio felső keresője a trackereket közvetlenül terhelje, a webes felületen (**Beállítások -> Preferenciák -> További preferenciák**) egyetlen kapcsolóval kikapcsolhatja.
  - A manifest (`/manifest.json`) a kapcsolótól függetlenül **mindig** hirdeti a `catalog` erőforrást és a két keresési katalógust. A Stremio és a Nuvio a manifestet a telepítéskor tárolja, így a kapcsolótól függő manifest csak az addon újratelepítése után érvényesült (hibajelentés, 2026-11-08: kikapcsolt állapotban telepítve a később bekapcsolt keresést a Nuvio nem látta). A kapcsoló így újratelepítés nélkül, azonnal érvényes.
  - Kikapcsolva a kliens a keresési kérést elküldheti, és a StremHU keresési sora üresen megjelenhet; a szerver ilyenkor trackerlekérdezés nélkül üres listát ad.
  - A backend végpontok (`/catalog/...`) védettek: közvetlen hívás esetén is azonnal üres listát (`metas: []`) adnak vissza felesleges tracker lekérdezések futtatása nélkül.

---

<!-- doc-anchor:doc-2-modositott-es-uj-fajlok-attekintese-diff-matrix-s4pp1stremhu-source-vs-featurestremio-catalog-search -->
<a id="doc-2-modositott-es-uj-fajlok-attekintese-diff-matrix-s4pp1stremhu-source-vs-featurestremio-catalog-search"></a>
## 2. Módosított és Új Fájlok Áttekintése (Diff Mátrix `s4pp1/stremhu-source` vs `feature/stremio-catalog-search`)

| Fájl elérési útja | Státusz | Változtatás összefoglalása |
| :--- | :---: | :--- |
| [`server/app/modules/stremio/catalogs_service.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/stremio/catalogs_service.py) | **MÓDOSÍTOTT** | Szabadszavas keresési ág integrálása, `media_type` szerinti célzott lekérdezés, `SeriesParser` alapú kategória-védelem, seederek szerinti rendezés és `MetaPreview` előállítás `imdb_id`-val és borítóképpel. |
| [`server/app/modules/stremio/schemas.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/stremio/schemas.py) | **MÓDOSÍTOTT** | `MetaPreview.from_torrent_file` és `MetaDetail.from_torrent_file` kiegészítése `imdb_id`, `poster` és `background` támogatással, valamint `MetaVideo` generálással. |
| [`server/app/modules/indexer_definitions/integrations/ncore.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/indexer_definitions/integrations/ncore.py) | **MÓDOSÍTOTT** | `_NCORE_MOVIE_CATEGORIES` és `_NCORE_SERIES_CATEGORIES` szétválasztása, `tipus="kivalasztottak_kozott"` és `kivalasztott_tipus[]` tömb átadása `media_type` alapján. |
| [`server/app/modules/indexer_definitions/base_indexer_definition.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/indexer_definitions/base_indexer_definition.py) | **MÓDOSÍTOTT** | `find_torrents_by_query`, `_find_all_by_query` és `_fetch_torrents_by_query` metódusok felkészítése az opcionális `media_type` paraméterre. |
| [`server/app/modules/indexers/service.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/indexers/service.py) | **MÓDOSÍTOTT** | `get_torrents_by_query` bővítése `media_type`-pal és a cache kulcs elkülönítése: `(indexer_id, query, media_type)`. |
| [`server/app/modules/torrent_source_provider/service.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/torrent_source_provider/service.py) | **MÓDOSÍTOTT** | `find_by_query` metódusban feladat-deduplikáció `media_type` szerint és paraméter továbbítása. |
| [`server/app/modules/stremio/utils.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/stremio/utils.py) | **MÓDOSÍTOTT** | `parse_stream_id` felkészítése az opcionális harmadik `:file_index` mező értelmezésére (`stremhu-source:{indexer}:{id}:{index}`). |
| [`server/app/modules/stremio/service.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/stremio/service.py) | **MÓDOSÍTOTT** | `file_index` továbbítása a `_torrent_streams_service.find_by_torrent_id` hívás felé. |
| [`server/app/modules/torrent_streams/service.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/torrent_streams/service.py) | **MÓDOSÍTOTT** | `find_by_torrent_id` metódus bővítése az opcionális `file_index` szűrő paraméterrel. |
| [`server/app/modules/torrent_streams/schemas.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/torrent_streams/schemas.py) | **MÓDOSÍTOTT** | `TorrentStream.from_torrent_id` metódusban a fájlok szűrése a megadott `file_index` alapján. |
| [`server/alembic/versions/e72a1c3d4f5b_add_enable_catalog_search_to_users.py`](file:///d:/Git/stremhu-source-anime/server/alembic/versions/e72a1c3d4f5b_add_enable_catalog_search_to_users.py) | **ÚJ** | Adatbázis migráció az `enable_catalog_search` (alapértelmezett: `True`) oszlop hozzáadására a `users` táblához. |
| [`server/app/modules/users/models.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/users/models.py) | **MÓDOSÍTOTT** | `enable_catalog_search` oszlop hozzáadása a `UserModel` ORM modellhez. |
| [`server/app/modules/users/schemas/internal.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/users/schemas/internal.py) | **MÓDOSÍTOTT** | `enable_catalog_search` hozzáadása a belső Pydantic sémákhoz (`BaseUser`, `UserUpdate`). |
| [`server/app/modules/users/schemas/api.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/users/schemas/api.py) | **MÓDOSÍTOTT** | `enable_catalog_search` mező átadása a `UserResponse` és adminisztrátori sémákban. |
| [`server/app/modules/me/schemas/api.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/me/schemas/api.py) | **MÓDOSÍTOTT** | `enable_catalog_search` engedélyezése a felhasználói beállításfrissítésben (`MeUpdateRequest`). |
| [`server/app/modules/users/service.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/users/service.py) | **MÓDOSÍTOTT** | Új felhasználó létrehozásakor az `enable_catalog_search` mentése. |
| [`server/app/modules/stremio/router.py`](file:///d:/Git/stremhu-source-anime/server/app/modules/stremio/router.py) | **MÓDOSÍTOTT** | A bejelentkezett `user` továbbítása a `catalogs_service.get_catalog` felé. |
| [`client/src/shared/schemas.ts`](file:///d:/Git/stremhu-source-anime/client/src/shared/schemas.ts) | **MÓDOSÍTOTT** | `enableCatalogSearchSchema` Zod validátor definiálása. |
| [`client/src/shared/lib/source/source-client.ts`](file:///d:/Git/stremhu-source-anime/client/src/shared/lib/source/source-client.ts) | **MÓDOSÍTOTT** | TypeScript típusdefiníciók frissítése (`enableCatalogSearch` a `UserResponse`, `MeUpdateRequest` stb. interfészekben). |
| [`client/src/routes/_protected/settings/preferences/-features/other-preferences.tsx`](file:///d:/Git/stremhu-source-anime/client/src/routes/_protected/settings/preferences/-features/other-preferences.tsx) | **MÓDOSÍTOTT** | Új UI kártya és kapcsoló a "Közvetlen Stremio katalógus-keresés" beállításához sonner toast mentéssel. |
| [`server/tests/test_stremio_catalog_search.py`](file:///d:/Git/stremhu-source-anime/server/tests/test_stremio_catalog_search.py) | **ÚJ** | Teljes körű unit tesztcsomag: film/sorozat kategória-szétválasztás, Metahub borítóképek, `SeriesParser` védelem, epizódgenerálás, stream azonosító elemzés, valamint manifest és katalógus kapuzási tesztek `enable_catalog_search` kapcsoló alapján. |

---

<!-- doc-anchor:doc-3-architektura-es-mukodesi-folyamatabrak -->
<a id="doc-3-architektura-es-mukodesi-folyamatabrak"></a>
## 3. Architektúra és Működési Folyamatábrák

<!-- doc-anchor:doc-31-kategoria-celzott-katalogus-kereses-es-boritokep-generalas -->
<a id="doc-31-kategoria-celzott-katalogus-kereses-es-boritokep-generalas"></a>
### 3.1. Kategória-Célzott Katalógus Keresés és Borítókép Generálás

```mermaid
sequenceDiagram
    autonumber
    actor User as Felhasználó (Stremio Keresősáv)
    participant Stremio as Stremio Kliens
    participant Router as StremioRouter (/catalog/...)
    participant CatService as StremioCatalogsService
    participant TSP as TorrentSourceProviderService
    participant Indexers as IndexersService
    participant nCore as nCore Integráció

    User->>Stremio: Beírja: "Lupin"
    par Film Katalógus Kérés
        Stremio->>Router: GET /catalog/movie/search/search=Lupin.json
        Router->>CatService: get_catalog(movie, "search", "Lupin")
        CatService->>TSP: find_by_query("Lupin", media_type="movie")
        TSP->>Indexers: get_torrents_by_query("Lupin", media_type="movie")
        Indexers->>nCore: _query_torrents(media_type="movie")
        Note over nCore: tipus=kivalasztottak_kozott<br/>kivalasztott_tipus[] = xvid_hun, hd_hun, dvd...
        nCore-->>CatService: Csak mozifilmek (pl. Arsene Lupin 2004, Lupin III)
        Note over CatService: SeriesParser ellenőrzi:<br/>nincs SxxExx -> megtartja<br/>Metahub poszter hozzárendelése (tt0373690)
        CatService-->>Stremio: 14 db film találat poszterekkel!
    and Sorozat Katalógus Kérés
        Stremio->>Router: GET /catalog/series/search/search=Lupin.json
        Router->>CatService: get_catalog(series, "search", "Lupin")
        CatService->>TSP: find_by_query("Lupin", media_type="series")
        TSP->>Indexers: get_torrents_by_query("Lupin", media_type="series")
        Indexers->>nCore: _query_torrents(media_type="series")
        Note over nCore: tipus=kivalasztottak_kozott<br/>kivalasztott_tipus[] = xvidser_hun, hdser_hun...
        nCore-->>CatService: Csak sorozatok (Lupin S01-S04 évadok)
        Note over CatService: SeriesParser ellenőrzi:<br/>van Sxx -> megtartja<br/>Metahub poszter hozzárendelése (tt2531336)
        CatService-->>Stremio: 30 db sorozat találat poszterekkel!
    end
```

---

<!-- doc-anchor:doc-4-tesztelesi-es-ellenorzesi-referencia -->
<a id="doc-4-tesztelesi-es-ellenorzesi-referencia"></a>
## 4. Tesztelési és Ellenőrzési Referencia

<!-- doc-anchor:doc-41-unit-tesztek-es-linter-eredmenyek -->
<a id="doc-41-unit-tesztek-es-linter-eredmenyek"></a>
### 4.1. Unit Tesztek és Linter Eredmények
```powershell
$env:HOST_IP="<HOST_IP>"; $env:PYTHONIOENCODING="utf-8"; cd server; .venv\Scripts\python -m ruff check .; .venv\Scripts\basedpyright.exe; .venv\Scripts\python -m pytest tests
```
- **Ruff:** `All checks passed!`
- **Basedpyright:** `0 errors, 0 warnings, 0 notes`
- **Pytest:** `223 passed, 64 snapshots passed in 2.42s` (beleértve a `test_catalog_disabled_for_user` és `test_manifest_catalog_gating` teszteket)

<!-- doc-anchor:doc-42-elo-docker-desktop-verifikacio-stremhu-local-test -->
<a id="doc-42-elo-docker-desktop-verifikacio-stremhu-local-test"></a>
### 4.2. Élő Docker Desktop Verifikáció (`stremhu-local-test`)
- **Bekapcsolt állapotban (`enable_catalog_search = True`):**
  - **Manifest lekérés:**
    ```powershell
    Invoke-RestMethod -Uri "https://<LOCAL_IP_DNS>:7070/api/<STREMHU_API_KEY>/stremio/manifest.json"
    ```
    *Eredmény:* `resources: [stream, catalog, meta, subtitles]`, `catalogs: 2 db` (Filmek és Sorozatok).
  - **Sorozatok keresés:**
    ```powershell
    Invoke-RestMethod -Uri "https://<LOCAL_IP_DNS>:7070/api/<STREMHU_API_KEY>/stremio/catalog/series/search/search=Lupin.json"
    ```
    *Eredmény:* 30 db tiszta sorozat találat (`Lupin.S04...`, `Lupin.S01...`), mindegyikhez `imdbId="tt2531336"` és `poster="https://images.metahub.space/poster/medium/tt2531336/img"`.
  - **Filmek keresés:**
    ```powershell
    Invoke-RestMethod -Uri "https://<LOCAL_IP_DNS>:7070/api/<STREMHU_API_KEY>/stremio/catalog/movie/search/search=Lupin.json"
    ```
    *Eredmény:* 14 db tiszta mozifilm találat (`Arsene.Lupin.2004...`, `Lupin.III.Cagliostro...`), mindegyikhez saját `imdbId` (`tt0373690`, `tt0079833`) és hivatalos borítókép.
- **Kikapcsolt állapotban (`enable_catalog_search = False`):**
  - **Manifest lekérés:**
    *Eredmény (2026-11-08 óta):* a manifest azonos a bekapcsolt állapotéval (`catalog` erőforrás, 2 keresési katalógus), hogy a kapcsoló újratelepítés nélkül működjön. *(Korábban a `catalog` hiányzott, ezért a később bekapcsolt keresést a kliensek nem látták.)*
  - **Katalógus végpont lekérés:**
    *Eredmény:* `metas: []` azonnali üres válasz tracker lekérdezések futtatása nélkül.
