# Database Layer — Build Report

**Owner:** Database Engineer · **Date:** 2026-07-07 · **Status:** complete and verified
**Scope:** the structured database foundation ("database FIRST") for the Jordan Real Estate
Intelligence Platform.

---

## 1. What was built

| Deliverable | Path | Lines |
|-------------|------|-------|
| Schema (all 12 tables) | `db/schema.sql` | 1–320 |
| DB initialiser (SpatiaLite-aware, idempotent) | `db/init_db.py` | 1–123 |
| Generic schema-driven CSV loader | `db/load_csv.py` | 1–333 |
| Data contract for other engineers | `docs/db-contract.md` | — |
| This report | `docs/db-report.md` | — |

The live database is `db/jordan_re.sqlite` (created by `init_db.py`; currently a pristine empty schema).

### Tables (`db/schema.sql`)

Every table in `MASTER-PLAN.md` §3 is implemented, plus the two engine-output tables the task
required:

- **Collected:** `listings`, `projects`, `poi`, `districts`, `zoning_plots`, `macro_series`,
  `evidence_items`, `neighborhood_profiles`, `cost_benchmarks`
- **Engine outputs:** `derived_premiums` (Adjustment Engine), `recommendations` (Decision Engine)
- **Meta:** `schema_meta` (schema version + spatial-capability flags)

Every collected table carries the universal columns (`evidence_category`, `language`) and the six
provenance columns. Enums are the exact master-plan sets plus the sentinel `unknown`. `price_per_m2`
on `listings` is a generated column (`schema.sql:43`) — always consistent, never collected.

---

## 2. Key decisions & fallbacks

1. **SpatiaLite is not installed on this machine.** `mod_spatialite` fails to load here (confirmed:
   `The specified module could not be found`). Per the task, `init_db.py` **falls back gracefully
   instead of crashing** (`init_db.py:33` `try_load_spatialite`, warning at `:84`): it logs a clear
   warning, stores polygons as GeoJSON text
   in `districts.geometry_geojson` / `zoning_plots.geometry_geojson`, keeps `centroid_lat/lng` for
   cheap mapping, and records `schema_meta.spatial_enabled = 0`. Point tables (`listings`, `projects`,
   `poi`) use plain `REAL` lat/lng as specified. If SpatiaLite is later installed, `init_db.py` will
   detect it, initialise spatial metadata, and flip the flag — no schema change needed. Downstream
   distance work uses haversine on lat/lng until then.

2. **Schema is the single source of truth for validation.** `load_csv.py` reads enums, required
   columns, numeric types and NOT-NULL rules **back out of the live schema** (`parse_enums` at
   `load_csv.py:112` + `PRAGMA table_xinfo` at `:132`). There is no second copy of the rules to
   drift from `schema.sql`.

3. **`unknown` vs blank** (`load_csv.py:validate_row`): `unknown` is the only legal null-object;
   blank in a required or enum column rejects the row with a logged reason; provenance
   (`source_name`/`source_url`/`capture_date`) must be present and not `unknown`; `unknown` numerics
   and dates become `NULL`; malformed numerics/dates reject the row.

4. **`price_per_m2` is derived, not collected.** The junior CSV header (K-PACKET Dataset 4) omits it;
   the DB computes it via a generated column. The loader ignores any derived/generated column that
   appears in a CSV.

5. **No hardcoded pricing weights anywhere.** `derived_premiums` starts empty; the Adjustment Engine
   populates it with values recomputed from market data (fractions, e.g. `0.08` = +8%).

6. **Idempotency.** `init_db.py` uses `IF NOT EXISTS` throughout (safe to re-run). `load_csv.py`
   skips existing primary keys (reported as duplicates) unless `--replace` is passed; `macro_series`
   is deduped by `UNIQUE(indicator, geography, period)`.

---

## 3. How to use

```bash
# 1. Create or upgrade the database (idempotent)
python db/init_db.py

# 2. Load a CSV — table auto-detected from the header
python db/load_csv.py data/raw/bayut/listings_20260708.csv

# 3. Force a table / upsert existing rows
python db/load_csv.py path/to/file.csv --table listings --replace
```

Each load writes `data/processed/load_report_<table>.txt` (rows read / inserted / duplicates /
rejected, with a reason per rejected row). Full column/enum reference: `docs/db-contract.md`.

---

## 4. Verification performed

All checks run against `db/jordan_re.sqlite`; the DB was reset to empty afterwards.

- `init_db.py` creates all **12 tables**; fallback mode logs cleanly and does not crash;
  `schema_meta` = `{schema_version: 1, spatial_enabled: 0}`.
- **Valid row inserts** and `price_per_m2` derives correctly (185000/200 → **925.0**; 120000/150 → 800.0).
- **Enum validation rejects** an illegal value (`view = ocean`) with the allowed list in the reason.
- **Strict provenance rejects** a row with a blank `source_url` (row absent from the DB afterwards).
- **`unknown` numerics** (`bedrooms`, `building_age_years`) stored as `NULL`.
- **Idempotency:** re-running the same CSV inserts 0 rows and reports the existing key as a duplicate.
- **Generic auto-detect** works on a second table (`cost_benchmarks`), rejecting an illegal `spec_class`.

---

## 5. Notes for downstream engineers

- Build against `docs/db-contract.md`; if it disagrees with `db/schema.sql`, the schema wins.
- Scraper output (Bayut/OpenSooq) must use the exact `listings` header in the contract (no
  `price_per_m2`) so the loader ingests it with zero mapping.
- Tables with surrogate auto-increment keys and no natural unique key (`cost_benchmarks`,
  `neighborhood_profiles`) are **not** deduplicated on reload — load each source CSV once, or add a
  natural key upstream if repeated loads are expected.
- Spatial queries currently use GeoJSON + haversine. Installing `mod_spatialite` upgrades this
  automatically on the next `init_db.py` run; no schema migration is required.
