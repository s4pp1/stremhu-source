---
doc_id: "feature-stream-performance-readme"
title: "Streamgyorsítás — munkacsomag"
kind: "navigation"
status: "navigation"
audience: ["developer", "ai-agent"]
tags: ["SP01-SP09", "performance", "implementation-plan", "evidence"]
source_commit: "0515d989c764bb4103d6f7286d703b98ec859ce6"
baseline: null
verification: "structure-only"
structure_reviewed: "2026-11-11"
related_docs: ["docs/feature/stream-performance/implementation-plan.md", "docs/feature/stream-performance.md"]
source_paths: []
---

# Streamgyorsítás — munkacsomag

<!-- doc-nav:start -->
**Navigáció:** [Dokumentáció](../../README.md) · [AI-index](../../AI-INDEX.md)

> **Státusz:** A terv végrehajtva, minden csomag lezárva (2026-11-11). Az eredmény a [végrehajtási állapotban](../stream-performance.md#execution-status) olvasható.

**Kapcsolódó:** [implementation-plan.md](implementation-plan.md) · [stream-performance.md](../stream-performance.md)

<details>
<summary>Fejezetek / közvetlen ugrás</summary>

- [Olvasási sorrend és állapot](#doc-olvasasi-sorrend-es-allapot)
- [A terv szerepe](#doc-a-terv-szerepe)

</details>

<!-- doc-nav:end -->

<!-- doc-anchor:doc-olvasasi-sorrend-es-allapot -->
<a id="doc-olvasasi-sorrend-es-allapot"></a>
## Olvasási sorrend és állapot

1. [Branch-összefoglaló](../stream-performance.md): cél, tervezett upstream-diffmátrix, érintett modulok, invariánsok és a végrehajtási állapot.
2. [Implementációs terv](implementation-plan.md):
   - a kilenc tétel (SP01–SP09) forrásból igazolt ténnyel és hipotézissel;
   - mérőeszközök (H1–H3), mérési kapuk és munkacsomag-sorrend;
   - nyitott döntések.
3. `evidence/`: a regisztrált protokollok és mérési eredmények (protokoll, terv, döntés, értékelés, összesítés, minden futás).

**Státusz:** a terv a `main` `0515d989c764bb4103d6f7286d703b98ec859ce6` forrásán készült; végrehajtva, az eredmény a [végrehajtási állapotban](../stream-performance.md#execution-status).

<!-- doc-anchor:doc-a-terv-szerepe -->
<a id="doc-a-terv-szerepe"></a>
## A terv szerepe

A terv a stabilitási ág [implementációs tervének](../stability-and-optimization/implementation-plan.md) szerkezetét követi. A tételek nem feltétel nélkül implementálandó hibák.
- **Kis csomag:** a helyességi és kockázatmentes tételek (SP03, SP05/a, SP06/a) kis csomagként mehetnek.
- **Kapus tételek:** a policyváltozások csak a saját mérési kapujuk PASS-a után kerülnek be.
- **Negatív kapu:** az eredmény a dokumentált elvetés.
