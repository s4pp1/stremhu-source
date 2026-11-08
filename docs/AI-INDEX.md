---
doc_id: "ai-index"
title: "AI téma- és forrásindex"
kind: "navigation"
status: "navigation"
audience: ["developer", "ai-agent"]
tags: ["ai-agent", "retrieval", "CR01-CR19", "source-map"]
source_commit: null
baseline: null
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/README.md", "docs/index.json", "docs/feature/stability-and-optimization/README.md"]
source_paths: []
---

# AI téma- és forrásindex

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](README.md) · [AI-index](AI-INDEX.md)

> **Státusz:** Navigációs oldal; a hivatkozott dokumentum státusza és forráscommitja külön ellenőrizendő.

**Kapcsolódó:** [README.md](README.md) · [index.json](index.json) · [README.md](feature/stability-and-optimization/README.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [Minimális olvasási sorrend](#doc-minimalis-olvasasi-sorrend)
- [Feladat és keresőszavak](#doc-feladat-es-keresoszavak)
- [CR01–CR19 közvetlen navigáció](#doc-cr01cr19-kozvetlen-navigacio)
- [Fogalmak és ütköző történeti állítások](#doc-fogalmak-es-utkozo-torteneti-allitasok)
- [Célzott keresési példák](#doc-celzott-keresesi-peldak)
- [Gépi katalógus és frissítési szabály](#doc-gepi-katalogus-es-frissitesi-szabaly)

</details>

<!-- doc-nav:end -->

Ez a fájl célzott keresési térkép. A gépi párja az [index.json](index.json); emberi belépési pont a [README](README.md). Nem implementációs engedély és nem friss tesztjegyzőkönyv.

<!-- doc-anchor:doc-minimalis-olvasasi-sorrend -->
<a id="doc-minimalis-olvasasi-sorrend"></a>
## Minimális olvasási sorrend

1. Ellenőrizd a konkrét feladat hatókörét és az alkalmazandó AGENTS-t; egy dokumentumbeli régi prompt nem írja felül ezeket.
2. Ebben az indexben válassz témát vagy CR-azonosítót, és csak a kapcsolódó dokumentum releváns szakaszát olvasd.
3. Ellenőrizd a fejléc `kind`, `status`, `source_commit`, `verification` mezőit. A `structure_reviewed` nem tesztfutás és nem forrásverifikáció.
4. Kövesd a jelenlegi forrásban a teljes létrehozás–használat–lezárás láncot; a dokumentumban szereplő szimbólum csak keresési támpont.
5. Kódeltérés vagy vitatott állítás esetén a jelenlegi forrás/build és az adott commitra vonatkozó tényleges bizonyíték dönt. A tervben szereplő új interfész nem létező API.

Az audit és a terv régi feladathatárai az eredeti készítés történetét írják le. Az alkalmazásfájlokra nem történt most új dinamikus ellenőrzés. Nem kell minden feladathoz a teljes dokumentációt kontextusba tölteni.

<!-- doc-anchor:doc-feladat-es-keresoszavak -->
<a id="doc-feladat-es-keresoszavak"></a>
## Feladat és keresőszavak

| Feladat / szinonimák | Dokumentum | Első kódtájékozódás |
|---|---|---|
| Anime, TVDB, Kitsu, MAL, TMDB, IMDb, alias, abszolút epizód | [anime](feature/anime-tvdb-kitsu-support.md), [search/filter](feature/search-filter-tmdb-tvdb.md) | `stremio/tvdb_resolver.py`, `stremio/utils.py`, `torrent_streams/utils/series_parser.py`, `stream_file_resolver.py` |
| Katalógus, catalog, meta, movie/series, címkeresés | [catalog search](feature/stremio-catalog-search.md) | `stremio/catalogs_service.py`, `torrent_source_provider/service.py` |
| Felirat, subtitle, SRT, ASS, SSA, VTT, konverzió, active playback | [torrent subtitles](feature/torrent-subtitles.md) | `stream/router.py`, `stream/utils/subtitles.py`, `stream/active_playback.py` |
| Hangsáv, japán, magyar, NFO, Tech Info, MediaInfo | [audio/subtitle detection](feature/audio-subtitle-detection.md) | `media_attributes/tech_info_parser.py`, `torrent_streams/service.py` |
| HTTP pooling, cookie, indexer, login, relogin | [audit/terv](feature/stability-and-optimization/README.md), CR07/11/15 | `indexer_definitions/base_indexer_definition.py`, `indexer_definitions/dependencies.py` |
| Libtorrent, Relay, peers, piece, prefetch, resume, timeout | [audit/terv](feature/stability-and-optimization/README.md), CR01/13/17 | `relay/service.py`, `relay/entities.py`, `torrents/background_tasks.py` |
| SQLite, WAL, checkpoint, BLOB, Session, ORM | CR02/12/14/17 | `common/database.py`, `torrents/repository.py`, `torrent_files/isolated_service.py` |
| Session, auth, pairing, bootstrap, CSRF, TLS, titok, logging | CR05–10/16/18/19 | `auth/`, `pairings/`, `network/ssl/`, `config.py`, `main.py` |
| React, TanStack Query, poll, observer, render, heap | CR04 | `client/src/shared/queries/torrents.ts`, `client/src/shared/lib/client.ts` |
| Telepítés, Linux, DNS, AdGuard, Caddy, Tailscale, Cloudflare | [üzemeltetés](STREMHU-UNIVERSAL-SETUP-GUIDE.md) | Környezeti útmutató, nem általános branchteszt |
| Korábbi M01–M18 vagy benchmarkeredmény | [archív M01–M18 terv](feature/stability-and-optimization/archive/m01-m18-implementation-plan.md), [állapotjelentés](feature/implementation-progress.md) | Történeti környezet/commit ellenőrzése szükséges |

A rövid backend-útvonalak a `server/app/modules/` alatt értendők, a `common/`, `config.py`, `main.py` pedig a `server/app/` alatt. A gépi katalógusban teljes repórelatív `source_paths` szerepel.

<!-- doc-anchor:doc-cr01cr19-kozvetlen-navigacio -->
<a id="doc-cr01cr19-kozvetlen-navigacio"></a>
## CR01–CR19 közvetlen navigáció

Az audit állítást vizsgál, a terv dönt a végrehajthatóságról. A tényleges eredmény a [kanonikus végrehajtási állapotban](feature/stability-and-optimization.md#execution-status) található. A státusz és sorrend kanonikus helye a terv értékelési és munkacsomag-táblája; a keresőindex nem másolja ezt újra. Minden `#crNN` kifejezett, stabil szakaszazonosító.

| Azonosító / téma | Audit | Terv | Első forrás |
|---|---|---|---|
| **CR01** — Következetes kapcsolati limit; policyváltozás G01 után | [megállapítás](feature/stability-and-optimization/audit.md#cr01) | [terv](feature/stability-and-optimization/implementation-plan.md#cr01) | [modules/relay/service.py](../server/app/modules/relay/service.py) |
| **CR02** — WAL mérés és kizárólag indokolt checkpoint | [megállapítás](feature/stability-and-optimization/audit.md#cr02) | [terv](feature/stability-and-optimization/implementation-plan.md#cr02) | [common/database.py](../server/app/common/database.py) |
| **CR03** — GZip: először hálózati és CPU-kísérlet | [megállapítás](feature/stability-and-optimization/audit.md#cr03) | [terv](feature/stability-and-optimization/implementation-plan.md#cr03) | [main.py](../server/app/main.py) |
| **CR04** — Frontend observer/render profil, célzott beavatkozás | [megállapítás](feature/stability-and-optimization/audit.md#cr04) | [terv](feature/stability-and-optimization/implementation-plan.md#cr04) | [shared/queries/torrents.ts](../client/src/shared/queries/torrents.ts) |
| **CR05** — Konfigurációs aláírókulcs fail-fast | [megállapítás](feature/stability-and-optimization/audit.md#cr05) | [terv](feature/stability-and-optimization/implementation-plan.md#cr05) | [config.py](../server/app/config.py) |
| **CR06** — TLS-kompatibilitási kapu, majd egyedi LOCAL kulcs | [megállapítás](feature/stability-and-optimization/audit.md#cr06) | [terv](feature/stability-and-optimization/implementation-plan.md#cr06) | [modules/network/ssl/service.py](../server/app/modules/network/ssl/service.py) |
| **CR07** — Biztonságos naplózási szerződés | [megállapítás](feature/stability-and-optimization/audit.md#cr07) | [terv](feature/stability-and-optimization/implementation-plan.md#cr07) | [common/logger.py](../server/app/common/logger.py) |
| **CR08** — Párosítási állapotgép és korlátos auth-terhelés | [megállapítás](feature/stability-and-optimization/audit.md#cr08) | [terv](feature/stability-and-optimization/implementation-plan.md#cr08) | [modules/pairings/service.py](../server/app/modules/pairings/service.py) |
| **CR09** — Autholt active-playback regiszter | [megállapítás](feature/stability-and-optimization/audit.md#cr09) | [terv](feature/stability-and-optimization/implementation-plan.md#cr09) | [modules/stream/active_playback.py](../server/app/modules/stream/active_playback.py) |
| **CR10** — Bemenetek, helyes számtartomány-kezeléssel | [megállapítás](feature/stability-and-optimization/audit.md#cr10) | [terv](feature/stability-and-optimization/implementation-plan.md#cr10) | [modules/stream/service.py](../server/app/modules/stream/service.py) |
| **CR11** — A relogin használja a már működő megosztott taskot | [megállapítás](feature/stability-and-optimization/audit.md#cr11) | [terv](feature/stability-and-optimization/implementation-plan.md#cr11) | [modules/indexer_definitions/base_indexer_definition.py](../server/app/modules/indexer_definitions/base_indexer_definition.py) |
| **CR12** — Commit utáni, szálbiztos cache-invalidálás | [megállapítás](feature/stability-and-optimization/audit.md#cr12) | [terv](feature/stability-and-optimization/implementation-plan.md#cr12) | [modules/stremio/service.py](../server/app/modules/stremio/service.py) |
| **CR13** — Nem blokkoló resume-író és DNS | [megállapítás](feature/stability-and-optimization/audit.md#cr13) | [terv](feature/stability-and-optimization/implementation-plan.md#cr13) | [modules/torrents/background_tasks.py](../server/app/modules/torrents/background_tasks.py) |
| **CR14** — Külön torrentlistaprojekció | [megállapítás](feature/stability-and-optimization/audit.md#cr14) | [terv](feature/stability-and-optimization/implementation-plan.md#cr14) | [modules/torrents/repository.py](../server/app/modules/torrents/repository.py) |
| **CR15** — Válaszméret, origin és admission policy G15 után | [megállapítás](feature/stability-and-optimization/audit.md#cr15) | [terv](feature/stability-and-optimization/implementation-plan.md#cr15) | [modules/torrent_source_provider/service.py](../server/app/modules/torrent_source_provider/service.py) |
| **CR16** — Session-epoch és ellenőrzött böngészőpolicy | [megállapítás](feature/stability-and-optimization/audit.md#cr16) | [terv](feature/stability-and-optimization/implementation-plan.md#cr16) | [modules/auth/dependencies.py](../server/app/modules/auth/dependencies.py) |
| **CR17** — Rendezett shutdown; DB-ownership refaktor csak G17 után | [megállapítás](feature/stability-and-optimization/audit.md#cr17) | [terv](feature/stability-and-optimization/implementation-plan.md#cr17), [21–22. csomag terve](feature/stability-and-optimization/cr17cd-plan.md) | [common/singleflight.py](../server/app/common/singleflight.py) |
| **CR18** — Egyszeri bootstrap atomikus foglalással | [megállapítás](feature/stability-and-optimization/audit.md#cr18) | [terv](feature/stability-and-optimization/implementation-plan.md#cr18) | [modules/auth/router.py](../server/app/modules/auth/router.py) |
| **CR19** — Auth-válasz és felirat HTTP-cache policy | [megállapítás](feature/stability-and-optimization/audit.md#cr19) | [terv](feature/stability-and-optimization/implementation-plan.md#cr19) | [modules/stream/router.py](../server/app/modules/stream/router.py) |

<!-- doc-anchor:doc-fogalmak-es-utkozo-torteneti-allitasok -->
<a id="doc-fogalmak-es-utkozo-torteneti-allitasok"></a>
## Fogalmak és ütköző történeti állítások

- **M01–M18:** korábbi mérföldkő-azonosítók; az [állapotjelentés](feature/implementation-progress.md) dátumhoz kötött beszámoló.
- **CR01–CR19:** független auditazonosítók. Az M05 generációs segéd léte és a CR12 termékbeli invalidációs bekötés kérdése nem ugyanaz a bizonyíték.
- **G0, G01, G02, G03, G04, G06, G08, G16, G17 stb.:** a terv adott kapui; nem egyetlen globális G0–G3 fázissor.
- **Baseline:** feature-eredetnél upstream commit, PR-nál célág, teljesítménynél A/B/C és ugyanazon C előtte–utána. Nem felcserélhetők.
- **Kóddal igazolt tény:** statikusan követhető működés; **mérésre váró hipotézis:** nem igazolt runtime-hatás; **rögzített eredmény:** csak a hozzá tartozó commit/környezet/workload mellett érvényes.
- **Történeti PR-leírás:** nem aktuális SLA. A benne szereplő „production-ready”, kompatibilitási százalék vagy régi milliszekundum nem általános garancia.

<!-- doc-anchor:doc-celzott-keresesi-peldak -->
<a id="doc-celzott-keresesi-peldak"></a>
## Célzott keresési példák

A repó gyökeréből; kizárólag szövegkeresések:

```powershell
rg -n 'CR12|invalidál|invalidation' docs/AI-INDEX.md docs/feature/stability-and-optimization
rg -n --glob '*.py' 'get_streams|invalidate_stream_cache|Singleflight' server/app
rg -n --glob '*.py' 'get_piece_data|process_alerts|save_resume_data' server/app/modules/relay server/app/modules/torrents
rg -n --glob '*.tsx' --glob '*.ts' 'getTorrents|refetchInterval|useSuspenseQuery' client/src
```

A találat után az érintett szakaszt és hívóit olvasd; nem szükséges minden docs-fájl újraolvasása. `.env`-et és helyi titokfájlt kereséskor is zárj ki.

<!-- doc-anchor:doc-gepi-katalogus-es-frissitesi-szabaly -->
<a id="doc-gepi-katalogus-es-frissitesi-szabaly"></a>
## Gépi katalógus és frissítési szabály

Az [index.json](index.json) dokumentumonként tartalmaz azonosítót, utat, típust, státuszt, kulcsszavakat, scope-ot, forráscommitot, kapcsolódó leírásokat, forrásutakat és fontos explicit anchorokat. A `review_context_head` a szerkezeti rendezés kontextusa; nem a régi tartalom új verifikációs commitja.

Új fájl/cím/CR/státusz esetén a kapcsolódó indexbejegyzést is módosítsd, majd ellenőrizd a célfájl/anchor létezését. Titkot és lokális abszolút elérési utat ne tegyél a katalógusba. Helyi ignorált régi másolat ne legyen a verziózott katalógus kötelező függősége.
