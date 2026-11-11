---
doc_id: "feature-stream-performance-implementation-plan"
title: "Streamgyorsítás — kódszintű implementációs terv"
kind: "implementation-plan"
status: "planning-only"
audience: ["developer", "ai-agent"]
tags: ["SP01-SP09", "performance", "gates", "work-packages", "tests", "rollback"]
source_commit: "0515d989c764bb4103d6f7286d703b98ec859ce6"
baseline: "s4pp1/stremhu-source@8c99c7d (feature origin); main@0515d98 (PR); pinned A/B/C + C legacy/candidate toggle (measurement)"
verification: "static source reading at source_commit; no tests, benchmarks or Docker runs"
structure_reviewed: "2026-11-08"
related_docs: ["docs/feature/stream-performance/README.md", "docs/feature/stream-performance.md", "docs/feature/stability-and-optimization/implementation-plan.md"]
source_paths: ["server/app/modules/relay/", "server/app/modules/stream/", "server/app/modules/indexers/search.py", "server/app/modules/torrent_source_provider/service.py", "server/app/modules/torrent_streams/service.py", "server/app/modules/indexer_definitions/integrations/ncore.py", "server/app/modules/stremio/service.py", "server/app/config.py", "scripts/fixtures/local_bt_seed.py"]
---

# Streamgyorsítás — kódszintű implementációs terv

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../../README.md) · [AI-index](../../AI-INDEX.md)

> **Státusz:** Terv (a `0515d98` forrásán). Végrehajtva; mi került be és mi nem, azt a [végrehajtási állapot](../stream-performance.md#execution-status) rögzíti, nem ez a dokumentum.

**Kapcsolódó:** [README.md](README.md) · [stream-performance.md](../stream-performance.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [0. Bemenet, állapot, használati szabály](#doc-0-bemenet-allapot-hasznalati-szabaly)
- [1. Kiinduló megállapítások és értékelés](#doc-1-kiindulo-megallapitasok-es-ertekeles)
- [2. Közös végrehajtási szerződés](#doc-2-kozos-vegrehajtasi-szerzodes)
- [3. Lejátszás: relay és streamválasz](#doc-3-lejatszas-relay-es-streamvalasz)
- [SP01 — Előtöltési ablak és prioritáspolitika lejátszás közben](#sp01)
- [SP02 — Indulási darabsorrend](#sp02)
- [SP03 — Lejátszási előzmény a válasz előtt](#sp03)
- [SP04 — Darabolvasás átfedése a küldéssel](#sp04)
- [SP10 — Beragadó peerek indulási büntetése](#sp10)
- [SP09 — `Connection: close` minden streamválaszon](#sp09)
- [4. Találatlista: keresés](#doc-4-talalatlista-kereses)
- [SP05 — Tracker-egészség és rövidzár](#sp05)
- [SP06 — Tech Info a kritikus úton](#sp06)
- [SP07 — Lejárt trackercache: régi találat azonnal, frissítés a háttérben](#sp07)
- [SP08 — A név szerinti tartalékkeresés soros lánca](#sp08)
- [5. Munkacsomag-tábla](#doc-5-munkacsomag-tabla)
- [6. Kockázatok](#doc-6-kockazatok)
- [7. Nyitott kérdések és döntési pontok](#doc-7-nyitott-kerdesek-es-dontesi-pontok)
- [8. Végrehajtási ellenőrzőlista](#doc-8-vegrehajtasi-ellenorzolista)

</details>

<!-- doc-nav:end -->

<!-- doc-anchor:doc-0-bemenet-allapot-hasznalati-szabaly -->
<a id="doc-0-bemenet-allapot-hasznalati-szabaly"></a>
## 0. Bemenet, állapot, használati szabály

- **Branch:** `feature/stream-performance`, a `main` `0515d989c764bb4103d6f7286d703b98ec859ce6` commitjáról (a PR #9 és a PR #10 után). A PR #10 squash commitja eredetileg `9984678` volt; 2026-11-08-án a Claude-attribúciós sor nélkül, azonos fájltartalommal újraírva lett `0515d98`.
- **Bemenet:** a 2026-11-08-i kódolvasásos átnézés a `main`-en, és a stabilitási ág mérési bizonyítékai, elsősorban a [`burst27-v3` keresési alapmérés](../stability-and-optimization.md#doc-27-cr15c).
- **Folyamat:** a [stabilitási ág](../stability-and-optimization.md) mintája. Minden tétel lépései:
  - értékelt tétel;
  - előre regisztrált mérési protokoll;
  - kis, önálló csomag és célzott viselkedési teszt;
  - Ruff → basedpyright → teljes pytest;
  - helyi Docker;
  - A/B/C és C előtte/utána mérés;
  - dokumentált kapudöntés.
- **Ez terv, nem végrehajtási engedély.** Ebben a körben forrás, teszt, függőség és szolgáltatás nem változott. Teszt, benchmark, Docker-futtatás és trackerkérés nem történt.
- **Hivatkozások:** a sorhivatkozások a fenti commitra vonatkoznak. A rövid `modules/...`, `common/...`, `config.py` utak előtt `server/app/` értendő. Az `Új` jelölésű fájl, konfigurációs mező vagy szimbólum még nem létezik. A javasolt nevek a csomag G0-lépésében véglegesítendők.
- **Verziók (requirements szerint):** Python 3.12, Hypercorn, libtorrent 2.1.1. A tényleges telepített API-t és viselkedést a G0 ellenőrzi; a terv nem épít dokumentálatlan natív viselkedésre.
- **Azonosítók:**
  - `SPxx`: tétel (stream performance);
  - `GSPxx`: a tétel mérési kapuja;
  - `H1`–`H3`: mérőeszköz;
  - `C0`–`C3`: kapun belüli jelölt változat.
- **Tesztmátrixok:** az E/B/M/V oszlop jelentése előfeltétel, bemenet, művelet, várt viselkedés.

<!-- doc-anchor:doc-rovid-belepesi-terkep -->
<a id="doc-rovid-belepesi-terkep"></a>
### Rövid belépési térkép

| Folyamat | Kiindulópont |
|---|---|
| Találatlista | `stremio/router.py:streams:66` → `StremioService.get_streams:161` (60 s-os felhasználói cache, singleflight) → `_get_streams_uncached:191` → `TorrentStreamsService.find_by_imdb:77` → `TorrentSourceProviderService.find_by_imdb_id:115` → `_SourceSearch.find_by_imdb_id:231` → `IndexerSearchService.get_torrents_by_imdb_id:153` |
| .torrent letöltés | `_SourceSearch._sync_torrent_files:326` → `_download_and_store:409` (indexerenként 5 letöltés, bájtkeret, 15 s-os határidő) |
| Tech Info | `TorrentStreamsService._enrich_torrent_streams_with_tech_info:358` → `_enrich_torrent_group:418` → `NcoreIndexerDefinition.fetch_tech_info` (`indexer_definitions/integrations/ncore.py:267`) |
| Lejátszás | `stream/router.py:stream:67` (auth, limit, `prepare_for_stream`, előzménymentés) → `File.stream` → `Stream._stream_inner` (`relay/entities.py:394`) → `RelayService.get_piece_data` (`relay/service.py:247`) |
| Darabprioritás | `RelayService.trigger_priority_update:128` → `priority_manager_loop:145` → `Torrent.priority_manager` (`relay/entities.py:83`) → `get_deadlines:120` |

<!-- doc-anchor:doc-1-kiindulo-megallapitasok-es-ertekeles -->
<a id="doc-1-kiindulo-megallapitasok-es-ertekeles"></a>
## 1. Kiinduló megállapítások és értékelés

**Bizonyítottsági szintek:**
- **Forrásból igazolt:** a kód ténylegesen így működik.
- **Hatás: hipotézis:** az, hogy ez lassítja a streamet, nincs mérve.

Lejátszási sebességmérés (TTFB, pufferelés, akadás) a projektben még nem készült. A keresési útról a stabilitási ág offline, fixture-alapú mérése áll rendelkezésre.

| SP | Terület | Forrásból igazolt tény | Hatás bizonyítottsága | Besorolás | Prioritás, függés |
|---|---|---|---|---|---|
| SP01 | Lejátszás | Aktív streamnél a torrent minden darabja 0 prioritást kap. Határidőt csak az aktuális és utána 4–8 hiányzó darab kap; ez a darabmérettől függően 2–64 MiB. | Hipotézis: kicsi puffer, korlátos átvitel, akadás | Előbb mérendő (GSP01) | P1; H1, SP02 után |
| SP02 | Lejátszás | Aktív streamnél a fájl első és utolsó legfeljebb 3 hiányzó darabja mindig 0 ms-os határidőt kap, az aktuális darabbal azonos sürgősséggel. | Hipotézis: lassabb indulás nagy darabméretnél | Előbb mérendő (GSP02) | P1; H1 |
| SP03 | Lejátszás | Minden GET/HEAD Range-kérés a válaszfejlécek előtt megvárja a lejátszási előzmény zárolt, szálon futó DB-műveletét. | Hipotézis: TTFB-többlet minden indításnál és tekerésnél; nagysága ismeretlen | Implementálható kis csomag, mérési kontrollal | P1; G0 kész (fogyasztók ellenőrizve) |
| SP04 | Lejátszás | A következő darab beolvasása csak az előző darab teljes elküldése után indul. | Hipotézis: főleg letöltött, nagy bitrátájú fájlnál | Előbb mérendő (GSP04) | P3; SP01 után |
| SP05 | Keresés | Trackerenként 12,5 s-os időkorlát, három azonos másolatban; a nem válaszoló trackert a rendszer nem jegyzi meg. | A mechanizmus igazolt: egy nem válaszoló tracker minden hideg keresést ~12,5 s-ig tart. A gyakoriság ismeretlen. | SP05/a implementálható refaktor; SP05/b mérési kapus policy | P1; H2 |
| SP06 | Keresés | A Tech Info legfeljebb 1,5 s-ot vár, a keresés után, sorban. Időtúllépéskor a munka elvész. Az adapterben elnyelt hiba üres eredményként 1 órára cache-elődhet. | Hipotézis a gyakoriságra; a cache-mérgezés lehetősége forrásból igazolt | SP06/a implementálható; SP06/b előbb mérendő | P2 |
| SP07 | Keresés | A 30 perces trackercache lejáratkor eldobja a bejegyzést, a következő kérés a teljes keresést kivárja. | Hipotézis | Előbb mérendő + termékdöntés | P2; SP05 után |
| SP08 | Keresés | A név szerinti tartalékkeresések egymás után futnak. | Csak 0 IMDb-találatnál érint; gyakoriság ismeretlen | Előbb mérendő; várható eredmény: nincs változtatás | P3; SP05 után |
| SP10 | Lejátszás | Egy peer, amely elfogadja a blokk-kérést, de nem válaszol, az első darabok blokkjait magánál tartja. A `pb0-v2` mixed profiljában (8 peerből 2 ilyen) az első bájt 13–18 s, az upstreamen és a forkon egyaránt. | Szintetikus profilban mérve igazolt; a valós swarmokban való gyakoriság ismeretlen | Előbb mérendő (GSP10) | P1; G0-próba bővítése |
| SP09 | HTTP | Minden streamválasz `Connection: close`. Upstreamből származik, szándékos (`92fcb8d`, #274). | Hipotézis: kérésenként új TCP/TLS-kapcsolat | Kompatibilitási kapu; alapból nincs változás | P3 |

**Ami jó, és nem változik:**
- trackerenkénti, 30 perces IMDb-trackercache és 5 perces lekérdezéscache;
- 60 s-os, felhasználónkénti stream-cache revíziókezeléssel;
- singleflight minden keresési szinten, és CR15/c admission;
- a .torrent fájlok tartós mentése, így csak egyszer töltődnek le;
- a trackerkeresés előindítása az epizódleképezéssel párhuzamosan (`stremio/service.py:340`);
- 50 kapcsolat torrentenként aktív streamnél (`relay/service.py:204`).

**Elvetett vagy halasztott irányok:**
- **Vak natív hangolás:** libtorrent `cache_size`, szálszám, `piece_timeout` vagy `request_timeout` vak hangolása. Ezek csak akkor kerülhetnek elő, ha a GSP01 adatai konkrétan rájuk mutatnak.
- **DHT:** bekapcsolása értelmetlen, mert a támogatott trackerek privátak.
- **Teljes torrent előtöltése** minden lejátszásnál: a lemez- és sávszélesség-költség nincs arányban a haszonnal.
- **HTTP/2, átkódolás, médiatömörítés:** a CR03 a globális médiatömörítést már elvetette.
- **Több worker:** az in-process állapotok egy processzre tervezettek.

<!-- doc-anchor:doc-2-kozos-vegrehajtasi-szerzodes -->
<a id="doc-2-kozos-vegrehajtasi-szerzodes"></a>
## 2. Közös végrehajtási szerződés

<!-- doc-anchor:doc-21-g0-elofeltetelek -->
<a id="doc-21-g0-elofeltetelek"></a>
### 2.1. G0 — Előfeltételek

1. **Kiinduló állapot:** HEAD, munkafa és alkalmazandó AGENTS újraellenőrzése. Eltérésnél az érintett hívási lánc újraolvasása.
2. **libtorrent 2.1.1 viselkedése**, egy `LocalSeed`-alapú, nem termékkódba kerülő próbával:
   - letöltődik-e a 0 prioritású darab, ha határidőt kap;
   - milyen prioritásra áll vissza a darab `reset_piece_deadline` után;
   - a határidős darabok sorrendje 1-es prioritású „háttér” darabok mellett;
   - a `have_piece` és `piece_priorities` hívásköltsége ablakmérettől függően;
   - párhuzamos `read_piece` viselkedése.

   Az SP01/SP02/SP04 ezek eredményéhez igazodik.
3. **Lejátszási előzmény fogyasztói (SP03), a forrásból ellenőrizve:**
   - a `check_playback_limit` a relay aktív streamjeit számolja, nem az előzményt (`playbacks/service.py:39–60`);
   - az előzménysort csak a dashboard aktív-lejátszás listája (`get_active_playbacks`) és az előzménylista olvassa;
   - a `get_or_create` meglévő sornál csak olvas (`playback_histories/repository.py:19–34`).
4. **SP09:** a Hypercorn keep-alive és `Connection` fejléc kezelése, valamint az upstream #274 indoka.
5. **Processzmodell:** egy processz, ahogy a stabilitási G0-ban. Az új in-process állapotok (breaker, cache, háttértaskok) nem globálisak több worker esetén.
6. **Migráció:** nem várható. Új beállítás csak `config.py` mezőként, alapértékkel kerül be. Plug & play: új kötelező környezeti változó nincs, felületi kapcsoló csak termékdöntés után.

<!-- doc-anchor:doc-22-ellenorzesi-sorrend-az-agents-szerint -->
<a id="doc-22-ellenorzesi-sorrend-az-agents-szerint"></a>
### 2.2. Ellenőrzési sorrend az AGENTS szerint

**Kódváltozás után**, Docker-build vagy commit előtt:
1. célzott viselkedési tesztek;
2. a `server/.venv`-vel: `python -m ruff check .` → `basedpyright.exe` → `python -m pytest tests`, helyi, nem loopback `HOST_IP`-vel és `PYTHONIOENCODING=utf-8`-cal;
3. kliensváltozásnál a `client/package.json` tényleges `lint`, `format` és `build` scriptje;
4. helyi Docker funkcionális teszt eldobható, szintetikus adattal;
5. a releváns mérési kapu.

Sikertelen lépés után nincs továbblépés.

**Mérési segédszkriptek:**
- csak szintetikus fixture-rel és belső Docker-hálózaton futnak;
- valós trackerhez, valós fiókhoz vagy a védett `scripts/benchmark_local.py`-hoz nem nyúlnak.

<!-- doc-anchor:doc-23-meroeszkozok -->
<a id="doc-23-meroeszkozok"></a>
### 2.3. Mérőeszközök

**H1 — helyi swarm és lejátszó-emuláció (SP01, SP02, SP03, SP04)**
- **Seeder:** az `scripts/fixtures/local_bt_seed.py` `LocalSeed` bővítése (`Új` opciókkal):
  - peerenkénti sávszélesség-korlát (token bucket);
  - kérésenkénti késleltetés és jitter;
  - „beragadó” peer, amely elfogadja a kérést, de nem válaszol (`piece_timeout` út);
  - choke/unchoke váltakozás.

  Az adat szintetikus nullbájt, ahogy most. A darabhash-ek a darabméretből számolódnak, az utolsó, rövidebb darabot is kezelve.
- **Tracker:** `Új` `scripts/fixtures/local_tracker.py`: minimális HTTP announce, amely a seeder végpontjait adja vissza tömör peerlistában. A szintetikus .torrent `private=1` jelzővel erre mutat, így a termékkód a valódi announce-úton, tesztkampó nélkül talál peert.
- **Topológia:** egy `--internal` Docker-hálózat, internetkimenet nélkül.
  - `sp-seed`: seeder + tracker;
  - a vizsgált StremHU-konténer;
  - `sp-client`: lejátszó-emulátor.

  Mindhárom ugyanabból a vizsgált image-ből indul felülírt belépési ponttal, így nem kell külső image. Letöltési kötet: eldobható Docker-kötet, nem tmpfs, mert a memóriakeretbe számítana.
- **Adatbetöltés:** egy konténeren belüli segéd az alkalmazás saját függvényeivel hoz létre szintetikus felhasználót, `torrent_files` sort és streamtokent, a `benchmark_cr_playback_signal.py` mintájára. Titkot, tokent és kulcsot nem ír ki.
- **Lejátszó-emulátor:** `Új` `scripts/benchmark_sp_playback.py`.
  - Valós HTTP(S)-en kér: `bytes=0-`, utána a fájlvég-próba (utolsó 1 MiB), majd lejátszás adott bitrátával, pufferelő modellel. A lejátszás N másodpercnyi pufferelés után indul; üres puffernél akadás.
  - Tekerés a fájl 50%-ára, újrapufferelés.
  - Kimenet JSON: időbélyegek és metrikák.
- **Profilok:**
  - **fast:** sok, gyors peer;
  - **mixed:** gyors, lassú és beragadó peerek vegyesen;
  - **thin:** 2 peer, a bitrátához közeli összsávszélességgel.

  Darabméret: 256 KiB, 1 MiB, 4 MiB, 16 MiB. Bitrátacélok: UX-döntés (7. fejezet).

**H2 — keresési harness (SP05, SP06, SP07, SP08)**
- **Alap:** a `scripts/benchmark_cr_search_http.py` és `benchmark_cr_search_policy.py` mintája. A valódi Stremio/provider/repository HTTP-út fut, a tracker-transzport stub.
- **`Új` bővítések:**
  - indexerenként beállítható késleltetés, időtúllépés, hiba és ingadozás;
  - nCore Tech Info-végpont stub késleltetéssel és hibaaránnyal;
  - rövid TTL-ek konfigurációból, az SP07-hez.
- **Profilok:**
  - **S1:** minden tracker egészséges;
  - **S2:** egy tracker nem válaszol;
  - **S3:** egy tracker lassú, de válaszol (pl. 8 s);
  - **S4:** ingadozó tracker.

**H3 — késleltető TCP-proxy (SP03, SP09)**
- `Új` asyncio-alapú proxy a kliens és a szerver között, beállítható RTT-vel (1/20/80 ms).
- `tc netem` és `NET_ADMIN` jogosultság nem kell.

<!-- doc-anchor:doc-24-kozos-meresi-protokoll-es-kapu -->
<a id="doc-24-kozos-meresi-protokoll-es-kapu"></a>
### 2.4. Közös mérési protokoll és kapu

- **Referenciák:**
  - A = upstream `s4pp1/stremhu-source` image;
  - B = fork `main` image;
  - C = branch image.

  Mindegyik digesttel, CPU- és memóriakerettel rögzítve; alapkeret 2 CPU / 1 GiB, ahogy a `burst27`-nél. Upstreamen hiányzó funkció (pl. Tech Info, trackercache): `N/A`.
- **C előtte/utána:** ugyanazon C image-en a policy kapcsolója (2.5) adja: a legacy és a jelölt, azonos builddel.
- **Előregisztráció:** a protokoll JSON a futás előtt kerül commitba (`docs/feature/stream-performance/evidence/<kapu>-vN-protocol.json`), forrásmanifesttel (SHA-256), ahogy a stabilitási ágon. Utána a `complete`, `summary` és `assessment` JSON.

  A kapu szabálya utólag nem igazítható. Új változat új verziószámmal regisztrálandó, a régi FAIL is megmarad.
- **Futtatás:**
  - A/B/C szekvenciálisan, ismétlésenként rotált sorrendben;
  - legalább 5 ismétlés;
  - cold és warm külön, az előmelegítés nem része a mintának;
  - minden futás friss, eldobható kötettel.
- **Zaj:** a változatlan C kétszer, ugyanazzal a protokollal. Metrikánként `J = max(a két baseline mediánjának eltérése, mérési felbontás)`.
- **Elfogadás:**
  - helyes eredmény, nulla új funkcionális hiba, OOM és timeout;
  - a célmetrika javulása legalább két ismételt sorozatban nagyobb J-nél;
  - mellékmetrikák (CPU, RSS, többletforgalom) az előre rögzített kereten belül.

  Negatív kapu esetén a csomag eredménye a mért elvetés; „csak azért is” implementáció nincs.
- **UX/SLO-keret:** a felhasználó a mérések előtt rögzíti (7. fejezet), utólag nem igazítható az eredményhez.

<!-- doc-anchor:doc-25-konfiguracio-es-visszaallitas -->
<a id="doc-25-konfiguracio-es-visszaallitas"></a>
### 2.5. Konfiguráció és visszaállítás

- **Kapcsoló:** minden viselkedést változtató policy (SP01, SP02, SP05/b, SP06/b, SP07) `Új` `config.py`-mezővel kapcsolható.
  - Az alapérték a legacy viselkedés, amíg a kapu nem PASS.
  - Az alapérték átállítása külön commit.
  - A legacy ág eltávolítása csak egy későbbi, külön csomag.
- **Plug & play:** minden mezőnek van alapértéke. Felhasználói felületen csak termékdöntés után jelenik meg, a meglévő `relay_settings` mintára.
- **Visszaállítás:** a mező legacy értékre állítása, újraindítással. DB-séma nem változik.

<!-- doc-anchor:doc-3-lejatszas-relay-es-streamvalasz -->
<a id="doc-3-lejatszas-relay-es-streamvalasz"></a>
## 3. Lejátszás: relay és streamválasz

<!-- doc-anchor:sp01 -->
<a id="sp01"></a>
### SP01 — Előtöltési ablak és prioritáspolitika lejátszás közben

**Forrás:**
- `relay/entities.py`:
  - `Torrent.__init__:47–55` (`critical_piece_count`, `prefetch_piece_count`);
  - `priority_manager:83–111`: aktív streamnél az egész torrent `PRIO_0`;
  - `get_deadlines:120–176`;
  - `Stream.get_critical_pieces:372–385`: holt kód, nem hívja semmi.
- `relay/service.py`:
  - `trigger_priority_update:128`, `priority_manager_loop:145–160`;
  - `piece_finished_alert:613–619`;
  - session-beállítások `:58–80` (`piece_timeout` 10, `request_timeout` 30, `strict_end_game_mode` False).
- `torrents/service.py:_get_priority:229–234`: teljes letöltésnél PRIO_1, egyébként PRIO_0.

**Jelenlegi működés (forrásból):**

| Darabméret | `critical_piece_count` | `prefetch_piece_count` | Határidős ablak |
|---|---|---|---|
| 256 KiB | 2 | 8 | 2 MiB |
| 512 KiB | 2 | 8 | 4 MiB |
| 1 MiB | 1 | 4 | 4 MiB |
| 2 MiB | 1 | 4 | 8 MiB |
| 4 MiB | 1 | 4 | 16 MiB |
| 16 MiB | 1 | 4 | 64 MiB |

- **Határidők** az aktuális darabtól mért távolság szerint: 0 ms, 1 darab → 300 ms, egyébként `1000 + 500·d` ms. Az upstream `2000 + 1000·d` ms-ot használ.
- **Ablak:** az aktuális darabtól előre számolja a hiányzó darabokat. Fájlvég közelében a fájl elejére fordul.
- **Minden más darab** aktív streamnél 0 prioritású, vagyis nem töltődik. Ez a teljes letöltésű (H&R) torrentekre is igaz; a stream végén visszaáll az alapprioritás.

**Hipotézis (nem mért):**
- Kis darabméretnél és nagy bitrátánál az ablak 1–2 másodpercnyi videó. Egy késő darab ezért akadást okoz.
- A kevés párhuzamosan kérhető blokk korlátozza az átvitelt sok peer mellett.

**Jelölt policy** (`Új` mezők: `relay_readahead_policy` `legacy|window`, `relay_readahead_bytes`, `relay_readahead_max_pieces`, `relay_readahead_tail_priority`; értékeiket a GSP01 választja):

```text
window_pieces = clamp(ceil(readahead_bytes / piece_size), min=4, max=readahead_max_pieces)
missing = az aktuális darabtól előre hiányzó darabok (a fájlvégi körbefordulás a legacy szerint), legfeljebb window_pieces
deadline(d=0) = 0; deadline(d=1) = 300
deadline(d>=2) = 1000 + distance_bytes * 1000 / assumed_rate    # darabméret-független, monoton
tail (csak C3): az aktív fájl ablakon túli darabjai readahead_tail_priority (pl. 1);
                a többi fájl a torrent alapprioritásán marad (teljes letöltésnél PRIO_1, különben 0)
stream vége: pontosan a mai visszaállítás (alapprioritás), határidők törlése
```

**Kapujelöltek:**
- **C0:** legacy;
- **C1:** 16 MiB-os ablak;
- **C2:** 32 MiB-os ablak;
- **C3:** a C2 és 1-es tail-prioritás.

Ha egyik sem PASS, a mért ok szerint új verzió regisztrálható. Ilyen lehet például egy megfigyelt olvasási sebességből számolt, adaptív ablak; vak paraméterkeresés nem.

**Invariánsok:**
- Az ablak felülről korlátos (`max_pieces`), így a prioritásfrissítés natív hívásainak száma is korlátos.
- A határidők a távolsággal nem csökkennek.
- Ugyanazon fájl több streamjénél darabonként a minimum határidő él.
- A `is_destroying` stream kimarad.
- Stream nélkül pontosan a mai alapprioritás áll vissza.
- A határ- és feliratdarabok logikája ebben a csomagban nem változik (az SP02 külön csomag).
- Legacy módban a kimenet bitre azonos a mai algoritmuséval.

**Tesztek** (`Új` `server/tests/test_relay_readahead_policy.py`, FakeHandle `have_piece`/`piece_priorities` naplóval):

| E | B | M | V |
|---|---|---|---|
| Aktív stream a 0. darabon, semmi sincs meg | 256 KiB, 1, 4, 16 MiB-os darab | `get_deadlines` | `window_pieces` számú határidő, az első 0, monoton, korlát alatt |
| Az ablak egy része megvan | Vegyes `have_piece` | `get_deadlines` | A meglévő darabot átugorja, a hiányzókat az ablakig számolja |
| Fájlvég közelében | Az aktuális darab az utolsó előtti | `get_deadlines` | A körbefordulás a legacy szemantika szerint, ablakon belül |
| Két stream egy fájlon | Eltérő pozíciók | `get_deadlines` | Darabonként a minimum; összesen legfeljebb 2 × ablak |
| Stream lezárás alatt | `is_destroying=True` | `get_deadlines` | Kimarad |
| C3 tail | Teljes letöltésű és normál torrent | `priority_manager`, majd stream vége | Az ablakon túli rész 1-es; a többi fájl az alapprioritáson; a stream vége után a mai állapot |
| Legacy kapcsoló | Előre rögzített bemenetmátrix | Legacy és a mai algoritmus | Azonos kimenet (golden) |

A holt `get_critical_pieces` eltávolítása önálló, viselkedésváltozás nélküli lépés ugyanebben a csomagban. Kódkeresés igazolja, hogy nincs hívója.

**GSP01 kapu (H1):**
- **Mátrix:**
  - darabméret 1/4/16 MiB, a 256 KiB-os éleset a fast profilon;
  - fast, mixed és thin profil;
  - bitráták az UX-döntés szerint.
- **Forgatókönyv:** indítás a 0. bájtról, folyamatos lejátszás (pl. 5 perc vagy 1 GiB), tekerés 50%-ra, megállítás.
- **Metrikák:**
  - TTFB és indulási idő (a puffer küszöbig);
  - akadások száma és összideje;
  - fenntartott átvitel;
  - tekerés utáni újraindulás;
  - konténer-CPU;
  - `priority_manager` futásidő p95;
  - leállítás után letöltött, fel nem használt bájt;
  - RSS.
- **Elfogadás (előre regisztrálva):**
  - mixed és thin profilon az akadás-összidő és az indulási idő J-n túl javul, két sorozatban;
  - fast profilon nincs J-n túli romlás;
  - CPU és többletforgalom az UX-kereten belül;
  - nulla funkcionális hiba.

**Visszaállítás:** `relay_readahead_policy=legacy`.

<!-- doc-anchor:sp02 -->
<a id="sp02"></a>
### SP02 — Indulási darabsorrend

> **Döntés (2026-11-10):** a `gsp02-v1`–`v3` FAIL után a `gsp02-v4` (bootstrap/Holm szabály) PASS:C2: alapértelmezés az upstream-szerű `edges` + `upstream`. A részletek és a fenntartás a [végrehajtási állapotban](../stream-performance.md#execution-status); a `graded`, `focus` és `startfocus` jelöltek elvetve.

**Forrás:**
- `relay/entities.py`:
  - `_set_file_boundary_priorities:178–191`;
  - `_set_matched_subtitle_priorities:193–204`;
  - `File.get_matched_subtitle_pieces:229–274`.
- A meglévő `server/tests/test_stream_optimizations.py:test_relay_file_boundary_priorities:318–353` a 0-s határidőt rögzíti. Ezt a teszt a csomagban szándékosan, dokumentált szerződésváltozásként módosul.

**Jelenlegi működés:**
- Aktív streamnél a fájl első és utolsó `min(3, darabszám//2)` hiányzó darabja mindig 0 ms-ot kap.
- Ez 16 MiB-os darabnál akár 96 MiB „azonnal kell” adat, az aktuális streamdarabbal (szintén 0) egy szinten.
- A párosított feliratdarabok (legfeljebb 6, csak kis feliratok) 500 ms-ot kapnak.
- Az upstreamben ugyanez a határdarab-logika él.

**Mért háttér (`pb0-v2`, leíró):** a fork indulása az upstreamnél J-n túl lassabb: fast/4 MiB 6,8 s vs 4,6 s, fast/16 MiB 13,2 s vs 8,9 s, és 16 MiB-os darabnál a fájlvég-próba ~4,2 s vs 0,05 s. A forrásdiff szerint az upstream csak a fájl első és utolsó darabját sürgeti (1+1), a fork az első és utolsó 3-at (6 darab, 0 ms). Az okot a GSP02 igazolja.

**Hipotézis:**
- Nagy darabméretnél az első lejátszható bájt később érkezik, mert a sürgős darabok egymással versenyeznek.
- A fájlvég-próba (MP4 `moov`, MKV cues) igénye kicsi, ezért bájtkorláttal is kiszolgálható.

**Jelölt** (`Új` `relay_start_policy` `legacy|graded`, `relay_head_bytes`, `relay_tail_bytes`):
- Az aktuális streamdarab marad az egyetlen 0 ms-os.
- **Fej:** a fájl első `head_bytes`-nyi része (pl. 2 MiB, legalább 1 darab). Csak akkor kap 0-t, ha a stream ott indul, egyébként 1000 ms-ot.
- **Vég:** az utolsó darab 200 ms. A további, `tail_bytes`-ig (pl. 4 MiB) terjedő végdarabok 1000 ms-tól fokozatosan.
- **Felirat:** változatlan 500 ms. A sorrendjét a kapu méri.

**Kapujelöltek:**
- **C0:** legacy;
- **C1:** fokozatos határidők a mai darabszámmal;
- **C2:** fokozatos és bájtkorlátos.

**Tesztek:**
- darabméret-mátrix;
- egy- és kétdarabos fájl;
- a fájl közepéről induló stream (tekerés), ahol az aktuális darab az első;
- változatlan feliratdarabok;
- legacy golden.

**GSP02 kapu (H1):**
- **Mátrix:** fájlvégi indexű MP4 és MKV fixture, 1/4/16 MiB-os darab, fast és mixed profil.
- **Metrikák:** a `bytes=0-` TTFB-je, a fájlvég-próba válaszideje, indulási idő, tekerés.
- **Elfogadás:** az előre rögzített szabály szerint, ugyanúgy, mint a GSP01-nél.
- **Sorrend:** az SP01 előtt fut, mert kisebb változás, és az indulási hatást elkülöníti.

**Visszaállítás:** `relay_start_policy=legacy`.

<!-- doc-anchor:sp03 -->
<a id="sp03"></a>
### SP03 — Lejátszási előzmény a válasz előtt

**Forrás:**
- `stream/router.py:stream:67–171`:
  - `verify_api_key` `:81`;
  - `check_playback_limit` `:89`;
  - `prepare_for_stream` `:101`;
  - `await save_playback_history` `:118`, a fejlécek előtt.
- `stream/service.py:save_playback_history:125–150`: `playback_history_lock`, szálváltás, izolált session, `get_or_create`.

**Tény:**
- Minden GET és HEAD Range-kérés megvárja a zárat, a szálváltást és egy SQLite-session megnyitását.
- Az első kérésnél beszúrás és commit történik, a többinél olvasás.
- A lejátszók indításkor több Range-kérést küldenek, és tekerésenként újat.

**Hipotézis:** az indítás és a tekerés TTFB-je ennyivel nő, SQLite-írási versengésnél (resume-író, torrentírások) többel. A nagyság ismeretlen.

**Terv:**
1. **Ismétlődő írás elhagyása:** `Új` process-szintű `RecentPlaybackHistory` (TTL pl. 6 h, kapacitás pl. 4096, kulcs: `playback_id`). Ha a playback már sikeresen rögzült, az újabb kérés nem nyúl a DB-hez. Ez megegyezik a mai `get_or_create` olvasási eredményével.
2. **Első írás a háttérben:** tulajdonolt háttértaskként fut, korlátos halmazzal (pl. legfeljebb 64 függő írás). Túlcsordulásnál szinkron tartalék, hogy írás ne vesszen el. Hiba esetén nincs „rögzült” jelölés, a következő kérés újrapróbál. A lifespan lezárás a CR17 mintájára megvárja vagy törli a függő írásokat.
3. **HEAD:** ugyanez a szabály.

**Invariánsok:**
- Az auth megelőzi az írást (CR09 sorrend).
- A lejátszási limit szemantikája változatlan, mert az aktív streameket számolja.
- Az előzmény playbackenként végül pontosan egyszer rögzül.
- A hibanapló titokmentes (`network_error_fields`).
- A dashboard aktív lejátszása legfeljebb az írás idejéig hiányozhat.

**Tesztek:**

| E | B | M | V |
|---|---|---|---|
| Első kérés | Új `playback_id` | GET | Egy írás ütemezve, a válasz nem vár rá |
| Ismétlés | Ugyanaz a `playback_id`, 10 Range | GET/HEAD | Nincs újabb DB-hívás |
| Írási hiba | A repository kivételt dob | GET, majd GET | A stream nem sérül; a második kérés újrapróbál; a napló titokmentes |
| Túlcsordulás | Telt függő halmaz | GET | Szinkron írás, nincs elvesztett előzmény |
| Leállítás | Függő írás | Lifespan lezárás | Megvárva vagy törölve; nincs árva task |

**Kapu (H1 + H3):**
- **Forgatókönyv:** letöltött (warm) torrent, 20 egymás utáni Range-kérés. Párhuzamos szintetikus DB-írási terheléssel és anélkül, 1 és 20 ms-os RTT mellett.
- **Metrikák:** TTFB p50/p95, elvesztett írás (0 kell).
- **Elfogadás:** TTFB-javulás J-n túl. Ha nincs J-n túli javulás, a csomag a stabilitási szabály szerint nem kerül be.

<!-- doc-anchor:sp04 -->
<a id="sp04"></a>
### SP04 — Darabolvasás átfedése a küldéssel

**Forrás:**
- `relay/entities.py:Stream._stream_inner:394–454`;
- `relay/service.py`: `get_piece_data:247–265` (megosztott task, `shield`), `_fetch_piece_with_retry:309–331`, `_fetch_piece_once:333–352`, `read_piece_alert:621` és utána.

**Tény:** a következő darab `read_piece`-e csak akkor indul, amikor az előző darab minden darabkáját elküldte. Darabonként egy lemezolvasás és egy alert-kör sorosan adódik.

**Hipotézis:** letöltött, nagy bitrátájú fájlnál és kis darabméretnél ez csökkenti az átvitelt.

**Terv** (`Új` `relay_piece_read_lookahead_bytes`, 0 = kikapcsolva):
- A N. darab megérkezése után az N+1. darab olvasása is elindul, a meglévő megosztott `get_piece_data` taskkal.
- Csak akkor, ha a darabméret legfeljebb a beállított bájtkorlát.
- Streamenként legfeljebb 1 előreolvasott darab, így a memória legfeljebb 2 darab streamenként.
- Lecsatlakozáskor a saját hivatkozás eldobva. A megosztott task a saját befejezéséig fut, a `_piece_fetch_tasks` takarítása változatlan.

**Invariánsok:**
- A sorrend megmarad.
- Lecsatlakozás után nincs új olvasás.
- Az előreolvasás hibája csak akkor jelenik meg, amikor az a darab sorra kerül.
- A `PieceReadAbortedError` torrent-eltávolításkor továbbra is terjed.
- A stream vége után nincs árva task (taskszám-teszt).

**GSP04 kapu (H1):**
- **Forgatókönyv:** letöltött fájl, 1 és 4 MiB-os darab, a kliens a lehető leggyorsabban olvas. Mellette a GSP01 lejátszási profilja regressziókontrollként.
- **Metrikák:** átvitel, CPU, RSS.

<!-- doc-anchor:sp10 -->
<a id="sp10"></a>
### SP10 — Beragadó peerek indulási büntetése

**Forrás:** `relay/service.py` session-beállítások `:58–80` (`piece_timeout` 10 s, `request_timeout` 30 s,
`strict_end_game_mode` False; az upstreammel azonosak); `relay/entities.py` határidő-kezelés.

**Tény (`pb0-v2`, leíró):** a mixed profilban 8 peerből 2 elfogadja a blokk-kérést, de nem válaszol. Az első bájt
13–18 s (4 és 16 MiB-os darab), a seederhez kapcsolódás után 12–15 s; A és B között nincs érdemi különbség.

**Hipotézis:** a határidős (time-critical) blokkok egy része a nem válaszoló peernél ragad, és csak időtúllépés
után kerül másik peerhez.

**Terv:**
1. A G0-próba bővítése: egy beragadó és több gyors peer mellett mérni, mennyi idő után kéri újra a libtorrent a
   határidős blokkot, és ez hogyan függ a `piece_timeout`, `request_timeout`, `peer_timeout` és a snub-logika
   beállításaitól. Vak hangolás nincs: csak a próbában mért hatású beállítás lehet jelölt.
2. **Jelöltek** (`Új` kapcsoló mögött, alapérték a mai): aktív streamnél rövidebb időkorlát a határidős
   kérésekre, vagy a lassú/beragadó peer kizárása a határidős darabokból.
3. **GSP10 kapu (H1):** a mixed profil 1/4/16 MiB-os cellái 8/30/60 Mbit/s-on; fő metrika az indulási idő;
   mellékmetrika a fast és thin profil (nincs J-n túli romlás).

**Függés:** az SP02 döntése után, mert az indulási sorrend és a beragadó blokkok hatása összeadódik.

<!-- doc-anchor:sp09 -->
<a id="sp09"></a>
### SP09 — `Connection: close` minden streamválaszon

**Forrás:**
- `stream/router.py:126–131`;
- upstream: `8c99c7d` `server/app/modules/stream/router.py:100–101`, bevezette `92fcb8d` („Kapcsolat zárása stream befejezésekor (#274)”).

**Tény:** minden Range-kérés új TCP-, HTTPS-nél TLS-kapcsolatot nyit.

**Hipotézis:** nagy RTT-jű kapcsolaton (távoli hozzáférés, Tailscale) a tekerés és az indulás kérésenként egy-két többlet-RTT-t fizet.

**Terv:**
1. A #274 indokának feltárása (upstream diff és issue). Ha a lezárás a lecsatlakozás-felismerést vagy a generátor felszabadítását szolgálja, az invariáns.
2. H3-mal mérni a kézfogás költségét Range-sorozatokon, 1/20/80 ms-os RTT-vel.
3. **Jelölt:** keep-alive csak a sikeresen, teljes egészében kiszolgált 206-os válaszoknál.

**Kompatibilitási kapu (G-kompat):** natív kliensek a felhasználó kézi tesztjével: Stremio desktop, Android, Android TV, iOS, valamint Kodi és VLC.

**Alapértelmezés:** nincs változás, csak J-n túli nyereség **és** kompatibilitási PASS esetén.

<!-- doc-anchor:doc-4-talalatlista-kereses -->
<a id="doc-4-talalatlista-kereses"></a>
## 4. Találatlista: keresés

<!-- doc-anchor:sp05 -->
<a id="sp05"></a>
### SP05 — Tracker-egészség és rövidzár

**Forrás:**
- `indexers/search.py`:
  - `get_torrents_by_torrent_id:63–120` (`timeout=12.5` `:98`);
  - `get_torrents_by_imdb_id:153–232` (`:210`);
  - `get_torrents_by_query:234–319` (`:297`);
  - `invalidate_indexer_cache:25–36`.
- `config.py:145` (`source_search_deadline_seconds` 15).
- `torrent_source_provider/service.py`: `_search_stage:220–229`, `_download_and_store:409–512` (csak a maradék határidőn belül tölt).
- Invalidálási hívók: `indexers/service.py:86, :149`.

**Tény:**
- Három azonos `fetch_and_map_with_timeout` másolat.
- A `gather` minden trackert megvár.
- Az időtúllépés nem cache-elődik, ami helyes. Ezért minden hideg keresés újra kivárja a nem válaszoló trackert.
- 15 s-os határidő mellett egy 12,5 s-os várakozás után legfeljebb 2,5 s marad a .torrent letöltésekre, így a találatok hiányosak lehetnek.

**SP05/a (viselkedésváltozás nélkül):**
- A három másolat egy `Új` `_fetch_with_timeout(indexer_account, op)` segédbe kerül.
- A hibaüzenet szövege változatlan.
- Teszt: a három út azonos hibaüzenetet és eredményt ad.

**SP05/b (policy, kapus):** `Új` process-szintű `IndexerHealth` regiszter, `indexer_id` szerint.
- **Számít:** `TimeoutError` és kapcsolódási hiba.
- **Nem számít:** hitelesítési hiba, feldolgozási hiba és lassú, de sikeres válasz.
- **Nyitás:** K egymás utáni hiba után (`Új` `indexer_breaker_threshold`; 0 = kikapcsolva, a jelölt 2) a tracker T ideig kimarad (`indexer_breaker_cooldown_seconds`, jelölt 120 s). Ismétlődéskor a T duplázódik `..._max_seconds`-ig (jelölt 600 s).
- **Kimaradás alatt:** hálózati kérés nélkül hibaüzenet: „‹név›: átmenetileg kihagyva, nem válaszolt; újrapróba kb. N s múlva”.
- **Lejárat után:** egyetlen próbakérés megy ki, a többi egyidejű kérés addig kihagyja. Sikerre a tracker visszaáll.
- **Alaphelyzet:** `invalidate_indexer_cache(indexer_id)` hívásakor (beállítás, bejelentkezés) a regiszter is nullázódik.
- **Hatókör:** csak keresés; a .torrent letöltésnek saját hibakezelése van. Csak az event loopról használható, egy processzre.

**Tesztek:**

| E | B | M | V |
|---|---|---|---|
| Egészséges tracker | Sikeres válaszok | Keresés | Nincs többletkésleltetés, nincs nyitás |
| K időtúllépés | Stub timeout | K keresés | Nyitva; a következő keresés hálózati hívás nélkül hibaüzenetet ad |
| Lejárt kihagyás | Párhuzamos keresések | Keresés | Pontosan egy próbakérés; a többi kihagy |
| Próba sikeres | | | Zárt, számláló nulla |
| Próba sikertelen | | | Dupla T, felső korláttal |
| Invalidálás | Nyitott állapot | `invalidate_indexer_cache` | Zárt |
| Hitelesítési hiba / lassú siker | | Keresés | Nem számít hibának |
| Több tracker | Egy rossz, egy jó | Keresés | Egymástól független |

**GSP05 kapu (H2, S1–S4):**
- **Metrikák:** hideg streamválasz p50/p95, forrásszám és egyezés a baseline-nal, kérésszám a rossz trackerre percenként, részleges-eredmény jelzés aránya.
- **Elfogadás:**
  - S2-ben a nyitás után a p50 J-n túl csökken;
  - S1-ben és S3-ban J-n belül változatlan, azonos forrásokkal;
  - S3-ban a breaker soha nem nyit.

Az adaptív időkorlát (SP05/c) halasztott, csak akkor kerül elő, ha az S3-típusú lassúság dominál.

<!-- doc-anchor:sp06 -->
<a id="sp06"></a>
### SP06 — Tech Info a kritikus úton

**Forrás:**
- `torrent_streams/service.py`:
  - `_enrich_torrent_streams_with_tech_info:358–416`: a jelöltek az első 5 torrentcsoport a forrássorrendben (`:381–397`); `asyncio.wait_for(..., 1.5)` (`:406–411`);
  - `_enrich_torrent_group:418–453`: cache csak sikeres lefutás után, TTL 3600 s, kapacitás 5000 (`:47–49`);
  - hívói: `find_by_imdb:282`, `find_by_torrent_id:353`.
- `indexer_definitions/integrations/ncore.py:fetch_tech_info:267–313`: két soros HTTP-kérés, egyenként 1,5 s. A kivételt elnyeli és `(None, None)`-t ad vissza.
- Az alaposztály alapértéke `(None, None)` (`base_indexer_definition.py:533`).

**Tény:**
1. Nem cache-elt válasznál legfeljebb +1,5 s a keresés után, sorban.
2. A külső időtúllépés a `gather`-t és benne a lekéréseket törli. Semmi nem kerül cache-be, így a következő nem cache-elt kérés újra fizeti az időt.
3. Ha a belső HTTP-hiba a külső korláton belül történik, a `(None, None)` üres metaadatként 1 órára cache-elődik. Ilyenkor a nyelvi attribútumok egy óráig hiányoznak.

**SP06/a (helyesség, implementálható):**
- A `fetch_tech_info` különböztesse meg a „nincs adat” és a „lekérés sikertelen” esetet: `Új` `TechInfoUnavailable` kivétel vagy állapotjelző.
- A sikertelen eredmény nem, vagy csak rövid ideig (`Új` `tech_info_negative_ttl_seconds`, jelölt 60 s) cache-elődik.
- Az alaposztály szemantikája (nincs támogatás) változatlan.

**SP06/b (kapus):**
- **Korábbi indítás:** a Tech Info előtöltése a megosztott keresésben (`_SourceSearch`) indul, a trackerfázis után, a .torrent letöltésekkel párhuzamosan.
  - Kulcsok: a Tech Info-t támogató indexerek találatai közül seederszám szerint a legjobb N (jelölt 5).
  - A Tech Info felhasználófüggetlen, ezért a megosztott keresésben a helye.
  - Nem nyújthatja meg a megosztott keresést: tulajdonolt háttértaskként indul, nem awaitolja.
- **Korlátok:** process-szintű kapacitás (jelölt legfeljebb 20 egyidejű lekérés) és kulcsonkénti in-flight deduplikáció.
- **Kérés oldalán:** a meglévő 1,5 s-os keretből csak a hátralévő időt várja a függő kulcsokra. Időtúllépéskor a háttértask fut tovább, és feltölti a cache-t.
- **Lezárás:** a lifespan lezárás törli és megvárja a taskokat (CR17 minta).

**Tesztek:**
- sikertelen lekérés nem kerül 1 órára cache-be, sikeres üres igen;
- kulcsonként egy lekérés;
- a kapacitás tartva, a többlet kihagyva;
- a kérés a kereten belül válaszol;
- időtúllépés után a háttér befejezi, a második kérés már nem kér;
- leállításkor nincs árva task;
- gyors válasznál az attribútumok azonosak a baseline-nal.

**GSP06 kapu (H2):**
- **Mátrix:** a Tech Info-stub késleltetése 0,2/1,0/2,0 s, 10% hibaarány.
- **Metrikák:** hideg p50/p95, cache-találat a második kérésnél, attribútum-helyesség a fixture-höz képest.

<!-- doc-anchor:sp07 -->
<a id="sp07"></a>
### SP07 — Lejárt trackercache: régi találat azonnal, frissítés a háttérben

**Forrás:** `indexers/search.py`:
- `:16–23`: TTL 1800 s és 300 s, kapacitás 1000;
- `:163–189`: lejáratkor eltávolítás, majd teljes lekérés;
- a kulcs része a `source_epoch` (`:157`, `:163`);
- invalidálás `:25–36`.

**Tény:** lejárat után a következő kérés a teljes trackerkeresést kivárja.

**Terv:**
- **Két TTL:**
  - a mai 1800 s a puha TTL;
  - `Új` `indexer_cache_hard_ttl_seconds` (0 = kikapcsolva) a kemény TTL, értéke UX-döntés (jelölt 6 vagy 24 óra).
- **Puhán lejárt találat:** azonnal a régi lista jön, `stale` jelzéssel, és kulcsonként egyetlen háttérfrissítés indul (in-flight halmaz).
  - A háttérfrissítések száma globálisan korlátos (jelölt 4).
  - Nem foglal felhasználói admission-helyet, de az adapter szemaforját betartja.
  - Frissítési hiba esetén a régi lista a kemény TTL-ig marad.
- **Új epizód védelme:** ha a régi lista a kért epizódra vagy filmre 0 lejátszható streamet ad, a `find_by_imdb` szinkron, kényszerített frissítést kér a név szerinti tartalék előtt.

  Ehhez a provider `find_by_imdb_id` `Új` `allow_stale` paramétert kap, a singleflight-kulcs része a jelző. Hívók: `stremio/service.py:340`, `torrent_streams/service.py:97–127`.
- **Nem változik:** a lekérdezéscache (300 s) ebben a csomagban; az invalidálás (`source_epoch`, `invalidate_indexer_cache`) a régi bejegyzést is törli.

**Tesztek (hamis órával):**
- friss találat;
- puhán lejárt: azonnal régi lista és pontosan egy frissítés;
- párhuzamos kérések egy frissítésen osztoznak;
- frissítési hiba: a régi lista marad;
- keményen lejárt: szinkron frissítés;
- invalidálás és epoch-váltás: nincs régi találat;
- új epizód: a régi listán nincs, a szinkron frissítés megtalálja.

**GSP07 kapu (H2, rövid TTL-ekkel):**
- **Metrikák:** puha lejárat utáni p50 a meleg úthoz képest, trackerkérés-szám, helyesség az új feltöltés esetén.

<!-- doc-anchor:sp08 -->
<a id="sp08"></a>
### SP08 — A név szerinti tartalékkeresés soros lánca

**Forrás:** `torrent_streams/service.py:167–279`, `_build_fallback_queries:781–839`.

**Tény:**
- Csak akkor fut, ha az IMDb-keresés nem ad streamet.
- A lekérdezések egymás után mennek, mindegyik minden trackerhez, a 20 s-os keretet csak a lekérdezések között ellenőrzi.

**Terv:**
- Előbb mérés: tipikusan hány jelölt fut a sikerig. Valós címlista csak a felhasználótól, opcionálisan.
- **Jelölt:** az első két lekérdezés párhuzamosan, az első siker a többit törli.
- **Várható eredmény:** nincs változtatás, mert a párhuzamosítás a trackerterhelést növeli.
- **Függés:** SP05 (a rövidzár a lánc farkát is rövidíti).

<!-- doc-anchor:doc-meleg-ut-profilja-gsp-w-nem-tetel -->
<a id="doc-meleg-ut-profilja-gsp-w-nem-tetel"></a>
### Meleg út profilja (GSP-W, nem tétel)

- **Mit mér:** a 0. csomagban a meleg streamválasz idejének megoszlását. Meleg: trackercache-találat, a .torrent fájlok a DB-ben.
- **Fázisok:** DB-snapshot betöltés, `TorrentStream.from_imdb_id` fájlfeloldás (évadcsomagoknál), szűrés, rendezés és deduplikáció, szerializálás.
- **Eszköz:** H2 és a beépített `cProfile`; új profilozó függőség nem kell.
- **Döntés:** ha egy fázis a meleg p50 előre rögzített részénél többet visz, új SP-tétel javasolható. Automatikus implementáció nincs.

<!-- doc-anchor:doc-5-munkacsomag-tabla -->
<a id="doc-5-munkacsomag-tabla"></a>
## 5. Munkacsomag-tábla

A sorszám a munkacsomagok sorrendje. Egy csomag egy commit, vagy kis, önállóan ellenőrizhető commitsor.

| Sorrend / csomag | Prioritás | Függés, belépés | Ellenőrizhető eredmény |
|---|---|---|---|
| 0 — G0 + H1/H2/H3 + baseline | kötelező | Külön implementációs engedély; tiszta kiindulás | A libtorrent-viselkedés próbája; mérőeszközök smoke-tesztje; zaj és A/B/C baseline minden kapuhoz; GSP-W profil. Termékkód nem változik. |
| 1 — SP03 | P1 | G0 3. pont (fogyasztók igazolva) | Az előzménymentés nem blokkol, playbackenként egy írás, lezárás tesztelve; kapudöntés |
| 2 — SP05/a | P1 | — | Egy időkorlát-segéd, viselkedésváltozás nélkül |
| 3 — SP06/a | P2 | — | Sikertelen Tech Info-lekérés nem mérgezi 1 órára a cache-t |
| 4 — GSP02 → SP02 | P1 | H1, UX-keret | Fokozatos indulási sorrend vagy mért elvetés |
| 5 — GSP01 → SP01 | P1 | SP02 döntése, H1, UX-keret | Bájtalapú előtöltési ablak vagy mért elvetés; holt kód eltávolítva |
| 5b — GSP10 → SP10 | P1 | SP02 döntése, a G0-próba bővítése | Beragadó peerek kezelése, vagy mért elvetés |
| 6 — GSP05 → SP05/b | P1 | SP05/a, H2 | Tracker-rövidzár vagy mért elvetés |
| 7 — GSP06 → SP06/b | P2 | SP06/a, H2 | Korábban induló, háttérben befejeződő Tech Info, vagy mért elvetés |
| 8 — GSP07 → SP07 | P2 | SP05/b döntése, UX-döntés a kemény TTL-ről | Azonnali régi találat háttérfrissítéssel, vagy mért elvetés |
| 9 — GSP04 → SP04 | P3 | SP01 döntése | Átfedő darabolvasás vagy mért elvetés |
| 10 — GSP08 → SP08 | P3 | SP05/b | Várhatóan nincs változtatás, dokumentált méréssel |
| 11 — SP09 kompatibilitási kapu | P3 | #274 feltárása, H3, natív kliensteszt | Várhatóan nincs változtatás |
| 12 — Lezárás | kötelező | Az összes döntés | Feature-referencia, upstream-diffmátrix, bizonyítékok, PR |

**Indok:**
- Először a kis, kockázatmentes és helyességi javítások jönnek (SP03, SP05/a, SP06/a), mert ezekhez nem kell policydöntés.
- Utána a lejátszás, mert itt várható a legnagyobb érezhető hatás, de ehhez a H1 kell.
- Végül a keresési policyk és a valószínűleg változtatás nélkül záruló tételek.

<!-- doc-anchor:doc-csomagonkenti-keszultseg-minimuma -->
<a id="doc-csomagonkenti-keszultseg-minimuma"></a>
### Csomagonkénti készültség minimuma

**Belépés:**
- a táblázatban szereplő függések teljesülnek;
- az adott HEAD-hez friss forráshivatkozások vannak;
- a regisztrált protokoll és baseline megvan;
- a visszaállítási út ismert.

**Kilépés:**
- a tétel tesztmátrixa sikeres;
- Ruff, basedpyright és a teljes pytest sikeres;
- a helyi Docker funkcionális teszt lefutott;
- a kapudöntés dokumentált a [végrehajtási állapotban](../stream-performance.md#execution-status).

Negatív kapu után a kész eredmény a mért elvetés. Hipotézis nem írható át ténnyé.

<!-- doc-anchor:doc-6-kockazatok -->
<a id="doc-6-kockazatok"></a>
## 6. Kockázatok

| Kockázat | Érintett | Kezelés |
|---|---|---|
| Nagyobb ablak több sávszélességet és lemezt használ, leállításkor fel nem használt adat marad | SP01 | Felső korlát; a többletforgalom mért mellékmetrika UX-kerettel |
| A prioritásfrissítés natív hívásai nőnek | SP01 | `max_pieces` korlát; a `priority_manager` futásideje mért metrika |
| A szintetikus swarm nem valós hálózat | SP01, SP02 | Több profil (beragadó és lassú peer); a végső kép a felhasználó kézi tesztje valós trackerrel |
| A rövidzár egy éppen helyreálló trackert kihagy | SP05 | Rövid, duplázódó kihagyás; egy próbakérés; látható hibaüzenet; invalidáláskor alaphelyzet |
| A régi találatból hiányzik az új epizód | SP07 | Szinkron frissítés, ha a régi lista 0 streamet ad |
| Háttértaskok halmozódása | SP03, SP06, SP07 | Minden háttérmunkának kapacitása, deduplikációja és lifespan-lezárása van (AGENTS 3.) |
| Keep-alive lejátszói inkompatibilitás | SP09 | Alapértelmezésben nincs változás; natív kliensteszt kapu |

<!-- doc-anchor:doc-7-nyitott-kerdesek-es-dontesi-pontok -->
<a id="doc-7-nyitott-kerdesek-es-dontesi-pontok"></a>
## 7. Nyitott kérdések és döntési pontok

A felhasználó dönt, a megfelelő mérés előtt:

1. **Célprofilok és indulási idő:** milyen bitrátákra optimalizálunk (pl. 1080p WEB ~8 Mbit/s, 1080p remux ~30 Mbit/s, 4K ~60 Mbit/s), és mi az elfogadható indulási idő? (GSP01, GSP02)
2. **Többletforgalom és CPU:** mennyi lehet leállításkor a fel nem használt, letöltött adat és a többlet-CPU? (GSP01)
3. **Teljes letöltésű (H&R) torrent:** folytatódjon-e a háttérletöltés lejátszás közben? Ma szünetel. (SP01 C3)
4. **Tracker kihagyása:** elfogadható-e egy nem válaszoló tracker ideiglenes kihagyása figyelmeztetéssel, és milyen hosszan? (SP05)
5. **Elavultság:** legfeljebb mennyire lehet régi a háttérben frissülő trackertalálat (kemény TTL)? (SP07)
6. **Natív kliensek:** vállalható-e a kompatibilitási kézi teszt (Stremio desktop, Android, Android TV, iOS, Kodi)? (SP09)
7. **Címlista:** van-e valós címlista, ahol az IMDb-keresés nem talál? (SP08, opcionális)

<!-- doc-anchor:doc-8-vegrehajtasi-ellenorzolista -->
<a id="doc-8-vegrehajtasi-ellenorzolista"></a>
## 8. Végrehajtási ellenőrzőlista

<!-- doc-anchor:doc-a-terv-atadasa-ennek-a-feladatnak-a-vege -->
<a id="doc-a-terv-atadasa-ennek-a-feladatnak-a-vege"></a>
### A terv átadása — ennek a feladatnak a vége

- [x] Branch a `main` `0515d98`-ról; HEAD és munkafa ellenőrizve; az alkalmazandó AGENTS elolvasva.
- [x] Kilenc tétel besorolva, forrásból igazolt tény és hipotézis elkülönítve; elvetett irányok rögzítve.
- [x] Hívási láncok, módosítandó fájlok, `Új` interfészek, invariánsok, tesztmátrixok, mérési kapuk és visszaállítás rögzítve.
- [x] Nem futott teszt, benchmark, Docker vagy tracker; nem indult implementáció.

<!-- doc-anchor:doc-csak-kesobbi-kulon-engedelyezett-vegrehajtaskor -->
<a id="doc-csak-kesobbi-kulon-engedelyezett-vegrehajtaskor"></a>
### Csak későbbi, külön engedélyezett végrehajtáskor

- [ ] A G0 és a célcsomag protokollja regisztrálva, baseline mentve, a libtorrent-viselkedés igazolva.
- [ ] A munkacsomag önállóan fejlesztve, szomszédos „opportunista” átírás nélkül.
- [ ] Viselkedési tesztek a tétel E/B/M/V mátrixa szerint.
- [ ] Ruff → basedpyright → teljes pytest; kliensnél a frontendellenőrzések.
- [ ] Helyi Docker funkcionális teszt eldobható, szintetikus adattal.
- [ ] A/B/C és C előtte/utána mérés; a negatív eredmény is megőrizve.
- [ ] A kapudöntés dokumentálva; a hipotézis nem került ténnyé átírásra.
- [ ] Titok- és privátcím-mentes kimenet; a védett helyi fájlok nincsenek stage-elve.
- [ ] Commit és push csak a feladatra kapott engedély szerint.

**Leállási pont:** a terv elkészültével megállni. A dokumentum nem engedély implementációra, tesztfuttatásra, buildre vagy szolgáltatásindításra.
