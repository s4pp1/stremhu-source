---
doc_id: "feature-stability-and-optimization-audit"
title: "StremHU Source — független Cloud Review"
kind: "audit"
status: "snapshot-audit"
audience: ["developer", "ai-agent"]
tags: ["CR01-CR19", "security", "performance", "static-review", "hypothesis"]
source_commit: "2615596f7cd181454dc5ae3e1ec9e4d215e3b154"
baseline: null
verification: "historical-audit-scope; structure-only-update"
structure_reviewed: "2026-11-03"
related_docs: ["docs/feature/stability-and-optimization/README.md", "docs/feature/stability-and-optimization/implementation-plan.md"]
source_paths: []
---

# StremHU Source — független Cloud Review

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../../README.md) · [AI-index](../../AI-INDEX.md)

> **Státusz:** Az eredeti commitra vonatkozó audit, megőrzött megállapításokkal. A navigáció rendezése nem új audit, teszt vagy incidensigazolás.

**Kapcsolódó:** [README.md](README.md) · [implementation-plan.md](implementation-plan.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [1. Határok és azonosítás](#doc-1-hatarok-es-azonositas)
- [2. Az öt vizsgálati terület összefoglalása](#doc-2-az-ot-vizsgalati-terulet-osszefoglalasa)
- [3. Bizonyítási láncok és javaslatok](#doc-3-bizonyitasi-lancok-es-javaslatok)
- [CR01 — A torrentenkénti kapcsolati keret legyen egyértelmű és következetes](#cr01)
- [CR02 — WAL-mérés és tranzakcióhatárok ellenőrzése checkpoint bevezetése előtt](#cr02)
- [CR03 — Stremio JSON-tömörítési kísérlet, feltételes bevezetéssel](#cr03)
- [CR04 — A torrentlista feliratkozásainak szűkítése; memoizálás csak profil alapján](#cr04)
- [4. Végrehajtható mérési és profiling terv — nem futtatva](#doc-4-vegrehajthato-meresi-es-profiling-terv-nem-futtatva)
- [5. Lefedettségi ellenőrzés és a második kör bizonyítékai](#doc-5-lefedettsegi-ellenorzes-es-a-masodik-kor-bizonyitekai)
- [6. Kiegészítő javaslatok és hibafaktorok](#doc-6-kiegeszito-javaslatok-es-hibafaktorok)
- [CR05 — Ismert alapértelmezett aláírókulcs megszüntetése](#cr05)
- [CR06 — Helyi HTTPS egyedi privát kulccsal](#cr06)
- [CR07 — Hitelesítő adatok maszkolása a naplókban](#cr07)
- [CR08 — Login/pairing munkakeret és egyszeri párosítási állapotgép](#cr08)
- [CR09 — Lejátszásregiszter csak auth után, globális korláttal](#cr09)
- [CR10 — Range és külső azonosítók határolt validálása](#cr10)
- [CR11 — Megszakításbiztos közös indexer-újrabejelentkezés](#cr11)
- [CR12 — Streamcache-invalidálás bekötése a valódi módosítási utakra](#cr12)
- [CR13 — Szinkron DB- és DNS-munka leválasztása az event loopról](#cr13)
- [CR14 — Torrentlista SQL- és BLOB-költségének csökkentése](#cr14)
- [CR15 — Külső válaszok méretkerete, URL-bizalmi határ és globális munkakeret](#cr15)
- [CR16 — Session-visszavonás és explicit böngészővédelmi szerződés](#cr16)
- [CR17 — Megosztott taskok saját DB-élettartama és rendezett shutdown](#cr17)
- [CR18 — Az első admin létrehozásának atomikussága](#cr18)
- [CR19 — Auth-védett HTTP-válaszok cache-policyja](#cr19)
- [7. Kiegészítő biztonsági és regressziós tesztterv — nem futtatva](#doc-7-kiegeszito-biztonsagi-es-regresszios-tesztterv-nem-futtatva)
- [8. Biztonsági kontrollok és a megmaradó lefedettségi határok](#doc-8-biztonsagi-kontrollok-es-a-megmarado-lefedettsegi-hatarok)

</details>

<!-- doc-nav:end -->

> **Lefedettségi felülvizsgálat (2026-11-03):** az első változat az eredetileg kért öt teljesítményterületet vizsgálta; teljes biztonsági auditot nem adott. A második kör hibakezeléssel, hitelesítéssel, párosítással, TLS-sel, naplózással, adat- és taskélettartammal egészíti ki. Az új CR05–CR19 tételek és a lefedettségi/kockázati mátrix az 5–8. fejezetben találhatók. **Minden optimalizálás és minden sérülékenység feltárását ez a forrásalapú audit sem garantálja.** Elsőként a feltételesen magas kockázatú CR05 és CR06 vizsgálandó; a tényleges helyi konfigurációt nem olvastam.

<!-- doc-anchor:doc-1-hatarok-es-azonositas -->
<a id="doc-1-hatarok-es-azonositas"></a>
## 1. Határok és azonosítás

- Audit dátuma: 2026-11-03. Módszer: statikus forráskód- és hívásilánc-vizsgálat, helyi Windows checkout.
- Ág: `Optimalization`.
- HEAD: `2615596f7cd181454dc5ae3e1ec9e4d215e3b154`.
- Szerzői és committer időpont: `2026-10-31T22:17:08+01:00`.
- Commit tárgya: `docs: add universal setup guide for split-horizon DNS (#8)` — kizárólag commit-metaadat; a dokumentáció tartalmát nem olvastam.
- A `git status --porcelain` az audit kezdetén és az írás előtt üres volt.
- Vizsgált tartalom: `server/app/`, releváns `server/tests/`, `client/src/`, `server/pyproject.toml`, `server/requirements.txt`, `Dockerfile`, `client/package.json`, `client/package-lock.json`, gyökér `AGENTS.md`. További alkalmazandó AGENTS fájlt a checkoutban és a közvetlen szülőkönyvtárakban nem találtam.
- A repó `docs/` könyvtárát, `.env` fájlját, helyi compose- és bootstrap/benchmark segédjeit nem olvastam. Nem indítottam alkalmazást, pytest-csomagot, szolgáltatást, trackerkeresést vagy távoli kapcsolatot. A második körben két alkalmazásimport nélküli, AST-ből kiemelt függvénypróba futott; ezek részletei az 5. fejezetben szerepelnek. Külső dokumentációt nem használtam. Nem történt forrás-, függőség- vagy gitállapot-módosítás, commit vagy push. Az egyetlen létrehozott eredmény ez a repón kívüli jelentés.
- A repó tesztfájljaiból a meglévő ellenőrzések célját azonosítottam; sikeres futásukat nem állítom. Az izolált függvénypróbák nem helyettesítik a tesztcsomagot vagy az integrációs tesztet. A felhasználó erre az auditfeladatra tesztfuttatási kivételt adott.

A `fájl:sor` hivatkozások a fenti HEAD checkoutjának soraira vonatkoznak, a repó gyökerétől relatívak. **Kóddal igazolt tény**: közvetlenül látható működés vagy konfiguráció. **Mérésre váró hipotézis**: erőforrás- vagy válaszidőhatás, illetve a nem rögzített futtatókörnyezet viselkedése. A javaslatok P1 = magas, P2 = közepes, P3 = alacsony prioritásúak. A prioritás nem CVSS-pontszám: a feltételeket minden tételnél külön jelölöm. A későbbi biztonsági kiegészítés magas kockázatú, konfigurációfüggő problémákat is azonosított.

<!-- doc-anchor:doc-verzioalap -->
<a id="doc-verzioalap"></a>
### Verzióalap

A Dockerfile Python 3.12 / Debian Bookworm runtime-ot és Node 24 buildet ír elő; `pip install -r requirements.txt`, illetve `npm ci` az installációs út. A backend leírója többek között `libtorrent==2.1.1`, `SQLAlchemy==2.1.4`, `fastapi[standard]==0.143.0`, `hypercorn==0.18.0` verziót ad meg. A tényleges indító `server/app/run.py` Hypercornt használ, nem a háttérleírásban említett Uvicornt.

A HTTPX és Starlette nincs közvetlenül rögzítve a requirements fájlban; backend lockfájlt nem találtam. Pontos HTTPX pool-alapérték, Starlette GZip-viselkedés, natív SQLite-verzió és libtorrent buildopció nem vezethető le egyértelműen ezekből a fájlokból. Telepített csomagok vagy futó konténer introspekcióját nem végeztem. A kliens lock a manifesttel egyezően React 19.3.0, React Query/query-core 5.104.2 és Axios 1.20.0 verziót tartalmaz (`client/package-lock.json:4246,4278,5325,7852`). A harmadik fél implementációját a megengedett olvasási határok miatt nem auditáltam.

<!-- doc-anchor:doc-2-az-ot-vizsgalati-terulet-osszefoglalasa -->
<a id="doc-2-az-ot-vizsgalati-terulet-osszefoglalasa"></a>
## 2. Az öt vizsgálati terület összefoglalása

| Terület | Megállapítás | Bizonyítottság szintje | Indokolt-e változtatás? |
|---|---|---|---|
| Indexer HTTP | Indexerenként tartós AsyncClient, folyamaton belüli singleton definíciószolgáltatás, leállításkori lezárás. A keresések nem hoznak létre új klienst. | Kóddal igazolt tény; a tényleges TCP-újrafelhasználás szerver- és idle-timeout-függő. | Pooling bevezetése nem indokolt. Keep-alive hangolás csak mérés után. |
| Libtorrent / Relay | Explicit globális és torrentenkénti korlátok, de aktív streamnél legalább 50-es torrentkeret. Cache-, I/O- és szálbeállítások nincsenek explicit megadva. | Kóddal igazolt tény; kis RAM melletti megfelelőség mérésre váró hipotézis. | CR01: kapcsolati beállítás jelentésének rendezése. Általános NAS tuning csak profilozás után. |
| Stremio JSON / GZip | Alkalmazásszintű GZip nincs; JSON-modellek és listák ismétlődő mezőket hordoznak. Normál címkeresés legfeljebb 40 jelöltet dolgoz fel. | Kóddal igazolt tény; tényleges válaszméret és tömörítési haszon mérésre váró hipotézis. | Azonnali globális middleware nem igazolt. Feltételes kísérlet: CR03. |
| SQLite WAL | WAL + NORMAL + 10 s várakozás, sessionlezárás/rollback van. Explicit checkpoint/retention beállítás nincs. | Kóddal igazolt tény; WAL-felhalmozódás és checkpoint-éhezés mérésre váró hipotézis. | CR02: ellenőrzés és megfigyelhetőség indokolt; periodikus TRUNCATE szükségessége nem bizonyított. |
| Kliens torrentlista | Adaptív 1,5/5 s poll, háttérpoll tiltva, közös kulcs, két observer, teljes lista feliratkozás, nem memoizált sorok. Nincs látható listatörténet-felhalmozás. | Kóddal igazolt tény; renderidő, extra HTTP-forgalom és heapnövekedés mérésre váró hipotézis. | CR04: feliratkozások szűkítése indokolható; memóriahiba vagy kötelező SSE-váltás nem igazolt. |

<!-- doc-anchor:doc-3-bizonyitasi-lancok-es-javaslatok -->
<a id="doc-3-bizonyitasi-lancok-es-javaslatok"></a>
## 3. Bizonyítási láncok és javaslatok

<!-- doc-anchor:doc-31-indexer-http-nem-talaltam-indokolt-pooling-valtoztatast -->
<a id="doc-31-indexer-http-nem-talaltam-indokolt-pooling-valtoztatast"></a>
### 3.1. Indexer HTTP: nem találtam indokolt pooling-változtatást

Létrehozási lánc:

`main.lifespan → sync_database_and_settings → get_indexer_definitions_service → IndexerDefinitionsService.__init__ → definition_class → BaseIndexerDefinition.__init__ → IndexerClient`.

- `server/app/sync.py:15,30`: induláskor ugyanazt a definíciószolgáltatást használja.
- `server/app/modules/indexer_definitions/dependencies.py:29`: `@functools.lru_cache(maxsize=1)`.
- `.../indexer_definitions/service.py:23–27,46`: a definíciópéldányok szótárban maradnak; a `get_by_id` ezeket adja vissza.
- `.../indexer_definitions/base_indexer_definition.py:42,88–95`: az `IndexerClient` az `httpx.AsyncClient` leszármazottja; a példányon egyszer készül el, 20 s timeouttal, redirectkövetéssel. Nincs egyedi transport, pooltiltás vagy keresésenkénti context manager.

Keresési lánc:

`create_indexers_service(db) → get_indexer_definitions_service() → IndexersService.get_torrents_by_imdb_id / get_torrents_by_query → get_by_id → find_torrents_by_* → _find_all* → integráció _fetch* → self._client.get`.

Hivatkozás: `.../indexers/dependencies.py:15–28`, `.../indexers/service.py:268–337,350–426`; nCore-példa: `.../integrations/ncore.py:107–155`. Az összes integráció HTTP-hívásai ugyanezt a `_client` mezőt használják. A torrentletöltés is ezen fut (`base_indexer_definition.py:283` szerinti `download_torrent`; `indexers/service.py:439–446`). Szemafor szabályozza a kéréseket (`base_indexer_definition.py:51,62,84,113`); alapértéke 5, két integráció saját értéket ad.

Lezárás: `main.py` lifespan kilépése → `IndexerDefinitionsService.close_all()` (`service.py:56–61`) → `BaseIndexerDefinition.close()` (`base_indexer_definition.py:393–395`) → `AsyncClient.aclose()`.

**Kóddal igazolt tény:** az AsyncClient kapcsolatpoolja számára megfelelő, kereséseken átívelő élettartam létezik. Ez nem garantálja, hogy két tetszőleges időpontú keresés ugyanazon TCP-kapcsolaton fut: a peer bezárhatja, az idle kapcsolat lejárhat, és más origin saját kapcsolatot igényel. A pool alapértékeit nem állítom számszerűen. Az alkalmazás tracker- és streamcache-e miatt egy második keresés akár HTTP nélkül is teljesülhet; ez önmagában nem bizonyít TCP reuse-t.

<!-- doc-anchor:cr01 -->
<a id="cr01"></a>
### CR01 — A torrentenkénti kapcsolati keret legyen egyértelmű és következetes

**Prioritás: P2. Bizonyítottság: kóddal igazolt tény a beállítás felülírása; mérésre váró hipotézis a RAM/CPU-hatás.**

A teljes lánc:

1. `main.py:37 → sync.py:34–35 → relay_settings/service.py:26–39` a tárolt RelaySettings értékeit alkalmazza.
2. `settings/schemas/internal.py:57–63`: alapértelmezésben globálisan **200**, torrentenként **20** kapcsolat. A `relay/service.py:38` szerinti 300 tehát a konstruktor kezdeti értéke, nem a normál sikeres szinkron utáni alapérték.
3. `relay/service.py:113–124`: a frissítés globális korlátot és minden meglévő handle torrentkeretét beállítja. Új handle: `:290–291`.
4. `relay/entities.py:81–99` prioritáskezelője azonban ezt számolja:

```python
target_max_connections = (
    max(self.service._torrent_connections_limit, 50)
    if self.has_active_streams
    else self.service._torrent_connections_limit
)
```

Ez az 50 alatti konfigurált torrentértéket aktív lejátszáskor felülírhatja. A globális limit továbbra is érvényes; ebből nem következik korlátlan peerszám. Az `entities.py:64` mezője ráadásul a korábban alkalmazott értéket őrzi, míg a `service.update_settings` közvetlenül módosítja a handle-t: a két állapot átmenetileg eltérhet.

**Javaslat:** tisztázni, hogy a felületi érték felső korlát vagy nyugalmi célérték. Felső korlát esetén a prioritáskezelő is tartsa be; szándékos streamboost esetén külön, látható és kis RAM-os profilban letiltható beállításként kezelni. A handle és a követett érték frissítése legyen összehangolt. Az 50-es minimum egyszerű törlését teljesítményvizsgálat nélkül nem javaslom élesíteni.

**Előny és mérés:** kiszámítható konfiguráció; 10/20/50/80-as beállításoknál handle limit, tényleges peerszám, konténermemória, CPU, streamindulási p95 és megakadások összevetése.

**Költség/kompromisszum/kockázat:** kicsi-közepes módosítás; kisebb aktív keret ronthatja a darabok elérhetőségét és a seeket. Külön boostmező tárolási/API/felületi munkát is igényelhet.

**Elfogadási feltétel:** a beállítás jelentése dokumentált; aktív↔inaktív átmenet, futás közbeni limitváltás és új torrent hozzáadása után a handle a definiált értéket mutatja. Tesztelendő például 20→10 és 20→80 váltás aktív stream közben, majd streamlezárás. A jóváhagyott terhelésen nincs új timeout vagy érdemi indulási regresszió.

**További Relay-eredmény:** `relay/service.py:34–56` nem ad meg explicit cache-méretet, disk I/O módot vagy I/O/hashing szálkeretet; az aktív torrentkorlátok `-1` értékűek. Ez nem bizonyít rossz hangolást. A 2.1.1 verzióhoz nem javasolok ellenőrizetlen, régebbi libtorrent-verzióból átvett `cache_size` receptet. `storage_mode_sparse` (`:288`) lemezfoglalási mód, nem RAM-limit. A prefetch 4–8 darabra épül (`entities.py:44–55`), így darabméret szerint változó adatmennyiséget jelent, nem fix MB-cache-t. A darabolvasás megosztott taskokat és határolt várakozást használ, és finally ágak takarítanak (`relay/service.py:161–264`); erre meglévő célzott tesztek vannak a `test_relay_pending_piece_requests.py` fájlban. A stream darabonként olvas és finally ágban destroy-t ütemez (`entities.py:400–460`). Statikus memóriaszivárgás-megállapítás nem indokolt.

<!-- doc-anchor:cr02 -->
<a id="cr02"></a>
### CR02 — WAL-mérés és tranzakcióhatárok ellenőrzése checkpoint bevezetése előtt

**Prioritás: P2. Bizonyítottság: kóddal igazolt tény a konfiguráció és a sessionélettartam; mérésre váró hipotézis a checkpointot akadályozó olvasó és a WAL tartós növekedése.**

`common/database.py:55–70`: `check_same_thread=False`, 10 s SQLite timeout, `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`. Nincs alkalmazásszintű `wal_autocheckpoint`, `journal_size_limit` vagy `wal_checkpoint`; ez **nem jelenti az SQLite automatikus checkpointjának kikapcsolását**. A tényleges alapértéket és fordítási beállításokat a buildleíró nem rögzíti.

Élettartam: `get_db → db_session → yield → commit/rollback → close` (`database.py:77–104`). Az auth ugyanilyen request-sessionből olvas (`auth/dependencies.py:18–21,79–85 → auth/service.py:38–58 → users/repository.py:19–20`). Ezután a Stremio handler hálózatra várhat: `stremio/router.py:73–84 → service.py:192–390 → torrent_source_provider/service.py:43–52 → indexers/service.py:272–337`. A forrásprovider a közös request-sessionből torrentfájlokat is olvas, majd letöltésekre vár (`torrent_source_provider/service.py:178–203`).

**Lényeges korlát:** az ORM-session nyitva tartása nem azonos a natív SQLite olvasótranzakció folyamatos nyitva tartásával. A SELECT utáni DBAPI-tranzakció a sqlite3 transaction-control módjától és a cursor életétől függ. A Python 3.12 alapimage és az SQLAlchemy verziója önmagában nem igazolja itt a checkpoint-éhezést. DML, nyitott cursor vagy explicit BEGIN más esetet jelenthet.

A külön írások már rövid sessionökben futnak (`torrent_files/isolated_service.py:24–29,66–104,113–117`). A touch 15 perces szűrést használ (`torrent_files/repository.py:10,106–142`). A `test_torrent_files_touch.py:60–130` stale/recent, írászáras és párhuzamos eseteket ellenőriz; a `test_cache_and_db_concurrency.py` cache-invalidálást és duplikált batch beszúrást vizsgál. Ezek nem tartós WAL-méretterhelési tesztek.

**Javaslat:** a későbbi helyi tesztharness rögzítse a natív tranzakcióidőt, WAL bájtméretet, checkpoint előrehaladást és commitlatenciát. Csak fennmaradó backlog esetén rövidíteni a bizonyítottan blokkoló tranzakciót; PASSIVE checkpointot akkor mérlegelni, ha az automatikus checkpoint viselkedése nem teljesíti a célt. Kérésenkénti vagy sűrű TRUNCATE nem igazolt megoldás. A checkpointolt WAL fizikai fájlja újrafelhasználás miatt nagy maradhat; a fájlhossz egyedül nem backlogmérő.

**Előny és mérés:** a normál újrafelhasználás elkülöníthető a blokkolt checkpointtól; backlog oldalszám, legöregebb tranzakció, WAL csúcs, lockhibák, commit p95/p99.

**Költség/kompromisszum/kockázat:** kicsi-közepes műszerezés; a PASSIVE checkpoint is munkát végez és befolyásolja a mérést, a TRUNCATE zárolási késleltetést okozhat. Tranzakcióhatár változtatása ORM-lazy-load és konzisztenciaregressziót okozhat.

**Elfogadási feltétel:** a kiválasztott helyi terhelésen nincs lock/5xx regresszió; a visszatartó olvasó lezárása után a checkpoint backlog legfeljebb két mérési perióduson belül kiürül. A fizikai WAL és backlog külön szerepel a mérésben. Beavatkozás előtt rögzített tárhelykeretet és commitlatencia-célt kell használni, nem általános fájlméret-ígéretet.

<!-- doc-anchor:cr03 -->
<a id="cr03"></a>
### CR03 — Stremio JSON-tömörítési kísérlet, feltételes bevezetéssel

**Prioritás: P3. Bizonyítottság: kóddal igazolt tény a GZip hiánya; mérésre váró hipotézis a nettó előny.**

`main.py` CORS- és session-middleware-t regisztrál, GZipet nem. `stremio/router.py:64–84,122–165` modellezett stream/katalógusválaszt ad; a sémák `schemas.py:156–167,399,488,604` szöveges leírásokat, URL-eket, opcionális feliratlistákat és listaburkolatokat tartalmaznak. Normál névkeresés: `catalogs_service.py:63–142 → torrent_source_provider/service.py:66–104`, legfeljebb 40 feldolgozott jelölttel. A streamlista más útvonal és nem feltétlenül azonos elemszámú. A memóriabeli Stremio-cache (`stremio/service.py:156–190`) nem tömörített HTTP-válaszcache.

**Javaslat:** reprezentatív, szintetikus JSON-válaszokon mérni a tömörítést; csak jelentős wire-byte csökkenés és elfogadható CPU/latencia mellett bevezetni méretküszöbös, kizárólag megfelelő JSON-válaszokra ható megoldást. A külső proxy esetleges tömörítéséről a megengedett fájlokból nincs bizonyíték. A konkrét middleware viselkedését az akkor ténylegesen telepített Starlette-verzión kell ellenőrizni.

**Előny és mérés:** kevesebb hálózati bájt; identity/gzip azonos JSON-nal, hideg/meleg cache mellett, p50/p95/p99, CPU/request és tömörítési arány.

**Költség/kompromisszum/kockázat:** kis-közepes implementáció; extra CPU, pufferelés és első bájt késleltetés kis NAS-on. Globális middleware a médiaválaszokat is érintheti; Range/206 és feliratletöltés regresszióját külön kizárni.

**Elfogadási feltétel:** megfelelő Accept-Encoding egyeztetés, Vary és Content-Encoding; kicsomagolva azonos JSON, hitelesítés változatlan. Nincs dupla tömörítés, a média Range-válasz byte-tartománya és fejlécei változatlanok. Előre választott kapuk például legalább 30% bájtcsökkenés a nagy válaszokon, legfeljebb 5% p95-romlás és a kijelölt CPU-keret tartása. Ezek javasolt elfogadási küszöbök, nem mért eredmények. Ha nem teljesülnek, nincs indokolt bevezetés.

<!-- doc-anchor:cr04 -->
<a id="cr04"></a>
### CR04 — A torrentlista feliratkozásainak szűkítése; memoizálás csak profil alapján

**Prioritás: P3. Bizonyítottság: kóddal igazolt tény a két teljeslista-observer; mérésre váró hipotézis a jelentős redundáns renderköltség.**

Lánc:

`main.tsx QueryClientProvider → relay/torrents/route.tsx loader ensureQueryData → index.tsx useSuspenseQueries(getTorrents) → Torrents useSuspenseQuery(getTorrents) → Torrent sorok`.

`client/src/shared/lib/client.ts:3–10`: egy QueryClient, 5 perc staleTime, 10 perc gcTime. `shared/queries/torrents.ts:14–33`: fix `['torrents']` kulcs, nincs háttérpoll; aktív/incomplete lista 1500 ms, egyébként 5000 ms. A hiányos, de álló torrent is gyors pollt válthat ki. A staleTime önmagában nem polltiltás.

`relay/torrents/index.tsx:22–32` teljes listára figyel, bár csak a hosszt jeleníti meg; `-features/torrents.tsx:14,30–32` ismét feliratkozik és stabil infoHash kulcsokkal térképez. `-components/torrent.tsx:63` sima függvénykomponens; a `useMemo(:71–77)` csak egy érték számítását memoizálja, nem a sort.

A közös queryKey közös cache-t jelent. A két observerből nem következik automatikusan kétszeres HTTP-forgalom: az időzítők és in-flight deduplikáció tényleges összhatását mérni kell. A Query v5 alapértelmezett structural-sharing/értesítési viselkedésére támaszkodhat a kód, de ennek pontos implementációját e forráshatárok között nem ellenőriztem. Változatlan JSON miatti újrarenderelést ezért nem állítok bizonyítottnak.

`queryFn` nem fűzi előző listához az új adatot. Nincs ezen az úton saját setInterval vagy felhalmozott történet. `source-client.ts:1437–1445 → source-client-instance.ts:13–20` Axioson adja vissza a válaszadatot. A queryFn nem továbbítja a Query AbortSignalját: navigálás után egy már folyó kérés még befejeződhet; ez nem bizonyított memóriaszivárgás. A backend minden kérésre összerakja a DB/Relay listát (`torrents/router.py:24–32 → service.py:52–71 → relay/service.py:133–139 → relay/schemas.py:50`); ennek terhe is része a profilnak.

**Javaslat:** egy listaobserver és adatátadás, vagy a darabszámhoz `select` használata. React.memo csak akkor, ha a profil sok változatlan sor renderelését mutatja, és az objektumazonosság ezt lehetővé teszi. SSE/WebSocket és listavirtualizáció a jelen bizonyítékból nem indokolt.

**Előny és mérés:** szűkebb feliratkozás, kevesebb felső komponensmunka, feltételesen kevesebb sorrender; React Profiler actualDuration/commit, soronkénti renderdarabszám, HTTP-kérésszám és heap-retainer vizsgálat.

**Költség/kompromisszum/kockázat:** kicsi; propátadás vagy select bevezetése. Hibás memo-összehasonlítás elavult statisztikát okozhat. A poll ritkítása rontja a frissességet, ezért azt nem javaslom automatikusan.

**Elfogadási feltétel:** változatlan elemszám melletti sebességfrissítés ne igényelje a darabszámnézet új renderét a választott megoldásban; módosítás/törlés és statisztikafrissítés továbbra is működik. Profil alapján csökkenjen a célzott renderköltség, kérés- vagy frissességregresszió nélkül. 30 perces futás és ismételt navigáció után a GC utáni heapnek ne legyen folyamatos, elérhető torrenttörténetből eredő növekedése.

<!-- doc-anchor:doc-4-vegrehajthato-meresi-es-profiling-terv-nem-futtatva -->
<a id="doc-4-vegrehajthato-meresi-es-profiling-terv-nem-futtatva"></a>
## 4. Végrehajtható mérési és profiling terv — nem futtatva

<!-- doc-anchor:doc-kozos-kornyezet-es-modszer -->
<a id="doc-kozos-kornyezet-es-modszer"></a>
### Közös környezet és módszer

Későbbi mérési munkában kizárólag helyi Windows Docker Desktop használható. Az AGENTS szerinti A/B/C összevetés: upstream image, fork main image és vizsgált branch, külön eldobható adatkönyvtárral. Az image-ek digestjét és a branch commitot rögzíteni kell; a változó latest címke önmagában nem reprodukálható referencia. Az összevethető végpontokat külön kell kezelni a csak a forkban létező funkcióktól. Kódváltoztatás előtt/után a C azonos workloadját is össze kell vetni, mert az upstream funkcionális különbségei torzíthatnak.

Minden mérés szintetikus felhasználóval, szintetikus torrenttel, helyi fixture trackerrel és szükség esetén helyi seedelővel fusson, internetkimenet nélkül. A meglévő éles hitelesítésekre épülő segédszkriptet erre nem szabad változtatás nélkül használni. Tesztkulcsok ne kerüljenek a naplózott URL-ekbe. Éles kötetet ne töröljön a mérés; cold start csak külön tesztkötetben.

Javasolt mátrix: 512 MiB / 1 GiB / 2 GiB konténerkeret, azonos CPU és Docker-erőforráskeret, 1/4/8 párhuzamos kliens. Minden ágon azonos bemenet, szekvenciális futtatás, legalább 5 ismétlés; rövid latencytesztnél legalább 100 kérés cellánként. Cold és warm szakaszt elkülönítve jelenteni. Memóriateszt 30 perc, WAL-teszt 60 perc. Rögzítendő: image/digest, telepített csomagverziók, natív SQLite-verzió, libtorrent `get_settings()` releváns értékei, threadszám és konténerkorlát.

<!-- doc-anchor:doc-m1-tcp-reuse -->
<a id="doc-m1-tcp-reuse"></a>
### M1 — TCP reuse

1. Helyi HTTP/1.1 fixture szerver rögzítsen egyedi kapcsolat-azonosítót és fogadott kérésszámot; megfelelő Content-Length és keep-alive támogatás szükséges.
2. Azonos definíciópéldányból két külön keresést futtatni 0,1 / 2 / 10 / 30 s szünettel, majd többlapos keresést és torrentletöltést. Eltérő keresőkulcsokkal vagy tesztbeli cacheürítéssel biztosítani, hogy valóban történjen HTTP.
3. Rögzíteni: kapcsolatnyitások, kérések, reuse-arány, p95 és lezárt socketek shutdown után. A fixture opcionálisan zárjon minden kapcsolatot, illetve legyen lassú és adjon auth-redirectet.
4. Eredmény: rövid szünetű keep-alive esetben legyen újrafelhasználás; peer-close esetben rendezett újracsatlakozás. Csak a ténylegesen mért idle-minta alapján mérlegelni keepalive-expiry hangolást. MockTransport nem alkalmas TCP pooling bizonyítására.

<!-- doc-anchor:doc-m2-relay-kis-ram-on-es-cr01 -->
<a id="doc-m2-relay-kis-ram-on-es-cr01"></a>
### M2 — Relay kis RAM-on és CR01

1. Helyi seedelővel 1/4/8 lejátszás, 1/10/50 betöltött torrent, 256 KiB / 1 MiB / 4 MiB darabméret; külön seeding és seekterhelés. Nagy fixtureméret esetén a tesztadat lemezen generált legyen.
2. Először a változatlan kódot mérni. Globális 50/100/200, torrentenként 10/20/50 keretekkel tesztelni; aktív prioritásfutás előtt/után a handle beállítását külön rögzíteni.
3. RSS mellett a konténer file-cache/anon memória és memory peak/OOM események is szükségesek. Mérni peer-, szál- és pending piece-task számot, I/O-t, CPU-t, indulási/seek p95-öt, timeoutot és megszakadt streamet. A Python tracemalloc nem látja a teljes C++ libtorrent memóriát.
4. Natív settings-kulcsot csak az adott 2.1.1 buildben való meglétének és jelentésének ellenőrzése után szabad variálni. Egyszerre egy paramétercsalád változzon. A kevesebb RSS önmagában nem elég, ha a konténer file-cache vagy a streamhibák nőnek.

<!-- doc-anchor:doc-m3-gzip -->
<a id="doc-m3-gzip"></a>
### M3 — GZip

1. A jelenlegi Pydantic-válaszmodellekből szintetikus, valósághűen ismétlődő stream- és katalógusválaszok: 0/1/10/40/200 elem. A 200-as katalógus stresszfixture, nem a normál 40 jelöltes út állított eredménye.
2. Identity vs gzip; 1/2/4/8 KiB méretküszöb és 1/4/6 kompressziós szint mint kísérleti mátrix. A tényleges framework által támogatott API-t előzetesen ellenőrizni kell.
3. A kliens automatikus dekompressziója helyett nyers átviteli bájtot is mérni. Kicsomagolt JSON-egyezés, CPU/request, TTFB és teljes latency. Külön LAN és helyileg sávszélesség-korlátozott profil.
4. Accept-Encoding nélküli, gzipet elutasító és gzipet kérő eset; Range 206, HEAD, redirect és felirat ellenőrzése. A CR03 kapui alapján bevezetni vagy elvetni.

<!-- doc-anchor:doc-m4-wal-es-cr02 -->
<a id="doc-m4-wal-es-cr02"></a>
### M4 — WAL és CR02

1. Külön fájlalapú SQLite adatbázisban a jelenlegi connect/session beállításokat használni. Kezdéskor lekérni: `journal_mode`, `synchronous`, `page_size`, `wal_autocheckpoint`, `journal_size_limit`; mérni a kapcsolat natív `in_transaction` állapotát és a tényleges BEGIN/COMMIT időket.
2. Rövid olvasók mellett 1/4/8 író, szintetikus torrent-BLOB batch insert és touch; a touch esetén stale/recent adatok külön, a 15 perces throttle megőrzésével.
3. Két külön hosszúolvasó-eset: az alkalmazásra jellemző SELECT utáni 5/30/120 s várakozás, illetve explicit BEGIN + SELECT nyitva tartott snapshot. Az utóbbi kontrollált stresszhelyzet, nem bizonyított jelenlegi requestviselkedés.
4. WAL-fájlhossz 1 s-onként, commit latency és lockhibák folyamatosan. Külön diagnosztikai kapcsolatból például 10 s-onként `PRAGMA wal_checkpoint(PASSIVE)`; rögzíteni a busy/log/checkpointed értékeket. Ez beavatkozó mérés, ezért legyen külön, aktív checkpoint-monitor nélküli kontrollfutás is. A könyvelésnél WAL-resetet figyelembe kell venni.
5. Az olvasó elengedése után mérni a backlog kiürülését. PASSIVE stratégia csak ezzel összevetve; TRUNCATE legfeljebb külön, nyugalmi kísérletben. A fizikai fájl csökkenése nem kötelező sikerfeltétel. Hibaarány, p95/p99 és backlog alapján dönteni, kell-e alkalmazásszintű stratégia.

<!-- doc-anchor:doc-m5-react-poll-render-es-heap -->
<a id="doc-m5-react-poll-render-es-heap"></a>
### M5 — React poll, render és heap

1. Helyi API-fixture 0/20/100/500 torrenttel: változatlan válasz, egy változó sor, minden változó sor, majd álló, hiányos torrent. Production buildet és külön profilozható buildet használni; a fejlesztői StrictMode többletmunkáját elkülöníteni.
2. Network panelben vagy fixture számlálóval 5 perces HTTP-kérésszámot rögzíteni két observer mellett; nem elég a pollintervallumból számolni. Ugyanez egy observerrel; háttérbe helyezés és visszatérés is szükséges.
3. React Profiler: szülő-, lista- és sorrenderek, commit count, actualDuration. Először változatlan kód, majd count-select/egy observer, végül csak szükség esetén memoizált sorok. A pollgyakoriság eközben maradjon azonos.
4. 30 perc alatt heap snapshot 0/10/20/30 percnél, GC után, továbbá 50 oda-vissza navigáció. Megvizsgálni a Query cache-ben maradó kulcsokat, régi tömbök retainereit, DOM-node számot és függő kéréseket; unmount után a 10 perces gcTime leteltével is ellenőrizni. A heap fűrészfoga vagy egy befejeződő Axios-kérés nem szivárgásbizonyíték.
5. Kiegészítő frontend-sikerfeltétel: minden friss sorérték látható marad, a menük, update/delete invalidáció és üres lista működik. Memóriaszivárgás csak tartós, GC után is élő és konkrét retainerlánccal igazolt növekedés alapján állítható.


<!-- doc-anchor:doc-5-lefedettsegi-ellenorzes-es-a-masodik-kor-bizonyitekai -->
<a id="doc-5-lefedettsegi-ellenorzes-es-a-masodik-kor-bizonyitekai"></a>
## 5. Lefedettségi ellenőrzés és a második kör bizonyítékai

Az eredeti öt kérdés mindegyikére volt válasz, de ez **nem fedte le az összes optimalizálási lehetőséget, hibafaktort vagy security risket**. A második körben tényleges további problémák kerültek elő.

Az összes `server/app/**/*.py` fájlon AST-leltár futott: **259 Python-fájl, 86 route-dekorátor**. A route-regisztrációkat, guardokat, HTTP-klienseket, fájlműveleteket, DB-hozzáféréseket, cache-eket, háttértaskokat és kliensoldali veszélyes sink-mintákat célzott keresés követte. Ez a megadott mintákra teljes leltár, **nem minden függvény minden végrehajtási útjának kézi vagy formális bizonyítása**. A releváns láncokat a következő tételekben követtem végig.

| Réteg | Második kör eredménye | Bizonyítottság / korlát |
|---|---|---|
| Aláírókulcsok | Ismert session-secret alapérték, közös kulcs két célra | Kóddal igazolt; tényleges konfiguráció ismeretlen — CR05 |
| Helyi TLS | Publikus végpontról kapott privát kulcs kerülhet a szerverhez | Kóddal igazolt; tényleges hálózati mód ismeretlen — CR06 |
| Naplózás | Hitelesítő adatot hordozó teljes URL naplózásra konfigurálva | Kóddal igazolt; tényleges logot nem olvastam — CR07 |
| Login/pairing | Rate limit nem látható; korlátlan kódkereső ciklus, nem egyszeri jóváhagyás | Kóddal igazolt; támadási throughput nem mért — CR08 |
| Auth előtti state | Lejátszásregiszter írása API-key validálása előtt | Kóddal igazolt; végpontterhelés nem futott — CR09 |
| Bemeneti határok | Kezeletlen Range int-hiba; nem numerikus ID-ből SPARQL literál | Range-próba is igazolja; külső queryhatás nincs tesztelve — CR10 |
| Indexer relogin | Várakozó cancelje lezárja a közös Future-t | Izolált forrásfüggvény-próbával igazolt — CR11 |
| Streamcache | Invalidáló függvénynek nincs termékbeli hívója | AST-vel igazolt — CR12 |
| Event loop | Szinkron DB-callback és DNS-resolve async láncban | Kóddal igazolt; lag nincs mérve — CR13 |
| Lista backend | Lazy kapcsolatok és szükségtelen BLOB-betöltés | Kóddal igazolt minta; költség mérendő — CR14 |
| Külső input/terhelés | Letöltési bájtkeret/globális munkakeret nem látható | Kontrollhiány kóddal igazolt; SSRF feltételes — CR15 |
| Session/böngésző | Password update nem vonja vissza a sessiont; Secure opció nem explicit | Kóddal igazolt; cookie-kimenet runtimefüggő — CR16 |
| Megosztott task/DB | Shieldelt task requesthez tartozó service-t és Sessiont használhat tovább | Ownership eltérés igazolt; tényleges DB-hiba hipotézis — CR17 |
| Bootstrap | Count-then-create az első adminnál | Minta igazolt; verseny kimenetele driverfüggő — CR18 |
| HTTP-cache | Auth-védett felirat `public, max-age=86400` | Fejléc igazolt; shared-cache viselkedés telepítésfüggő — CR19 |

<!-- doc-anchor:doc-tenylegesen-lefuttatott-izolalt-probak -->
<a id="doc-tenylegesen-lefuttatott-izolalt-probak"></a>
### Ténylegesen lefuttatott izolált próbák

A `server/.venv/Scripts/python.exe -B -` standard bemenetéről futó program csak `ast`, `asyncio`, `pathlib`, `types` modulokat használt. Nem importálta az appot/Configot, nem olvasott `.env`-et, nem ért el hálózatot/DB-t és nem írt tesztfájlt vagy bytecode-ot. AST-ből kiemelte a Range-függvényt és segédjét, illetve a relogin metódust; HTTPException/ParsedRangeHeader minimális helyettesítőt, a login helyi asyncio.Eventet kapott.

```text
range normal -> OK, 10 bájt
range latin1-digit -> ValueError, kezeletlen
range long-ascii-number -> ValueError, kezeletlen
relogin cancelled joiner -> owner: InvalidStateError
Production invalidate_stream_cache call sites: 0
```

Bemenetek: `bytes=0-9`, latin-1 felső indexű kettest tartalmazó szám, 5000 ASCII számjegyes kezdőérték. Az utolsó eredmény a helyi Python int-limitjétől is függ. Reloginnál egy tulajdonos után csatlakozó várakozó indult; a csatlakozó törlése után folytatódott a login. Ezek függvénypróbák, nem HTTP-integrációs tesztek: a HTTP-parser korábban is elutasíthat egyes bemeneteket.

<!-- doc-anchor:doc-6-kiegeszito-javaslatok-es-hibafaktorok -->
<a id="doc-6-kiegeszito-javaslatok-es-hibafaktorok"></a>
## 6. Kiegészítő javaslatok és hibafaktorok

<!-- doc-anchor:cr05 -->
<a id="cr05"></a>
### CR05 — Ismert alapértelmezett aláírókulcs megszüntetése

**Prioritás: P1, ha a default secret használatban marad. Bizonyítottság: kóddal igazolt alapérték; tényleges konfiguráció ellenőrzésre váró hipotézis.**

Lánc: `config.py:31 → main.py:110–113 SessionMiddleware → auth/router.py:41,56 user_id → auth/dependencies.py:33–54 user/role betöltése`. Ugyanez a secret a `stream/utils/stream_token.py:9–12` aláírókulcsa. A repo ismert alapértéke nem megfelelő kriptográfiai titok. Ismert kulcs és létező userazonosító birtokában a session sértetlensége nem megbízható. **Nem állítom, hogy a telepítés defaultot használ vagy hogy minden támadó ismer adminazonosítót.** A stream végpont külön API-key ellenőrzése megmarad; az aláírás hamisíthatósága nem jelent önmagában tetszőleges fájlolvasást. Titok konkrét értékét nem közlöm.

**Javaslat:** default/üres secret induláskori elutasítása vagy erős, első induláskor generált és perzisztált kulcs; megtervezett rotáció, szükség esetén külön session/stream kulcs.

**Előny/mérés:** ismert alapkulccsal nincs elfogadható hitelesítés; szintetikus installáció default/hiányzó/erős kulccsal. **Költség/kompromisszum/kockázat:** kicsi-közepes; rotáció érvénytelenítheti a sessionöket/lejátszó URL-eket. **Elfogadás:** defaulttal nem indul védtelenül, generált kulcs újraindításkor stabil, másik kulcs aláírása elutasított; legitim login/stream működik.

<!-- doc-anchor:cr06 -->
<a id="cr06"></a>
### CR06 — Helyi HTTPS egyedi privát kulccsal

**Prioritás: P1 megosztott kulcsú LOCAL módban, ellenséges hálózati közeg esetén. Bizonyítottság: kóddal igazolt kulcsbeszerzés; tényleges használat ismeretlen.**

`boot/network.py:39–49 → network/service.py:45 setup_local → network/ssl/service.py:72–96 get_local_ip_certificate`: publikus szolgáltatás `/keys` végpontjának `fullchain` és `privkey` mezőit használja. `boot/network.py:30–38,65–72` lemezre írja, `run.py:62–63` Hypercornnak adja. A szolgáltatást nem kerestem fel; a bizalmi modell a kódból látható.

A publikus módon megszerezhető privát kulcs nem ad egyedi szerverazonosságot. A megfelelő domain kliensforgalmát megszerző/eltérítő támadó megszemélyesítheti a szervert. Ez **nem** bizonyít passzív visszamenőleges TLS-dekódolhatóságot vagy megtörtént támadást.

**Javaslat:** egyedi, telepítésen kívül nem hozzáférhető kulcs, megfelelő reverse proxy/ACME vagy megbízható helyi CA; a megosztott kulcsú mód biztonsági tulajdonságát a felület jelezze helyesen.

**Előny/mérés:** publikus közös kulcs nem használható másik telepítés szerverazonosságához; két fixture-install kulcsujjlenyomatának és kliens trustjának ellenőrzése. **Költség/kompromisszum/kockázat:** közepes; helyi CA-bizalom és kényelmes telepítés változhat. **Elfogadás:** eltérő installáció eltérő privát kulcs, biztonságos úton nincs közös privátkulcs-letöltés, céllejátszók tanúsítvány-ellenőrzése működik.

<!-- doc-anchor:cr07 -->
<a id="cr07"></a>
### CR07 — Hitelesítő adatok maszkolása a naplókban

**Prioritás: P2. Bizonyítottság: kóddal igazolt logkonfiguráció/hívás; tényleges logkiszivárgás nincs vizsgálva.**

`run.py:64–65` teljes pathot/queryt naplóz; a Stremio/Kodi/stream API-keyt hordoz pathban, Torznab queryben (`torznab/dependencies.py:38–58`), pairing status device_code-ot pathban. `base_indexer_definition.py:283–292` hibánál teljes download_url-t logol. HunTorrentnél ez passkeyt hordozhat (`integrations/huntorrent.py:255–274`). A DDNS-provider HTTPX-kivételszövege is tartalmazhat querytitkot (`network/ddns/providers/duckdns.py:40–45`, `myaddr.py:37–42`); ez a konkrét kivételtől függ.

**Javaslat:** útvonalsablon/titokmaszkolt URL, query allowlist, kivétellánc-redakció; requestazonosító, státusz, idő és szolgáltató megőrzése. **Előny/mérés:** logolvasási jogból nem származik újrafelhasználható hitelesítés; jelölőtitkokkal 200/4xx/timeout/redirect/HTTPStatusError logellenőrzés. **Költség/kompromisszum/kockázat:** kicsi-közepes; kevesebb diagnosztikai URL-részlet. **Elfogadás:** jelölőtitok teljes alakban sem logban, sem traceback URL-jében nincs; hibák továbbra is korrelálhatók.

<!-- doc-anchor:cr08 -->
<a id="cr08"></a>
### CR08 — Login/pairing munkakeret és egyszeri párosítási állapotgép

**Prioritás: P2. Bizonyítottság: kóddal igazolt kontrollhiány; túlterhelés sebessége mérésre váró hipotézis.**

`auth/router.py:46–57 → auth/service.py:16–36`: login próbálkozási limit nélkül; létező jelszavas accountnál Argon2-munka. Külső proxylimit nem látható. `pairings/router.py:21–44` init/status szándékosan publikus; `pairings/service.py:19–45` 4 számjegyes kódot keres korlátlan `while` ciklussal. `repository.py:18–19` a takarítatlan lejárt kódot is foglaltnak látja; cleanup óránként fut. A modell kódindexei nem unique-ok (`models.py:19–29`), az ellenőrzés/insert nem atomi. `service.py:76–96` nem követel PENDING státuszt, ezért érvényességen belüli LINKED kód más userhez újraköthető. A status API-keyt ad a device_code birtokosának (`:66–72`), ezért az állapot integritása számít. **Ez önmagában nem bizonyított tetszőleges fióklopás.**

**Javaslat:** login account+forrás szerinti limit; pairing init/poll/verify külön kerete; `secrets` alapú kód, határolt retry; DB-ben kikényszerített aktív kódegyediség és atomi PENDING→LINKED. A device-poll retryját tervezetten megőrizni, nem vakon az első válaszra törölni.

**Előny/mérés:** korlátos kódkeresés, kisebb login CPU-terhelés, nincs újrakötés. **Költség/kompromisszum/kockázat:** közepes; NAT mögötti felhasználók és device-poll kompatibilitás. **Elfogadás:** telített/lejárt készletből kontrollált hiba, nem végtelen ciklus; párhuzamos init nem ad azonos aktív kódot; LINKED kódot más user nem köthet át; normál párosítás/retry működik.

<!-- doc-anchor:cr09 -->
<a id="cr09"></a>
### CR09 — Lejátszásregiszter csak auth után, globális korláttal

**Prioritás: P2. Bizonyítottság: kóddal igazolt sorrend és megőrzés; RAM-hatás nincs mérve.**

`stream/router.py:66–70` API-key ellenőrzés előtt hívja a `record_active_playback` függvényt; auth csak `:78–83`. A token dependency előbb lefut: **érvényes aláírt streamtoken szükséges**, tehát nem tetszőleges anonim requestről van szó. A token nincs API-keyhez kötve (`stream/schemas.py:6–12`), ezért legitim streamtoken változó hibás API-keyvel is eléri az írást.

`stream/active_playback.py:5,23–31` kulcsonként 20 elemet tart, de az API-key szótár külső kulcsszáma korlátlan; TTL csak az éppen írt kulcs listáját tisztítja. Más termékbeli globális törlést nem találtam. Ez megőrzési út, nem számszerű memóriaszivárgás-állítás.

**Javaslat:** sikeres auth/előkészítés után regisztrálni belső userazonosítóval; globális TTL-takarítás és korlát. **Előny/mérés:** elutasított kulcs nem foglal tartós helyet; invalid-key burst után regiszterméret/heap. **Költség/kockázat:** kicsi; feliratindulási értesítés időzítése változik. **Elfogadás:** rossz kulcs nem ír; lejárt kulcsok eltűnnek; stream/felirat mindkét indulási sorrendje működik.

<!-- doc-anchor:cr10 -->
<a id="cr10"></a>
### CR10 — Range és külső azonosítók határolt validálása

**Prioritás: P2. Bizonyítottság: kóddal és Range-próbával igazolt; külső queryhatás nem tesztelt.**

`stream/service.py:248–262`: az `isdigit()` elfogad olyan latin-1 karaktert, amelyen az `int()` ValueError-t dob; túl hosszú decimális számon a Python int-limitje is kivételt okozhat. Nincs kontrollált 416-ra fordítás. A meglévő RFC-mátrix (`tests/test_range_and_file_validation.py:7–57`) e két esetet nem fedi. HTTP-parsertől függően végpontbeli kezeletlen hiba lehet; végpontteszt nem futott.

`stremio/utils.py:65–111` TVDB-idnél csak nemüres értéket követel; `schemas.py:640–662` külső ID-mezői sima stringek. `tvdb_resolver.py:108,133–141` az ID-t idézett SPARQL-literálba fűzi, MAL-nál ugyanez történik `:514–521` körül. A teljes query URL-quote-ja nem SPARQL-literal escaping. Érvényes API-key és sikertelen első feloldóút esetén idézőjeles ID módosíthatja a külső query szintaxisát. A Torznab numerikus parsere szigorúbb (`torznab/query.py:133–159`). Ez **nem helyi SQL injection vagy bizonyított appoldali SSRF**.

**Javaslat:** ASCII-decimális Range-validálás, hosszkorlát és ValueError→416; metadata ID-knál konzisztens numerikus, méretkorlátos séma routerben és resolverben. **Előny/mérés:** nincs int-hibából 500 vagy ID-ből queryszintaxis; normál/hibás ID és Range-mátrix. **Költség/kockázat:** kicsi-közepes; régi támogatott prefixek kompatibilitása. **Elfogadás:** hibás/nem ASCII/túl hosszú Range kontrollált 416; idézőjeles/path-szerű ID 4xx külső HTTP nélkül; legitim TVDB/Kitsu/MAL/TMDB formátum működik.

<!-- doc-anchor:cr11 -->
<a id="cr11"></a>
### CR11 — Megszakításbiztos közös indexer-újrabejelentkezés

**Prioritás: P2. Bizonyítottság: izolált forrásfüggvény-próbával is igazolt hiba.**

`IndexerClient.request → AuthSessionError → BaseIndexerDefinition.relogin` (`base_indexer_definition.py:58–59,368–391`). A csatlakozó közvetlenül a közös Future-t awaiteli (`:375–376`), így cancelje azt is cancelheti. A tulajdonos login végén `set_result`-ot hív (`:385`) a már lezárt Future-re: InvalidStateError. A tulajdonos cancelje viszont finally ágban eldobhatja a referenciát a csatlakozók lezárása nélkül. A 12,5 s-os `wait_for` (`indexers/service.py:325–326`) valós megszakítási forrás. Az általános Singleflight védelme ezt a külön Future-megoldást nem módosítja.

**Javaslat:** közös login task saját élettartammal, shieldelt várakozókkal, determinisztikus hibaterjesztéssel. **Előny/mérés:** egy request timeoutja nem rontja a többi indexerkérést; owner/joiner/all cancel, error és retry tesztmátrix. **Költség/kockázat:** kicsi-közepes; cookiecsere/retry helyessége kritikus. **Elfogadás:** egyszeri login több várakozónál, hibák minden élő várakozónak terjednek, cancel után új próbálkozás indulhat; nincs pending Future vagy InvalidStateError.

<!-- doc-anchor:cr12 -->
<a id="cr12"></a>
### CR12 — Streamcache-invalidálás bekötése a valódi módosítási utakra

**Prioritás: P2. Bizonyítottság: kóddal és AST-híváshely-kereséssel igazolt hiány.**

`stremio/service.py:51–61` definiálja az invalidáló/generációs mechanizmust, de az egész `server/app/` AST-jében **nulla hívási helye van**. A közvetlenül meghívó teszt a segédet, nem a termékbeli bekötést vizsgálja.

A kulcs (`service.py:166`) több flaget/API-keyt tartalmaz, de nincs benne például `torrent_seed`, smart-filter csoportosítási preferencia, attribútumkizárások vagy preferenciarangsor. Ezek hatnak az eredményre (`torrent_streams/service.py:288–305,538–566,629–654`). Módosítási utak: `me/router.py:45–54 → users/service.py:update`; `user_preference_definitions/service.py:update/reorder/delete`; `attribute_exclusions/service.py:create/delete`. Azonos kulccsal a régi válasz a 60 s TTL-ig visszajöhet; a régi in-flight fetch is visszaírhat változatlan generációnál.

**Javaslat:** sikeres commit után userszintű generációemelés; globális/indexer-beállításra megfelelő tágabb scope. Commit előtti puszta ürítés rollback esetén nem elegendő szerződés. **Előny/mérés:** mentett szűrés következő kérésben érvényes; warm-cache→endpoint-módosítás→azonnali újrakérés és in-flight barrier teszt. **Költség/kockázat:** közepes; túl széles invalidáció cache-hit veszteség. **Elfogadás:** seed/filter/preferencia/exclusion változás azonnal hat, régi fetch nem ír vissza, rollback/másik user cache-e helyes. API-key rotáció eleve változtatja a kulcsot, azt nem állítom ugyanígy hibásnak.

<!-- doc-anchor:cr13 -->
<a id="cr13"></a>
### CR13 — Szinkron DB- és DNS-munka leválasztása az event loopról

**Prioritás: P2. Bizonyítottság: kóddal igazolt blokkoló lánc; a lag mértéke mérésre váró hipotézis.**

`relay/service.py:64–67` event-loopra ütemezi a `process_alerts`-ot. `:396–407` szinkron callbacket hív: `torrents/background_tasks.py:9–13 → db_session → TorrentsService.save_resume_data → TorrentRepository.update/flush → commit`. A callbacket `background_tasks.py:25–28` regisztrálja. Szinkron SQLite I/O és lehetséges lockvárakozás így a piece-alert feldolgozásának szálára kerül. A resume loop 600 s-onként ment (`relay/background_tasks.py:8–13`).

Másik ág: `network/ssl/service.py:27–60 wait_for_dns_propagation` async függvény szinkron `resolver.resolve`-ot hív (`:43`), konfigurálás/megújítás idején. Az ASS→VTT konverzió is a loopon fut (`stream/router.py:474`), de már van forrásméret-korlátja; annak offloadját csak profil alapján indokolt eldönteni.

**Javaslat:** bounded, koaleszkáló resume-író worker saját sessionnel; async DNS vagy workerben resolve. Alert/future-kezelés maradjon megfelelő loopon. **Előny/mérés:** kisebb looplag/piece tail latency; DB-lock és DNS-késés fault injection. **Költség/kockázat:** közepes; mentési sorrend és shutdown flush. **Elfogadás:** lassú commit/DNS alatt független health/piece kérés nem várja ki ugyanazt a teljes blokkolást; queue korlátos, szükséges mentés shutdownkor megvárt.

<!-- doc-anchor:cr14 -->
<a id="cr14"></a>
### CR14 — Torrentlista SQL- és BLOB-költségének csökkentése

**Prioritás: P2 nagyobb listán. Bizonyítottság: kóddal igazolt betöltési minta; pontos költség/nyereség mérendő.**

`TorrentsService.get_torrents` (`service.py:52–71`) a `TorrentRepository.find()` (`repository.py:15–16`) teljes ORM-listáját olvassa. A `resume_bytes` nem deferred (`torrents/models.py:53–56`). A ciklus lazy `torrent.torrent_file.info_hash` hozzáférést végez; a kapcsolat alapbetöltése a `TorrentFileModel.torrent_bytes` BLOB-ját is hozhatja (`torrent_files/models.py:53`). A response újabb lazy láncot érint: `torrents/schemas/api.py:37–39 → torrent.indexer_account.indexer_definition`. Az identity map accountonként csökkentheti az ismétlést, tehát pontos `3N+1` számot nem állítok. A lista nem használ nyers resume/torrent bájtokat; az info_hash a TorrentModelben már rendelkezésre áll.

**Javaslat:** külön lista-query célzott mezőkkel/eager kapcsolatokkal vagy DTO-val, restore/stream adatigényét külön megőrizve. **Előny/mérés:** kevesebb SQL és adatmozgatás 1,5–5 s-onként; SQL-számláló, 20/100/500 elemes fixture, DB/poll p95 és RSS. **Költség/kockázat:** kicsi-közepes; hibás load_only után property rejtett lazy queryt indíthat. **Elfogadás:** változatlan JSON/DB-Relay szűrés, listához nincs szükségtelen BLOB-oszlop; a választott stratégia SELECT-száma nem nő lineárisan torrentenként; restore és indítás tovább működik.

<!-- doc-anchor:cr15 -->
<a id="cr15"></a>
### CR15 — Külső válaszok méretkerete, URL-bizalmi határ és globális munkakeret

**Prioritás: P2. Bizonyítottság: kóddal igazolt kontrollhiány; túlterhelés/SSRF feltételes, mérésre váró hipotézis.**

`base_indexer_definition.py:88–95,283–287` redirectet követő klienssel teljes HTTP-választ olvas memóriába explicit bájtkeret nélkül. A download_url trackeradatból jön (például `integrations/ncore.py:185` körül). `torrent_source_provider/service.py:193–218` minden hiányzó fájlhoz taskot készít, eredményeket a batch insert előtt összegyűjti. A szemafor a futó indexer-HTTP-t korlátozza, nem a várakozó taskok, requestek közötti teljes munka vagy válaszbájtok összegét. A keresés/HTTP timeout nem bájtkeret és nem a teljes többfázisú pipeline közös deadline-ja.

Abszolút trackerlink/redirect más originre vihet, célhálózati policy nem látható. Normál kliensbemenet nem közvetlen tetszőleges URL és az indexerkliens TLS-ellenőrzése nincs kikapcsolva, ezért **nem állítok előfeltétel nélküli publikus SSRF-et**. Manipulált/kompromittált trackeradat/redirect a feltételezés. A libtorrent metainfo announce/webseed célkezelésének pontos 2.1.1-es viselkedését külön kell ellenőrizni; bizonyított natív útvonalhibát nem állítok.

**Javaslat:** streamelt letöltés ellenőrzött, kicsomagolt bájtkerettel; metadata/fájlszám-keret; összesített queue/deadline kontroll; integrációspecifikus origin/redirect policy. DNS/IP-védelemnél IPv6/rebinding és legitim CDN figyelembevétele szükséges. **Előny/mérés:** kontrollált memória/munka rossz külső válasznál; oversized/chunked/compressed fixture és egyedi kulcsos burst. **Költség/kockázat:** közepes-magas; legitim nagy torrent/CDN/burst elutasítása. **Elfogadás:** túlméret kontrolláltan megáll, tiltott cél/redirect nem érhető el, normál integrációk működnek; telített queue nem nő korlátlanul, gyors kontrollált válasz van.

<!-- doc-anchor:cr16 -->
<a id="cr16"></a>
### CR16 — Session-visszavonás és explicit böngészővédelmi szerződés

**Prioritás: P2. Bizonyítottság: kóddal igazolt revokációs hiány és middleware-beállítás; böngészős kihasználás nem tesztelt.**

`main.py:110–114` 30 napos max_age-et ad, explicit Secure/https_only és same_site nélkül. A tényleges alapérték Starlette-verziófüggő; kimenő cookie-t nem vizsgáltam. `SessionGuard` csak user_idt olvas és DB-user/role-t ellenőriz (`auth/dependencies.py:33–54`). `users/service.py:update` jelszóváltoztatáskor nem módosít session-epochot; ilyen mező a UserModelben sincs. Logout a választ fogadó kliens cookie-ját üríti, nem vonja vissza egy korábban lemásolt, érvényes aláírású cookie minden példányát.

Alkalmazásszintű CSRF-token/Origin-ellenőrzés a sessiones módosítások előtt nem látható. A `allow_credentials=False` és böngészős SameSite viszont számít: **wildcard CORS-ból nem következik automatikus sessiones CSRF**. A Stremio publikus CORS-át nem indokolt vakon megszüntetni.

**Javaslat:** user session-epoch/visszavonható session, password reset/revoke esetén érvénytelenítés; explicit HTTPS/Secure és kompatibilis SameSite/Origin-CSRF policy. Érzékeny műveletnél újrahitelesítés mérlegelhető. **Előny/mérés:** régi session vészhelyzetben visszavonható; másolt szintetikus cookie és idegen origin teszt. **Költség/kockázat:** közepes; sessionmigráció, proxy/TLS/eszközlogin. **Elfogadás:** reset/revoke után régi cookie elutasított, role-downgrade azonnali, cookie megfelel explicit policynek; idegen origin nem módosít állapotot, natív API-key használat működik.

<!-- doc-anchor:cr17 -->
<a id="cr17"></a>
### CR17 — Megosztott taskok saját DB-élettartama és rendezett shutdown

**Prioritás: P2 vizsgálati/tervezési tétel. Bizonyítottság: ownership-eltérés kóddal igazolt; tényleges DB-hiba/szivárgás mérésre váró hipotézis.**

`stremio/dependencies.py:56–77` request Sessionből épít service-t. `stremio/service.py:175–190` self/user állapotot körbezáró fetch-et ad Singleflightnak. `common/singleflight.py:27–44` külön shieldelt taskot indít, amely request-cancel után tovább futhat; ugyanez a forrásproviderben (`torrent_source_provider/service.py:18,38–40,61–64`). A request sessiont a dependency kilépésekor lezárja (`database.py:77–104`), a háttértask viszont még DB-t használhat. Több alias ugyanazon providerből párhuzamos `to_thread(find_list)` műveleteket is indíthat (`torrent_streams/service.py:119–126 → indexers/service.py:272–274`). A `check_same_thread=False` nem Session-szintű konkurenciavédelem.

A Session close utáni újrafelhasználhatósága, lazy-load és threadidőzítés befolyásolja a kimenetet; ebből nem bizonyítottam adatvesztést vagy memóriaszivárgást. Shutdownkor `main.py:60–75` klienseket zár, taskokat cancelöl, de a globális keresési singleflightokat nem üríti és a priority/save taskok befejezését nem awaiteli. `indexer_definitions/service.py:56–61 close_all` első adapterhibája a teljes ciklust megszakítja: konkrét cleanup-kivételkezelési rés.

**Javaslat:** shared task saját rövid DB-sessionnel/DTO-határral; ugyanaz a mutable Session ne fusson párhuzamos workerekben. Feladatok rendezett cancel/awaitje, utána klienslezárás; adapterenként független cleanup. **Előny/mérés:** determinisztikus cancellation/kapcsolat-visszaadás; request-cancel, két user azonos kulcsa, alias és shutdown fault injection. **Költség/kockázat:** közepes-magas; tranzakció/eager adatigény változik. **Elfogadás:** nincs Session-overlap, kint maradó checkout vagy pending task; egyik adapter close hibája nem akadályozza a többit.

<!-- doc-anchor:cr18 -->
<a id="cr18"></a>
### CR18 — Az első admin létrehozásának atomikussága

**Prioritás: P2. Bizonyítottság: kóddal igazolt check-then-act; konkrét race kimenetel mérésre váró hipotézis.**

`auth/router.py:23–39` auth nélkül countot kér, nulla usernél ADMIN-t hoz létre. `users/service.py:create` hash-el, majd insert/flush történik; nincs egyszeri atomikus bootstrap-foglalás. A username uniqueness két eltérő névnél nem védi az „egyetlen első admin” invariánst. Két request láthat nullát; a driver tranzakciókezelése szerint több admin vagy lockhiba lehet a kimenet. Ezt DB-n nem futtattam.

**Javaslat:** atomi, egyszer használható bootstrap-foglalás, szükség esetén egyszeri setup-hitelesítéssel. **Előny/mérés:** determinisztikus egyszeri setup; üres teszt-DB-n 10 párhuzamos eltérő nevű register szinkronizált count/insert pontokkal. **Költség/kockázat:** kicsi-közepes; elakadt setup/újratelepítés. **Elfogadás:** pontosan egy sikeres adminlétrehozás, többi kontrollált elutasítás, nem 500; rollback után legitim setup újrapróbálható.

<!-- doc-anchor:cr19 -->
<a id="cr19"></a>
### CR19 — Auth-védett HTTP-válaszok cache-policyja

**Prioritás: P2 shared cache/érzékeny válaszok tárolása esetén. Bizonyítottság: kóddal igazolt fejlécek; külső cache viselkedése mérésre váró hipotézis.**

A feliratcache helyesen authol szerveroldali cache-hit előtt (`stream/router.py:381–399`), bájt- és bejegyzésszámban korlátos. A HTTP-válasz azonban mindkét ágon `Cache-Control: public, max-age=86400` (`:316–319`, `:440–445`). A pathbeli API-key nem HTTP Authorization: e policy megengedi shared cache tárolását. Ilyen cache szerveroldali újrahitelesítés nélkül adhat választ a régi URL-re kulcsvisszavonás után. Nem állítom, hogy jelenleg létezik ilyen proxycache.

A `/me`, login és pairing status újrafelhasználható API-keyt ad (`users/schemas/api.py:37`, `pairings/service.py:66–72`); explicit `no-store` itt nem látható. Ez nem jelenti, hogy minden böngésző tárol minden ilyen választ.

**Javaslat:** érzékeny auth/key válasz `no-store`; feliratnál revokációs követelménnyel egyező `private`/`no-store` vagy tudatos rövid TTL. A szerver belső autholt bájtcache megmaradhat. **Előny/mérés:** shared HTTP-cache nem kerüli meg a jogosultsági policyt; helyi proxy-cache/rotáció teszt. **Költség/kockázat:** kicsi; több kérés/cachekompatibilitás. **Elfogadás:** visszavont kulcs régi URL-je nem ad policyellenes cache-hitet, auth-válaszok no-store-osak; Range/HEAD és belső cache működik.

<!-- doc-anchor:doc-7-kiegeszito-biztonsagi-es-regresszios-tesztterv-nem-futtatva -->
<a id="doc-7-kiegeszito-biztonsagi-es-regresszios-tesztterv-nem-futtatva"></a>
## 7. Kiegészítő biztonsági és regressziós tesztterv — nem futtatva

A végponttesztek csak izolált helyi Docker Desktop környezetben, szintetikus userekkel és helyi HTTP/DNS-fixture-rel futhatnak. Valós tracker, távoli szerver, meglévő adatbázis vagy valódi hitelesítés nem szükséges. A két már lefutott függvénypróba kivételével ezek tervek, nem elvégzett tesztek.

| Teszt | Végrehajtás | Elfogadási bizonyíték |
|---|---|---|
| Alapkulcs/TLS | Két üres install default/egyedi secret mellett; LOCAL kulcsforrás helyi fixture-rel; ujjlenyomatok | Nincs ismert defaulttal induló védelem; installonként eltérő privát kulcs — CR05/06 |
| Auth/role | Minden módosító route anonymous, user-session, user API-key, admin-session/admin API-key kombinációval; `/me` payloadban idegen user/role | Serveroldali auth/ownership; UI-szereprejtés nem kontroll |
| Rate limit/pairing | Login/init/poll burst; telített/lejárt kódkészlet; párhuzamos init; két user ugyanazt a kódot verifyolja | Bounded munka, kontrollált limitválasz, nincs aktív duplikátum/újrakötés — CR08 |
| Bootstrap race | Üres teszt-DB, 10 párhuzamos eltérő username, barrier a count/insert között | Pontosan egy admin, nincs 500 — CR18 |
| Logredakció | Jelölőtitkok path/query/download URL-ben; 200/redirect/4xx/timeout/HTTPStatusError | Log/traceback nem tartalmaz teljes titkot — CR07 |
| Auth előtti state | Érvényes fixture streamtoken, sok hibás API-key; utána jó kulcs, majd TTL-expiry | Rossz kulcs nem növeli a regisztert; TTL valóban takarít — CR09 |
| Parserhatár | Két ismert Range int-szélsőérték és normál mátrix HTTP-n; idézőjeles/túl hosszú metadata ID | Kontrollált 4xx, malformed ID-ra nincs külső kérés — CR10 |
| Cancel/fault | Relogin owner/joiner/all cancel és login failure; singleflight owner-request cancel, párhuzamos aliasok | Várakozók lezárulnak, nincs Session-overlap/kint maradó kapcsolat — CR11/17 |
| Valódi invalidáció | Warm streamcache→HTTP user seed/exclusion/preferencia módosítás→azonnali ugyanazon kérés; in-flight barrier | Azonnali helyes válasz, régi generáció nem ír vissza — CR12 |
| Looplag/SQL | Resume-burst alatt DB-lock, késleltetett DNS; lista SQL-számlálás 20/100/500 torrenttel | Független kérések nem blokkolódnak; nincs lineáris lazy SELECT/BLOB-terhelés — CR13/14 |
| Külső input | Oversized/chunked/compressed válasz, más originre redirect, egyedi kulcsos burst helyi fixture-ön | Méret-, cél-, queue- és összidőkeretek tartva — CR15 |
| Session/CSRF/cache | Másolt cookie reset/revoke előtt/után; idegen origin; Secure attribútum; helyi shared cache key-rotáció mellett | Revokáció/böngészős policy működik, cache nem kerüli meg az authot — CR16/19 |
| Shutdown | Futó keresés/relogin/piece/resume közben szabályos shutdown; egy adapter close kivételt dob | Rendezett task/kapcsolatlezárás, többi adapter is zár, nincs pending task — CR17 |

A meglévő tesztek több stabilitási részt lefednek (Singleflight cancel, piece timeout/cleanup, Range normálesetek, subtitle bájtkeret/headerkódolás, touch konkurencia), de ebből nem következik a fenti auth/TLS/DoS/cache mátrix lefedettsége. Az auth mockolása endpointtesztben nem igazolja a valódi middleware/session-biztonságot.

<!-- doc-anchor:doc-8-biztonsagi-kontrollok-es-a-megmarado-lefedettsegi-hatarok -->
<a id="doc-8-biztonsagi-kontrollok-es-a-megmarado-lefedettsegi-hatarok"></a>
## 8. Biztonsági kontrollok és a megmaradó lefedettségi határok

| Kategória | Mit igazol a jelen forrásvizsgálat? | Mi marad kívül vagy bizonytalan? |
|---|---|---|
| Jogosultság | Az admin módosító route-ok explicit admin guardot használnak; Stremio/Kodi/Torznab API-keyt ellenőriz; `/me` userazonosítója sessionből jön | Teljes végrehajtott szerep/ownership mátrix nincs; általános „nincs auth bypass” bizonyítvány nem adható |
| Nyilvános metaadat | Health, status/roles, attributes/preferences publikus route; `system/service.py:status` host/port/verziót is ad | Szándékos bootstrap-viselkedés lehet; threat model nélkül nem minősítek minden publikus mezőt hibának. A tényleges értékeket nem olvastam/nem közlöm |
| SQL/kódfuttatás | A vizsgált repository-k ORM/paraméterezett SQL-t használnak; a globális keresés nem mutatott requestből táplált shell/eval/exec/pickle sinket | Nem formális SQLi/RCE-mentességi bizonyíték; a C++/natív könyvtárak belseje nem auditált |
| XSS/fájlútvonal | Torrentnevek React-szövegként jelennek meg; nincs talált dangerouslySetInnerHTML sink; subtitle fejléc szűrt/URL-encode-olt; stream nem kliens által adott lemezútvonalat nyit | React/Starlette/libtorrent belső védelmeit és külső lejátszók megjelenítését nem auditáltam; natív path-traversal-mentességet nem állítok |
| Lemezen tárolt titkok | IndexerAccountModel jelszó/TOTP/cookie SQL-oszlopot használ; NetworkSettings kulcsot/tokent kezel; appoldali titkosítás nem látható | Újrabelépéshez visszanyerhető titok kell, egyszerű hash erre nem megoldás. DB/backup/host jogosultság nincs vizsgálva; DB-titkosítás külső kulcs nélkül nem old meg teljes app/host kompromittálást |
| Konténerjog | Dockerfileban nincs explicit USER-jogcsökkentés | Tényleges UID/compose user/capability/seccomp/read-only mount/limit deploymentfüggő. Build-context titokkizárása `.dockerignore` vizsgálata nélkül nem igazolható; az a megadott audit scope-on kívül maradt |
| Supply chain/CVE | Verzióleírók ellenőrizve; npm ci/lock; több backend tranzitív verzió nincs rögzítve | Registry/CVE/image-scan/SBOM nem történt. CVE megléte/hiánya nem állapítható meg e forrásból; külön engedett külső adatforrás és tényleges image szükséges |
| Proxy/TLS/böngésző | Appbeli CORS/session/TLS lánc vizsgálva | Proxycache, TLS-terminálás, forwarded-header trust, DNS rebinding, CSP/HSTS és tényleges browsereredmény nincs élesben ellenőrizve |
| Minden méretű teljesítmény | Konkrét optimalizálási helyek és reprodukálható tervek szerepelnek | Hardver, DB-méret, tracker-válasz, darabméret és workload nélkül sem minden bottleneck, sem számszerű gyorsulás nem bizonyítható |

**Értékelés:** az eredeti öt kérdés lefedett volt, az első jelentés biztonsági és hibafaktor-lefedettsége viszont hiányos. A bővített változat ezt konkrét bizonyítékokkal és 15 további CR-tétellel javítja. Ezek nem mind megerősített incidensek: a konfigurációfüggő és mérésre váró tételek külön jelöltek. Felelősen nem állítható, hogy minden lehetséges optimalizálás, hiba vagy security risk biztosan megtalálásra került.
