---
doc_id: "feature-readme"
title: "Feature-katalógus"
kind: "navigation"
status: "navigation"
audience: ["developer", "ai-agent"]
tags: ["feature", "catalog", "reference"]
source_commit: null
baseline: null
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/AI-INDEX.md", "docs/templates/feature.md"]
source_paths: []
---

# Feature-katalógus

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../README.md) · [AI-index](../AI-INDEX.md)

> **Státusz:** Navigációs oldal; a hivatkozott dokumentum státusza és forráscommitja külön ellenőrizendő.

**Kapcsolódó:** [AI-INDEX.md](../AI-INDEX.md) · [feature.md](../templates/feature.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [Funkciók és kanonikus dokumentumok](#doc-funkciok-es-kanonikus-dokumentumok)
- [Történeti munkák és azonosítók](#doc-torteneti-munkak-es-azonositok)
- [Új feature dokumentálása](#doc-uj-feature-dokumentalasa)

</details>

<!-- doc-nav:end -->

A dokumentumok az egyes funkciók eredetét és technikai összefüggéseit mutatják. A régebbi feature-referenciák nem kaptak most új működési/tesztigazolást. A jelenlegi implementációt a mellettük megjelölt forrásból ellenőrizd.

<!-- doc-anchor:doc-funkciok-es-kanonikus-dokumentumok -->
<a id="doc-funkciok-es-kanonikus-dokumentumok"></a>
## Funkciók és kanonikus dokumentumok

| Téma | Kanonikus dokumentum | Kulcsfogalmak | Forrás belépési pont |
|---|---|---|---|
| Anime és többféle médiaazonosító | [Anime / TVDB / Kitsu](anime-tvdb-kitsu-support.md) | IMDb, TVDB, Kitsu, MAL, abszolút epizódszám, alias, resolver | [tvdb_resolver.py](../../server/app/modules/stremio/tvdb_resolver.py), [stream_file_resolver.py](../../server/app/modules/torrent_streams/utils/stream_file_resolver.py) |
| Címkeresés, TMDB és több-trackeres találatok | [Search / filter / TMDB / TVDB](search-filter-tmdb-tvdb.md) | fallback, dedup, info_hash, seeders, évadcsomag | [torrent_streams/service.py](../../server/app/modules/torrent_streams/service.py), [indexers/service.py](../../server/app/modules/indexers/service.py) |
| Katalógus és meta | [Stremio catalog search](stremio-catalog-search.md) | catalog, meta, movie, series, névkeresés | [catalogs_service.py](../../server/app/modules/stremio/catalogs_service.py) |
| Külső torrentfelirat | [Torrent subtitles](torrent-subtitles.md) | SRT, ASS, SSA, VTT, active playback, fallback, Range | [stream/router.py](../../server/app/modules/stream/router.py), [subtitles.py](../../server/app/modules/stream/utils/subtitles.py) |
| Hangsáv- és feliratattribútum | [Audio/subtitle detection](audio-subtitle-detection.md) | Tech Info, NFO, MediaInfo, japán hangsáv, magyar felirat | [tech_info_parser.py](../../server/app/modules/media_attributes/tech_info_parser.py) |
| Stabilitás és biztonsági audit | [Branch-összefoglaló](stability-and-optimization.md) → [munkacsomag](stability-and-optimization/README.md) | CR01–CR19, auth, TLS, cache, WAL, cancellation | Audit és értékelt terv; [aktuális végrehajtás](stability-and-optimization.md#execution-status) |
| Streamgyorsítás | [Branch-összefoglaló](stream-performance.md) → [munkacsomag](stream-performance/README.md) | SP01–SP10, előtöltési ablak, TTFB, tracker-időkorlát, Tech Info, trackercache | Kész, mért kapukkal (PR a `main` felé); [végrehajtási állapot](stream-performance.md#execution-status) |

<!-- doc-anchor:doc-torteneti-munkak-es-azonositok -->
<a id="doc-torteneti-munkak-es-azonositok"></a>
## Történeti munkák és azonosítók

- **M01–M18:** [archív eredeti terv](stability-and-optimization/archive/m01-m18-implementation-plan.md) és [2026-10-30-i állapotjelentés](implementation-progress.md). A dokumentumokban rögzített eredmények történetiek; nem az aktuális HEAD tesztjegyzőkönyvei.
- **CR01–CR19:** [független audit](stability-and-optimization/audit.md) és [részletes terv](stability-and-optimization/implementation-plan.md). A terv minden tételt újraértékel, és egyes változtatásokat mérési kapu mögé tesz.

<!-- doc-anchor:doc-uj-feature-dokumentalasa -->
<a id="doc-uj-feature-dokumentalasa"></a>
## Új feature dokumentálása

A [feature-sablon](../templates/feature.md) használható. A cél, modulok, invariánsok, diffbaseline, hibautak és ellenőrzési bizonyíték kapjon helyet; nagyobb munkához alárendelt audit/terv külön fájlban tartható. A meglévő névkonvenciót és bejövő linkeket őrizd meg.
