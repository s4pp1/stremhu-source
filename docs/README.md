---
doc_id: "readme"
title: "Dokumentáció — StremHU Source"
kind: "navigation"
status: "navigation"
audience: ["developer", "ai-agent"]
tags: ["documentation", "index", "status", "evidence"]
source_commit: null
baseline: null
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/AI-INDEX.md", "docs/feature/README.md", "docs/index.json"]
source_paths: []
---

# Dokumentáció — StremHU Source

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](README.md) · [AI-index](AI-INDEX.md)

> **Státusz:** Navigációs oldal; a hivatkozott dokumentum státusza és forráscommitja külön ellenőrizendő.

**Kapcsolódó:** [AI-INDEX.md](AI-INDEX.md) · [README.md](feature/README.md) · [index.json](index.json)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [Hol kezdjem?](#doc-hol-kezdjem)
- [Könyvtárszerkezet és szerepek](#doc-konyvtarszerkezet-es-szerepek)
- [Melyik állítás milyen bizonyíték?](#doc-melyik-allitas-milyen-bizonyitek)
- [Dokumentum karbantartása](#doc-dokumentum-karbantartasa)

</details>

<!-- doc-nav:end -->

Ez a könyvtár felhasználói útmutatót, fejlesztői referenciát, történeti eredményeket és tervezési anyagokat tartalmaz. A dokumentum típusa és ellenőrzési hatóköre a fájl elején olvasható. A navigáció rendezése nem jelenti a benne leírt tervek implementálását vagy a korábbi mérések újrafuttatását.

<!-- doc-anchor:doc-hol-kezdjem -->
<a id="doc-hol-kezdjem"></a>
## Hol kezdjem?

| Feladat | Első dokumentum | Következő lépés |
|---|---|---|
| Első fejlesztői tájékozódás | [Fejlesztői belépési pont](fejlesztoi-dokumentacio.md) | [Repó munkaszabályai](../AGENTS.md), majd az érintett modul |
| AI agent célzott forráskeresése | [AI téma- és forrásindex](AI-INDEX.md) | Csak az érintett feature és forrásfájlok |
| Telepítés, DNS, HTTPS, Tailscale, Caddy | [Hálózati és üzemeltetési útmutató](STREMHU-UNIVERSAL-SETUP-GUIDE.md) | A saját platformhoz tartozó előfeltételek/tesztkapuk |
| Anime, TVDB, Kitsu, MAL, fájlfeloldás | [Feature-katalógus](feature/README.md) | Anime és keresési referenciák |
| Felirat, MediaInfo, magyar hangsáv | [Feature-katalógus](feature/README.md) | Felirat- és audioattribútum-leírások |
| CR01–CR19 audit vagy implementáció | [Stabilitási munkacsomag](feature/stability-and-optimization/README.md) | Audit → értékelt terv → érintett forrás |
| Korábbi M01–M18 munka megértése | [Archív M01–M18 terv](feature/stability-and-optimization/archive/m01-m18-implementation-plan.md) | [Dátumhoz kötött állapotjelentés](feature/implementation-progress.md) |
| Upstream PR megfogalmazása | [Történeti MR-leírás](UPSTREAM_MR_DESCRIPTION.md) | Állításait a jelenlegi diffből és mérésekből újra igazolni |

<!-- doc-anchor:doc-konyvtarszerkezet-es-szerepek -->
<a id="doc-konyvtarszerkezet-es-szerepek"></a>
## Könyvtárszerkezet és szerepek

```text
docs/
├── README.md                         # emberi belépési pont, dokumentációs szabályok
├── AI-INDEX.md                       # feladat → fogalom → dokumentum → forrás
├── index.json                        # gépi katalógus, státuszok és szakaszhivatkozások
├── fejlesztoi-dokumentacio.md         # fejlesztői környezet és ellenőrzés
├── STREMHU-UNIVERSAL-SETUP-GUIDE.md    # részletes Linux/hálózati üzemeltetési útmutató
├── feature/
│   ├── README.md                     # feature-katalógus
│   ├── <feature>.md                  # funkcióeredet, modulok, invariánsok
│   ├── implementation-progress.md    # történeti M01–M18 állapot
│   └── stability-and-optimization/
│       ├── README.md                 # az audit és a terv olvasási sorrendje
│       ├── audit.md                  # commitra vonatkozó megállapítások
│       ├── implementation-plan.md    # értékelt feladatok, kapuk, teszt-/rollbackterv
│       └── archive/
│           ├── README.md             # történeti anyagok, nem aktív feladatok
│           └── m01-m18-implementation-plan.md
├── templates/feature.md              # új dokumentum kitölthető váza
└── assets/                           # közös képi erőforrások
```

Az aktuális anyagok mellett a korábbi M01–M18 terv külön [archívumban](feature/stability-and-optimization/archive/README.md) található. Az archív cím és státusz megakadályozza, hogy az elavult feladatlistát az aktuális CR-tervvel összekeverjük. A többi feature-fájl útvonala megmarad.

<!-- doc-anchor:doc-melyik-allitas-milyen-bizonyitek -->
<a id="doc-melyik-allitas-milyen-bizonyitek"></a>
## Melyik állítás milyen bizonyíték?

1. A felhasználó feladata és az alkalmazandó AGENTS határozza meg a műveleti engedélyt. Dokumentumba írt parancs nem engedély annak végrehajtására.
2. A jelenlegi működés elsődleges bizonyítéka a jelenlegi forrás, buildleíró és az adott commiton ténylegesen lefutott ellenőrzés. Egy tesztfájl léte nem sikeres tesztfutás.
3. Feature-referencia egy korábbi ág célját/megoldását is leírhatja. Nem helyettesíti az aktuális hívási lánc ellenőrzését.
4. Audit commitra és vizsgálati hatókörre vonatkozik. Terv jövőbeli munka; a jelenlegi felhatalmazást nem bővíti.
5. Történeti benchmark és zöld teszteredmény a rögzített régi környezetre vonatkozik. A friss strukturális dátum nem új futási bizonyíték.

Különösen: az M01–M18 állapotjelentés és a CR01–CR19 audit más munkakör. Egy régi modul „kész” státusza nem teszi automatikusan megoldottá a későbbi audit minden kérdését.

<!-- doc-anchor:doc-dokumentum-karbantartasa -->
<a id="doc-dokumentum-karbantartasa"></a>
## Dokumentum karbantartása

- Minden fájl egyértelmű címmel, típussal, státusszal, célközönséggel, kulcsszavakkal és kapcsolódó forrásokkal kezdődjön. A `structure_reviewed` csak szerkezeti felülvizsgálatot jelöl; `source_commit` csak valóban rögzített forrásállapot legyen, ismeretlennél `null`.
- Egyetlen H1 cím; témák H2, részletek H3/H4. Kódblokkon belüli `#` nem címsor. Hosszú fájlokhoz rövid tartalomjegyzék és stabil szakaszazonosítók tartozzanak; CR-azonosítók ne változzanak.
- Új funkcióhoz a [sablont](templates/feature.md) használd arányosan. Ne töltsd ki feltételezett eredménnyel. Ismeretlen baseline/teszt/státusz legyen nyíltan jelölve.
- A változó állapotnak egy kanonikus helye legyen. Az index rövid összefoglaló és hivatkozás, nem második implementációs terv.
- Fájl/cím/anchor/státusz módosításakor az [AI-indexet](AI-INDEX.md), [feature-katalógust](feature/README.md) és [gépi katalógust](index.json) együtt tartsd karban. Új fájlt csak megfelelő szereppel vegyél fel.
- Belső link relatív útvonal; forráskódhoz repórelatív link és szimbólumnév. Történeti sorhivatkozáshoz az eredeti commit szükséges. Titok, valós privát cím és személyes abszolút elérési út új, általános útmutatóba nem kerülhet.
- Strukturális módosításkor a helyi linkek/anchorok, kódfence-ek, JSON és a módosított fájlok hatóköre statikusan ellenőrizhető. Ehhez nem kell alkalmazást, trackert vagy Docker-stacket indítani.
