---
doc_id: "feature-stability-and-optimization-implementation-plan"
title: "StremHU Source — kódszintű implementációs terv"
kind: "implementation-plan"
status: "planning-only"
audience: ["developer", "ai-agent"]
tags: ["CR01-CR19", "gates", "work-packages", "tests", "rollback"]
source_commit: "2615596f7cd181454dc5ae3e1ec9e4d215e3b154"
baseline: null
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/feature/stability-and-optimization/README.md", "docs/feature/stability-and-optimization/audit.md"]
source_paths: []
---

# StremHU Source — kódszintű implementációs terv

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../../README.md) · [AI-index](../../AI-INDEX.md)

> **Státusz:** Audit-/tervezési munkakör, nem igazolt CR-implementáció. A mérési kapuk és a konkrét feladat engedélye érvényes.

**Kapcsolódó:** [README.md](README.md) · [audit.md](audit.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [0. Bemenet, állapot, használati szabály](#doc-0-bemenet-allapot-hasznalati-szabaly)
- [1. Az audit előzetes, kritikus értékelése](#doc-1-az-audit-elozetes-kritikus-ertekelese)
- [2. Minden munkacsomag közös végrehajtási szerződése](#doc-2-minden-munkacsomag-kozos-vegrehajtasi-szerzodese)
- [3. Hitelesítés, TLS, bemenet és HTTP-policy](#doc-3-hitelesites-tls-bemenet-es-http-policy)
- [CR05 — Konfigurációs aláírókulcs fail-fast](#cr05)
- [CR06 — TLS-kompatibilitási kapu, majd egyedi LOCAL kulcs](#cr06)
- [CR07 — Biztonságos naplózási szerződés](#cr07)
- [CR19 — Auth-válasz és felirat HTTP-cache policy](#cr19)
- [CR10 — Bemenetek, helyes számtartomány-kezeléssel](#cr10)
- [CR08 — Párosítási állapotgép és korlátos auth-terhelés](#cr08)
- [CR18 — Egyszeri bootstrap atomikus foglalással](#cr18)
- [CR16 — Session-epoch és ellenőrzött böngészőpolicy](#cr16)
- [4. Relay, cache és feladat-élettartam](#doc-4-relay-cache-es-feladat-elettartam)
- [CR11 — A relogin használja a már működő megosztott taskot](#cr11)
- [CR09 — Autholt active-playback regiszter](#cr09)
- [CR12 — Commit utáni, szálbiztos cache-invalidálás](#cr12)
- [CR13 — Nem blokkoló resume-író és DNS](#cr13)
- [CR17 — Rendezett shutdown; DB-ownership refaktor csak G17 után](#cr17)
- [CR01 — Következetes kapcsolati limit; policyváltozás G01 után](#cr01)
- [5. Adatforgalom és mérési kapus optimalizálások](#doc-5-adatforgalom-es-meresi-kapus-optimalizalasok)
- [CR14 — Külön torrentlistaprojekció](#cr14)
- [CR02 — WAL mérés és kizárólag indokolt checkpoint](#cr02)
- [CR03 — GZip: először hálózati és CPU-kísérlet](#cr03)
- [CR04 — Frontend observer/render profil, célzott beavatkozás](#cr04)
- [CR15 — Válaszméret, origin és admission policy G15 után](#cr15)
- [6. Prioritási, függőségi és munkacsomag-tábla](#doc-6-prioritasi-fuggosegi-es-munkacsomag-tabla)
- [7. Nyitott kérdések és döntési pontok](#doc-7-nyitott-kerdesek-es-dontesi-pontok)
- [8. Végrehajtási ellenőrzőlista](#doc-8-vegrehajtasi-ellenorzolista)

</details>

<!-- doc-nav:end -->

<!-- doc-anchor:doc-0-bemenet-allapot-hasznalati-szabaly -->
<a id="doc-0-bemenet-allapot-hasznalati-szabaly"></a>
## 0. Bemenet, állapot, használati szabály

- Bemenet: `D:\Git\docs\optimization-audit-cloud.md`, a 19 CR-tételes, kibővített audit.
- Audit SHA-256: `664CF0C6FC29750D7206D8BE5C931022CA90FE09891865D936AE42CD90B26BCB`.
- Vizsgált ág: `Optimalization`; HEAD: `2615596f7cd181454dc5ae3e1ec9e4d215e3b154`.
- Tervezés dátuma: 2026-11-03. A HEAD az audit óta változatlan; kezdetkor a munkafa tiszta. A lényeges forrásláncokat ennek ellenére újraolvastam.
- Alkalmazandó utasítás: gyökér `AGENTS.md`; további AGENTS-t a checkoutban és közvetlen szülőiben nem találtam. A repó `docs/` könyvtárát és `.env` fájlját nem olvastam. Az audit a repón kívüli kifejezetten engedélyezett bemenet.
- Ez **terv, nem végrehajtási engedély**. Nem változott forrás, teszt, függőség, Git-állapot vagy szolgáltatás. Ebben a körben dinamikus próba, teszt, benchmark és trackerkeresés sem futott. Egyetlen létrehozandó kimenet ez a fájl; az audit nem módosul.

A további utasítások egy később külön engedélyezett implementációra vonatkoznak. `Új` jelölésű fájl/szimbólum még nem létezik. A relatív útvonalak a checkout gyökeréből értendők; a sorhivatkozások **a fenti commitból**, nem az implementáció utáni állapotból származnak. A rövid `modules/...` utak előtt `server/app/` értendő. A tesztmátrixok E/B/M/V oszlopa: előfeltétel, bemenet, művelet, várt viselkedés.

A requirements Python 3.12 runtime mellett FastAPI 0.143.0, Hypercorn 0.18.0, SQLAlchemy 2.1.4, libtorrent 2.1.1 verziókat ír elő. HTTPX/Starlette tranzitív verziója nincs egyértelműen lockolva. A React Query 5.104.2. Új harmadik fél csomag nem szükséges a biztos javításokhoz. A jövőbeli implementáló nem használhat ellenőrizetlen libtorrent-settinget vagy feltételezett middleware-viselkedést; verziófüggő részletekre a G0 kapu vonatkozik.

<!-- doc-anchor:doc-rovid-belepesi-terkep-uj-fejlesztonek -->
<a id="doc-rovid-belepesi-terkep-uj-fejlesztonek"></a>
### Rövid belépési térkép új fejlesztőnek

| Folyamat | Kiindulópont és lényeges tulajdonos |
|---|---|
| Indítás | `server/app/run.py:start_server:18`; `boot/setup.py:run_migrations:19` az `alembic.ini` alapján upgrade-el; `main.py:lifespan:33` szinkronizál, taskokat indít |
| DB | `common/database.py:59–104`: közös Engine, request `db_session`, külön `isolated_db_session`; commit a context végén |
| Hitelesítés | `auth/router.py:register:23, login:50`; `auth/dependencies.py:SessionGuard:24, OptionalSessionGuard:57, ApiKeyGuard:75` |
| Indexer | `indexer_definitions/dependencies.py:29` singleton → adapterenként tartós HTTP-kliens; request-service a singleton referenciáját kapja |
| Keresés | `stremio/router.py:streams:65` → `StremioService.get_streams:156` → `TorrentStreamsService.find_by_imdb:74` → forrásprovider → indexer; több szinten singleflight/cache |
| Média | `stream/router.py:stream:59` auth+előkészítés, majd Relay darabonként streamel; felirat külön handler `:361` |
| Relay | `relay/dependencies.py:7` singleton → natív session; alert callback a Python event loopra kerül |
| Kliens | Egy QueryClient (`client/src/shared/lib/client.ts:3`), torrentpoll `shared/queries/torrents.ts:14`; route és lista külön observer |

<!-- doc-anchor:doc-1-az-audit-elozetes-kritikus-ertekelese -->
<a id="doc-1-az-audit-elozetes-kritikus-ertekelese"></a>
## 1. Az audit előzetes, kritikus értékelése

A státusz a tétel első munkacsomagjára vonatkozik. Egy tétel biztos javítása és mérésfüggő kiterjesztése külön szerepel; egyik rész státusza nem ad engedélyt a másikra.

| CR | Besorolás | Megtartott feladat / korrekció | Prioritás és függés |
|---|---|---|---|
| CR01 | Implementálható, korlátozottan | Egyetlen effektív limitalkalmazó és következetes belső állapot, a jelenlegi aktív 50-es minimum megőrzésével. A boost megszüntetése/külön konfigurációja előbb mérendő | P2; runtime-limit változás G01 |
| CR02 | Előbb mérendő | WAL/backlog és tényleges tranzakciók mérése. TRUNCATE/új PRAGMA nem feltétlenül szükséges | P2; G02, CR17 előtti/utáni kontroll |
| CR03 | Előbb mérendő | GZip kísérlet; a globális médiatömörítés elvetett | P3; G03, CR19 megőrzése |
| CR04 | Előbb mérendő | Render/request profil; csak igazolt többletnél szűkítés/memo. Nem bizonyított leak vagy dupla forgalom | P3; G04; CR14 külön mérés |
| CR05 | Implementálható | Ismert/hiányzó secret fail-fast. Kulcsgeneráló és kettős aláírási rendszer most halasztott, mert szükségtelen komplexitás | P1 a default esetén |
| CR06 | Előbb mérendő | Biztonsági tény megtartva, de automatikus egyedi TLS-re váltás csak kliens-trust kompatibilitási kapu után | P1 feltételes; G06; nem puszta sebességmérés |
| CR07 | Implementálható | Kifejezett érzékeny URL/exception logok megszüntetése. Az auditból nem következik, hogy prod access INFO valóban megjelenik: `common/logger.py:26–44` prod WARNING-ot állít | P2; G0 logútvonal-ellenőrzés |
| CR08 | Implementálható | Bounded kódgenerálás, DB-egyediség, egyszeri kötés. Rate-limit mechanizmus megtartva; küszöbök baseline/kompatibilitási kapun át | P2; G08; DB-migráció |
| CR09 | Implementálható | Auth utáni regisztráció és globális TTL/kapacitás. API-key helyett user_id belső kulcs | P2; CR19-től független |
| CR10 | Implementálható | Telített, ASCII-számfeldolgozás és numerikus külső ID-k; a hosszú, egyébként érvényes Range-et nem kell pusztán számjegyszám miatt hibának nevezni | P2; önálló |
| CR11 | Implementálható | Meglévő Singleflight újrafelhasználása adapterenként reloginra; általános Singleflight újraírása elvetett | P2; CR17 shutdownhoz csatlakozik |
| CR12 | Implementálható | Valódi write-utak commit utáni invalidálása, globális epoch-visszaállítási rés bezárása | P2; single-process feltétel G0 |
| CR13 | Implementálható részben | Resume DB és DNS leválasztása. ASS→VTT offload csak mérés után, külön részfeladat | P2; CR17 shutdown, G13-convert |
| CR14 | Implementálható | Külön listaprojekció, BLOB/lazy query nélkül; számszerű nyereség baseline után | P2; önálló |
| CR15 | Előbb mérendő | Válaszméret/origin/deadline/admission policy adatgyűjtés után. Nyílt publikus SSRF állítás elvetett; natív announce/webseed változtatás halasztott | P2; G15, CR11/17 |
| CR16 | Implementálható részben | Jelszóváltozás session-epochja; Secure/Origin policy G16 után. Minden logout globális revokációvá alakítása és új session-adatbázis halasztott | P2; DB-migráció; CR05/08 |
| CR17 | Implementálható cleanup; ownership előbb mérendő | Adapterenkénti close és rendezett shutdown biztos rés. Request/session ownership és párhuzamos DB a G17 célzott próbája után, nem bizonyított leak javításaként | P2; a nagy refaktor G17 |
| CR18 | Implementálható | DB-ben atomikus egyszeri bootstrap-foglalás; valós race reprodukció a javítás elfogadásához kell, nem újabb auth-architektúra kitalálásához | P2; CR08 rate-limit, CR16 session issuance |
| CR19 | Implementálható | Érzékeny HTTP-válasz no-store; belső feliratcache megmarad. Nem állítjuk, hogy most van shared proxycache | P2; CR03-nál megőrzendő |

Külön elvetett/halasztott irányok: új indexerpool bevezetése (már tartós); minden poll SSE-re cserélése; bizonyítatlan frontend memóriaszivárgás-javítás; vak libtorrent `cache_size`/thread tuning; állandó WAL-TRUNCATE; általános „CORS=* = CSRF” javítás; feltételezett CVE-khez függőségfrissítés. Ezekhez a forrás nem ad elég alapot.

<!-- doc-anchor:doc-2-minden-munkacsomag-kozos-vegrehajtasi-szerzodese -->
<a id="doc-2-minden-munkacsomag-kozos-vegrehajtasi-szerzodese"></a>
## 2. Minden munkacsomag közös végrehajtási szerződése

<!-- doc-anchor:doc-21-g0-elofeltetelek-csak-kesobbi-implementaciokor -->
<a id="doc-21-g0-elofeltetelek-csak-kesobbi-implementaciokor"></a>
### 2.1. G0 — Előfeltételek, csak későbbi implementációkor

1. HEAD/worktree és alkalmazandó AGENTS újraellenőrzése; eltéréskor az érintett forráslánc újraértékelése. A jelen terv nem tesz változtatást.
2. Helyi, eldobható, szintetikus tesztadat; nincs távoli szerver és nincs valós tracker. A konfigurációtesztek explicit tesztkonfigurációval fussanak, valós dotenv automatikus betöltése nélkül. A jelenlegi importkori `config=Config()` miatt ennek tesztelhető loaderhatárát CR05-ben kell létrehozni; ne olvasson a teszt titkot „kényelmi” inicializálásból.
3. A tényleges telepített HTTPX/Starlette/dnspython/SQLAlchemy verziót és releváns API-aláírásokat később lokálisan ellenőrizni; nem elég a requirements tranzitív függőségét megbecsülni. GZip/async DNS/streamelt HTTP csak ennek sikerével implementálható. Új csomagot vagy libtorrent-beállítást nem tervezünk találomra.
4. Workerszám rögzítése. CR08 memóriabeli limiter és CR12 memóriabeli epoch **egy processzre** tervezett. Több worker esetén ez a változat nem kész: DB/shared koordinációs terv és külön terheléskapu kell, vagy a támogatott indítás egy workerre korlátozandó. Ezt nem lehet a jelenlegi kódból futtatva ellenőrzöttnek nevezni.
5. Migrációs munkánál a következő revízió és tényleges verziókönyvtár felderítése az `alembic.ini` alapján; jelen feladatban a korábbi szűk scope miatt migrációfájlokat nem olvastam. A migrációk tervezett sémája itt szerepel, revízióazonosítót nem találok ki. `boot/setup.py:19–25` meglévő upgrade út megőrzendő.

<!-- doc-anchor:doc-22-ellenorzesi-sorrend-az-agents-szerint -->
<a id="doc-22-ellenorzesi-sorrend-az-agents-szerint"></a>
### 2.2. Ellenőrzési sorrend az AGENTS szerint

Ez a lista **nem most végrehajtandó**. Minden későbbi kódmódosítás után, Docker-build/commit előtt a `server/.venv` környezettel sorrendben: `python -m ruff check .`, `basedpyright.exe`, `python -m pytest tests`. Kötelező `HOST_IP`: helyi, nem loopback tesztcím, értékét nem írjuk a jelentésbe; `PYTHONIOENCODING=utf-8`. Előbb célzott tesztfejlesztés, végül a teljes fenti három ellenőrzés; hibánál javítás, csak utána továbblépés. Kliensváltozásnál a `client/package.json` tényleges `lint`, `format`, `build` parancsai, illetve a repo tesztrunnerének G0-n ellenőrzött közvetlen futtatása. Nincs package.json-ban meglévő `test` script, ilyet nem szabad adottnak venni.

Utána helyi Docker Desktop funkcionális teszt és releváns A/B/C mérés. Az AGENTS helyi compose/bootstrap/benchmark segédjei nem commitolhatók; itt nem olvastuk/futtattuk őket. A valós trackerekre konfigurált benchmarkot nem szabad vakon használni a szintetikus munkában. Később külön fixture-harness vagy engedélyezett helyi konfiguráció szükséges. Commit/push előtt a branchdokumentációra vonatkozó AGENTS-előírást a későbbi feladat engedélyezett scope-jával összehangolni; ebben a feladatban repóbeli docs-művelet nincs.

<!-- doc-anchor:doc-23-kozos-benchmarkprotokoll-es-regresszios-kapu -->
<a id="doc-23-kozos-benchmarkprotokoll-es-regresszios-kapu"></a>
### 2.3. Közös benchmarkprotokoll és regressziós kapu

- A = upstream image, B = fork main image, C = feature image az AGENTS szerinti három konténeren; külön eldobható DB/letöltési kötet. Image-digest, commit, CPU/RAM-limit, Docker-beállítás, csomagverzió és input-fixture azonosítva. Upstreamen hiányzó funkció `N/A`, nem nulla ms.
- Az A/B/C referencia mellett kötelező ugyanazon C módosítás előtti/utáni kontrollja. A baseline-t a megfelelő munkacsomag előtt menteni; nincs kitalált gyorsulás.
- Azonos fixture tracker/seeder/metadata válaszok, internetkimenet tiltva. A/B/C szekvenciálisan, sorrendjüket ismétlésenként rotálva. Cold: csak saját tesztcache/tesztkötet alapállapot; warm: előmelegítés külön, nem beleszámítva. Tilos meglévő felhasználói kötet wipe-ja.
- Rövid út: legalább 5 ismétlés, cellánként legalább 100 kérés, párhuzamosság 1/4/8; futásonként p50/p95/p99, hibák, CPU, RSS és konténermemória (anon/file-cache külön), SQL/kérésszám, megfelelő funkcionális eredmény. Hosszú futás: 30 perc memória/poll, 60 perc WAL. Libtorrent: 512 MiB/1 GiB/2 GiB, dokumentált CPU.
- Zaj: előtte változatlan C kétszer ugyanazzal a protokollal. Metrikánként `J = max(|két baseline medián eltérése|, mérőeszköz felbontása)` és baseline tartomány. Nem kész a mérés, ha gépháttérterhelés/thermal/disk cache drift uralja az eredményt; előbb környezet stabilizálása.
- Biztonsági/helyességi fixnél elfogadás: minden célzott viselkedési teszt sikeres, nulla új funkcionális hiba/OOM/timeout; latency/CPU/RSS nem mutat a baseline tartományon és J-n túl ismételhető romlást. Ha mégis, a funkcionális fix nem marad automatikusan el: okfeltárás és tudatos, rögzített költségkeret szükséges a release előtt.
- Optimalizálásnál emellett a célmetrika javulása legalább két ismételt sorozatban nagyobb legyen J-nél; mellékmetrikák ne romoljanak a fenti kapun túl. Gyorsulási százalék előre nincs ígérve. A később kijelölt UX/SLO-keret első mérések előtt írásban rögzítendő, utólag az eredményhez igazítani nem szabad.

A további „közös kapu” hivatkozás ezt a teljes ellenőrzést jelenti; nem minden funkcióhoz szükséges a teljes hardvermátrix. A modulnál megadott workload a kötelező minimum.

<!-- doc-anchor:doc-3-hitelesites-tls-bemenet-es-http-policy -->
<a id="doc-3-hitelesites-tls-bemenet-es-http-policy"></a>
## 3. Hitelesítés, TLS, bemenet és HTTP-policy

<!-- doc-anchor:cr05 -->
<a id="cr05"></a>
### CR05 — Konfigurációs aláírókulcs fail-fast

**Jelenlegi cél/lánc:** `config.py:18–32 Config`, importkor `config=Config()` (`config.py:121`) → `main.py:110–114 SessionMiddleware`; `stream/utils/stream_token.py:9–12 serializer`. A publikus alapérték mindkét aláírási célra használható. A tényleges install kulcsa ismeretlen, ezért incidens nem állítható. Kívánt invariáns: nem indul ismert/üres kulccsal, de a már biztonságosan konfigurált kulcs nem változik újraindításkor; API-key külön ellenőrzése megmarad.

**Fájlszintű terv:**

- `config.py Config.session_secret`: alapérték eltávolítása; legalább 32 karakter és tiltott ismert default ellenőrzése. A hossz policy, nem entrópiabizonyíték; telepítési előfeltétel kriptográfiai RNG-vel generált érték. A hiba csak mezőnevet/okot mutathat, soha értéket. A meglévő validációs hibaformázóhoz is ezt megtartani.
- Új `load_config(...) -> Config` saját függvény: tesztek explicit forrásból adhassanak konfigurációt, dotenv automatikus olvasása nélkül; normál indítás eddigi dotenv-forrásai megmaradhatnak. A Pydantic loader konkrét paraméterezése G0 aláírás-ellenőrzéshez kötött; nem másolunk feltételezett internális attribútumot. Appimport előtt beállítható, explicit `STREMHU_LOAD_DOTENV=false` tesztüzemmód tervezett, alapja `true`; hiányos tiltott tesztkonfiguráció fail-fast.
- `main.py`, `stream_token.py`: csak validált konfigurációból olvassanak, serializer ne generáljon saját átmeneti kulcsot. Nincs új második keyring, nincs elfogadott gyenge „legacy key”.

**Alternatíva:** perzisztált automatikus generálás kényelmesebb, de fájljog/multiworker/backup és rotáció új lifecycle-t igényel; most halasztott. A fail-fast kisebb ellenőrizhető változtatás.

| E | B | M | V |
|---|---|---|---|
| Explicit izolált config | hiányzó/üres/ismert default/rövid kulcs | load | kontrollált hiba, kimenetben nincs bemeneti érték |
| RNG fixture kulcs | két újraindítás ugyanazzal | session/token round-trip | stabil aláírás, régi URL nem pusztán restarttól romlik |
| Két külön fixture kulcs | másik aláírás | parse/session request | elutasítás; normál API-key auth sem kerülhető meg |
| Dotenv tiltott tesztmód | külön tesztconfig | app import tesztharnessben | nincs valós env-file megnyitás |

Új tervezett `server/tests/test_auth_configuration.py`; token parser és valódi middleware teszt is kell, nem csak Config mock. Metrika: startupidő + warm auth/stream út közös kapuval; változatlan helyes kulcsnál nincs új I/O. **Kész:** tesztek + kötelező ellenőrzések, szintetikus helyi login/manifest/stream. **Visszaállítás:** kódrevert mellett erős kulcs megtartása; gyenge default visszaengedése nem támogatott rollback. Kulcsrotációt csak külön release-lépésként, session/URL érvénytelenítésének közlésével.

<!-- doc-anchor:cr06 -->
<a id="cr06"></a>
### CR06 — TLS-kompatibilitási kapu, majd egyedi LOCAL kulcs

**Forrás:** `boot/network.py:_ensure_db_network_settings:41`, `write_certs_to_disk:29`, `ensure_network_settings:56`; `network/service.py:setup_local:44`, `_do_setup:116`, `check_ssl_certificate:316`; `network/ssl/service.py:get_local_ip_certificate:72`, `_generate_self_signed_certificate_fallback:104`; `run.py:start_server:18,62–63`. A publikus szolgáltatástól kapott közös privát kulcs egyedi szerverazonosságot nem ad. A meglévő self-signed fallback egyedi RSA-kulcsot/SAN-t generál, de nem lesz ettől automatikusan publikus CA által megbízható.

**G06 eljárás/baseline/döntés:** csak szintetikus helyi installon összevetni jelenlegi LOCAL, meglévő fallbackből épített egyedi self-signed, illetve már támogatott MANUAL/reverse-proxy vagy AUTO/ACME módot a tényleges célkliens-verziókon (Stremio/Nuvio/Kodi). Rögzítendő trust/import lehetősége, kapcsolat/szolgáltatásfelfedezés, restart/megújítás, hibaüzenet. Ha valamely kötelező kliens nem tud megbízhatóan csatlakozni, **nincs automatikus LOCAL-default váltás**: a release előtt választandó és elfogadandó meglévő MANUAL/AUTO átállási út. Nem tervezzük más által birtokolt domainre új, publikus tanúsítvány mágikus kiadását.

**G06 sikerénél választott terv:**

1. `SslService.get_local_ip_certificate` ne töltsön privát kulcsot hálózatról. A már létező generátort használja; új neve lehet `generate_local_certificate(host_ip)`, I/O/CPU workerben, kizárólag saját kulcs.
2. `NetworkLocalSettings` (`settings/schemas/internal.py:10–18`) kapjon `certificate_source: Literal['instance-self-signed','legacy-shared']` mezőt. Hiányzó mező régi LOCAL rekordban **legacy-shared**; így issuer vagy hostname találgatása nélkül felismerhető az átállási igény. Új rekord mindig instance-self-signed. A beállítás JSON, nem szükségszerű új SQL-oszlop.
3. `boot/network.py:_ensure_db_network_settings`: megfelelő forrás, egyező SAN/IP, nem lejárt és összetartozó cert/key esetén reuse; nem generálhat minden induláskor. Legacy rekordot csak a jóváhagyott G06 átállás szerint rotáljon; titkot nem logol. `NetworkService.setup_local` ugyanezt az ellenőrzést hívja, megújításkor is. MANUAL/AUTO ág változatlan.
4. `boot/network.py` új, LOCAL-specifikus `write_local_certificate_generation`: új generációkönyvtárba írja mindkét fájlt, validálja az összetartozást, majd egy kis aktív-generáció manifestet cserél atomikusan. BootNetworkConfig kizárólag egyazon validált generáció két útját kaphatja. Két külön PEM-fájl egymás utáni rename-je nem atomikus párcsere; ezt nem szabad annak nevezni. Írás/crash hiba esetén a régi generáció/manifest marad használható; korlátozott privátkulcs-jogosultság, siker után legfeljebb az utolsó két generáció megtartása. AUTO/MANUAL meglévő írási útja ebben a csomagban nem íródik át.
5. A `run.py` és a hálózati felület ne „internethibának” nevezze a tudatos self-signed módot; jelezze a trustfeltételt/alternatívát. A kliens `network-access` feature szövegváltozása csak e csomagban.

| E | B | M | V |
|---|---|---|---|
| Két üres install | fixture host | cert generálás | eltérő publikus kulcs-ujjlenyomat; privát kulcs nincs kimenetben |
| Saját érvényes pár | restart | boot | azonos ujjlenyomat |
| Legacy/lejárt/rossz SAN/rossz pár | mentett JSON | boot/renew | szabályozott migráció vagy indulási hiba; nincs publikus kulcsletöltés |
| Írási hiba | meglévő jó pár | csere fault injection | régi jó pár megmarad |
| G06 kliensmátrix | új trust | manifest + média | minden kötelező kliens működik |

Tervezett `test_local_certificate_lifecycle.py`, crypto/network fixture-ek; külső ACME/DNS nem érhető el. Metrika: cold certgenerálás és warm restart, megújítási üzemszünet; nincs gyorsulási elvárás, a trust/helyesség a kapu. **Rollback:** jóváhagyott egyedi MANUAL/AUTO út vagy saját korábbi még érvényes kulcs; közös privát kulcs automatikus visszakapcsolása nem biztonságos rollback. **Nyitott release-blokkoló:** támogatott kliens és trustpolitika; G06 sikere nélkül a tétel mérési/átállási terv marad.

<!-- doc-anchor:cr07 -->
<a id="cr07"></a>
### CR07 — Biztonságos naplózási szerződés

**Forrás/lánc:** `run.py:64–65` Hypercorn access format; `common/logger.py:26–44` RichHandler, prod WARNING; `indexer_definitions/base_indexer_definition.py:283–292 download_torrent`; `network/ddns/providers/duckdns.py:41–45`, `myaddr.py:38–42`; `torrent_source_provider/service.py:206–208`. A full path/query formátum léte önmagában nem bizonyít éles logbejegyzést. A direkt error URL logolása elég a javítás indokolásához.

**Módosítás:** `run.py` access formátumból teljes URL/query elhagyása, megtartva a már használt metódus/státusz/idő atomokat. Új `common/log_safety.py`: `network_error_fields(exc) -> NetworkErrorSummary(kind: str, status_code: int|None)`, `safe_endpoint_label(indexer_id,operation)`; ezek saját új interfészek, nem állítólagos Hypercorn bővítmények. HTTPX-kivétel `str(exc)`/raw exc_info helyett osztály és státusz kerüljön ki a hálózati titkos utaknál. A trackerletöltésnél indexer_id+torrent_id/operation elegendő, passkey URL nem. A provider a felhasználónak sem fűzheti vissza az eredeti query-URL-t a RuntimeErrorba. A source-provider logger ne emelje vissza a nyers cause-t.

A redakciót a log keletkezési pontján végezni; RichHandler tracebackjét általános string-regexszel „biztosan tisztának” nyilvánítani elvetett. Belső, nem érzékeny hibák stackje megmaradhat. Request/body/secret debugdump nem új feature. Invariáns: siker/hiba diagnosztizálható szolgáltatóval és művelettel, hitelesítő adat nélkül.

Teszt `test_log_redaction.py`: E=caplog és tényleges formatter/handler fixture, B=jelölőtitok path/query/download URL/cookie-szerű exception szöveg, M=200/redirect/4xx/timeout/providerhiba; V=teljes jelölőtitok sem formatted logban, sem kivételláncban, HTTP-válaszban nincs, státusz/operation megvan. G0-n prod és dev effektív logszintet külön ellenőrizni. Metrika: 1000 szintetikus logesemény CPU/byte baseline előtt-után, közös kapu; URL-elrejtés nem függhet a logszinttől. **Rollback:** csak a módosított logút kódja; titoklogolást visszakapcsoló debugflag nincs. Függés CR05-höz nincs.

<!-- doc-anchor:cr19 -->
<a id="cr19"></a>
### CR19 — Auth-válasz és felirat HTTP-cache policy

**Forrás:** `stream/router.py:_build_cached_subtitle_response:305–321`, `stream_subtitle:361,381–399,440–445`; `auth/router.py:18–69`; `me/router.py:get:39, update:46, regenerate_api_key:58`; `pairings/router.py:status:36`. A szerver belső cache-hit előtti auth jó, megőrzendő. A `public, max-age=86400` viszont shared cache-t engedhet; tényleges proxy jelenléte ismeretlen.

**Választott szerződés és fájlok:** minden feliratválasz (cached, raw stream, ASS→VTT, GET/HEAD/206/hibák) legyen `Cache-Control: no-store`; CORS, Content-Disposition, Content-Range és bájttartalom maradjon. Új közös helper a stream routeren belül `subtitle_response_headers(...)` előzi meg az ágak driftjét. Az auth, pairing és me routerek válaszaihoz célzott Response-header/dependency állítson no-store-t. A felhasználói tokeneket más admin DTO-k is visszaadják (`users/schemas/api.py:27–47`, playback DTO): `users` és `playbacks` autholt válaszokra is alkalmazni. Error pathon külön exception/ASGI headerkezelést kell tesztelni; nem elég sikeres handlerben Response-t módosítani. Célszerű kis, célzott ASGI response-start policy az érintett routercsaládokra; API-key értéket nem logol, nem pufferel bodyt.

A belső feliratcache kulcsa/32 MiB kerete/TTL-je változatlan, így no-store nem egyenlő drága újra-letöltéssel. Stremio metadata egészének vak no-store-ja nem része ennek. Alternatíva `private,max-age`: olcsóbb klienscache, de a kijelölt visszavonhatóságot nem adja; itt elvetett.

Tesztmátrix: E=ismert fixture bájtcache és jó/rossz/rotált kulcs, B=GET/HEAD/Range/konverzió, M=kérés cold és cache-hit után; V=no-store minden érintett válaszon, auth mindig lefut, bájtok/fejlécek/416 jók. E=helyi shared cache, M=először jó kulcs, majd rotáció és régi URL, V=nincs kiszolgálás a szerver megkerülésével. Meglévő `test_subtitles.py`, `test_subtitle_hardening.py`, ezek mellé új `test_sensitive_cache_headers.py`. Metrika: warm szervercache hit, kérésmennyiség, media/subtitle p95 a közös kapuval; több HTTP-kérés tudatos költség, nem kitalált gyorsulás. **Rollback:** headerpolicy külön revertelhető, belső cache nem változik; visszavonhatósági követelmény engedélyezés nélkül nem gyengíthető.

<!-- doc-anchor:cr10 -->
<a id="cr10"></a>
### CR10 — Bemenetek, helyes számtartomány-kezeléssel

**Lánc:** `stream/router.py:93–98 → StreamService.prepare_for_stream:52 → parse_range_header:216`; `stremio/utils.py:parse_stream_id:19 → schemas.py:TvdbStreamId:640/MalStreamId:659 → tvdb_resolver.py:resolve_tvdb:96,resolve_mal:446`. A Range `isdigit`→`int` (`stream/service.py:248–262`) ValueError-t enged ki; az ID string SPARQL-literálba kerülhet. A szigorúbb Torznab-parser (`torznab/query.py:133–159`) jó kompatibilitási referencia, nem átírandó teljes modul.

**Algoritmus:** új privát `parse_ascii_uint_capped(text, cap)` ellenőrzi az összes karaktert ASCII `0..9` szerint; leading zero levágás után hossz/lexikografikus összehasonlítással capre telít. Csak capnél rövidebb szám kerül `int`-be, így 5000 számjegy sem dob int-limit hibát.

```text
require nonempty and every char ASCII decimal; else 416
digits = strip_leading_zeroes(text) or '0'
if len(digits)>len(str(cap)) or equal_length_and_greater: return cap
return int(digits)
start: cap=N; ha >=N ->416
end: cap=N-1; suffix: cap=N; suffix=0 ->416
start>end ->416; egyébként a már meglévő 200/206/Content-Range szabály
```

Ez megőrzi a hatalmas, de kielégíthető end/suffix clampelését, nem nevez minden hosszú számot szintaktikai hibának. Hiányzó Range/üres fájl, multi-range és hibás egység eddigi viselkedése marad. Nyers ValueError-t nem kell mindenre általánosan elnyelni; a helper eleve kizárja.

`common/validators.py`: új `validate_numeric_media_id(value: str)->str`, ASCII-decimális és tervezett 32 karakteres felső védelmi korlát (új alkalmazáspolitika, nem állított providerlimit). A prefixelt router ID-t szétbontás után validálni; resolver publikus belépőin is védekezni, hiszen nem csak Stremio hívja. Helyes korábbi prefixek (`anime:`, `tvdb:`, `tvdb_`, stb.) megmaradnak, nem numeric címkeresést nem tiltunk be ezzel. Rossz routerbemenet kontrollált 400, Torznab megtartja protokollhibáját. A resolver ne indítson hálózatot hibás numerikus ID-nál; Pydantic field-validator hibáját a router ne engedje 500-ra fordulni.

Teszt: meglévő `test_range_and_file_validation.py:test_parse_range_header_rfc9110_matrix`, `test_tvdb_streams.py`, katalógus/torznab tesztek; új paraméterezések: latin-1 digit, Unicode digit, 5000 számjegy, sok leading zero, N=0/1, start=N, end>N, suffix>N, prefixek, idézőjel/path/whitespace/33 hosszú ID. E=HTTP/metadata fixture számláló, M=hibás kérés, V=kontrollált 4xx és nulla külső request; hosszú valid Range értelmes clamp/416, soha 500. Metrika: parseridő headerhossz függvényében, lineáris karakterellenőrzés, normál stream p95 közös kapu. **Rollback:** önálló parser/validator revert; új szigorítás előtt támogatott ID-k regressziós fixture-je kötelező, gyenge default kulcsot nem hozunk vissza a teszthez.

<!-- doc-anchor:cr08 -->
<a id="cr08"></a>
### CR08 — Párosítási állapotgép és korlátos auth-terhelés

**Forrás/lifecycle:** `pairings/router.py:init:24, status:36, verify:50` → request Session → `PairingsService.generate_pairing_codes:19`, `authorize_pairing_code:76`, `poll_pairing_status:47`; `repository.py:15–20`; `models.py:18–26`; cleanup `scheduler.py:51–59`. A kliens user_code 4 számjegyes, device_code UUID, élettartam 10 perc. A poll LINKED állapotban ugyanazt az aktuális user API-keyt adja le lejáratig: ennek retry-kompatibilitása megőrzendő. A login sync út `auth/router.py:login:50 → AuthService.validate:16`.

**CR08 állapotgép-csomag, rate tuning nélkül is implementálható:**

- `PairingModel`: unique user_code és device_code. Részleges index `expires_at > now` feltétellel nem választható: időfüggő index nem megfelelő SQLite-megoldás. Teljes user_code-egyediség és az adott lejárt kód tranzakción belüli törlése legyen az egyszerű szerződés.
- Migráció: a pairingek rövid életű, újrakezdhető adatok. A constraint hozzáadása előtt a régi párosításokat lejáratni/törölni a migrációban (egységesen a törlés választott); így régi duplikátum nem blokkol upgrade-et. Ezt release-megjegyzésben jelezni: új device-init kell. Sem users, sem API-key, sem trackeradat nem törölhető.
- Repository új műveletek: `try_create_unique_pairing(code,device_code,expires_at,now)`, `link_if_pending(user_code,user_id,now)->LinkResult`, `find_valid_by_device_code(...)`. A `LinkResult` saját enum: LINKED_NOW, ALREADY_LINKED_TO_SAME_USER, CONFLICT, EXPIRED_OR_MISSING.
- Generálás `secrets` segítségével 4 ASCII számjegy; legfeljebb 16 próbálkozás. Az insert a repóban már használt SQLite `INSERT ... ON CONFLICT(user_code) DO NOTHING` mintával készüljön (`torrent_files/repository.py:26–48` referencia); érintett sor alapján siker vagy következő jelölt. A rowcount/RETURNING választott publikus felülete G0-n ellenőrzendő. Így user_code-ütközés nem teszi hibássá a Sessiont, és nincs új SAVEPOINT/legacy SQLite implicit-BEGIN csapda. Más integrity/DB-hibát nem szabad kódütközésként lenyelni; a rendkívüli device_code unique konfliktus kontrollált503 és teljes rollback. Lock timeoutra nem 16 újabb várakozás, hanem gyors kontrollált 503. Elfogyott próbálkozásra 503 és tervezett 30 s Retry-After. A 10 000-es unique kódtér így a táblasorok felső korlátja is; globális pendingszámot külön count-race-el nem ígérünk.

```text
repeat at most 16:
  candidate = secure_four_digits()
  in the same outer transaction:
    DELETE matching candidate only if expires_at <= now
    INSERT candidate, new UUID device_code, pending, now+10min ON CONFLICT(user_code) DO NOTHING
  if inserted rowcount is zero: continue
  on lock timeout: stop with 503
  on success: return pair, outer request commits
otherwise: 503

UPDATE pairings SET status=linked,user_id=:user
WHERE user_code=:code AND status=pending AND expires_at>:now
if affected=1: LINKED_NOW
else: re-read current record:
  same user + linked + valid -> idempotent success, no mutation
  other linked user ->409
  expired/missing -> controlled existing error family
```

Óra injektálható `now()` legyen; a meglévő naive helyi DateTime sémát ebben a csomagban nem alakítjuk UTC-migrációvá. A lejárás minden ágon azonos `<=now` feltételt használjon. A service validálja a 4 jegyű verify-kódot; eszközpoll nem kap session guardot, a véletlen device_code továbbra is bearer-azonosító. Tokenkézbesítés nem válik első-pollra törlődővé.

**G08 rate-limit kapu:** helyi kliensfixture-ön mérni login/init/verify/status normál csúcsát és NAT-esetet; összevetni változatlan C-vel. Új `common/auth_rate_limit.py` csak e kapu után bekötendő: processzszintű, `threading.Lock` által védett token bucket, monoton óra, legfeljebb 4096 kulcs; live bucketet nem szabad kilökni és ezzel limitet újrakezdeni, telített tároló kontrollált 429. Szerepkörönként/route-onként eltérő saját policyobjektum. Tervezett induló kísérleti policy: login forrásonként 30/perc és accountonként 10/perc, pair-init 60/perc/forrás, verify 30/perc/user, status 120/perc/device. Ezek **új tesztelendő policyjelöltek, nem mért szükségletek**; éles bekötésük csak G08 sikerével, szükség esetén módosított és rögzített alapértékekkel.

Azonosítás a transport peer alapján; untrusted X-Forwarded-For nem használható. Proxy esetén G0/G08-ban ellenőrzött trusthatár kell, különben mindenki egy cím alá kerülhet. Bucketkulcsban device_code hash-e, nem teljes bearerérték; nincs per-request új limiterpéldány. Több processz esetén a lokális változat nem ad globális limitet, G0 blokkolja. Cancel nem adhat vissza elhasznált tokent, a számláló önmagában nem hosszú háttértask.

| E | B | M | V |
|---|---|---|---|
| Óra/RNG fixture | ismételt 16 ütközés | init | véges 503, DB tranzakció használható |
| Valós fájl-DB két sessionnel | azonos első RNG-kód | párhuzamos init | külön aktív kód/unique conflict kezelve, nincs 500 |
| Pending rekord | két eltérő user | párhuzamos verify | legfeljebb egyik köt, másik nem írja át |
| Már kötött kód | azonos/idegen user | verify, majd device poll | saját replay idempotens; idegen409; eredeti user marad |
| Lejárat határa | now==expires_at | verify/status/init candidate reuse | egységes lejárt szabály, nincs régi tokenkézbesítés |
| Fake monotonic/4096 bucket | refill/burst/új kulcs | admit | determinisztikus429/Retry-After, cap nem kerülhető meg evikcióval |
| G08 normál/NAT kliens | legitim poll és login | terhelés | nincs téves limit a jóváhagyott workloadon |

Tervezett `test_pairing_state_machine.py`, `test_pairing_concurrency.py`, `test_auth_rate_limits.py`; DB-session fixture a meglévő touch/concurrency mintákból, de valódi két kapcsolat kell. Teljesítmény: auth CPU, init SQL-szám/p95, limitelt válaszidő, bucket/tábla méret; közös kapu és A/B/C csak közösen létező auth végpontokra. **Rollback:** limiter külön visszavonható a küszöbök módosításával, állapotgép/unique szerződés megtartandó; migráció downgrade csak párosítási rekordok újrakezdésével, felhasználói adat nem érinthető.

<!-- doc-anchor:cr18 -->
<a id="cr18"></a>
### CR18 — Egyszeri bootstrap atomikus foglalással

**Forrás:** `auth/router.py:23–41 register` count-then-create; `users/service.py:create:42–68`, `_hash_password:184`; `users/repository.py:create:25`, `count:22`; `settings/models.py:SettingModel:7–11` meglévő `key` PK. A több admin/lockhiba konkrét race-kimenetele nem bizonyított, de az egyszeri regisztráció invariánsát a kód nem teszi atomikussá.

**Választott megoldás:** külön `auth/bootstrap.py` (új) `BootstrapService.register_first_admin(username,password)->CommittedUserSnapshot`. A router ne meglévő request Sessionből indítsa a bootstrap írását. Hash-elés írólakat előtt, CR08 által limitálva; opcionális gyors, külön rövid read-only count csak korai elutasítás, nem biztonsági döntés. Utána dedikált izolált sessionben **első írásként** insert `SettingModel(key='auth_bootstrap_complete',value={})`, explicit flush; PK-konfliktus a vesztesnek kontrollált403. Ezután count: meglévő usernél403/rollback. Nincs hosszú hash a write tranzakció alatt. Előkészített hashból létrehozni az admint, a foglalás+user insert ugyanabban a commitban. A router csak sikeres commit után állít sessiont a visszaadott id/epoch alapján. A `CommittedUserSnapshot` tervezett alakja `{user: UserResponse, session_epoch: int}`: a nested role és minden response-mező még a saját sessionön belül materializálódik, a kész DTO viszont csak sikeres context-commit után tér vissza; zárt Sessionhöz kötött UserModel nem adható vissza.

Új privát `UsersService.create_from_prepared_password(...)` vagy BootstrapService-beli belső constructor csak szerver által előállított hash-t fogadhat; publikus DTO-ra hashmező nem kerülhet, nem lehet új felhasználó-létrehozási kerülőút. Más `IntegrityError` nem automatikusan403: a bootstrap PK ütközését külön azonosítani, rollback után külön rövid ellenőrzéssel. DB locktimeout kontrollált503. Már létező userállománynál foglalási sor hiánya sem nyithat regisztrációt; a tranzakción belüli count védi. A marker fennmarad, ha később minden usert eltávolítanak: új bootstrap csak külön adminisztratív helyreállítási eljárással, nem publikus API-val. A meglévő settings tábla miatt új séma nem kell, opcionális enum konstans megengedett.

Teszt `test_first_admin_registration.py`: E=üres fájl-DB, B=10 eltérő név, M=barrierrel egyidejű regisztráció, V=egy committed admin+marker, többi403/503 legfeljebb időleges lock esetén, ismétlés után403, nincs500. E=hash/user-insert/commit fault, V=nem marad árva marker, nincs kiadott sikeres session; E=nemüres DB marker nélkül, V=403; E=minden user törölve markerrel, V=403. Metrika: bootstrap hash és writerlockidő külön, normál login változatlan; közös kapu. **Kockázat/rollback:** régi bináris nem ismeri a markert; rollback mellett a publikus register út lezárandó vagy az állapot mentésből visszaállítandó. Marker törlését normál downgrade-automatika ne végezze. CR08/CR16 interfészeivel egyeztetendő.

<!-- doc-anchor:cr16 -->
<a id="cr16"></a>
### CR16 — Session-epoch és ellenőrzött böngészőpolicy

**Lánc:** `auth/router.py:register/login/logout`, `auth/dependencies.py:SessionGuard:24`, `OptionalSessionGuard:57`; `users/service.py:update:91–134`; `me/router.py:update:46`; `users/models.py:UserModel:19`; `main.py:110–114`. Role minden kérésnél DB-ből friss, ezt megőrizni; API-key nem válik sessionné. A meglévő logout **helyi logout marad**: a másolt cookie külön visszavonásához szerverállapot kell, de ebből nem következik, hogy minden logoutot minden eszközre ki kell terjeszteni.

**CR16 epoch-csomag:**

- `UserModel` új, belső `session_epoch:int`, NOT NULL, default/server default0; additív migráció a meglévő usereknek0. UserResponse nem teszi publikussá.
- `UsersRepository.bump_session_epoch(user_id)` SQL-szintű `epoch=epoch+1` update, ugyanabban a tranzakcióban, amelyben jelszó változik/törlődik; a régi érték Python read-modify-write-ja elveszíthet konkurens revokációt. `UsersService.update` minden explicit password mezőnél meghívja, rollback együtt történik.
- Login és sikeres bootstrap: session előző tartalmának clear, majd user_id+session_epoch. Bootstrapnál CR18 committed snapshot. Mindkét guard összeveti a cookie epochját a DB aktuálisával. Hiányzó/eltérő epoch: kötelező guard401+clear, opcionális guardNone+clear. Régi cookie-k egyszeri újrabelépést igényelnek; nincs veszélyes missing→0 fallback.
- Saját jelszóváltoztatás minden régi sessiont, az aktuálisat is érvényteleníti. `me/router.py` Requestet is kap, password payloadnál clear; `client/src/shared/queries/me.ts:useUpdateMe:65` sikeres password műveletnél query cache clear+login navigáció a megfelelő form/route együttműködésével. Más profilmezőnél a jelenlegi setQueryData megmarad. Admin jelszóváltoztatás a céluser sessionjeit vonja vissza, nem az adminét.

**G16 böngészőkapu:** változatlan C tényleges Set-Cookie-jának vizsgálata HTTPS és helyi tesztapp mellett; pontos Starlette-paraméterek G0-n. Későbbi bekötés: explicit `https_only=True`, `same_site='lax'` ha az ellenőrzött verzióban ezek az aláírások léteznek. A lokális tesztmiddleware explicit teszt-override-ot kaphat, prod downgrade flag nincs. `Origin`-policy saját helperként: sessiones módosító auth/me/users/network/system/indexer/relay/torrent utakra az Origin scheme+host+port egyezzen a trusted konfigurált app originjével; `null`/idegen origin tiltott, Host/X-Forwarded-Host nem trustforrás. Origin nélküli natív JSON-kliens megengedett; böngészős cross-site jelzés ellenőrizendő. API-keyes Stremio/Kodi/Torznab olvasás CORS-a nem változik. Ha a proxy/legitim kliens alternate originje ezt megtöri, csak explicit konfigurált allowlisttel és új teszttel folytatható, nem wildcarddal.

Teszt `test_session_revocation.py`, `test_session_origin_policy.py`: E=valódi signed session middleware és fájl-DB, B=jó/hiányzó/rossz epoch, M=védett és /me request, V=megfelelő401/None, role-check változatlan. E=két session ugyanahhoz a userhez, M=password update, V=mindkettő érvénytelen, másik user működik; rollbacknál régiek élnek; két bump mind számít. E=régi cookie, V=egyszeri login szükséges. E=Origin saját/idegen/null/nincs, natív API-key és proxyfixture, V=jóváhagyott policy, nem általános CORS-letiltás. Metrika: auth SQL-szám (többnyire eddigi user-select mezőbővül), login/update p95 közös kapu. **Rollback:** séma additív, oszlop maradhat; régi kód epochot ignorálna, ezért csak kulcsrotációval/sessionek kivezetésével biztonságos. Új „logout all” API, teljes szerveroldali sessiontábla és kötelező reauth UX most halasztott.

<!-- doc-anchor:doc-4-relay-cache-es-feladat-elettartam -->
<a id="doc-4-relay-cache-es-feladat-elettartam"></a>
## 4. Relay, cache és feladat-élettartam

<!-- doc-anchor:cr11 -->
<a id="cr11"></a>
### CR11 — A relogin használja a már működő megosztott taskot

**Forrás:** `base_indexer_definition.py:84–86,368–395`, `IndexerClient.request:47–74`; meglévő `common/singleflight.py:20–58`. A Future nem shieldelt, tulajdonos cancelje sem zárja le biztosan a várakozókat. A Singleflight viszont már kezeli a waiter-cancelt és saját befejezéskor takarít; ezt nem újraimplementáljuk.

**Módosítás:** adapter konstruktor új `Singleflight[None]` mezőt kap, `_login_in_progress` Future eltűnik. `relogin()` a per-adapter instance egyetlen rögzített `login` kulcsát futtatja `lambda:self.login()` factoryval. A factory csak feladatindításkor fut; minden várakozó ugyanazt a taskot várja. Direkt első login és cookiecsere viselkedése nem változik, a HTTP-szemafor ne maradjon megszerezve relogin alatt. `close()` először a login-regisztert zárja/cancel-awaiteli, majd HTTP-klienst; a stopping állapotot CR17 biztosítja. Új total login-timeoutot nem találunk ki: a létező HTTP timeout megmarad, esetleges közös deadline CR15 kapus feladata.

| E | B | M | V |
|---|---|---|---|
| Fake adapter gate-elt login | 5 request | párhuzamos relogin | 1 login, mind siker |
| Owner/joiner külön task | egyik cancel | többiek gate utáni folytatása | siker, nincs InvalidStateError |
| Minden waiter cancel | login később hiba | task befejezése | registry takarít, nincs unhandled exception |
| Login fail, majd jó | két hullám | retry | az első élők hibát kapnak, második új task siker |
| Futó login | close/stopping | új request | folyó feladat megvárt, új munka nem indul, kliens zár |

Új `test_indexer_relogin.py`; a meglévő `test_singleflight.py` és `test_relay_pending_piece_requests.py` regresszióként változatlan elvárással. Metrika: relogin HTTP-darabszám és waiterek lezárási ideje, közös auth/keresési p95 kapu; nincs ígért gyorsulás. **Rollback:** adapterre korlátozott; a hibás Future-re visszaállás helyett a release hibáját izolálni. Függés: CR17 shutdownrész, de cancellation-javítás külön tesztelhető.

<!-- doc-anchor:cr09 -->
<a id="cr09"></a>
### CR09 — Autholt active-playback regiszter

**Forrás/lánc:** `stream/router.py:65–81` regisztrál, majd authol; `stream/active_playback.py:5–31,48–80` API-key szerinti tároló+events; `stremio/service.py:582–585` API-keyvel vár. A TTL nem a külső kulcsokat takarítja. Érvényes streamtoken szükséges a támadási úthoz, ezt nem szabad elhallgatni.

**Változás:** az auth sikerét követően és a playbacklimit ellenőrzése után, még a lassú `prepare_for_stream` elé kerüljön regisztráció. Így a feliratvárakozó nem veszti el az indulási értesítést. Ez „hitelesített indulási szándék”, nem garantált lejátszás; ha az előkészítés hibázik, a szándék visszavonható, de újabb ugyanazon torrentindulást nem törölhet (record monotonic nonce alapján `remove_if_matches`). A `HEAD` megtartja az eddigi indulási-jelzés kompatibilitását, külön klienspróba szükséges.

Új saját `ActivePlaybackRegistry` az eddigi modulban: `record(user_id,group)->RecordId`, `find(user_id,valid_groups,max_age)`, `wait(...)`, `prune(now)`, `remove_if_matches`, `close()`. Monoton óra injektálható; history userenként20, globálisan tervezett1024 user; TTL7200 s marad. Expired history-k prune-ja record/find/wait műveletenként; a méretkorlát idle esetben is biztos, aktív terhelés nélkül új memória nem nő. Eseményvárakozók külön életciklusúak: finally eltávolítás, globális tervezett4096 várakozó fölött nincs új Event, a hívó azonnal `None`-ot kap, így a feliratfallback működik. History evikciója ne dobja el a még élő waiterek handle-jeit. `close()` jelez/takarít, ne hagyjon várakozót futni.

`record/find/wait` és `StremioService.get_subtitles` argumentuma API-key helyett user.id, csak belső interfész változik; URL/token nem. A regiszter loophoz kötött, az összes hívó ott fut; nem kerül új workerbe. Felhasználó törlése commit után `remove_user`-t ütemezhet; global TTL/kapacitás ettől függetlenül védi. A számok új korlátpolicyk, nem mért szükségletek; G09 terhelésen ellenőrizendők, szükség esetén paraméterezve.

Teszt új `test_active_playback_registry.py` fake órával és valódi asyncio.Eventtel: rossz kulcs+jó streamtoken→401 és változatlan registry; jó user→feliratértesítés mindkét indulási sorrendben; 1025 user→cap, TTL utáni takarítás; wait cancel/timeout→nincs eventmaradvány; régi prepare hiba nem törli az új recordot; shutdown minden várakozót lezár. Meglévő `test_subtitles.py` active-binge eseteit user_idra igazítani, elvárt felirat nem változhat. Metrika: registry/event elemszám, 30 perces heap, subtitle-indulási p95; közös kapu/A/B/C szintetikus stream+subtitle, upstreamnél támogatás szerint N/A. **Rollback:** csak belső kulcsváltás és registry; migráció nincs, átmeneti history restartkor elveszhet, ez korábban is így volt.

<!-- doc-anchor:cr12 -->
<a id="cr12"></a>
### CR12 — Commit utáni, szálbiztos cache-invalidálás

**Forrás:** `stremio/service.py:40–61,156–190`; a generációs segédnek az auditban nincs termékbeli hívója. Write-utak: `users/service.py:update:91,regenerate_api_key:136,delete:141`; `user_preference_definitions/service.py:create:52,update:76,delete:95,reorder:109`; `attribute_exclusions/service.py:create:18,delete:47`; indexerlogin/delete `indexers/service.py:68,166`; `settings/service.py:save_system:25,save_network:77`; globális preferencia-definíciók módosítási service-ei. A globális invalidálás jelenleg a generációt nullázza, ezért egy régi `0` snapshot újra érvényesnek tűnhet; ezt is rendezni kell.

**Választott minimális architektúra (egy processz, G0):**

- Új `modules/stremio/cache.py` `StreamCacheState`: `revision(user_id)->(global_epoch,user_epoch)`, `get`, `put_if_revision`, `invalidate_user`, `invalidate_all`. Minden rövid dictionary-művelet közös `threading.RLock` alatt; sem HTTP, sem DB, sem await nem történhet lock alatt. A generációellenőrzés+beírás egyetlen kritikus szakasz. `invalidate_all` **inkrementálja** a globális epochot, nem állítja0-ra. Userszintű revision-tábla tervezett1024 fölött globális epochváltással kiüríthető, így nem lesz régi revision újra érvényes. Cache500, TTL60 marad.
- `StremioService.get_streams`: új kulcs a revision-párt is tartalmazza; az induláskor másolt policy/revision alapján kér, végén atomi `put_if_revision`. Régi folyó kérés befejezhető a régi callernek, de nem töltheti vissza az új cache-generációt, és új kérés nem csatlakozhat hozzá azonos kulccsal.
- Új `common/commit_actions.py`: `mark_stream_cache_dirty(db,user_id|None)` a Session.info-ban csak coaleszkáló scope-ot tárol, nem Request/ORM/coroutine referenciákat. `database.py:db_session` és `isolated_db_session` kizárólag **saját sikeres outer commitjuk után** futtatják `drain_commit_actions(db)`-t; rollback/finally töröl. Nem használunk vak after_commit eseményt, mert az adott SQLAlchemy-verzióban a nested SAVEPOINT viselkedését nem igazoltuk. A wrapperben világos a külső transaction határ. Külön explicit commitoló alkalmazási utak G0 leltára kötelező; ugyanazt a drain szerződést kell használniuk.
- A felsorolt service-módosítók sikeres mutate/flush után jelölnek a saját repository Sessionjével. Globális változásnál all-scope, userspecifikusnál céluser, API-key rotációnál is a régi adatok mielőbbi kivezetése. Reorder és exclusion-delete se maradhat ki. A read-only lekérdezések nem jelölnek.
- Commit és drain két külön hibatartomány: ha commit sikertelen, nincs invalidáció; ha sikeres commit után invalidációs váratlan hiba történik, a DB már nem rollbackelhető. Biztonságos globális cacheclear/epochváltás és titokmentes hibanapló az előírt fallback, nem „sikertelen commit” üzenet. Processzek közötti koherenciát ez nem állítja; több workernél új terv szükséges G0 szerint.

```text
with session:
  mutate; dirty_scope union=affected users/all
  try COMMIT
  on failure: ROLLBACK; discard scope; raise
  after success: cache.invalidate(scope) synchronously under short RLock
  finally: discard scope; CLOSE
fetch start snapshot=(global,user); finish -> compare-and-put under same lock
```

Alternatíva DB-s revision minden cache-hit előtt: multiworkerben jobb, de itt új adatbázis-read/migráció és szélesebb módosítás lenne; G0 single-process esetén nem szükséges. Route-onként commit előtti `invalidate()` nem választott, mert rollback/in-flight rést hagy.

Teszt `test_cache_and_db_concurrency.py` megmarad, új `test_stream_cache_write_invalidation.py`: valódi endpoint warm-cache→seed/exclusion/preferencia/grouping/indexer változás→azonnali helyes válasz; másik user nem invalidálódik szükségtelenül; rollbackkor cache érintetlen; gate-elt régi fetch nem írhat vissza user/global epochváltás után; nested rollback/commit nem drainel külső commit előtt; workerthread commit és loop fetch race számlálóval determinisztikusan tesztelve. Metrika: cache-hit arány, lockvárakozás, DB-select és warm p95; A/B/C funkcionális rangsor+találatszám egyezés a jóváhagyott policy szerint, közös kapu. **Rollback:** write-hookok/cache együtt revertelendők; cache restartkor törölhető, sémamigráció nincs. CR17 snapshotrefaktorja a revision-t a taskbemenettel egységesen rögzítse.

<!-- doc-anchor:cr13 -->
<a id="cr13"></a>
### CR13 — Nem blokkoló resume-író és DNS

**Forrás:** `relay/service.py:64–67,390–407` loopon szinkron callback → `torrents/background_tasks.py:handle_save_resume_data:8` → külön DB-session, de ugyanazon loop szálán; `relay/background_tasks.py:resume_save_loop:6` 600 s-onként; `network/ssl/service.py:wait_for_dns_propagation:27–60` szinkron resolver. Az I/O-kockázat igazolt, a lag nagysága nem.

**Kis csomag 1 — DNS:** G0 után a már függőségként jelen lévő dnspython async resolver API-ját ellenőrizni, majd azt használni. Saját `resolve_txt_async(host)->list[str]` wrapper; ugyanazok a nameserverek, TXT-szegmensek és 300 s összidőkeret, de monoton deadline. Minden await előtt remaining számítása; lookup/sleep nem lépheti túl a teljes keretet. CancelledError propagálódik, a timeout eddigi domainhibára fordul. Ha ellenőrzött async API nem áll rendelkezésre, `asyncio.to_thread` alternatíva csak a háttér DNS-call tényleges befejezésének megvárásával; cancel nem állítja le a threadet. ACME-kliens teljes szinkron működését ez a csomag nem nyilvánítja megoldottnak.

**Kis csomag 2 — resume:** új `modules/torrents/resume_writer.py` `ResumeWriter.submit(info_hash,bytes)->bool`, `start()`, `flush_and_close()`. Callback kizárólag loopon koaleszkál; OrderedDictben pending, ugyanazon hash utolsó értéke felülírja a korábbit. Pending+in-flight bájt együttesen számítson; tervezett alapkeret8 MiB, legfeljebb1024 hash, workerbatch64. Ezek új policyjelöltek, a baseline resume-méretkapu ellenőrzi. Túl nagy/telt queue nem blokkolja a piece-alertet: explicit elutasítás+számláló+titokmentes warning, nem néma siker. A resume periodikus best-effort állapot, nem torrentpayload; overloadnál utolsó köztes mentés elvesztése dokumentált kompromisszum.

A worker batch-et leválasztja, `asyncio.to_thread(save_batch)`-ben egy worker-owned `isolated_db_session` tranzakcióval ír. Nincs ORM/session átadás. Commit után byte-lease felszabadul; hiba esetén maximum egyszer újrapróbálható, majd számlált hiba, ne legyen végtelen háttérloop. In-flight DB-call cancelje nem öl threadet: flush/close a valós befejezést várja; shutdown-grace túllépéskor sikertelen mentést kell jelenteni, nem hamis „minden kész”-et. CR17 határozza meg az alert→writer shutdown sorrendjét.

`register_persisted_torrents_callbacks` writer submitot regisztrál, visszaad eltávolítható callback-handle-t; lifespan újraindulás nem duplikálhatja. `handle_save_resume_data` szinkron DB-munkája a worker `save_batch` funkcióba költözik; a meglévő `TorrentsService.save_resume_data` használható az új sessionön belül.

Teszt új `test_resume_writer.py`, `test_async_dns_wait.py`: E=blokkolt fake DB/DNS és loop heartbeat, B=burst, M=submit/resolve, V=heartbeat fut, legutóbbi hashállapot mentve; DB-fail/retry/kilépés; byte cap az inflightot is számolja; queue rejection látható; ugyanazon hash newer pending értékét régebbi retry nem írhatja felül (globális monoton submit-sorszám az envelope-ban; latest-by-hash metaadat csak pending/in-flight hashhez élhet, befejezéskor törlendő). DNS success/NoAnswer/határidő/cancel determinisztikus órával. Meglévő Relay piece tesztek regressziók. Metrika: looplag p99, piece p95, resume backlog/bytes/rejected, flushidő; közös kapu és 10/100/500 torrent+helyi DB-lock fixture. **Rollback:** DNS önálló; writer külön revertelhető, callback dupla regisztráció kizárva. ASS→VTT csak G13-convert után: profil a jelenlegi 8 MiB korláton belül; CPU/looplag dominancia esetén külön worker, nincs feltétel nélküli áthelyezés.

<!-- doc-anchor:cr17 -->
<a id="cr17"></a>
### CR17 — Rendezett shutdown; DB-ownership refaktor csak G17 után

**Forrás:** `stremio/dependencies.py:48–63` request Sessiont ad tovább; `stremio/service.py:175–190` self/user capture; `torrent_source_provider/service.py:18–20,34–64,178–218` globális singleflight és requestservice; `torrent_streams/service.py:119–126` párhuzamos aliasok; `common/database.py:77–104` Session close; `common/singleflight.py:27–38` shield. A shielding szándékos és helyes egy várakozó cancelje esetén. Abból még nem állítható konkrét szivárgás, hogy a task tovább futhat.

**G17 eljárás:** csak helyi fájl-DB/fixture tracker. Instrumentált Session-proxy rögzítse sessionazonosítóval (nem titokkal) a create/use/commit/close és az aktív DB-művelet kezdet/vég időit. Barrierrel (a) request owner cancel majd még egy várt DB-read, (b) két request azonos keresőkulccsal, (c) két alias külön `to_thread(find_list)`, (d) shutdown alatti munka. Baseline változatlan C. Trigger: request-close után közös task még azonos Sessiont használ, vagy azonos Session műveletei/implicit lazy-loadjai átfednek, vagy pool-checkout nem tér vissza. Nem elég csak kivételt várni: a tiltott ownership/overlap önmagában tervezési szerződéssértés. Ha a teljes trace és lazy-load leltár szerint ilyen nincs, a nagy DTO-refaktor halasztandó, cleanup önmagában marad.

**Biztos cleanup-csomag:** `IndexerDefinitionsService.close_all` (`service.py:56–61`) adapterenként fogjon kivételt és folytassa, titokmentes összesítéssel. Új module-level saját cleanup függvények a meglévő regiszterekhez: `stremio.service.close_stream_searches()`, `torrent_source_provider.service.close_source_searches()` (mindhárom regiszter), adapter relogin zárása CR11 szerint. A `Singleflight` kapjon minimális „closed” őrt és saját `aclose()`-t a már meglévő cancel_all köré; a bevált dedup/shield/exception-consume algoritmus nem változik. Closed run új saját `SearchStoppingError`, HTTP503-ra fordítva, nem véletlen500.

`main.py:lifespan` yield köré try/finally; sorrend:

1. Keresések/admission stop, új shared task nem indulhat; scheduler új jobjainak megállítása.
2. Stream/source/download singleflightok és relogin taskok cancel+await; priority és resume-periodikus producer cancel+await. A külön `to_thread` műveletek valós befejezését saját ownerük követi, egy await canceljét nem tekintjük threadmegállításnak.
3. Relay piece requestek close+await; utolsó resume snapshot kérése, alertfeldolgozás még él. Ne fix 1 s sleep legyen bizonyíték: ismert handle-listához tartozó save_resume_data/sikertelenség visszajelzés vagy megadott deadline döntsön.
4. CR13 writer drain/close; timeout vagy elutasított snapshot esetén explicit részleges mentési eredmény, nem hamis siker.
5. HTTP-kliensek zárása; callbackek lekapcsolása (regisztrált Python callbackek eltávolítása, native notify ismert callable felületén no-op). Native session explicit felszabadításához a libtorrent 2.1.1 pontos támogatott API-ja G0-n ellenőrzendő: ismeretlen `abort/close` hívást nem írunk elő.
6. Memóriabeli playback/cache és singleton referenciák takarítása a komponens újraindíthatósági szerződése szerint. Egyszeri processzexit és ismételt lifespan külön teszt; zárt singleton HTTP-klienst új lifespan nem kaphat vissza. Bármely cleanuphiba mellett a többi cleanup fusson le.

**G17 trigger után választott DB-határ:** nem egy hosszú request Sessiont zárunk még tovább a háttértask köré. Rövid sync UoW-k saját workerben nyitnak/zárnak Sessiont, és kizárólag adatot adnak vissza; HTTP await alatt nincs ORM-kapcsolat.

| Új saját adattípus/interfész | Tartalom és kódbeli feladat |
|---|---|
| `SearchPolicySnapshot` | user_id, API-key (nem logolható), seedküszöb, flags, csoportosítás, tiltott attribute-idk, előre számított rangtérképek, CR12 revision |
| `IndexerAccountSnapshot` | indexer_id, név/URL/definition flag-ek, full-download policy; jelszó/cookie nem másolódhat keresési DTO-ba |
| `TorrentFileSnapshot` | indexer_id, torrent_id, info_hash, szükség szerinti torrent_bytes és már materializált TorrentInfo; nincs lazy ORM-property |
| `TorrentSourceSnapshot` | előző indexer/file snapshot, torrent_id/download_url/imdb_id/seeders, médiaattribútum-értékek |
| `load_search_policy(user_id)`, `load_indexer_accounts()`, `load_torrent_files(ids)`, `store_torrent_files(items)` | minden hívás önálló izolált sessiont használ ugyanazon worker műveleten belül és commit/close után tér vissza |

Érintett fájlok: `torrent_source_provider/dependencies.py` a request-service helyett stateless factoryt adjon a shared tasknak; `service.py` publikus find_* a snapshotot visszaadó factoryt zárja körbe, ne request-self-et. `indexers/dependencies.py/service.py` readlist saját UoW/DTO; `torrent_files/isolated_service.py` bővülő read-many snapshotművelet. `torrent_streams/service.py:_filter/_sort` a user lazy kapcsolatai helyett SearchPolicySnapshot előre számított mapjait használja. `torrent_streams/schemas.py`, `stremio/schemas.py`, `torznab/items.py`, katalógus-meta konverterek az új értéktípusokat fogadják; régi `.info`/`.indexer_torrent` olvasások tételes térképe a G17 leltár része, megmaradt ORM-kapcsolat nem fogadható el. Shared eredmény ne legyen hívók által módosítható: tuple/frozen értékek, vagy a fogyasztónak mély másolat a meglévő Pydantic-objektumokról, költsége mérve. A letöltéshez használt account secret továbbra is az adapter saját storage-ából jön.

Ez a nagyobb rész több kis csomag: policy snapshot; indexer/file UoW; forrásprovider/konverterek; csak utána keresési lifecycle integráció. Változatlan payload/sorrend/dedup és cancel-szerződés kötelező, singleflight kikapcsolása nem helyettesíti a javítást.

Teszt `test_search_resource_ownership.py`, `test_lifespan_cleanup.py`; meglévő singleflight/stream/catalog/torznab regressziók. E/B/M/V a G17 négy trace-forgatókönyve: nincs owner-close utáni DB-use vagy átfedő Session, pool checkout visszatér, két user nem kap egymás URL-jéből, waiter cancel nem szakítja a többit. Cleanupnál egy adapterhiba, futó DB-thread és ismételt lifespan; minden elvárt erőforrás befejeződik vagy jól azonosított deadline-hiba látható. Metrika: task/checkouts/szálak, 30 perces heap és keresési p95/SQL-szám; közös kapu+A/B/C. **Rollback:** snapshot-alcsomagok külön, a biztos cleanupot nem kell velük visszavonni; külső API/séma nem változik, feature-flag legfeljebb tesztben enged két összevethető keresési pipeline-t, prod default a kapu után egyértelmű.

<!-- doc-anchor:cr01 -->
<a id="cr01"></a>
### CR01 — Következetes kapcsolati limit; policyváltozás G01 után

**Forrás:** `relay/service.py:update_settings:101–131`, `add_torrent:266–308`; `relay/entities.py:Torrent.__init__:29–60`, `priority_manager:81–99`; `settings/schemas/internal.py:57–71`; `relay_settings/service.py:sync_settings:26–39`. A UI `client/src/routes/_protected/relay/settings/-features/connection.tsx` „maximális szám”-nak nevezi a mezőt, a kód aktív állapotban mégis max(base,50)-et céloz. A natív globális alap normál sync után200, nem a constructor300. Ez sem „végtelen peer”, sem bizonyított NAS-hiba.

**Biztos minimális csomag:** egyetlen saját `RelayService.apply_torrent_connection_policy(torrent)` legyen a handle és `_last_applied_limit` írója. Új rövid `threading.RLock` a service limitpolicy/handle-alkalmazás köré, mert update_settings sync workerből és prioritáskezelő más workerből is érkezhet. Lock alatt nincs await/DB/network. `priority_manager`, update_settings és add_torrent ezt hívja; más közvetlen set_max_connections ne maradjon. Állapot: base limit és legacy active minimum50; az effektív limit változatlan szabály szerint számolva. A snapshot kiszámítása és handle+tracked update ugyanazon lock alatt történjen, hogy egy régi prioritásfrissítés ne írja felül az új beállítást. Handle-invalid/disappeared eset nem okozhat félrögzített „alkalmazva” értéket.

```text
under policy lock:
  target = max(base,50) if has_active_streams else base
  if valid_handle and last_applied != target:
    native set_max_connections(target)
    last_applied = target       # csak siker után
```

G01: baseline C-n globális50/100/200, base10/20/50/80; stream0/1/4/8, darab256 KiB/1 MiB/4 MiB, container512 MiB/1/2 GiB, lokális seeder. Mérni valódi peerszámot, natív handle limitet, RSS+file-cache/CPU, indulás/seek p95, timeout/megakadás. Először a statefix legacy policyvel, utána tesztcandidate az aktív minimum nélkül. Ha a hard cap célpolicynak megfelel és nincs közös kapun túli streamingromlás, a meglévő torrentConnectionsLimit legyen tényleges cap, az 50-es boost kivezethető. Ha a boost szükséges, a változatlan cap-felirat helyett külön idle/active limit policy kell termékdöntéssel; addig nincs unconditional defaultsűrítés. Konkrét külön active mező csak e kapu sikeres döntése után, minden érintett schemas/internal, schemas/api, relay sync és kliensform változtatásával, régi rekordhoz explicit legacy50-migrációval; nem csak egy backend kulcs hozzáadásával.

Teszt `test_relay_connection_policy.py` FakeHandle+barrier: active/inactive,20→10/80→20, új handle, invalid handle, párhuzamos settings/priority; V=egyetlen konzisztens target a választott policy szerint, natív hiba nem „sikeresen alkalmazott”. Meglévő boundary/piece tesztek maradnak. **Elfogadás:** state és handle nem driftel, policy leírt, funkcionális/regressziós kapu teljesül; gyorsulás nem állított. **Rollback:** statefix önálló, policy/migráció külön csomag; régi JSON mezők megtarthatók, visszavonáskor legacy50 explicit, nem véletlen default.

<!-- doc-anchor:doc-5-adatforgalom-es-meresi-kapus-optimalizalasok -->
<a id="doc-5-adatforgalom-es-meresi-kapus-optimalizalasok"></a>
## 5. Adatforgalom és mérési kapus optimalizálások

<!-- doc-anchor:cr14 -->
<a id="cr14"></a>
### CR14 — Külön torrentlistaprojekció

**Lánc:** `torrents/router.py:get_list:24–32 → TorrentsService.get_torrents:52–71 → TorrentRepository.find:15–16`; `torrents/models.py:resume_bytes:53, torrent_file:69`; `torrent_files/models.py:torrent_bytes:47`; DTO `torrents/schemas/api.py:31–50`. Az általános find() a restore-ban is kell, ezért azt nem szabad globálisan BLOB-mentessé alakítani.

**Fájl/interfész:** új `torrents/schemas/internal.py:TorrentListRecord` frozen adat: torrent_info_hash, file_info_hash, indexer_id,torrent_id,is_persisted,full_download,updated_at,created_at és az IndexerDefinitionResponse hat mezőjének értékei. Új `TorrentRepository.find_list_records()->list[TorrentListRecord]`: explicit oszlopprojekció, inner join torrent_files összetett indexer_id+torrent_id kulcson, indexer_accounts és indexer_definitions relációkon. Nincs teljes ORM-entitás, torrent_bytes vagy resume_bytes. A joined-table inheritance miatt a szükséges saját definition oszlopokra kell hivatkozni; ORM mappinget nem építünk találomra.

`TorrentsService.get_torrents_for_list()` egy Relay státuszlistát kér, dictionarybe rendezi, recordonként illeszt. Fontos: a mostani kód **file_info_hash alapján keres Relayt**, de a válasz TorrentModel.info_hash-t mutat. A terv mindkettőt viszi, és ezt az esetleges inkonzisztenciát nem rejti el új invariánssal. Hiányzó torrent_file eddig kimaradt, az inner join ugyanezt teszi. Új `TorrentResponse.from_list_record(record,relay)` konverter; csak a list router tér át, get_one/update/restore marad a régi úton. Új sorrendet nem vezetünk be mellékesen; a meglévő implicit DB-sorrend nem stabil API-szerződés, ezt a payloadtesztnél kulcs szerinti összevetéssel kezelni kell, a felületi sorrendet külön figyelni.

Teszt `test_torrent_list_projection.py`: E=fájl-DB20/100/500 torrent, kevés/sok indexer, méretes BLOB-ok, részben hiányzó Relay, M=list request, V=régi út JSON-jával azonos tartalom,0 BLOB-érték az eredményobjektumokban,1 célzott lista SELECT, nincs per-torrent lazy query. A response során SQL-t számoló fixture későbbi implicit queryt is észlel; aliasolt hash-mismatch fixture a jelen szemantikát ellenőrzi. Restore/indítás regresszióban a szükséges bytes elérhető. Metrika baseline előbb: SQL/kérés, visszaolvasott oszlopok, poll p95/RSS; a javítás iránya kóddal indokolt, a gyorsulás nem előre számszerű. Közös kapu+A/B/C listaút. **Rollback:** router/service új listametódusa külön revertelhető; séma és általános find nem változik.

<!-- doc-anchor:cr02 -->
<a id="cr02"></a>
### CR02 — WAL mérés és kizárólag indokolt checkpoint

**Forrás:** `common/database.py:59–104` Engine/connect hook/sessionek; `torrent_files/isolated_service.py:22–29,59–105,108–118`; `torrent_files/repository.py:10,106–142` 15 perces touch throttle. Nincs explicit autocheckpoint override, de ebből nem következik kikapcsolt SQLite-autocheckpoint. ORM Session nyitva != bizonyított native olvasósnapshot.

**G02 eljárás:** előbb változatlan C baseline; külön CR17 utáni kontroll, ha ott változott ownership. Fájlalapú DB, 1/4/8 író, normál rövid olvasók, stale/recent touch, szintetikus torrent-BLOB batch. Második szakaszban requesthez hasonló SELECT utáni várakozás, harmadikban explicit BEGIN+SELECT snapshot 5/30/120 s-ig. Az utóbbi stresszkontroll, nem bizonyított mostani viselkedés. Kezdetkor SQLite verzió, page_size,journal_mode,synchronous,wal_autocheckpoint,journal_size_limit; trace DBAPI in_transaction és tényleges BEGIN/COMMIT. 60 perc, WAL-fájlméret1 s-onként, commit p95/p99, lockhibák. Külön futás 10 s-onként diagnosztikai `wal_checkpoint(PASSIVE)`-val: busy/log/checkpointed mezőkkel; ez beavatkozik, ezért monitor nélküli kontroll kötelező. WAL resetnél a backlog különbségét nem szabad naivan negatívként értékelni.

**Döntés és folytatás:**

- Fájl nagy, de újrafelhasználódik és checkpoint előrehalad, nincs SLO/tárhelyprobléma → **nincs alkalmazásváltoztatás**, CR02 lezárható mérési eredménnyel.
- Snapshot megakad és felszabadítás után a következő tényleges checkpointnál kiürül → először a hosszú tranzakció konkrét hívója, szükség szerint CR17. Nem kell garantálni, hogy pusztán az olvasó bezárásától írás nélkül automatikusan csökken a fájl.
- Rövid tranzakciók mellett, azonos terhelésen ismételhető backlog/commitspike vagy jóváhagyott tárhelykeret sérül → csak ekkor candidate PASSIVE karbantartás. Új `common/database_maintenance.py:checkpoint_passive` saját diagnosztikai kapcsolattal workerben; a scheduler/lifespan kezeli, nem request. Az időközt 10/30/60 s jelöltből mérés választja; induló defaultja **disabled**, míg G02 nem teljesül.
- Folyamatosan fogott olvasó mellett checkpoint nem ad szigorú méretplafont; `journal_size_limit` sem ilyen ígéret. TRUNCATE requestútban elvetett; nyugalmi kézi művelet csak külön üzemeltetési terv.

Tesztterv kapu után: E=valódi tmp DB, B=nyitott explicit snapshot+írások, M=checkpoint és reader release, V=busy kontrollált, nincs új lockhiba; felszabadítás után két monitorperióduson belül a következő checkpoint(ok) előrehaladnak/kiürítenek. E=leállítás/DB-hiba, V=worker/scheduler lezár, app kérések működnek. Meglévő `test_torrent_files_touch.py`, `test_cache_and_db_concurrency.py` nem cserélendő WAL-mérettesztre. Metrikák/közös A/B/C a fenti workload szerint; ismert baseline nélkül nincs termelési PRAGMA. **Rollback:** karbantartási task off, meglévő WAL/NORMAL megmarad; checkpoint után adat nem törölhető rollback címén.

<!-- doc-anchor:cr03 -->
<a id="cr03"></a>
### CR03 — GZip: először hálózati és CPU-kísérlet

**Forrás:** `main.py:98–118` CORS/session middleware, nincs GZip; `stremio/router.py:61–73,104–165` stream/catalog/meta JSON; `torrent_source_provider/service.py:90–104` névkeresés40 jelölt; `stream/router.py:118–121` médiához no-transform. A tényleges nagy JSON mérete ismeretlen.

**G03:** ugyanazon Pydantic-modellekből szintetikus0/1/10/40/200 stream/meta, változó valósághű leíráshossz és feliratlista; 200-as katalógus stresszfixture, nem mostani normál út. Identity vs gzip1/4/6 szint, threshold1/2/4/8 KiB candidate; LAN és helyileg kontrollált sávszélesség, 1/4/8 concurrent. Cold/warm külön: az upstream tracker/metadata költséget stubbal állandóvá tenni. Nyers wire bájt+TTFB/teljes p95, CPU/request és peak memory, automatikus kliensdekompressziót elkülönítve. Baseline C és közös A/B/C.

**Döntés:** ha a jóváhagyott linkprofilon a teljes válaszidő/bájtteher haszna nem ismételhető vagy CPU/LAN latency a közös kapun túl romlik, CR03 elvetendő. Ha van a zajon túli haszon és belefér a kijelölt CPU/memória/TTFB-keretbe, a mérés választ threshold/szint párt; nem kerül a tervbe garantált százalék.

**Csak pozitív kapu után:** G0-n ellenőrzött Starlette GZip middleware köré saját szűk útvonaladapter a `main.py` közelében (új `common/stremio_compression.py`), kizárólag Stremio JSON stream/catalog/meta végpontokra. Nem globális app- vagy static/media middleware. Ugyanazon serializer marad a forrás; Pydantic response_mode alias/None szabályt nem másoljuk egy új kézi gzip JSON helperbe. A request Accept-Encoding/q/identity és Vary kezelését az ellenőrzött könyvtár végezze, ne házi parser. Adapter titokértéket nem logol; média, felirat, HEAD/Range/no-transform és már Content-Encoding-os response ne kapjon új tömörítést. Ennek pontos middleware-határa G0 verzióteszttel rögzítendő; ha a könyvtár nem ad helyes route-szűrést, a csomag nem kész, nem kerülőmegoldás a globális bekapcsolás. Tervezett feature flag `STREMHU_STREMIO_GZIP_ENABLED=false`; threshold/szint csak a kiválasztott mérési érték, nem ellenőrizetlen constructorparaméter.

Teszt új `test_stremio_compression.py`, meglévő Stremio/Range/subtitle regressziók: E=ugyanaz a JSON, B=encoding nincs/identity/gzip;q=0/gzip/több encoding, M=GET small/large/error, V=kicsomagolt érték és status/auth változatlan, Vary/Content-Encoding/Content-Length helyes; már tömörített válasz nem dupla. Média206, HEAD és felirat byte/fejléc-identitás kötelező. **Rollback:** flag off, majd adapter revert; proxygzip külön adminisztratív policy, nem vizsgált automatikusan.

<!-- doc-anchor:cr04 -->
<a id="cr04"></a>
### CR04 — Frontend observer/render profil, célzott beavatkozás

**Lánc:** `client/src/main.tsx:45–57` egy QueryClient; `shared/lib/client.ts:3–10` stale5perc/gc10perc; `shared/queries/torrents.ts:14–33` adaptív1,5/5s, backgroundfalse; `relay/torrents/index.tsx:22–24` és `-features/torrents.tsx:14` külön observer ugyanarra a kulcsra; `-components/torrent.tsx:63–77` useMemo csak fullDownload számításra. Structural sharing/deduplikáció pontos runtime-viselkedését tesztelni kell; nem bizonyított dupla request vagy leak.

**G04:** production/profiling build, nem fejlesztői StrictMode-darabszám. Fixture0/20/100/500 torrent, változatlan JSON, egy változó sor, minden változó sor, álló hiányos torrent. 5 perc request count, React commit/render actualDuration és soronkénti render;30perc GC utáni heap +50 navigáció és10perc gcTime kivárás. CR14 előtti/utáni backendköltséget ne keverjük a React-optimalizálással: rögzített API-válaszfixture kell. Közös mérési zajprotokoll, A/B/C kliens csak összevethető buildnél, egyébként C két változata a döntő.

**Elágazás és fájlterv:**

- Ha nincs érdemi render-/requesttöbblet a kívánt listaméreten → CR04 kódváltozás elvetett, profilingeredmény elég.
- Ha a változó statisztika feleslegesen mozgatja a csak countot használó route-ot: `index.tsx` saját teljeslista-observerét eltávolítani; új kis `TorrentCount` komponens `useSuspenseQuery({...getTorrents,select:items=>items.length,refetchInterval:false})`-val. A lista adaptív observerje marad az egyetlen pollproducer. A szám továbbra is ugyanazon cache-ből értesül. A React Query 5.104.2 selector/observer viselkedését G0/mérés ellenőrzi, nem feltételezett re-rendergát.
- Ha stabil objektumú, változatlan sorok is renderelnek és ez dominál: `Torrent` default `React.memo` köré; nincs házi deep comparator, ami régi statisztikát rejthet el. Ha minden sor tényleg változik, memo nem megoldás, nem készítünk placebo PR-t.
- Pollperiódus vagy stalled-incomplete felismerés változása csak külön G04-frissességi összevetéssel; most az1,5/5s és a háttérszabály megőrzendő. AbortSignal-továbbítás nem automatikus része: generált API/axios támogatását ellenőrizni kell; folyó kérés unmount utáni befejeződése nem bizonyít leaket.

Teszt tervezett kliens komponens/query fixture: E=egy QueryClient és virtuális óra, B=stabil/egysoros változó válasz, M=időelőreléptetés, V=friss adat/counter, normál pollszám; count változatlanul nem igényel új rendercommitot a célkomponensen; delete/update invalidáció működik. E=hidden/unmount/remount, V=nincs saját árva timer és heap-retainer lánc a régi listákhoz. A repo React Query API tesztje legyen valódi, ne mindent mockoló rendercounter. Metrikák a kapu szerint; **kész** csak J-n túli céljavulás és változatlan frissesség esetén. **Rollback:** observer/memo önálló revert, API/DB/migráció nincs.

<!-- doc-anchor:cr15 -->
<a id="cr15"></a>
### CR15 — Válaszméret, origin és admission policy G15 után

**Lánc:** `base_indexer_definition.py:47–74,88–95,283–292`; `integrations/ncore.py:185` tracker-download_url; `torrent_source_provider/service.py:178–218,253–276` gather és download singleflight; `indexers/service.py:321–337` keresési timeout. Szemafor és timeout már van; mégsem méret-/globális queue-limit. Külső URL normál kliensből nem tetszőleges: publikus SSRF-ígéret nincs.

**G15 eljárás/baseline:** helyi fixture trackeren reprezentatív érvényes torrentek, nagy darabszámú metadata, HTML-login redirect, CDN-szerű eltérő origin, chunked és tömörített nagy válasz, lassú csepegés, egyedi keresőkulcs-burst. Rögzíteni nyers/dekódolt bytes, .torrent fájlszám/metadata-méret, heapben egyidejű példányok, peak pending task, per-stage latency. C baseline+A/B/C; adapterenként engedélyezendő originminta helyi fixture-rel, élő tracker nélkül. Döntés: mely normál méret és origin szükséges, illetve mekkora összmunka fér a kijelölt RAM/CPU-keretbe. Amíg ez nincs meg, konkrét prodlimit és origin allowlist **nem** található ki. Ha a normál workloadot csak hibásan törné a javasolt limit, jelöltet módosítani vagy részt halasztani.

**Pozitív kapu után, külön kis alcsomagok:**

1. **Csak torrentdownload méretkeret:** új saját `IndexerClient.request_limited(...,max_decoded_bytes)->Response` és `BaseIndexerDefinition.download_torrent` átállítása. G0-n ellenőrzött public HTTPX stream/send felülettel, Content-Length előellenőrzés + tényleges dekódolt chunk számlálás; context finally mindig zár. Privát `_content` mező írása és egy korlátlan aread méretellenőrzés előtt tilos. Teljes, határolt bodyt a meglévő auth-detektor kapja; szükség esetén public Response konstrukció decoded tartalommal és ehhez igazított encoding/length fejlécekkel, history/request megőrzésével. Pontos konstruktor API G0-n. A sima `.stream()` **nem** feltételezhetően hívja az override-olt `.request()`-et: auth/szemafor megkerülése külön regressziós veszély.
2. **Közös auth attempt-szerződés:** a sima és limited út saját `perform_authorized(attempt)` helperen menjen. Attempt alatt semaphore, utána release, auth-error detektálás, legfeljebb1 relogin+retry. Login await alatt nincs semaphore (max_concurrent=1-nél különben deadlock). Cookie/per-origin kezelés a kliensé, nem kézi általános Cookie-header.
3. **Redirect-policy:** limited downloadnál auto-redirect helyett ellenőrzött, legfeljebb10 lépés; minden hop célját és bodykeretét vizsgálni, relatív Location feloldva. Integrációhoz rögzített HTTPS scheme/host/port allowlist; CDN csak G15-ben jóváhagyott. Cookie nem kerülhet idegen originre. Egyszerű előzetes DNS-check nem teljes rebindingvédelem: natív célhálózat-szűrés/transport binding csak külön ellenőrzött tervvel, nincs „teljes SSRF védelem” címke erre.
4. **Munka/batchkeret:** forráskereső unique task indítása előtt processzszintű bounded admission, joined singleflight waiter nem foglal új slotot. Nincs korlátlan várakozó queue; telítettség gyors503. `_sync_torrent_files` ne készítsen minden fájlhoz egyszerre taskot: fix worker/iterátor, bounded batch insert. A választott max_parallel/max_batch_bytes/max_result_bytes G15-ből következik; teljes resultlistában ORM BLOB-ok megőrzését is mérni kell. Ha ez dominál, CR17 search snapshotból a nyers bytes elhagyása előfeltétel, nem elég csak a downloadbatch szűkítése.
5. **Összdeadline:** monoton határ a teljes owned keresési taskra; szakasz remaininget kap. Egy waiter cancelje nem oldhatja fel a még futó közös task lease-ét. Threadmunkához lease csak tényleges befejezéskor szabadul fel; timeout nem jelent megölt threadet. Deadline/overload/invalid input külön kontrollált hibatípus, a meglévő részleges indexerhibák szerződésével összhangban.

Teszt új `test_indexer_bounded_download.py`, `test_search_admission.py`; E=valódi helyi HTTP/fixture transport, B=oversized encoded/decoded/chunked, M=download, V=korlátnál megáll+kapcsolat lezár, nincs fél .torrent DB-insert. E=HTML auth, redirectloop/off-origin, max_concurrent1, V=authretry/cookie működik, nincs bypass/deadlock. E=azonos és eltérő kulcs-burst, waiter cancel/timeout/DB-thread gate, V=cap betartott, same-key dedup, nincs korai lease-release, normál találatszám/sorrend nem csökken némán. Metrika peakmem/tasks/queue és keresési p95; G15 limitjei és közös kapu dönt. **Rollback:** alcsomagonként, sikertelen túl szűk policy módosítható; natív tracker/webseed célkezelés és tetszőleges új transport írása külön kapu nélkül halasztott. Új konfigurációs alapértékek csak G15 jegyzőkönyvvel kerülhetnek kiadásba.

<!-- doc-anchor:doc-6-prioritasi-fuggosegi-es-munkacsomag-tabla -->
<a id="doc-6-prioritasi-fuggosegi-es-munkacsomag-tabla"></a>
## 6. Prioritási, függőségi és munkacsomag-tábla

Az alábbi sorszám munkacsomagsorrend, nem új auditazonosító. A `CRxx/a` egy meglévő javaslat külön ellenőrizhető alcsomagja. A mérés/gate is önálló eredményt ad; negatív kapueredmény után nem készül „csak azért is” implementáció.

| Sorrend / csomag | Prioritás | Függés, belépés | Egyetlen ellenőrizhető eredmény / készültség |
|---|---|---|---|
| 0 — G0 + baseline | kötelező | Külön implementációs engedély; tiszta kiinduló állapot | Verzió/worker/migrációs határ, fixtureazonosítók, zaj- és C baseline rögzítve, semmilyen optimalizáció nincs előrefeltételezve |
| 1 — CR05 | P1 feltételes | G0 config loader teszthatár | Fail-fast kulcspolicy, nincs titok a hibában; biztonságos konfiguráció restartkompatibilis |
| 2 — CR07 | P2 | G0 logszint/handler út | Direkt URL/exception és accesslog policy tesztelt; jelölőtitok nem távozik |
| 3 — CR19 | P2 | G0 middlewarehatár | no-store célzott válaszokon, auth/cache-hit/Range identitás |
| 4 — CR10 | P2 | Izolált parser/ID fixture | Normál/óriás/nem ASCII Range és külső ID helyesen kezelt |
| 5 — CR11 | P2 | Meglévő Singleflight regressziók | Relogin Future helyett megosztott task, cancellation-mátrix kész |
| 6 — CR09 | P2 | Fixture subtitle/stream | Auth előtti írás megszűnt, user_id registry TTL/cap/eventcleanup tesztelt |
| 7 — CR12/a | P2 | G0 single-process; cache unit tesztek | Szálbiztos epoch és compare-put, global reset race kizárva; write-hook még nincs |
| 8 — CR12/b | P2 | CR12/a, outer commit wrapper | Service write-mátrix+rollback+in-flight endpointtesztek, minden szükséges út jelöl |
| 9 — CR08/a | P2 | G0 migrációs head; snapshot backup eljárás | Pairing uniqueness, korlátos retry, egyszeri/idempotens link; rate tuning nélkül is kiadható |
| 10 — G08 + CR08/b | P2 | Normál auth/pairing baseline; peer/proxy trust ismert | Limiter terhelés/kapacitás és jóváhagyott alapértékek; téves normál elutasítás nincs |
| 11 — CR18 | P2 | CR08 limiter vagy egyenértékű izolált védelem; bootstrap fixture | Atomikus foglalás+user commit; pontosan egy sikeres admin, árva marker nincs |
| 12 — CR16/a | P2 | G0 additív user-migráció, CR18 session issue | Session-epoch+jelszórevokáció, régi cookie migráció, saját password utáni UI-viselkedés |
| 13 — G16 + CR16/b | P2 | Valódi cookie és támogatott origin/proxy mátrix | Explicit Secure/Origin policy csak kompatibilitási teszt után; API-key CORS megőrzött |
| 14 — CR14 | P2 | Lista SQL/BLOB baseline | Külön projekciós listaút, azonos payload, BLOB/lazy query nélkül |
| 15 — CR01/a | P2 | FakeHandle concurrency fixture | Egy író effektív limitállapot, legacy boost megőrzött; új limitpolicy még nincs |
| 16 — CR13/a | P2 | G0 async DNS API | Nem blokkoló TXT-wait, deadline/cancel tesztelt |
| 17 — CR13/b | P2 | Resume blobbaseline+kapacitás policy | Bounded koaleszkáló writer, DB-session owner egyértelmű; túlcsordulás látható |
| 18 — CR17/a | P2 | CR11/13 callback- és closeinterfészek | Rendezett close sorrend, egy hibától független többi cleanup, ismételt lifespan |
| 19 — G17 | P2 | Cancellation/DB trace fixture; a változtatás előtti trace is mentett | Ownership/overlap döntés explicit, reprodukció vagy indokolt halasztás |
| 20 — CR17/b | feltételes P2 | Pozitív G17 | SearchPolicySnapshot és filter/sort leválasztás, azonos rangsor |
| 21 — CR17/c | feltételes P2 | CR17/b | Indexer/file rövid UoW-k, DTO-konverterek, ORM/lazy referencia nem jut shared eredménybe |
| 22 — CR17/d | feltételes P2 | CR17/c + CR17/a | Provider owned-task integráció; owner cancel és több consumer helyes |
| 23 — G01 → CR01/b | feltételes P2 | CR01/a; baseline/seedermátrix | Hard cap/boost termékdöntés mérési bizonyítékkal; csak ezután policy/UI/JSON kompatibilitás |
| 24 — G06 → CR06 | feltételes P1 | Kötelező kliens/trustlista és átállási út | Egyedi TLS lifecycle külön csomag; pozitív trustkapu nélkül nincs defaultváltás |
| 25 — G15 → CR15/a | feltételes P2 | Méret/origin fixture adatok, G0 HTTPX API, CR11 | Bounded torrentdownload az auth/szemafor megőrzésével |
| 26 — CR15/b | feltételes P2 | CR15/a; G15 originmátrix | Redirect/origin policy, nincs auth-cookie átszivárgás |
| 27 — CR15/c | feltételes P2 | CR15/a; eredményretenció eldöntve, szükség esetén CR17/d | Bounded admission/batch/deadline, nincs korai lease-release |
| 28 — G02 → CR02 | feltételes P2 | DB baseline; CR17 utáni kontroll, ha releváns | Nincs változtatás vagy indokolt PASSIVE worker, vak TRUNCATE nélkül |
| 29 — G04 → CR04 | feltételes P3 | CR14-től független API fixture | Nincs változtatás, vagy igazolt observer/memo javulás, frissességromlás nélkül |
| 30 — G03 → CR03 | feltételes P3 | CR19, G0 Starlette API, reprezentatív JSON | Nincs változtatás, vagy route-szűkített gzip igazolt nettó haszonnal |
| 31 — G13-convert | feltételes P3 | CR13/a,b után is mért CPU/looplag | ASS→VTT offload csak megmaradó domináns költségnél; külön csomag |

Indok: először kis, egyértelmű biztonsági/helyességi hibák, majd adatbázis- és taskhatárok; végül a mérésfüggő hangolások. A G06/G01/G02/G04/G15 baseline-előkészítése önállóan történhet, de eredményük nem előfeltétele a kis parser/log/cancel javításoknak. Egy csomag nem húzhatja be a teljes táblázatot egy nagy PR-ba. A migrációs változások (pairing, session_epoch) külön-külön tesztelendők, nem egy visszagörgethetetlen „optimalizációs migrációban”.

<!-- doc-anchor:doc-csomagonkenti-keszultseg-altalanos-minimuma -->
<a id="doc-csomagonkenti-keszultseg-altalanos-minimuma"></a>
### Csomagonkénti készültség általános minimuma

Belépés: a táblában szereplő függések, az adott HEAD-hez friss forráshivatkozások, célzott fixture/baseline és visszaállítási út megvan. Kilépés: a modul tesztmátrixa és a 2.2 szerinti ruff/basedpyright/pytest (kliensnél a releváns frontend ellenőrzések is) sikeres; helyi funkcionális regresszió és a változásra releváns A/B/C/C-előtte-utána kapu dokumentált. Negatív gate esetén a kész eredmény a mért elvetés/halasztás; nem hibás teljesítés az, hogy nincs kódváltoztatás.

Nem teljesített gate mellett a csomag ne kapjon „kész” címkét azzal, hogy a hipotézist ténynek írják át. A valódi memóriaszivárgás-jelentéshez GC utáni retainerlánc és ismételhető növekedés, teljesítményállításhoz mentett mérési adatok kellenek.

<!-- doc-anchor:doc-7-nyitott-kerdesek-es-dontesi-pontok -->
<a id="doc-7-nyitott-kerdesek-es-dontesi-pontok"></a>
## 7. Nyitott kérdések és döntési pontok

1. **Milyen worker-/processzszám támogatott?** Az in-process state már jelenleg is több helyen létezik; CR08/12 single-process tervének G0 előfeltétele. Multiworkerre nem szabad ezt globális kontrollnak nevezni.
2. **Mely kliensverzióknak kell elfogadniuk az új TLS-t, milyen trust telepíthető?** CR06 release-blokkoló G06; saját self-signedet nem lehet a régi megosztott domain publikus CA-bizalmával automatikusan egyenértékűvé tenni.
3. **Torrentlimit tényleges felső korlát vagy idle érték?** A jelen UI maximumot mond. CR01/a ezt nem rejti el új architektúrával; CR01/b G01 eredménye és rögzített termékdöntés nélkül nem válthat policyt.
4. **Mely hálózati origin a böngésző számára támogatott, és hol végződik a TLS?** CR16/CR07 middleware/proxykapuk; untrusted forwarded fejlécek nem válaszok erre. Éles beállításokat e tervezés nem olvasott.
5. **Mekkora a normál .torrent/resume/JSON méret és legitim NAT/poll burst?** CR08 rate, CR13 writerkeret és CR15 méret/admission alapérték kiadása előtt fixture/baseline döntés. Az itt megadott kísérleti korlátok új policyjelöltek, nem visszamenőleges tények.
6. **Mi az elfogadható latency/CPU/memória/tárhely-keret?** Ismeretlen szám helyett baseline+zaj, majd előre rögzített UX/SLO; gzip és NAS tuning addig mérés marad.
7. **A konkrét HTTPX/Starlette/dnspython/libtorrent build milyen publikus lifecycle/stream API-t támogat?** G0 ellenőrzés; nem kerülhet a kódba dokumentálatlan privát attribútum vagy találomra választott natív setting. A natív libtorrent-session explicit felszabadításának receptje e tervben tudatosan API-kapu mögött marad.
8. **Mi a tényleges Alembic head és verziókönyvtár?** `boot/setup.py:21–23` az ini alapján futtatja; a migrációforrás ebben a szűk vizsgálatban nem volt olvasva. Implementációkor az engedélyezett scope-ban felderítendő; több head esetén nem szabad önkényesen revíziószámot választani.
9. **Mi a jelszóváltozás utáni felületi szerződés?** A választott terv minden korábbi sessiont, a callerét is lezárja, a UI loginra lép. Ha a termék saját session újrakiadását kívánja, az külön commit-utáni issuance-terv és teszt, nem implicit mellékhatás.
10. **Vannak-e a közös Session-wrappereket megkerülő későbbi explicit commitutak?** CR12 write-leltár és CR17 trace ezt ellenőrzi; a cachehookot nem szabad csak a most ismert route-ok egy részén bekötni.

A fenti kérdések nem azt jelentik, hogy az implementálható kis csomagokhoz új architektúrát kell kitalálni: mindenhez megadott a választott határ. A hozzájuk tartozó kaput viszont nem lehet bizonyíték nélkül átugrani. CVE/image-scan, at-rest titokkezelés, konténercapability és teljes natív könyvtárbiztonság nem vált automatikusan implementációs feladattá az audit nyitott kockázati táblájából; ezek külön scope és külső/telepítési bizonyíték nélkül halasztottak.

<!-- doc-anchor:doc-8-vegrehajtasi-ellenorzolista -->
<a id="doc-8-vegrehajtasi-ellenorzolista"></a>
## 8. Végrehajtási ellenőrzőlista

<!-- doc-anchor:doc-a-terv-atadasa-ennek-a-feladatnak-a-vege -->
<a id="doc-a-terv-atadasa-ennek-a-feladatnak-a-vege"></a>
### A terv átadása — ennek a feladatnak a vége

- [x] Audit bemenete és hash-e azonosítva; ág/HEAD egyezik.
- [x] Alkalmazandó AGENTS elolvasva; repó docs/.env olvasása nélkül.
- [x] Mind a 19 CR besorolva, alaptalan kiterjesztések elvetve/kapu mögött.
- [x] Jelenlegi hívási láncok, módosítandó fájlok, új saját interfészek és megőrzendő invariánsok rögzítve.
- [x] Teszt-, mérési-, hibakezelési-, migrációs és rollbacktervek; kis csomagok belépési/kilépési feltételekkel.
- [x] Nem futott dinamikus teszt/benchmark/tracker vagy szolgáltatás; nem indult implementáció.
- [x] Kizárólag `D:\Git\docs\optimization-implementation-plan-cloud.md` a létrehozott dokumentum.

<!-- doc-anchor:doc-csak-kesobbi-kulon-engedelyezett-vegrehajtaskor -->
<a id="doc-csak-kesobbi-kulon-engedelyezett-vegrehajtaskor"></a>
### Csak későbbi, külön engedélyezett végrehajtáskor

- [ ] G0 és célcsomag baseline/fixture elkészült, verziófüggő API ellenőrizve.
- [ ] Érintett munkacsomag fejlesztése önállóan; nincs szomszédos „opportunista” átírás.
- [ ] Viselkedési tesztek a modul E/B/M/V mátrixa szerint, valódi DB-konkurencia ahol szükséges.
- [ ] Ruff → basedpyright → teljes pytest a server/.venv-vel, kötelező helyi nem loopback HOST_IP; frontend releváns ellenőrzések.
- [ ] Csak ezután helyi Docker funkcionális teszt, eldobható szintetikus adatokkal.
- [ ] Releváns A/B/C és C-előtte-utána, azonos környezet/cold-warm/ismétlés/zaj; adatokat és negatív eredményt is megőrizni.
- [ ] Mérési kapu döntése dokumentált; hipotézishez nincs unconditional implementáció.
- [ ] Migráció fresh és meglévő szintetikus DB-n, failed transaction/rollback/újraindítás tesztelve.
- [ ] Titok- és privátcím-mentes log/kimenet; segédfájlok commitvédelme ellenőrizve.
- [ ] Csomag elfogadási feltétele és rollbackút teljesült; későbbi commit/push előtt AGENTS branchdokumentációs kötelezettség az akkori engedélyezett scope szerint.

**Leállási pont:** a terv elkészültével megállni. A dokumentum létrehozása nem engedély implementációra, tesztfuttatásra, buildre, migrációra vagy szolgáltatásindításra.
