---
doc_id: "templates-feature"
title: "Feature-dokumentum sablon"
kind: "template"
status: "template"
audience: ["developer", "ai-agent"]
tags: ["template", "feature", "evidence", "documentation"]
source_commit: null
baseline: null
verification: "structure-only"
structure_reviewed: "2026-11-03"
related_docs: ["docs/README.md", "docs/feature/README.md"]
source_paths: []
---

# Feature-dokumentum sablon

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../README.md) · [AI-index](../AI-INDEX.md)

> **Státusz:** Kitölthető sablon, nem megvalósított funkció vagy lefutott ellenőrzés.

**Kapcsolódó:** [README.md](../README.md) · [README.md](../feature/README.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [Dokumentumfejléc](#doc-dokumentumfejlec)
- [1. Cél, hatókör, nem célok](#doc-1-cel-hatokor-nem-celok)
- [2. Jelenlegi működés és bizonyíték](#doc-2-jelenlegi-mukodes-es-bizonyitek)
- [3. Változtatás és invariánsok](#doc-3-valtoztatas-es-invariansok)
- [4. Erőforrások, hibautak, kompatibilitás](#doc-4-eroforrasok-hibautak-kompatibilitas)
- [5. Ellenőrzés és mérési kapuk](#doc-5-ellenorzes-es-meresi-kapuk)
- [6. Kockázat, visszaállítás, nyitott kérdések](#doc-6-kockazat-visszaallitas-nyitott-kerdesek)
- [7. Kapcsolódó leírások](#doc-7-kapcsolodo-leirasok)

</details>

<!-- doc-nav:end -->

Ez kitölthető szerkezet, nem megvalósított funkció. Másold a megfelelő `docs/feature/<feature>.md` helyre, és csak a ténylegesen releváns részeket töltsd ki. A helyőrző nem tesztbizonyíték.

<!-- doc-anchor:doc-dokumentumfejlec -->
<a id="doc-dokumentumfejlec"></a>
## Dokumentumfejléc

A fájl eleji YAML-metaadatban használd a következő mezőket: `doc_id`, `title`, `kind`, `status`, `audience`, `tags`, `source_commit`, `baseline`, `verification`, `structure_reviewed`, `related_docs`, `source_paths`. A `source_commit` lehet `null`, ha nincs igazolt commit; ne írd rá automatikusan az aktuális HEAD-et egy régi mérésre.

Javasolt kind: `feature-reference`, `audit`, `implementation-plan`, `historical-report`, `operator-guide`, `developer-guide`. A státusz mondja meg, hogy történeti referencia, terv vagy forrásból ellenőrzött leírás; az implementáció állapotát külön bizonyítsd.

<!-- doc-anchor:doc-1-cel-hatokor-nem-celok -->
<a id="doc-1-cel-hatokor-nem-celok"></a>
## 1. Cél, hatókör, nem célok

- Milyen használati esetet/problémát érint?
- Mely branch/commit és mely modulok a hatókör?
- Mi marad változatlan, és mi nem része a munkának?

<!-- doc-anchor:doc-2-jelenlegi-mukodes-es-bizonyitek -->
<a id="doc-2-jelenlegi-mukodes-es-bizonyitek"></a>
## 2. Jelenlegi működés és bizonyíték

- Hívási lánc: belépési pont → service → erőforrás → lezárás.
- Fájl + szimbólum + commit; sor csak ehhez a commitállapothoz.
- Megállapításonként: kóddal igazolt tény / mérésre váró hipotézis / ismeretlen.

<!-- doc-anchor:doc-3-valtoztatas-es-invariansok -->
<a id="doc-3-valtoztatas-es-invariansok"></a>
## 3. Változtatás és invariánsok

| Fájl / szimbólum | Változás | Megőrzendő szerződés |
|---|---|---|
| `<repo-relative-path>` | `<konkrét feladat>` | `<auth/séma/élettartam/kompatibilitás>` |

Funkcióeredet baseline-ját, PR-célágat és teljesítménybaseline-t külön add meg. Komplex esetben releváns Mermaid komponens-/szekvencia-/döntési ábra; egyszerű módosításhoz nem kell mindhárom.

<!-- doc-anchor:doc-4-eroforrasok-hibautak-kompatibilitas -->
<a id="doc-4-eroforrasok-hibautak-kompatibilitas"></a>
## 4. Erőforrások, hibautak, kompatibilitás

Csak ahol releváns: DB-session/tranzakció, szál/async ownership, cancellation, timeout, queue/cache-keret, init/close, migráció, régi kliens és konfiguráció.

<!-- doc-anchor:doc-5-ellenorzes-es-meresi-kapuk -->
<a id="doc-5-ellenorzes-es-meresi-kapuk"></a>
## 5. Ellenőrzés és mérési kapuk

| Előfeltétel | Bemenet | Művelet | Várt megfigyelhető eredmény |
|---|---|---|---|
| `<fixture>` | `<adat>` | `<használati eset>` | `<viselkedési elfogadás>` |

Tervben jövőbeli ellenőrzés szerepeljen. Eredményben commit, környezet, dátum, parancs/workload, tényleges kimenetel és korlát. Ismeretlen baseline-nál előbb mérés, utána döntés és feltételes következő lépés.

<!-- doc-anchor:doc-6-kockazat-visszaallitas-nyitott-kerdesek -->
<a id="doc-6-kockazat-visszaallitas-nyitott-kerdesek"></a>
## 6. Kockázat, visszaállítás, nyitott kérdések

Kis munkacsomagok, belépési/készültségi feltételek, szükséges migráció/flag és rollback. Nem eldöntött kérdést ne rejts feltételezett API vagy kitalált mérési szám mögé.

<!-- doc-anchor:doc-7-kapcsolodo-leirasok -->
<a id="doc-7-kapcsolodo-leirasok"></a>
## 7. Kapcsolódó leírások

Kanonikus dokumentumokra és forrásokra relatív link. Új dokumentum/címsor/státusz után a README/AI-index/index.json megfelelő része is frissüljön. A projekt ellenőrzési parancsait az AGENTS-ből hivatkozd, ne több eltérő másolatban tartsd fenn.
