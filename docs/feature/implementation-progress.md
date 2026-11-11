---
doc_id: "feature-implementation-progress"
title: "Implementációs állapot – 2026-10-30 (M01 – M18 lezárva)"
kind: "historical-report"
status: "historical-results"
audience: ["developer", "ai-agent"]
tags: ["M01-M18", "progress", "benchmark", "tests", "2026-10-30"]
source_commit: null
baseline: null
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/feature/stability-and-optimization/archive/m01-m18-implementation-plan.md", "docs/feature/stability-and-optimization/README.md"]
source_paths: []
---

# Implementációs állapot – 2026-10-30 (M01 – M18 lezárva)

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../README.md) · [AI-index](../AI-INDEX.md)

> **Státusz:** Dátumhoz kötött M01–M18 állapot- és mérési beszámoló. Nem a CR01–CR19 készültsége és nem friss tesztjegyzőkönyv; az újabb audit korlátai is figyelembe veendők.

**Kapcsolódó:** [m01-m18-implementation-plan.md](stability-and-optimization/archive/m01-m18-implementation-plan.md) · [README.md](stability-and-optimization/README.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [Elkészült fejlesztési és stabilitási modulok](#doc-elkeszult-fejlesztesi-es-stabilitasi-modulok)
- [Ellenőrzési Eredmények](#doc-ellenorzesi-eredmenyek)

</details>

<!-- doc-nav:end -->

A stabilitási és teljesítményjavítási terv ([`docs/feature/stability-and-optimization/archive/m01-m18-implementation-plan.md`](stability-and-optimization/archive/m01-m18-implementation-plan.md)) valamennyi modulja implementálásra került és éles adatos háromutas A/B/C benchmarkkal validálva lett.

<!-- doc-anchor:doc-elkeszult-fejlesztesi-es-stabilitasi-modulok -->
<a id="doc-elkeszult-fejlesztesi-es-stabilitasi-modulok"></a>
## Elkészült fejlesztési és stabilitási modulok

- **M01 (Singleflight feladat-megszakítás védelem):** `common/singleflight.py` létrehozva `asyncio.shield` + waiters tracking logikával. Integrálva a provider és Stremio service-ekbe. Új tesztcsomag: `test_singleflight.py` (6 teszt).
- **M02 (Relay darabolvasások határideje és lezárása):** `config.relay_piece_timeout_seconds=120.0` és `relay_read_timeout_seconds=15.0`. `PieceReadAbortedError`, pending piece read törlés leálláskor. Új tesztcsomag: `test_relay_pending_piece_requests.py` (9 teszt).
- **M03 (Katalógus szűrés):** `stremio/catalogs_service.py`-ban a szűrés feltétel nélkül érvényesül. Új regressziós teszt: `test_catalog_rejection_regression.py`.
- **M04 (Fájlszintű deduplikáció & forráshelyesség):** Erős kulcs: `(info_hash, file_index)`. Eltérő hash esetén nincs összevonás; a letöltött forrás URL-je és attribútumai érvényesülnek. Frissített tesztek: `test_stream_optimizations.py`.
- **M05 (Cache kulcsok, generációk és invalidálás):** Folyamaton belüli `_user_cache_generations` és `invalidate_stream_cache(user_id)`. In-flight védelem: generációellenőrzés cache-be írás előtt. `invalidate_indexer_cache` fiókváltáskor. Új teszt: `test_cache_and_db_concurrency.py`.
- **M06 (Anime aliasok és epizódmetaadat-cache):** FMA/Brotherhood téves alias megszüntetve; animációs műfaji jelző megőrzése Cinemeta cache-hit esetén is.
- **M07 (Felirat hardening):** Bájtteljesség ellenőrzés (`len == file.size`), 32MB memóriakorlát, RFC 6266 fejléc, referenciaszámlált `KeyedLock`, `raise_errors=True` generátor. Új tesztcsomag: `test_subtitle_hardening.py` (4 teszt).
- **M08 (Keresési időkeret):** Monotonic deadline (20s) a fallback ciklusban; timeout esetén azonnali lezárás.
- **M09 (Méltányos jelöltfeldolgozás):** Fair interleaving trackerenként a fix top 30 vágás helyett (max 40 elem).
- **M10 (Torrentletöltés Singleflight & SQLite ON CONFLICT):** Letöltések összevonása Singleflight-tal; atomi `create_many_ignore_duplicates` `sqlite_insert(...).on_conflict_do_nothing()`.
- **M11 (Range RFC 9110 és fájlvalidáció):** 416 válasz `Content-Range: bytes */N` fejléccel; `require_subtitle=True` validáció minden streamre. Új tesztek: `test_range_and_file_validation.py`.
- **M12 (Célzott állapotlekérés és DB session határok):** `_sort_torrent_streams`-ben felesleges `get_torrents()` teljes tábla scan megszüntetése; célzott hash-ek és torrent file_progress memóriacache.
- **M13 (Relay prioritások és szálbiztonság):** Dinamikus kapcsolatlimit (`max(torrent_connections_limit, 50)`), biztonságos kollekciómásolatok a worker szálban.
- **M14 (Tech Info gyorsítás & nCore optimalizálás):** `_HUN_SUB_REGEX` gyorsútvonal torrent/fájlnévre; torrentenkénti csoportosítás (max 5); felesleges `torrent_drop` hívás kihagyása ha az NFO már tartalmaz MediaInfo-t.
- **M16 (Session cookie max_age):** 30 nap másodpercben megadva.
- **M17 (Docker buildcache):** `package.json` + `npm ci` külön rétegen a klienshez.
- **M18 (A/B/C benchmark):** Háromutas mérési infrastruktúra (`benchmark_local.py`).

<!-- doc-anchor:doc-ellenorzesi-eredmenyek -->
<a id="doc-ellenorzesi-eredmenyek"></a>
## Ellenőrzési Eredmények

- **Ruff linter:** 0 hiba (`All checks passed!`).
- **basedpyright típusellenőrző:** 0 hiba, 0 figyelmeztetés.
- **Pytest egységtesztek:** **256 sikeres teszt**, 64 sikeres snapshot.
- **Helyi Docker Build:** `stremhu-source:local-test` hibátlanul épül ~4s alatt.
- **Háromutas A/B/C Benchmark:**
  - Átlagos cold start: **3876.6 ms** (Feature Branch C) vs. **4081.4 ms** (Fork Master B) és **3753.6 ms** (Upstream A).
  - Átlagos warm válaszidő: **2.9 ms** (C) vs. **3.0 ms** (B) vs. **3297.6 ms** (Upstream A).
  - 100%-os pontosságú japán hangsáv és magyar felirat detekció és kártyajelölés.
