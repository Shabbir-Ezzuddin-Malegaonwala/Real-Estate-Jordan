# Friend-Data Mining Report

**Date:** 2026-07-08 · **By:** friend-data-miner (Claude Code) · **DB:** `db/jordan_re.sqlite`
**Scripts:** `scrapers/friend_building_cost.py` (P1 parser), `scrapers/friend_data_miner.py` (loader, all 4 priorities)

Mined the underused friend archive at `data/research-data/frnd/extracted/Data/`. Everything is
sourced, deduped against what was already loaded, and idempotent (a second run inserts 0 rows).
No number was fabricated — every figure traces to a file + source URL.

---

## Headline: construction cost per m² (our #1 gap — now filled with official data)

**DoS Building-Licenses filed cost per m² (new buildings), recent 12 quarters (2023 Q2 → 2026 Q1):**

| Authority | JD/m² range | mean | → filled `cost_benchmarks` |
|---|---|---|---|
| **Kingdom (national)** | **152.8 – 160.0** | 157.4 | `basic` |
| **Greater Amman Municipality** | **174.3 – 175.1** | 174.8 | `standard` |

Long-run Kingdom trend (annual avg, new buildings): 2004 = 112.7 → 2012 = 161.9 → 2020 = 155.9
→ 2026 Q1 = 159.0 JD/m². Remarkably flat in nominal terms over the last ~15 years.

**Important honesty caveat (recorded in every row's `notes`):** this is the *licensing authority's
filed estimated cost* — an administrative valuation developers submit for the permit. It is a
**conservative floor and understates turnkey market build cost** (real finished construction in
Amman is materially higher). It is the right number for the cost-approach *floor* in the residual
land-value calculator, but it must not be read as full build cost. It is official, dated, and
sourced — strictly better than the `NULL` that was there before.

Before this pass, `cost_benchmarks.basic` and `.standard` had `NULL` low/high (no construction
number at all); the other rows were portal *asking prices* (400–2667 JD/m²) mislabeled as cost.
The engine's construction-feasibility dimension (`app/engine/opportunity.py`, `median(mids)`) and
residual floor (`cost_for()`) now have real official anchors.

---

## P1 — DoS quarterly Building Licenses → `dos_building_cost` (NEW table)

- **Source:** DoS Building Licenses quarterly reports, `.../DOS_Jordan_Building_Licenses/downloads/quarterly/<year>/*Table1*.xls`
- **Parsing:** the `.xls` files are actually HTML tables (first bytes `<html …`), not real Excel —
  `pandas.read_html` reads them. Header states *"Area in 000 M2 and Cost JD 000"*, so
  `cost_jd_per_m2 = estimated_cost_jd / area_m2` directly. Area & cost are authority **totals**
  (all building types blended; ~90% of licenses are residential by count — captured in
  `residential_license_share`). Counts split Residential/Nonresidential/Fences; area/cost do not.
- **Loaded:** **1,196 rows** across **89 quarter-files, 2004–2026**, 5 issuing authorities
  (Kingdom, Greater Amman Municipality, Municipalities, Joint district committees, Regional
  authorities) × 3 license types (new / extension / existing).
- **New vs already-present:** genuinely additive. The prior DoS data in `macro_series`
  (`official_data.py`, `dos_permits.py`) was *annual* and had **no cost/m²**. This adds the
  **cost dimension**, quarterly granularity, full 2004–2026 history, and 2025–2026 quarters.
- **Also updated:** `cost_benchmarks` `basic` + `standard` rows (see headline).

## P2 — Aqaba ASEZ official land-use → `zoning_plots` (+118 rows)

- **Source:** ASEZAGIS "Aqaba General LandUse" ArcGIS web-map snapshot
  (`https://www.arcgis.com/home/item.html?id=d7f591c9dff647068e01de91988048fa`), WGS84.
- **Loaded:** **118 polygons** — `Iqlim_Landuse.geojson` (100, regional land-use classes) +
  `GeneralLanduse.geojson` (18), tagged `neighborhood=Aqaba`, `source_name="Aqaba ASEZ official"`,
  centroids computed for haversine/mapping. 43 distinct land-use classes.
- Top classes: obstacle Area (40), Minning (8), Residential (7), Non Developed Area (7),
  Secondary/Local Residential, Private Ownership, Pastures, Touristic/Industrial zones.
- **New vs already-present:** the existing zoning is OSM community landuse for Amman; this is the
  **official regulatory land-use layer for the Aqaba submarket** — the Aqaba equivalent of GAM GIS.
  (`Zoning.geojson`/`District.geojson` were left out: they carry named districts, not land-use
  classes, so they don't feed the zoning/feasibility layer.)

## P3 — DLS English annual reports → `macro_series` (+17 rows, deduped)

- **Source:** DLS Annual Reports (English), `.../DLS_Jordan_Annual_Reports/downloads/EN/*.pdf`,
  `https://www.dls.gov.jo/EN/List/Annual_Reports`. All 7 (2012–2018) have clean text layers.
- **Loaded (exact figures pulled by regex, source sentence kept in `notes`):**
  - `Real estate sale transactions (count)` 2012–2018: 112,212 → 98,581 → 105,643 → 108,026 →
    143,387 → 134,148 → 130,207.
  - `Non-Jordanian sale transactions (count)` 2012–2018: 4,992 → … → 2,661 (a clear **downtrend in
    foreign buying** post-2015).
  - `Real estate trading volume` 2016/2017/2018 = 7,000 / 6,000 / 5,000 million JD (report states
    "seven/six/five billion" — rounded to the billion; noted as such).
- **Dedup:** `macro_series` had only 2025 national figures (news-derived) + the CBJ index. The
  transaction-count indicators are new; the trading-volume rows *extend* the existing indicator to
  2016–2018 without colliding (UNIQUE on indicator+geography+period). No double-count of the DLS
  monthly/2025 data.
- **Skipped (honest):** the Arabic monthly newsletters `nashra_aqaria*` are ~50% image-scanned
  (0-char text layer); their national aggregates overlap the DLS data already loaded, so they were
  not OCR'd for marginal, duplicative value.

## P4 — ASEZ foreign-ownership regulation → `evidence_items` (+6 rows)

- **Source:** ASEZA **Instructions No. 132/2007** (selling/leasing immovable property to
  non-Jordanians in ASEZ) + **Regulation No. 7/2001** (land sale & lease), via OpenData Jordan
  Portal. Read directly from the Arabic PDFs; rules cited, not interpreted.
- **Loaded 6 cited regulatory facts** (feed the Feasibility "Regulatory Readiness" dimension for the
  Aqaba submarket / foreign buyers):
  - Non-Jordanians may own **residential land up to 6 dunums** (tiered approval) — Art. 4.
  - Non-Jordanians may own **residential buildings up to 2000 m²** — Art. 5.
  - **Arab-nationality buyers are exempt from reciprocity** — Art. 6.
  - **Resale lock:** 3 yrs (residential) / 5 yrs (other) before transfer — Art. 13.
  - **Legal persons:** business land up to 100 dunums (tiered) — Art. 10.
  - Land sale/lease governed by **Regulation 7/2001** — Art. 4.
- All `type=policy`, `confidence=H`, `published_date=2007-09-11`, cited to article number.

---

## Verification

- `python tests/run_all.py` → **engine suites 73 passed, API suite OK.** The new table/rows do not
  break the engine. (The e2e-frontend suite fails only because the web dev server on :5173 is not
  running — a data load cannot affect page rendering; unrelated to this work.)
- Idempotency confirmed: a second `friend_data_miner.py` run inserts **0** rows in every priority.
- Schema: `dos_building_cost` added to `db/schema.sql` (idempotent `IF NOT EXISTS`) and created via
  `db/init_db.py`.

## Rows added (per table)

| Table | Rows added | Note |
|---|---|---|
| `dos_building_cost` (new) | 1,196 | 2004–2026, 5 authorities × 3 license types |
| `cost_benchmarks` (update) | 2 updated | basic + standard filled with DoS official floor |
| `zoning_plots` | 118 | Aqaba ASEZ official land-use |
| `macro_series` | 17 | DLS annual transaction counts + market size |
| `evidence_items` | 6 | ASEZ foreign-ownership rules |

**Note for the API server:** it reads the DB at startup — restart `:8000` to pick up the new rows.
