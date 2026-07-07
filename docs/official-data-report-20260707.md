# Official Data & Zoning Fallback — Collection Report

**Workstream:** Official Data Specialist · **Date:** 2026-07-07 · **Collected by:** `official-data-agent`
**Deliverables:** `data/processed/macro_series.csv`, `data/processed/zoning.geojson`, raw downloads under `data/raw/{cbj,dos,dls}/`, scrapers under `scrapers/`

---

## Summary

| Task | Source | Priority | Outcome | Rows / Features |
|------|--------|----------|---------|-----------------|
| A | CBJ Real Estate Price Index | P0 | **DONE** — full quarterly series extracted | 910 macro rows |
| B | DLS monthly trading reports | P1 | **BLOCKED** — site unreachable (TCP timeout); documented for human transcription | 0 |
| C | DoS building permits | P1 | **DONE (exceeded)** — authoritative PxWeb API, 12 governorates, 21 quarters | 504 macro rows |
| D | Amman zoning fallback | P0 | **PARTIAL** — official GAM geo-blocked & named mirrors token-gated; delivered OSM-landuse fallback | 2,246 polygons |

`macro_series.csv` total = **1,414 rows**, 16 indicators, 13 geographies, span **2013-Q1 → 2026-Q1**, all `confidence=H`, frozen schema columns exact.

---

## Network reachability (verified today, 2026-07-07)

| Host | Result |
|------|--------|
| `www.cbj.gov.jo` | HTTP 200 — reachable |
| `dosweb.dos.gov.jo` | HTTP 200 — reachable |
| `jorinfo.dos.gov.jo` (DoS PxWeb databank) | HTTP 200 — reachable, **programmatic API works** |
| `www.arcgis.com` (ArcGIS Online) | HTTP 200 — reachable |
| `services.arcgis.com` public feature services | HTTP 200 — reachable |
| `statisticaldb.cbj.gov.jo` (CBJ stat DB) | **TCP timeout — unreachable** |
| `www.dls.gov.jo` / `dls.gov.jo` (http+https, www+apex) | **TCP timeout — unreachable (all 4 variants)** |
| `data.gov.jo` (Jordan Open Data) | **Connection refused — unreachable** |

Pattern: most `*.gov.jo` hosts are geo-blocked from this network; the two exceptions that respond are CBJ's main site and DoS's web + JorInfo databank.

---

## Task A — CBJ Real Estate Price Index (DONE, P0)

**Source page:** https://www.cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index
**File downloaded:** `data/raw/cbj/real_estate_en.xls` (85 KB, genuine OLE2 `.xls`, `content-type: application/vnd.ms-excel`)
**Method:** The download link is a plain href embedded in the page HTML (`/ebv4.0/root_storage/en/eb_list_page/real_estate.xls`); fetched with a browser User-Agent. Parsed with `xlrd` (legacy binary format — `openpyxl` cannot read it).

**Structure:** 3 sheets — (1) index by property type, (2) index by governorate, (3) methodology. Base year **2012=100**, published quarterly. Annual columns 2005-2020 plus quarterly columns 2013-Q1 … **2021-Q3**.

**Extracted → `macro_series.csv` (evidence_category=`macro`):**
- **14 property-type indicators** at national (`geography=Jordan`) level: `cbj_repi_general_index`, `_apartment`, `_villa`, `_house`, `_residential`, `_non_residential`, `_commercial`, `_industrial`, `_other`, `_lands`, `_land_residential`, `_land_commercial`, `_land_industrial`, `_non_regulated`.
- **`cbj_repi_general_index` by governorate**: Amman, Irbid, Zarqa, Balqa, Mafraq, Karak, Tafila, Ma'an, Madaba, Jerash, Ajloun, Aqaba (12).
- 35 quarters each (2013-Q1 → 2021-Q3). `unit=index_2012=100`.

**IMPORTANT — data latency:** The official CBJ Excel is **stale: it stops at 2021-Q3.** That is the newest quarter the file contains; the CBJ page exposes exactly one download link and no newer file. Fresher quarters (if published at all) would live in `statisticaldb.cbj.gov.jo`, which is **unreachable from this network.** For time-adjustment of listings dated 2022+, the engine must either (a) extrapolate the index with a documented assumption, or (b) obtain fresher CBJ data via a Jordan-exit VPN. This is a real limitation to flag to the client, not a collection error.

Amman general-index sanity check (2020-Q4 → 2021-Q3): 116.68 → 117.31 → 117.41 → 117.56 (base 2012=100) — flat-to-gently-rising, consistent with the known post-2017 plateau in Amman residential.

---

## Task C — DoS Building Permits (DONE, exceeded, P1)

**Descriptive page:** https://dosweb.dos.gov.jo/industry/building-licenses/ (text only — no inline data; TablePress content is client-side).
**Authoritative source found:** the **JorInfo PxWeb databank REST API** — base `https://jorinfo.dos.gov.jo/Databank/api/v1/en/`, database `DOS_Database`, folder `19` = *Building Licenses*, table **`BUILD_T3`** = *Licenses Issued for New Residential and Non-Residential Buildings by Major Building Material for Walls and Governorate*.
**Raw response saved:** `data/raw/dos/BUILD_T3_response.json`. (Note: API returns JSON with a UTF-8 BOM — decoded with `utf-8-sig`.)

**Method:** POST query selecting `KIND_BUILD` = {No. of Licenses, Total Area}, `MAT_BUILD` = {Stone, Cement Bricks} (summed), all 12 governorates, all 4 quarters, years 2020-2026. Response format `json`.

**Extracted → `macro_series.csv` (evidence_category=`government`):**
- `dos_building_licenses_count` — unit `licenses`
- `dos_building_licensed_area_thousand_m2` — unit `thousand_m2`
- 12 governorates × 21 quarters = 252 rows each (504 total).
- **Period span: 2020-Q1 → 2026-Q1.** Source omits **2024 entirely** (TIME jumps 2023 → 2025); noted in every row's `notes`. Future/unreported 2026-Q2/Q3/Q4 zeros were dropped.

**Unit caveat (verified):** DoS reports licensed area in **thousands of m² (000 M2)**, confirmed by BUILD_T1's explicit label and by the count-to-area ratio (Amman 2025-Q4 = 795 licenses / 1,204 → ≈1,515 m² average per building; raw-m² reading would be absurd). Indicator name and unit both say `thousand_m2` to prevent misreading. **The frontend/engine must multiply by 1,000 for absolute m².**

Sanity check: Amman = **39.6%** of national licenses in 2023 — correct order of magnitude for the dominant governorate. Amman 2025 quarterly license counts: Q1 537, Q2 670, Q3 655, Q4 795.

---

## Task B — DLS Monthly Trading Reports (BLOCKED, P1)

**Attempted (all failed, TCP ConnectTimeout):**
- `https://www.dls.gov.jo/Default/En`
- `https://www.dls.gov.jo/AR/List/مؤشرات`
- `https://www.dls.gov.jo/EN/List/Annual_Reports`
- Retry variants: `http://www.dls.gov.jo/`, `http://dls.gov.jo/`, `https://dls.gov.jo/` — all TCP timeout.
- Alternative `data.gov.jo` (CKAN open-data portal) — connection refused.

**Conclusion:** `dls.gov.jo` is unreachable from this network (same geo-block class as GAM ArcGIS). No DLS transaction volume / count / Amman-share could be retrieved programmatically here.

**What a human should transcribe** (once on a Jordan-exit VPN or from a downloaded PDF), into `macro_series.csv` with `evidence_category=government`, `language=ar`, `confidence=H`:
- Latest 1-2 monthly DLS trading reports → `indicator=dls_transaction_volume_jd` (unit `jd`), `dls_transaction_count` (unit `transactions`), `dls_amman_share_pct` (unit `percent`).
- Reports live under `dls.gov.jo/AR/List/مؤشرات` (monthly, Arabic PDF) and `.../EN/List/Annual_Reports`.
- **Partial substitute already in hand:** CBJ REPI is *derived from DLS transaction microdata* (the Excel's own source line reads "Department of Lands and Survey & Central Bank of Jordan"), so the price-trend dimension DLS would provide is already covered by Task A. What remains missing is raw *volume/liquidity* (JD traded, transaction counts) — a demand-velocity signal, which the master plan already classifies as P1/roadmap.

---

## Task D — Amman Zoning Fallback (PARTIAL, P0)

**Goal:** plot-level zoning/landuse polygons for the map layer.

**Attempt log:**
1. **Named mirror item `4909a23609c441408ba48660bdecbdd0` (Amman_2022_WFL1):** item-metadata endpoint returns HTTP 200 but null fields (restricted). Service URL resolved via search = `services3.arcgis.com/0IVKjWoVA5tJIUq8/.../Amman_2022_WFL1/FeatureServer`. Querying it → **HTTP 200 `error 499 Token Required`** at service root and every layer. **Not publicly accessible.**
2. **Named mirror item `f4e390d55fe94a5b9f3df0687d918321` (AMMAN_PLOT):** service = `services6.arcgis.com/cpH3GzzxXWyuR151/.../AMMAN_PLOT/FeatureServer` → **`499 Token Required`.** Not accessible. (Also `Zahran_WFL1` = same owner, same token error.)
3. **ArcGIS Online search** (`q=Amman landuse OR zoning OR GAM`, 429 hits): the bulk are `Amman_OJAI_*` services owned by `Emil_2018` — these are **aviation flight procedures** (OJAI = Queen Alia ICAO; SID/STAR = departure/arrival routes), **not zoning.** Irrelevant.
4. **Public open service found & used:** `services.arcgis.com/lqRTrQp2HrfnJt8U/arcgis/rest/services/Amman/FeatureServer` — fully public, no token. Layer 5 = **`landuse`** polygons (OSM-derived): **2,246 features.** Type distribution: 942 residential, 462 farmland, 268 orchard, 66 industrial, 33 commercial, 8 retail, plus recreation/quarry/cemetery/etc. **91 built-up (residential/commercial/retail/industrial) polygons intersect the west-Amman target bbox** (Abdoun/Sweifieh/Khalda/Shmeisani/Dabouq).

**Delivered:** `data/processed/zoning.geojson` — all 2,246 landuse polygons, WGS84 (CRS84), with injected provenance on every feature and a top-level `_provenance` block.

**Property dictionary** (per feature `properties`):
| Field | Meaning |
|-------|---------|
| `FID`, `osm_id` | ArcGIS FID / original OSM object id |
| `name` | landuse name (often Arabic; frequently blank) |
| `type` | OSM landuse class — residential, commercial, industrial, retail, farmland, orchard, recreation_groun, quarry, etc. |
| `Shape__Area`, `Shape__Length` | geometry metrics (service SR) |
| `source_name` | "ArcGIS Online public mirror (OSM-derived Amman landuse)" |
| `evidence_category` | `gis` |
| `authenticity` | `UNOFFICIAL_MIRROR — OSM landuse, NOT GAM regulatory zoning; verify before client use` |
| `capture_date`, `collected_by` | 2026-07-07 / official-data-agent |

**⚠️ Verify before client use.** This is **OSM landuse, not GAM regulatory zoning.** It has **no** `zone_class` / `far` / `max_height_m` — the Res A/B/C/D classes and FAR the pricing engine wants are NOT in this data. Treat it as a coarse landuse backdrop for the map, and as a stand-in for the `zoning_plots` layer until official GAM data is obtained.

**Path to the real thing:** GAM ArcGIS (`ammancitygis.gov.jo/arcgis/rest/services`) confirmed geo-blocked → requires a **Jordan/regional-exit VPN**. That is the only route to authentic plot-level zoning + FAR. Recommend flagging "official source identified (GAM ArcGIS REST), access pending VPN" honestly in the deliverable.

---

## Files produced

```
data/processed/
  macro_series.csv        1,414 rows — frozen schema, CBJ + DoS
  zoning.geojson          2,246 landuse polygons (OSM fallback, labelled)
  _cbj_rows.csv           intermediate (CBJ partial)
  _dos_rows.csv           intermediate (DoS partial)
data/raw/
  cbj/real_estate_en.xls          + _dump.txt + page HTML
  dos/BUILD_T3_response.json       + permits_en.html + permits_ar.html
  dls/                             (empty — source unreachable)
scrapers/
  cbj_fetch.py  cbj_download.py  cbj_inspect.py  cbj_extract.py
  probe_sources.py  zoning_discover.py  zoning_inspect.py  zoning_export.py
  dos_permits.py  build_macro_series.py
```

## Recommendations to team lead

1. **CBJ index latency (2021-Q3) is the biggest official-data gap.** Decide: extrapolate with a documented assumption, or acquire fresher CBJ data via VPN. Do not silently present a stale index as current.
2. **DoS permits are strong and current (to 2026-Q1)** — good supply-pipeline signal; wire directly into the supply-trend feature. Remember the ×1,000 area conversion and the missing-2024 gap.
3. **Zoning:** ship the OSM-landuse layer as a labelled placeholder; put "GAM zoning access pending (VPN)" in the methodology doc. Do not represent it as regulatory zoning.
4. **DLS volume/liquidity** is the only P1 dataset fully missing — assign to a VPN-enabled human or the junior/Perplexity route (Homes-Jordan blog summaries of DLS monthly data are the documented fallback).
