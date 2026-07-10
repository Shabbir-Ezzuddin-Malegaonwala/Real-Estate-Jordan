# Geo-Context Integration Report

**Date:** 2026-07-07 · **Scope:** additive only — new queryable tables + one non-priced evidence chip.
**Hard constraint honored:** elevation / population / night-light do **not** move the price. All 5 price bands are byte-for-byte unchanged; 100+ existing tests still pass.

---

## 1. Schema additions (`db/schema.sql`, section E)

Two tables, columns matching the friend CSVs exactly. Provenance columns enforced
(`source_name`/`source_url`/`capture_date` non-blank, `confidence` ∈ H/M/L/unknown). Unlike
collected tables they carry **no** `evidence_category`/`language` (the source data has none).

- **`listing_geofeatures`** — PK `listing_id`; `elevation_m, slope_deg, aspect_deg, aspect_cardinal, population_density, nightlight_intensity` + provenance + `notes` + `created_at`.
- **`neighborhood_geocontext`** — PK `neighborhood`; `median_elevation_m, elevation_rank, median_population_density, median_nightlight, dominant_aspect, context` + provenance + `created_at`.

`db/init_db.py` needed no change — it re-runs `schema.sql` (all `CREATE TABLE IF NOT EXISTS`),
so both tables are created idempotently on the existing DB with no data loss.
`docs/db-contract.md` updated with both tables.

## 2. Load counts (zero rejects)

| CSV | Table | Rows | Inserted | Rejected |
|-----|-------|------|----------|----------|
| `listing_geofeatures_clean.csv` | `listing_geofeatures` | 23,617 | **23,617** | 0 |
| `neighborhood_geocontext.csv` | `neighborhood_geocontext` | 5 | **5** | 0 |

Loader header auto-detection resolves both files to the correct table (verified), so a reload
without `--table` works too.

## 3. Non-priced evidence chip

`app/engine/evidence.py::geocontext_evidence()` mirrors the existing `market_composition_evidence`
context chip. Wired into `recommendation._collect_evidence` **after** the price band is computed
(lines that set min/rec/premium run first; evidence objects never feed back into price).
`data.py` gained a `NeighborhoodGeoContext` record, a `DataBundle.geocontext` list, a
`geocontext_for()` lookup, and a SQLite loader (`_table` returns `[]` for older DBs → chip simply
omitted, fully backward-compatible).

Chip shape: `factor="Neighborhood spatial context"`, `adjustment="context — not a price adjustment"`,
`confidence="High"`, `category="current_state"`, `datasets=["neighborhood_geocontext"]`,
`sources=[Copernicus DEM, GHS-POP, VIIRS]` with the real raster URLs. Omitted (never fabricated)
when the subject's submarket has no row.

### Exact chip text (all 5)

- **Abdoun** — Dense, high-activity premium submarket on mid-elevation ground. median ground ~914 m, rank 4/5; population density ~25,032/km²; night-time light index ~81; dominant aspect NE. Context only; does not move the price.
- **Dabouq** — Low-density upscale villa suburb on high ground; least built-up and dimmest at night. median ground ~959 m, rank 2/5; population density ~2,815/km²; night-time light index ~29; dominant aspect NE. Context only; does not move the price.
- **Sweifieh** — Flat-ground commercial-retail hub with mid-to-high residential density. median ground ~910 m, rank 5/5; population density ~13,225/km²; night-time light index ~70; dominant aspect **flat**. Context only; does not move the price.
- **Khalda** — Highest ground of the five; low-to-mid-density residential western suburb. median ground ~1000 m, rank 1/5; population density ~8,120/km²; night-time light index ~65; dominant aspect N. Context only; does not move the price.
- **Shmeisani** — Central high-density, highest-activity commercial-residential core (brightest at night). median ground ~922 m, rank 3/5; population density ~42,322/km²; night-time light index ~118; dominant aspect NE. Context only; does not move the price.

(Sweifieh's `dominant_aspect` is the literal word "flat", rendered as-is.)

## 4. Verification

- `python tests/run_all.py` → **all suites OK** (engine, api, e2e).
- Engine suites: **66 passed** (63 baseline + 3 new in `tests/test_engine_edge_cases.py::NeighborhoodGeoContextChip`): chip present + `current_state` + non-numeric adjustment + http sources; chip omitted without fabrication (empty and uncovered-neighborhood); **identical min/rec/premium and confidence with vs without the chip**.
- `python -m app.engine.emit_sample` → price bands **unchanged**:

| Submarket | min / rec / premium (JD/m²) | Baseline |
|-----------|------------------------------|----------|
| Abdoun | 650 / 991 / 1333 | ✔ identical |
| Dabouq | 596 / 840 / 1084 | ✔ identical |
| Sweifieh | 534 / 821 / 1108 | ✔ identical |
| Khalda | 522 / 634 / 746 | ✔ identical |
| Shmeisani | 332 / 511 / 690 | ✔ identical |

- No hardcoded weights: the `NoHardcodedWeights` scanners over **all** engine modules still pass (the new code contains no attribute→fraction map or `_MULT` table).
