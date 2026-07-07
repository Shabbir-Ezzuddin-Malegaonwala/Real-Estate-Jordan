# Data Integration Report

**Owner:** Database Engineer · **DB:** `db/jordan_re.sqlite` · **Passes:** #1–5 · **Updated:** 2026-07-07

Tracks every source loaded into the database: rows loaded vs rejected, header mismatches flagged
back to owners, reconciliation decisions, and a coverage matrix across the 9 collected tables and
5 target submarkets. No data is fabricated or backfilled — empty tables are reported as gaps.

**Coverage: 5 of 9 collected tables populated** (listings, poi, districts, macro_series, zoning_plots).
**Listings expanded to 854** (Bayut 600 + OpenSooq 254) in pass #4.

---

## 1. Loads so far

| Source | Table | Read | Inserted | Rejected/Skip | Owner | Loader |
|--------|-------|-----:|---------:|--------------:|-------|--------|
| `data/raw/listings_bayut_20260707.csv` (expanded) | `listings` | 600 | **600** | 240 dup skipped | scraper-eng | `load_csv.py` |
| `data/raw/listings_opensooq_20260707.csv` | `listings` | 254 | **254** | 0 | scraper-eng | `load_csv.py` |
| `data/raw/listings_opensooq_20260707.csv` (re-run, upsert) | `listings` | 254 | 0 ins / **254 upd** | 0 | scraper-eng | `load_csv.py --upsert` |
| `data/processed/poi.csv` | `poi` | 984 | **984** | 0 | gis-specialist | `load_csv.py` |
| `data/processed/neighborhoods.geojson` | `districts` | 5 | **5** | 0 | gis-specialist | `load_geojson.py` |
| `data/processed/macro_cbj_price_index.csv` | `macro_series` (CBJ) | 1377 | **1377** | 0 | gis-specialist | `load_csv.py` |
| ~~`macro_series.csv` (DoS portion)~~ **replaced in pass #4** | `macro_series` (DoS) | 504 | ~~504~~ **deleted** | — | official-data-agent | see §2b |
| `data/processed/macro_dos_permits.csv` | `macro_series` (DoS) | 540 | **540** | 0 | gis-specialist | `load_csv.py` |
| `data/processed/macro_dls_transactions.csv` | `macro_series` (DLS) | 10 | **10** | 0 | gis-specialist | `load_csv.py` |
| `data/processed/zoning.geojson` | `zoning_plots` | 2246 | **2244** | 2 skipped | gis-specialist | `load_geojson.py` |

Per-source reports live in `data/processed/load_report_*.txt`. The 2 skipped zoning features
(#1119, #1432) had degenerate/empty geometry — recorded in `load_report_zoning_plots.txt`.

---

## 2. Macro reconciliation decisions

### 2a. CBJ reconciliation (pass #3) — CONFIRMED by lead

Two overlapping CBJ sources existed. Investigated before merging — did **not** blindly append.

| | Already loaded (`macro_cbj_price_index.csv`) | New consolidated (`macro_series.csv`, CBJ part) |
|---|---|---|
| Rows | 1377 | 910 |
| Span | **2005 → 2021-Q3** | 2013-Q1 → 2021-Q3 |
| Recency | 2021-Q3 | 2021-Q3 (same) |
| Indicators | 14 (human-readable names) | 14 (machine slugs `cbj_repi_*`) |
| Governorates | 14 | 13 |
| Pre-2013 history | **216 rows across all 14 geographies + 14 indicators** | none |

**Decision — keep the already-loaded CBJ set as authoritative; do NOT load the new file's CBJ.**
Rationale (per the "keep whichever is more complete/longer-span" rule): both sets end at the same
quarter (2021-Q3), but the loaded set has 8 extra years of history (2005–2012, 216 rows) and more
rows. The new file's CBJ is a strict subset in time; its only advantage is slug naming.

**Discrepancy logged (not silently resolved):** the two sets name the same series differently
(e.g. `Real estate price index - Buildings - Residential` vs `cbj_repi_residential`). Because
`macro_series` is deduped by `UNIQUE(indicator, geography, period)`, appending the new CBJ would
**not** have deduped — it would have created 910 parallel duplicate rows under different names.
That is exactly why only the DoS portion was loaded. Verified post-load: **0 duplicate
(indicator, geography, period) tuples; 0 `cbj_repi_*` rows present.**

**Lead confirmed (pass #4): keep this CBJ set, do NOT switch to the slug-named consolidated set —
the 2005–2012 history outweighs naming cosmetics.** No change made.

### 2b. DoS building-permits swap (pass #4)

Two DoS versions existed at different granularity — the ONE rule was to keep only one (no double-count).

| | Previously loaded (official-data) | New (gis-specialist) — **chosen** |
|---|---|---|
| Rows | 504 | **540** |
| Granularity | quarterly, by governorate | annual, by issuing authority |
| Span | 2020-Q1 → 2026-Q1 | **2019 → 2024** |
| 2024 | missing | **present (90 rows)** |
| Amman relevance | governorate "Amman" | **"Greater Amman Municipality" (108 rows)** |
| Confidence | H | H |

**Decision (per lead): replaced the 504 with the 540.** Deleted the old set with a guarded query
(`evidence_category='government' AND collected_by='official-data-agent' AND source_name LIKE '%JorInfo%'`,
asserted exactly 504 matched before deleting; CBJ verified untouched at 1377), then loaded the 540.
More current (reaches 2024) and its Greater-Amman-Municipality breakdown is the better Amman proxy.
No double-count: verified 0 rows remain with `collected_by='official-data-agent'`.

### 2c. DLS transactions (pass #4) — NEW context

Loaded `macro_dls_transactions.csv` as-is: 10 national-aggregate rows (real-estate trading volume,
transaction revenues, foreign-ownership value), transcribed from dated news articles citing DLS
(Zawya 6, Jordan News 4). `confidence=L` — honest labelling; the primary DLS site was unreachable
and each row cites its own article URL. National trend context only.

### 2d. Clean rebuild (pass #5) — supersedes the surgical swap above

Per the lead's final instruction, `macro_series` was **cleared and rebuilt from exactly three
canonical, contract-aligned files** (simpler and guaranteed free of any leftover rows from the old
official-data set). Deleted all 1927 rows, reloaded the three; 1377 + 540 + 10 = **1927**, zero
rejections. The canonical CBJ file now carries `evidence_category=government` (was `macro`) — this
also resolves the earlier labelling note.

### Final `macro_series` composition — 1927 rows

- **CBJ price index:** 1377 rows, 14 indicators, **2005 → 2021-Q3**, 14 governorates. `evidence_category=government`, `confidence=H`, source = CBJ.
- **DoS building permits:** 540 rows, **annual 2019 → 2024** (90 rows in 2024), by issuing authority (incl. Greater Amman Municipality, Kingdom, Municipalities, Joint district committees, Regional authorities). `evidence_category=government`, `confidence=H`, source = DoS. Caveat in `notes`: area in **000 m²**, cost in **000 JD**.
- **DLS transactions:** 10 rows, national, `evidence_category=news`, `confidence=L`, sources Zawya (6) / Jordan News (4).
- Verified: **0 duplicate (indicator, geography, period) tuples; 0 old official-data rows remaining.**

*Awaited: a small CBJ supplemental (recent ~8 quarters past 2021-Q3) from deep-research R5, to be appended when it lands (the CBJ statistical DB is geo-blocked — 2021-Q3 is a genuine source limit).*

---

## 3. Coverage matrix

### Collected tables

| Table | Rows | Status |
|-------|-----:|--------|
| `listings` | 854 | ✅ populated (Bayut 600 + OpenSooq 254) |
| `poi` | 984 | ✅ populated |
| `districts` | 5 | ✅ populated (all 5 target neighborhoods) |
| `macro_series` | 1927 | ✅ populated (CBJ 1377 + DoS 540 + DLS 10) |
| `zoning_plots` | 2244 | ✅ populated (UNOFFICIAL OSM landuse — see §4) |
| `projects` | 0 | ⛔ gap — deep-research (competitor projects) pending |
| `evidence_items` | 0 | ⛔ gap — deep-research (infrastructure/news) pending |
| `neighborhood_profiles` | 0 | ⛔ gap — deep-research pending |
| `cost_benchmarks` | 0 | ⛔ gap — deep-research (construction costs) pending |

Engine tables `derived_premiums` and `recommendations` are intentionally empty (Decision-Engine output).

### Target-submarket coverage (the 5 premium areas)

| Neighborhood | listings (sale/rent) | poi | district boundary |
|--------------|:--------------------:|----:|:-----------------:|
| Abdoun | 170 (96/74) | 37 | ✅ (approx circle) |
| Dabouq | 177 (100/77) | 12 | ✅ (approx circle) |
| Sweifieh | 169 (100/69) | 41 | ✅ (approx circle) |
| Khalda | 166 (95/71) | 40 | ✅ (approx circle) |
| Shmeisani | 172 (101/71) | 64 | ✅ (approx circle) |

Listings total **854**: by portal Bayut 600 / OpenSooq 254; by type 492 sale / 362 rent (all
apartments); 0 outside the 5 target neighborhoods. 815 have a usable `price_per_m2`; 600 have
lat/lng (all Bayut — see caveat below).

`macro_series` and `zoning_plots` are governorate/city-wide, not per-target-neighborhood (Jordan
does not publish sub-city macro data; the OSM landuse mirror covers greater Amman).

---

## 4. `zoning_plots` — UNOFFICIAL, read the caveat

The 2244 polygons are **OSM landuse, NOT GAM regulatory zoning** (GAM ArcGIS is geo-blocked). They
carry **no `zone_class`, `far`, or `max_height_m`** (all NULL) — those regulatory fields require the
real GAM source. Every row's `notes` begins `UNOFFICIAL OSM landuse, not GAM regulatory zoning`, and
`confidence=L`. The land-use category is in `land_use` (top values: residential 942, farmland 460,
orchard 268, recreation_ground 117, quarry 78, industrial 66; some category strings are truncated in
the source mirror, e.g. `recreation_groun`). Use these for landuse context only, not for FAR/height
regulatory reasoning. Replace with real GAM zoning if the community-mirror/VPN retrieval succeeds.

---

## 5. Not loaded — no schema home (by design)

- `data/processed/roads.geojson` (2558 LineStrings) — no `roads` table; consumed directly as
  GeoJSON by the frontend map layer. Not a gap.

---

## 6. Data-quality observations (informational — not blocking, not mine to fix)

- **OpenSooq listings (254) have NO lat/lng** — the SERP exposes none. Loaded with NULL coords
  (not rejected, per instruction); flagged for a downstream centroid/geocoding pass before they can
  be placed on the map or used in distance features. Bayut's 600 all have coords.
- **55 listings have `price_jd` < 1000 JD** (rent-as-sale / placeholder noise) — kept raw per
  instruction; the engine handles outliers. 815/854 have a usable `price_per_m2`.
- **Listings attribute fill rates (post sale-detail-enrichment upsert, pass #7, across all 854):**

  | Attribute | All 854 | Bayut 600 | OpenSooq 254 |
  |-----------|--------:|----------:|-------------:|
  | seller_type | **100%** | 600 | 254 |
  | floor_level | 41% | 120 | 231 |
  | parking | 38% | 326 | 0 |
  | furnishing | 35% | 51 | 254 |
  | building_age_years | 25% | 85 | 132 |
  | finish_quality | 25% | 219 | 2 |
  | **view** | **~0%** | 1 | 0 |
  | total_floors | 0% | 0 | 0 |

  Sale-detail enrichment lifted parking (12%→38%), finish_quality (18%→25%), building_age (21%→25%),
  floor_level (38%→41%), and **seller_type to 100% real values** (727 agent / 127 private — the
  earlier defaulted 'agent' placeholder is gone). `description_raw` upgraded to full detail text
  (avg 529 chars; 521 rows > 300 chars), merged with a longest-text-wins rule so descriptions never
  shrink. Rates above are across all 854; **sale-only rates run higher** (~48% parking, ~44%
  floor/age) since rent rows dilute the denominators.
  **`view` stays ~0% — Bayut/OpenSooq do not expose orientation; documented limitation, Phase-2/R7.**
  The engine's view/aspect factor must lean on neighborhood-level qualitative signals (R7) rather
  than per-listing view. `total_floors` also unavailable from either portal.
- **Dabouq POI density is thin (12)** vs Shmeisani (64) → weaker distance/density features there.
- **CBJ *price* index ends at 2021-Q3.** DoS permits (to 2024) and DLS transactions (to 2025) now
  extend official context, but the CBJ price index itself stops in 2021-Q3 — if the engine needs a
  current price time-adjustment factor, the latest CBJ quarters need a refresh from gis-specialist.
- **DLS is `confidence=L`, news-sourced, national-only** — use as trend context, not as a precise
  input; each row cites its own article.

---

## 7. Still awaited (next passes)

- `data/raw/research/` — deep-research CSVs: `projects`, `evidence_items`, `cost_benchmarks`,
  `neighborhood_profiles`.
- Real GAM `zoning_plots` (regulatory zone_class/FAR/height) if community mirrors/VPN succeed.
- CBJ price-index refresh past 2021-Q3, if recency is needed.
- The Bayut view-enrichment file (upsert) — see §6 fill rates.

All loads are idempotent (duplicate primary keys / `UNIQUE(indicator, geography, period)` skipped),
so re-running is always safe. Report re-issued each pass.
