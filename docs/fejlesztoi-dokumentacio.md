---
doc_id: "fejlesztoi-dokumentacio"
title: "Fejlesztői belépési pont"
kind: "developer-guide"
status: "source-paths-reviewed"
audience: ["developer", "ai-agent"]
tags: ["development", "windows", "python", "node", "testing"]
source_commit: "d9554c4324b432dd023307c9bf29e0aab4da3747"
baseline: null
verification: "source-paths-and-package-scripts; no-runtime-tests"
structure_reviewed: "2026-11-03"
related_docs: ["docs/README.md", "docs/AI-INDEX.md"]
source_paths: ["server/app/config.py", "server/app/run.py", "server/requirements.txt", "server/pyproject.toml", "client/package.json", "Dockerfile"]
---

# Fejlesztői belépési pont

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](README.md) · [AI-index](AI-INDEX.md)

> **Státusz:** Forrásutak és csomagscriptek ellenőrizve; ebben a dokumentációs körben parancs, teszt és szolgáltatás nem futott.

**Kapcsolódó:** [README.md](README.md) · [AI-INDEX.md](AI-INDEX.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [Előfeltételek és olvasási sorrend](#doc-elofeltetelek-es-olvasasi-sorrend)
- [Környezet és függőségek](#doc-kornyezet-es-fuggosegek)
- [Ellenőrzési sorrend](#doc-ellenorzesi-sorrend)
- [Docker, integráció és teljesítmény](#doc-docker-integracio-es-teljesitmeny)
- [Átadás](#doc-atadas)

</details>

<!-- doc-nav:end -->

<!-- doc-anchor:doc-elofeltetelek-es-olvasasi-sorrend -->
<a id="doc-elofeltetelek-es-olvasasi-sorrend"></a>
## Előfeltételek és olvasási sorrend

1. [AGENTS.md](../AGENTS.md): engedélyezett hatókör, adatvédelem és feladattípushoz kötött ellenőrzések.
2. [AI-index](AI-INDEX.md): az érintett funkció és forrásmodul kiválasztása.
3. Csak a feladathoz tartozó feature-referencia, aktuális forrás és tesztek. Audit/terv esetén a vizsgált commitot hasonlítsd össze az aktuálissal.

Ez a leírás a helyi fejlesztői belépéshez készült. A [Linux/DNS/TLS üzemeltetési útmutató](STREMHU-UNIVERSAL-SETUP-GUIDE.md) más célra szolgál; annak szolgáltatásindító parancsai nem részei egy dokumentációs vagy auditfeladatnak.

<!-- doc-anchor:doc-kornyezet-es-fuggosegek -->
<a id="doc-kornyezet-es-fuggosegek"></a>
## Környezet és függőségek

| Komponens | Ellenőrzött forrás | Jelenlegi előírás |
|---|---|---|
| Kliens Node | [node-verzió](../.node-version), [package.json](../client/package.json), [Dockerfile](../Dockerfile) | Node 24 |
| Backend runtime | [Dockerfile](../Dockerfile), [environment.yaml](../server/environment.yaml) | Python 3.12 |
| Backend csomagok | [requirements.txt](../server/requirements.txt) | Az itt megadott verziók; tranzitív csomagok pontos verzióját nem szabad kitalálni |
| Python ellenőrzések | [pyproject.toml](../server/pyproject.toml) | Ruff, basedpyright, pytest |
| Szerverindító | [run.py](../server/app/run.py) | Hypercorn |

A meglévő Windows tesztkörnyezet `server/.venv`. Ne hozz létre automatikusan másik interpreterkörnyezetet, ha a feladat csak kódolvasás vagy dokumentáció. A Docker-build saját `/opt/venv` környezetet használ; ez nem a Windows `.venv` útvonala.

<!-- doc-anchor:doc-opcionalis-kornyezetkezelok -->
<a id="doc-opcionalis-kornyezetkezelok"></a>
### Opcionális környezetkezelők

- `fnm`: `fnm install`, majd `fnm use` a repó gyökerében, a `.node-version` alapján. Nem kötelező új eszköz telepítése, ha már van megfelelő Node.
- Conda: a leíró `server/environment.yaml`; a parancsokat ebből a könyvtárból futtasd, például `conda env create -p ./.conda -f environment.yaml`. Ez alternatív környezet, nem az AGENTS szerinti `.venv` automatikus helyettesítője. Létrehozás/frissítés csak környezetbeállítási feladatban.
- Függőségfrissítés vagy lock-újragenerálás nem mellékes lintjavítás; külön indokolni és ellenőrizni kell.

<!-- doc-anchor:doc-ellenorzesi-sorrend -->
<a id="doc-ellenorzesi-sorrend"></a>
## Ellenőrzési sorrend

A pontos, hibánál megálló backendparancssor az [AGENTS ellenőrzési fejezetében](../AGENTS.md#4-ellenőrzések-a-feladat-típusához-igazítva) található. A `HOST_IP` legyen előre beállított helyi, nem loopback tesztcím; konkrét cím vagy kulcs ne kerüljön a megosztható parancsba.

- Backend-munkacsomag: célzott viselkedési teszt → Ruff → basedpyright → teljes pytest a `server/.venv`-ből.
- Frontend-munkacsomag: releváns tesztek és a `client/` tényleges `npm run lint`, `npm run format`, `npm run build` scriptjei; kilépési kód külön ellenőrzendő. `npm test` scriptet ne feltételezz.
- Dokumentáció/AGENTS: statikus link-, anchor-, fence-, státusz- és hatókör-ellenőrzés. Nem szükséges automatikus alkalmazásteszt vagy Docker-indítás.

A [Config](../server/app/config.py) importkori dotenv-betöltést is tartalmaz. Ne feltételezd, hogy egy appimport vagy teszt automatikusan titokmentes/offline. Az engedélyezett tesztprofilt és a hálózati fixture-öket a futtatás előtt ellenőrizni kell; a tervben javasolt jövőbeli config-loader még nem jelenlegi API.

<!-- doc-anchor:doc-docker-integracio-es-teljesitmeny -->
<a id="doc-docker-integracio-es-teljesitmeny"></a>
## Docker, integráció és teljesítmény

Az [AGENTS Docker- és benchmarkfejezete](../AGENTS.md#5-helyi-docker-és-biztonságos-készültségvizsgálat) a kanonikus helyi munkafolyamat. Alapértelmezett a helyi szintetikus tesztadat. A valós trackerre konfigurált bootstrap/benchmark nem indítható pusztán azért, mert egy dokumentumban példaként szerepel.

Teljesítményhez A/B/C mellett C előtte–utána kontroll kell, ugyanazzal a workload-dal és zajbecsléssel. Korábbi feature-dokumentum száma nem helyettesíti az aktuális baseline-t.

<!-- doc-anchor:doc-atadas -->
<a id="doc-atadas"></a>
## Átadás

Jelöld a vizsgált commitot, a megváltoztatott területet, a tényleges ellenőrzést és az el nem végzett lépéseket. Funkcionális változáshoz a [feature-katalógus](feature/README.md) megfelelő referenciáját frissítsd; új dokumentumhoz [sablon](templates/feature.md) áll rendelkezésre.
