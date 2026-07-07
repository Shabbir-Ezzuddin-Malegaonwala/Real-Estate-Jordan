# Excel + Text2SQL Deliverables — Build Report

**Generated:** 2026-07-07 · **Source of truth:** `db/jordan_re.sqlite` · **Owner:** Claude Code (technical lead)

Two manager-facing deliverables were produced directly from the populated database. No values
were fabricated — every figure traces to a DB table, `docs/master-source-inventory.csv`, or the
engine sample run `app/engine/sample_output.json`.

---

## Deliverable 1 — `deliverables/Jordan_Real_Estate_Master_Dataset.xlsx`

- **Size:** 2.26 MB · **Sheets:** 16 · Validated: file re-opens cleanly in openpyxl, every sheet
  has data, header row bold on dark fill + frozen (`A2`), autofilter on the header of every table sheet.
- **Currency:** JOD as published (no conversion). `price_per_m2` is the DB-derived column.

| Sheet | Rows (excl. header) | Source |
|---|---|---|
| Overview | narrative | what/coverage/caveats/provenance + sheet index |
| Listings_Covered | 10,226 | `listings` WHERE neighborhood in the 5 covered submarkets (full detail, 34 cols) |
| Listings_All_Aggregate | 863 groups | ALL 24,471 listings grouped by neighborhood × property_type × listing_type (count + median price/ppm2/area) |
| Projects | 6 | `projects` |
| POIs | 984 | `poi` |
| Macro_Series | 1,927 | `macro_series` |
| Zoning | 2,244 | `zoning_plots` (geometry_geojson replaced with a size marker) |
| Districts | 5 | `districts` (geometry_geojson replaced with a size marker) |
| Evidence_Items | 14 | `evidence_items` |
| Neighborhood_Profiles | 5 | `neighborhood_profiles` |
| Cost_Benchmarks | 10 | `cost_benchmarks` |
| Recommendations | 5 | `app/engine/sample_output.json` (scalars + confidence + counts + narrative) |
| Sources | 94 | `docs/master-source-inventory.csv` |
| Data_Quality | table | per-table row counts + listings key-field fill rates + coverage |
| Unknowns_Gaps | 8 | known gaps and their impact |
| Roadmap | 7 | prioritised next steps |

### The 24,471-listing handling (no silent truncation)
The full listings table is 24,471 rows. Rather than truncate:
- **Listings_Covered** carries the 10,226 rows of the 5 covered submarkets in full (34 columns).
- **Listings_All_Aggregate** represents **all 24,471** rows (verified: sum of group counts = 24,471)
  as grouped counts + medians, so every non-covered listing is still accounted for, just aggregated.
- Provenance columns are intact on every raw-export sheet.

### Notable data decisions
- `geometry_geojson` (Zoning, Districts) is huge GeoJSON (up to ~12.6 KB/row); embedding it whole
  would bloat the workbook and is useless to a manager, so those cells hold a
  `[GeoJSON geometry, N chars — omitted from Excel; full polygon in DB]` marker. Noted in Overview.
- Recommendations narrative text was UTF-8 double-encoded in the JSON; fixed on export.

---

## Deliverable 2 — `deliverables/text2sql_training_document.md`

Follows the platform's strict, regex-parseable 3-section format (verified against the exact
ingestion regexes in `Text2SQL-Semantic-Layer-Documentation.html`):

- **## 1. DDL Schema of the Database** — real `CREATE TABLE` statements pulled from the live DB
  (`sqlite_master`), 11 tables. Regex split yields **11 CREATE TABLE chunks**.
- **## 2. Documentation of Business Rules** — **34 bullet rules** (business rules, entity
  definitions, join relationships). Domain-specific: `price_per_m2 = price_jd / area_m2`, only 5
  covered submarkets, asking-vs-transaction 5–15% gap, `confidence` = source trust not price
  reliability, sparse structural attributes (view 0.1% / parking 1.3% / floor 1.4% / finish 1.0%),
  CBJ index ends 2021-Q3, mixed `period` TEXT formats, the SQLite median idiom, engine-output
  tables empty, `evidence_items.impact_area` is free-text (LIKE, not equality join), typing/CAST notes.
- **## 3. Example Queries** — **21 natural-language questions**, each with runnable SQLite SQL in a
  `Q: … / ```sql``` ` block matching the ingestion's Q/SQL regex.

### SQL testing
**All 21 example queries were executed against `db/jordan_re.sqlite` — 21/21 pass, 0 errors.**
Covers medians (SQLite ordered-subquery idiom), per-submarket aggregates, cross-table joins
(`listings`↔`neighborhood_profiles`), `evidence_items` LIKE matching, cost benchmarks, macro index,
POI counts, portal breakdown, and asking→transaction discounting.

One example was corrected after testing: a `cost_benchmarks WHERE spec_class='high'` query ran but
returned 0 rows (that class has no populated cost in this snapshot — most rows are `spec_class='unknown'`
and basic/standard have NULL cost). Replaced with `WHERE cost_jd_per_m2_low IS NOT NULL` (8 rows) and
added a matching caveat rule in Section 2.

---

## Update — geo tables added (2026-07-07)

Two new context-only tables were added to the DB and folded into both deliverables:

- **`listing_geofeatures`** (23,617 rows): per-listing elevation/slope/aspect/population_density/nightlight
  (Copernicus DEM / GHS-POP / VIIRS, nearest-cell join). 9,372 rows fall in the 5 covered submarkets.
- **`neighborhood_geocontext`** (5 rows): per-covered-submarket elevation/density/nightlight/aspect + context.

**Domain rule enforced (honest):** geo is CONTEXT ONLY. Elevation does NOT correlate with price
(~0); no elevation/height/view premium. population_density and nightlight are affluence/activity
proxies (Jordan has no neighborhood-income source), not price drivers. This is stated in the Text2SQL
business rules, the workbook Overview (caveat 7), and Data_Quality.

- xlsx now **18 sheets** (2.77 MB): added **Geo_Context** (5 rows) and **Listing_GeoFeatures_Covered**
  (9,372 covered rows in full, with neighborhood prepended). Overview + Data_Quality updated. All 16
  prior sheets reproduced unchanged; Recommendations carries the refreshed engine bands.
- text2sql doc now **13 DDL chunks / 42 rule bullets / 24 Q-SQL pairs**; the 3 new geo examples
  (densest/most-active submarket, avg Khalda elevation, elevation-vs-price join) all tested.

## Verification summary
- xlsx: opens, 18/18 sheets populated, styled, all 24,471 listings represented + geo context. ✓
- text2sql doc: 3 sections regex-parseable (13 DDL / 42 rules / 24 Q-SQL); **24/24 SQL pass**. ✓
- Geo layers documented as context-only, no price effect. ✓
- No fabricated data; empty engine tables (`derived_premiums`, `recommendations`) disclosed, not hidden. ✓
