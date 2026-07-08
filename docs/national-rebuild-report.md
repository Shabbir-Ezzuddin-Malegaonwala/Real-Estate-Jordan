# National Data Rebuild — Build Report

**Branch:** `feature/national-data-rebuild` · **Date:** 2026-07-08
**Goal:** Re-fuel the proven reference engine with the full Project-on-Jordan dataset (6 portals, nationwide) — executing Phase 0 (data foundation) + Phase 1 (CMA on the new data) + the highest-value fix (DOS cost floor) from the implementation plan.

---

## 1. What was built

| Asset | File | What it does |
|---|---|---|
| Portal → canonical ingester | `scrapers/ingest_national.py` | Maps all 6 raw portal CSVs onto the frozen `listings` schema, with provenance, rent-periodicity normalization, and neighborhood canonicalization |
| Neighborhood canonicalizer | `scrapers/neighborhoods.py` | Merges spelling/script variants (Abdun/Abdoun, خلدا/Khalda) into one canonical name so comps pool correctly |
| DOS cost parser | `scrapers/dos_costs.py` | Parses the 220 DOS HTML-tables → national construction cost/m² → `cost_benchmarks` + a 21-year `macro_series` |
| National precompute | `scrapers/emit_national.py` | Writes `app/web/public/engine_output.json` for the frontend (offline mode), nationwide set |
| National database | `db/jordan_national.sqlite` | 56,854 listings + cost benchmarks + cost series, built with the **existing** schema + loader |

**The engine, API, DB schema, and loaders were NOT modified** — the reference architecture was reused as-is and simply pointed at the new data. This validates the core thesis: *data-infrastructure gap, not a methodology gap.*

## 2. The data foundation (Phase 0)

**56,854 listings** loaded, **0 rejected** by the strict schema/provenance validator.

| Portal | Rows | | Type | Rows | | Governorate | Rows |
|---|--:|---|---|--:|---|---|--:|
| Bayut | 23,520 | | sale | 40,874 | | Amman | 41,343 |
| OpenSooq | 20,797 | | rent | 15,976 | | Irbid | 1,969 |
| EurekaJo | 6,938 | | | | | Zarqa | 1,919 |
| Homes-Jordan | 3,864 | | apartment | 26,898 | | Jerash | 769 |
| 4321Property | 1,235 | | land | 17,564 | | Salt | 1,318 |
| AbuJudom | 500 | | villa | 7,364 | | Mafraq | 502 |
| | | | commercial | 4,733 | | Aqaba | 435 |

- **25,378 usable sale comps** (price + area); **951 distinct neighborhoods**; **714 exposed via the API** (have sale comps).
- **Scope: nationwide** — all 12 governorates present (vs the reference app's 854 Amman-only listings — a **66× increase**).
- Neighborhood canonicalization merged 23+ variant clusters for the premium Amman submarkets (e.g. Abdoun 423+263→686; Dair Ghbar 514+238→752; Khalda incl. Arabic خلدا→1,169).

## 3. The cost-floor fix (highest-value item)

The reference app's `cost_benchmarks` table was **empty**, so Minimum-Safe rested on the confidence band alone. Now:
- `dos_costs.py` parses the DOS building-licence tables (authority-nested HTML) → national new-build construction cost/m² = *estimated cost ÷ area*.
- Result: **~155 JD/m²** (stable 2019–2024), loaded as a `standard` benchmark (153.5–156.4, 2024) + a 21-year trend series.
- The cost floor now **fires** in every recommendation as a real, sourced evidence row. (It is construction-only and conservative — DOS declares a licence valuation, excl. land — so it correctly does *not* bind premium-Amman prices where land dominates, but it protects against below-rebuild pricing anywhere.)

## 4. Bug found & fixed by testing

**Rent periodicity.** Bayut quotes rent **yearly** (median 72 JD/m²/yr), OpenSooq **monthly** (7.5 JD/m²/mo). The engine annualizes ×12, so Bayut rents were 12× inflated → an **81.8% "yield"** and a garbage income ceiling. Fixed in ingestion (`normalize_rent_monthly`): any rent > 25 JD/m²/mo is an annual quote → ÷12. After the fix, yields are sane (Abdoun ~7%) and the premium band is driven by comp dispersion, not the broken ceiling.

## 5. Test results

| Test | Result |
|---|---|
| Engine unit suite (`app.engine.test_pipeline`) | **21/21 pass** (engine unchanged) |
| Broad sweep — 39 neighborhoods with ≥40 comps | **0 anomalies** (all bands ordered, all in 100–3000 JD/m²) |
| API end-to-end (`uvicorn` on national DB) | `/health` 56,854 listings, **714 neighborhoods**; `/recommend` OK; unknown place → 422 |
| Price plausibility | Amman apt median 733 JD/m²; Abdoun rec ~870–935 (ref app: 1,051); Shmeisani 556 (**matches ref app exactly**) |
| Confidence scaling | Amman = M, dense Al Jubaiha = **H**, secondary cities (Irbid/Zarqa/Aqaba) = **L** — honest, automatic |

**Sample national ladder** (apartment, high finish): Dabouq 1188 · Abdoun 935 · Umm Uthaina 819 · Sweifieh 691 · Dair Ghbar 783 · Khalda 616 · Shmeisani 655 · Aqaba 423 · Irbid 319 · Zarqa 303.

Every recommendation carries market-derived evidence objects (OLS slopes / paired-median premiums with sample sizes — **no hardcoded weights**), a firing cost floor, an income ceiling, and Abdoun/Dabouq/etc. comps that are correctly neighborhood-specific.

## 6. What's done vs deferred

**Done (Phase 0 + Phase 1 + cost floor):** national canonical DB, dedupe, neighborhood canonicalization, rent normalization, DOS cost floor, engine producing sensible nationwide recommendations, API serving them, precomputed frontend output.

**Deferred (later phases, as planned):**
- **Phase 2 features** — terrain-view (DEM), affluence (VIIRS), density (GHS-POP), POI-proximity: not yet wired (grids loaded elsewhere; joining to listings is next).
- **Frontend map GeoJSON** — still the 5-Amman layers; national POIs/boundaries not regenerated (pricing panel is national via `engine_output.json`, the map layers are not).
- **DLS price index** — held copy ends 2018-Q4; time-adjustment self-disables as stale until re-pulled.
- **Free-text mining** — finish/view from descriptions (the described Phase-0 unlock) not yet applied; most `finish_quality` remains `unknown`.
- **Long-tail cleanup** — city-name variants (Al Salt / Salt) and unmapped Arabic neighborhoods still fragment the long tail (premium Amman submarkets are clean).

## 7. How to reproduce

```bash
python scrapers/ingest_national.py                        # -> data/processed/listings_national_20260708.csv
python scrapers/dos_costs.py                              # -> cost_benchmarks + macro cost series
python db/init_db.py  --db db/jordan_national.sqlite
python db/load_csv.py data/processed/listings_national_20260708.csv       --db db/jordan_national.sqlite --table listings
python db/load_csv.py data/processed/cost_benchmarks_dos_20260708.csv     --db db/jordan_national.sqlite --table cost_benchmarks
python db/load_csv.py data/processed/macro_construction_cost_dos.csv      --db db/jordan_national.sqlite --table macro_series
python -m scrapers.emit_national                          # -> app/web/public/engine_output.json
JORDAN_RE_DB=db/jordan_national.sqlite uvicorn app.api.main:app --port 8000   # serve
```

**Verdict:** the national vertical slice works end-to-end and is defensible — same proven engine, 66× the evidence, honest confidence, and the cost floor firing for the first time.
