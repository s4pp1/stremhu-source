---
doc_id: "feature-torrent-subtitles"
title: "Fejlesztői és AI Agent Dokumentáció: feature/torrent-subtitles"
kind: "feature-reference"
status: "historical-reference"
audience: ["developer", "ai-agent"]
tags: ["subtitle", "srt", "ass", "ssa", "vtt", "active-playback", "range", "fallback"]
source_commit: null
baseline: "8c99c7d"
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/feature/README.md", "docs/feature/audio-subtitle-detection.md"]
source_paths: ["server/app/modules/stream/router.py", "server/app/modules/stream/utils/subtitles.py", "server/app/modules/stream/active_playback.py"]
---

# Fejlesztői és AI Agent Dokumentáció: `feature/torrent-subtitles`

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../README.md) · [AI-index](../AI-INDEX.md)

> **Státusz:** Korábbi feature technikai referenciája. A tartalom és a mérések nem kaptak most új runtime-verifikációt; aktuális működéshez kövesd a forráskódot.

**Kapcsolódó:** [README.md](README.md) · [audio-subtitle-detection.md](audio-subtitle-detection.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [1. A Branch Célja és Motivációja](#doc-1-a-branch-celja-es-motivacioja)
- [2. Módosított és Új Fájlok Áttekintése (Diff Mátrix)](#doc-2-modositott-es-uj-fajlok-attekintese-diff-matrix)
- [3. Architektúra és Folyamatábrák](#doc-3-architektura-es-folyamatabrak)
- [4. Modulonkénti Részletes Működés és Kritikus Invariánsok](#doc-4-modulonkenti-reszletes-mukodes-es-kritikus-invariansok)
- [5. Hidegindítási és Keresési Teljesítmény-Optimalizációk (Smart Anime Gating & Lazy Dynamic Alias)](#doc-5-hideginditasi-es-keresesi-teljesitmeny-optimalizaciok-smart-anime-gating-lazy-dynamic-alias)

</details>

<!-- doc-nav:end -->

> [!IMPORTANT]
> **Viszonyítási alap (Baseline):**
> Ez a dokumentáció az eredeti **[s4pp1/stremhu-source](https://github.com/s4pp1/stremhu-source)** (`8c99c7d` commit) és a jelenlegi **`feature/torrent-subtitles`** ág közötti felirat-kezelési, streamelési, GUI és teljesítménybeli fejlesztéseket dokumentálja (a `main` ágon lévő Anime / TVDB / Kitsu támogatásra építve).

---

<!-- doc-anchor:doc-1-a-branch-celja-es-motivacioja -->
<a id="doc-1-a-branch-celja-es-motivacioja"></a>
## 1. A Branch Célja és Motivációja

Az eredeti upstream `s4pp1/stremhu-source` kizárólag a torrentben található **videófájl** streamelését támogatta. Magyar és anime torrenteknél azonban a magyar felirat nagyon gyakran **különálló fájlként** (`.srt`, `.ass`, `.ssa`, `.vtt`, `.sub`) található a torrent gyökerében vagy egy `Feliratok` / `Subs` almappában (pl. `[Naruto-Kun.Hu] Naruto Shippuden - E001.srt`, `Noragami - 01.ass`).

A `feature/torrent-subtitles` ág az alábbi problémákat oldja meg:
1. **Külső torrent-feliratok automatikus kinyerése és kiszolgálása** a Stremio `subtitles` erőforráson (`/subtitles/{type}/{id}/{extra}.json`) és a stream objektumok `subtitles` mezőjén keresztül.
2. **Univerzális WebVTT konverzió (`.ass` / `.ssa` -> `.vtt`):** A webes lejátszók (Nuvio Web, Stremio Web) és okostévék (LG webOS, Samsung Tizen) nem támogatják natívan az `.ass`/`.ssa` formátumot; a szerver valós időben, memóriában konvertálja őket szabványos WebVTT-vé.
3. **Magyar nyelvű szűrés és „ismeretlen = magyar” heurisztika:** Magyar trackereken (nCore, HunTorrent, Majomparádé) a különálló feliratfájlok gyakran nem tartalmaznak nyelvi kódot (`01.srt`). A rendszer kiszűri az ismert idegen nyelveket (`eng`, `ger`, `fre` stb.), a jelöletlen és magyar feliratokat pedig `hun` nyelven szolgálja ki.
4. **Aktív lejátszás követése (`active_playback.py`) és 1:1 felirat-párosítás:** Azokban a kliensekben (pl. Nuvio), amelyek a `/subtitles` végpont hívásakor nem küldenek `videoSize` vagy `filename` paramétert, a szerver az éppen elindított videó-stream alapján beazonosítja a lejátszott torrentet, és kizárólag ahhoz az 1 torrenthez tartozó feliratot adja vissza.
5. **Választható feliratkölcsönzés (Fallback) GUI kapcsolóval és Hit'n'Run védelemmel (`enable_fallback_subtitles`):** Ha a választott videó-torrentben nincs külön feliratfájl, a felhasználó a webes felületen dönthet úgy, hogy másik találatból „kölcsönöz” feliratot (kizárólag olyan tracker esetén, ahol nincs bekapcsolva a *Teljes torrent letöltése*), részletes tájékoztatással a dupla seedkötelezettségről.
6. **Epizódszintű felirat-piece előtöltés (`500 ms` deadline) és memória-cache (`_subtitle_content_cache`):** Garantálja, hogy a felirat már a videó első képkockáinál azonnal megjelenjen és tekeréskor `< 1 ms` alatt betöltődjön.

---

<!-- doc-anchor:doc-2-modositott-es-uj-fajlok-attekintese-diff-matrix -->
<a id="doc-2-modositott-es-uj-fajlok-attekintese-diff-matrix"></a>
## 2. Módosított és Új Fájlok Áttekintése (Diff Mátrix)

| Modul / Fájl | Státusz | Változtatás összefoglalása |
| :--- | :---: | :--- |
| `server/app/modules/stream/utils/subtitles.py` | **ÚJ** | `ass_to_vtt` valós idejű ASS/SSA -> WebVTT konverter (biztonságos `split(".", 1)` időbélyeg-átalakítás, `{...}` stílustagek tisztítása, `{\\p1}` rajzolt vektorok kizárása, `\\h` nem törő szóközök cseréje, előre fordított regexek). |
| `server/app/modules/stream/active_playback.py` | **ÚJ** | Felhasználónkénti aktív lejátszott `binge_group` nyilvántartása és versenyhelyzet-mentes `asyncio.Event` lista alapú egyidejű felébresztése (`wait_for_active_binge_group`) Nuvio-kompatibilitáshoz. |
| `server/app/modules/torrent_streams/utils/resolver_helpers.py` | Módosult | `SUBTITLE_EXTENSIONS`, `is_subtitle_file` és 4-lépcsős `detect_subtitle_language` (fájlnév prioritása, szülőmappák, torrentcím, ismeretlen = `hun`). |
| `server/app/modules/torrent_streams/utils/stream_file_resolver.py` | Módosult | `resolve_subtitles(video_file)`: elválasztó karaktert ellenőrző prefix-illesztés, epizódszám-ellenőrzés `SeriesParser`-rel és mappaszintű felirat-párosítás. |
| `server/app/modules/torrent_streams/schemas.py` | Módosult | `TorrentStreamSubtitle` séma; `.ass`/`.ssa` fájlok átirányítása `.vtt` végpontra; `subtitles` lista felépítése a `TorrentStream`-en. |
| `server/app/modules/stremio/router.py` & `service.py` | Módosult | `/subtitles/{content_type}/{stream_id}.json` és `/{extra}.json` végpontok; `get_subtitles`, `_find_played_stream`, `_can_borrow_subtitle` és `enable_fallback_subtitles` logika. |
| `server/app/modules/stream/router.py` & `service.py` | Módosult | `/api/{api_key}/subtitles/{stream_token}/{filename}` végpont (`GET`/`HEAD`, `Range: bytes=...` / `206 Partial Content`), in-flight kérés-összevonás (`_subtitle_locks`), `_subtitle_content_cache` memória-gyorsítótár. |
| `server/app/modules/relay/entities.py` | Módosult | `File.is_subtitle`, `File.get_matched_subtitle_pieces` (magyar feliratok prioritásával a 6-darabos kvótában) és `Torrent._set_matched_subtitle_priorities` (`500 ms` deadline a lejátszott epizód felirat-piece-eire). |
| `server/app/modules/users/models.py` & Alembic migráció | Módosult | `enable_fallback_subtitles: Mapped[bool]` mező a `users` táblán (`d41f8e2a1b5c` migráció). |
| `client/src/features/subtitle-settings/subtitle-settings.tsx` | **ÚJ** | `SubtitleSettingsCard` React komponens: *„Felirat kölcsönzése más találatból”* kapcsoló, Hit'n'Run figyelmeztető `Alert` és lenyitható `Accordion` tájékoztató fül. Felhasználónkénti beállítás (`/api/me`), ezért egyetlen helyen jelenik meg: **Beállítások → Preferenciák → További preferenciák** (2026-11-08 óta az admin Rendszer oldalról eltávolítva, ahol csak az admin saját beállítását írta). |
| `server/tests/test_subtitles.py` | **ÚJ** | 16 db átfogó unit és integrációs teszt a nyelvfelismeréshez, ASS->VTT konverzióhoz, határeset-prefixekhez, konkurens aktív lejátszás követéséhez, GUI fallback kapcsolóhoz és felirat-piece előtöltéshez. |

---

<!-- doc-anchor:doc-3-architektura-es-folyamatabrak -->
<a id="doc-3-architektura-es-folyamatabrak"></a>
## 3. Architektúra és Folyamatábrák

<!-- doc-anchor:doc-31-felirat-feloldas-aktiv-lejatszas-kovetes-es-fallback-dontesi-folyamat -->
<a id="doc-31-felirat-feloldas-aktiv-lejatszas-kovetes-es-fallback-dontesi-folyamat"></a>
### 3.1. Felirat-feloldás, Aktív Lejátszás Követés és Fallback Döntési Folyamat

```mermaid
flowchart TD
    Req["GET /subtitles/{type}/{stream_id}/{extra}.json"]
    GetStreams["StremioService.get_streams(user, parsed_id)<br/>(_stream_cache 60s találat -> 0 ms)"]
    ParseExtra["Extra / Query paraméterek elemzése:<br/>videoSize, filename, videoHash"]
    FindByExtra{"_find_played_stream()<br/>talált egyező streamet?"}
    WaitActive["wait_for_active_binge_group(user.id, timeout=2.5s)<br/>(Megvárja, amíg a lejátszó elindítja a /stream/{token} kérést)"]
    ActiveFound{"Van aktív lejátszott<br/>binge_group?"}
    HasOwnSubs{"A lejátszott streamnek<br/>van saját felirata?"}
    ReturnOwn["Kizárólag a lejátszott torrent<br/>saját feliratát adja vissza (1 torrent = 1 seed)"]
    CheckFallbackToggle{"user.enable_fallback_subtitles == True?"}
    CheckCanBorrow{"_can_borrow_subtitle(played_ts):<br/>not download_full_torrent ÉS<br/>not requires_full_download?"}
    BorrowSub["Kölcsönzés: az első olyan másik találat felirata,<br/>amely szintén _can_borrow_subtitle == True<br/>(Két torrentre keletkezik seedkötelezettség!)"]
    ReturnEmpty["Üres lista: []<br/>(Nincs második torrent indítás)"]

    Req --> GetStreams --> ParseExtra --> FindByExtra
    FindByExtra -- Igen --> HasOwnSubs
    FindByExtra -- Nem (pl. Nuvio) --> WaitActive --> ActiveFound
    ActiveFound -- Igen --> HasOwnSubs
    ActiveFound -- Nem --> CheckFallbackToggle
    HasOwnSubs -- Igen --> ReturnOwn
    HasOwnSubs -- Nem --> CheckFallbackToggle
    CheckFallbackToggle -- Nem --> ReturnEmpty
    CheckFallbackToggle -- Igen --> CheckCanBorrow
    CheckCanBorrow -- Igen --> BorrowSub
    CheckCanBorrow -- Nem --> ReturnEmpty
```

<!-- doc-anchor:doc-32-video-inditas-felirat-piece-prefetch-500-ms-es-memoria-cache-szekvencia -->
<a id="doc-32-video-inditas-felirat-piece-prefetch-500-ms-es-memoria-cache-szekvencia"></a>
### 3.2. Videó Indítás, Felirat Piece-Prefetch (`500 ms`) és Memória-Cache Szekvencia

```mermaid
sequenceDiagram
    autonumber
    actor Player as Lejátszó (Stremio / Nuvio)
    participant StreamAPI as StreamRouter (/stream/{token})
    participant Active as active_playback
    participant SubAPI as StremioRouter (/subtitles)
    participant Relay as Relay (Torrent.get_deadlines)
    participant SubStream as StreamRouter (/subtitles/{idx}/{name}.vtt)

    par Párhuzamos videó-indítás és felirat-lekérdezés
        Player->>StreamAPI: GET /api/{key}/stream/{token} (Range: bytes=0-)
        StreamAPI->>Active: register_active_playback(user_id, "stremhu-ncore-2114813")
        StreamAPI->>Relay: Videó stream indítása (File.has_active_streams = True)
        Relay->>Relay: Videó piece #0 deadline = 0 ms<br/>Párosított felirat piece-ek deadline = 500 ms!
    and
        Player->>SubAPI: GET /api/{key}/stremio/subtitles/series/tt0988824:4:1.json
        SubAPI->>Active: wait_for_active_binge_group(user_id) -> "stremhu-ncore-2114813"
        SubAPI-->>Player: 1 db illesztett felirat URL (.../Naruto Shippuuden - 072.vtt)
    end

    Player->>SubStream: GET .../subtitles/502/Naruto%20Shippuuden%20-%20072.vtt
    alt _subtitle_content_cache találat (30 perc TTL)
        SubStream-->>Player: Azonnali válasz RAM-ból (< 1 ms, 200 OK vagy 206 Partial Content)
    else Első letöltés
        SubStream->>Relay: Előtöltött felirat-piece-ek kiolvasása
        SubStream->>SubStream: UTF-8 / CP1250 / Latin-2 dekódolás (+ ass_to_vtt ha .ass)
        SubStream->>SubStream: Mentés _subtitle_content_cache-be
        SubStream-->>Player: WebVTT / SRT válasz (Accept-Ranges: bytes)
    end
```

---

<!-- doc-anchor:doc-4-modulonkenti-reszletes-mukodes-es-kritikus-invariansok -->
<a id="doc-4-modulonkenti-reszletes-mukodes-es-kritikus-invariansok"></a>
## 4. Modulonkénti Részletes Működés és Kritikus Invariánsok

1. **`detect_subtitle_language(filename: str, path: str = "")` (`resolver_helpers.py`):**
   - **4-lépcsős hierarchia:**
     1. *Fájlnév vizsgálata:* Ha a felirat fájlneve explicit magyar mintát (`hun`, `hu`, `magyar`, `hunsub`) vagy idegen nyelvet (`eng`, `ger`, `spa` stb.) tartalmaz, ez azonnal dönt. Ezzel elkerülhető, hogy egy `.HUN.` jelölésű release mappa almappájában lévő `English.srt` tévesen magyarként legyen kiszolgálva.
     2. *Szülőmappák vizsgálata:* Ha a fájlnév jelöletlen (pl. `01.srt`), a közvetlen szülőmappák nyelve dönt (pl. `Subs/eng` -> `eng`, `Subs/hun` -> `hun`).
     3. *Torrent útvonal vizsgálata:* Ha a szülőmappák sem tartalmaznak nyelvet, de a torrentcím magyar jelölést hordoz (pl. `[HunSub]`), a felirat magyarnak minősül.
     4. *Alapértelmezés:* Magyar trackereken a teljesen jelöletlen feliratok alapértelmezetten `("hun", "Hungarian (Torrent)")` címkét kapnak.

2. **`StreamFileResolver.resolve_subtitles(video_file)` (`stream_file_resolver.py`):**
   - **1. szint (Stem prefix elválasztó karakterrel):** Ha a felirat törzsneve a videófájl nevével kezdődik, megköveteli, hogy a prefix után elválasztó jel (`.`, `-`, `_`, szóköz, `[`, `(`) vagy a sztring vége következzen (így megelőzhető, hogy pl. `Movie 1.mkv`-hez a `Movie 10.hun.srt` illeszkedjen).
   - **2. szint (Epizódszám-egyezés):** Sorozatoknál a `SeriesParser` kinyeri a felirat évad- és epizódszámát, és ellenőrzi az `_is_episode_match` szabályait (beleértve az anime `alt_episodes_set` abszolút számozást is!). Ha a torrentben több felirat van, de egy másik epizódhoz tartozik, kizárja.
   - **3. szint (Ugyanazon mappa / Egyetlen felirat):** Filmeknél vagy egyepizódos mappákban az azonos mappában lévő feliratot hozzárendeli a videóhoz.

3. **Kölcsönzött felirat életciklusa és Hit'n'Run védelem (`stream/router.py` & `stremio/service.py`):**
   - Amikor a `stream_subtitle` végpontot egy olyan torrentre hívják meg, amely még nincs az adatbázisban (pl. a felhasználó még csak rákattintott a felirat-újratöltésre, vagy kölcsönzött feliratot tölt be), a `prepare_torrent_for_Download` `persist_torrent=False` paraméterrel hívódik meg, így nem dob `HTTP 400` hibát, viszont amint a `libtorrent` letölti a felirat piece-eit, a `TorrentModel` bekerül a helyi kliens automatikus seedelési és automatikus törlési szabályai alá.
   - A `_can_borrow_subtitle(torrent_stream)` ellenőrzi, hogy `not indexer_account.download_full_torrent and not indexer_definition.requires_full_download` — így ha egy forrásnál a teljes torrent letöltése kötelező vagy be van kapcsolva, abból sosem kölcsönöz feliratot.
   - Az egyidejű feliratkéréseket az aszinkron `_subtitle_locks` zár fogja össze, megelőzve a párhuzamos dupla letöltést és WebVTT transzkódolást.

4. **Epizódszintű Felirat Piece-Prefetch (`relay/entities.py`):**
   - A `File.get_matched_subtitle_pieces()` a `StreamFileResolver(t_info, series=SeriesInfo(season=..., episode=...)).resolve_subtitles(target_vfile)` hívással kizárólag az **aktuálisan nézett epizódhoz** tartozó feliratfájlok piece-eit adja vissza (így egy 500 részes Naruto pakkban nem tölti elő az összes 500 `.srt` fájlt, csak a nézett részét!).
   - A darabok kiválasztásakor a **magyar nyelvű feliratok piece-ei élveznek prioritást**, így a 6-darabos kvótát nem foglalják el az idegen nyelvű feliratok.
   - A `Torrent._set_matched_subtitle_priorities` ezekre a piece-ekre `500 ms` deadline-t állít be.

---

<!-- doc-anchor:doc-5-hideginditasi-es-keresesi-teljesitmeny-optimalizaciok-smart-anime-gating-lazy-dynamic-alias -->
<a id="doc-5-hideginditasi-es-keresesi-teljesitmeny-optimalizaciok-smart-anime-gating-lazy-dynamic-alias"></a>
## 5. Hidegindítási és Keresési Teljesítmény-Optimalizációk (Smart Anime Gating & Lazy Dynamic Alias)

1. **Intelligens Anime-Kapu (`TvdbResolver.get_alternate_imdb_ids`):**
   - A hollywoodi filmeknél és nyugati sorozatoknál a `get_alternate_imdb_ids(imdb_id, is_series=..., allow_dynamic_search=False)` kizárólag a statikus `_IMDB_ALIASES` szótárat és az in-memory gyorsítótárat ellenőrzi (0.01 ms).
   - Teljesen elmaradnak a külső szinkron HTTP lekérdezések a Kitsu Anime API és a Cinemeta felé, megspórolva **700 – 1 200 ms** felesleges hálózati késleltetést.
2. **Lusta (Lazy) Alias-Keresés:**
   - A dinamikus Kitsu iker-IMDb feloldás (`allow_dynamic_search=True`) kizárólag fallbackként fut le abban a ritka esetben, ha az elsődleges IMDb kódra **0 torrent találat** érkezett.
   - Szigorú cím-összehasonlítás kizárja a téves alcímes egyezéseket (pl. az *Inception* nem társul az *Inception: The Cobol Job* animációs rövidfilmhez).
3. **Nyugati sorozatok Kitsu 404-mentesítése (`TvdbResolver.get_episode_mappings`):**
   - Nem-anime sorozatoknál (*Stranger Things*, *Breaking Bad*, *Game of Thrones*) a resolver közvetlenül a Cinemeta kumulatív adatokból számolja ki az abszolút epizódszámokat, kikerülve az `anime-kitsu.strem.fun` felesleges 404-es hálózati hibáját (~350 ms megtakarítás).
4. **Teljesítménymérési Eredmény:**
   - A cold start átlagos válaszideje **9 068 ms-ról 3 835 ms-ra csökkent (-57.7%)**, amivel a fork a korábbi lemaradását ledolgozva gyorsabb lett még a minimális funkciókészletű Upstream referenciánál is (3 892 ms), miközben a meleg lekérdezési idő **3.2 ms** maradt (~360-szoros gyorsulás a memóriabeli gyorsítótárral).
