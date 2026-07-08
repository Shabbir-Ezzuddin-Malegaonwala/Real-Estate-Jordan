# Databases — which is which

This project has **two** SQLite databases. Do not confuse them.

| File | Rows | Role | Attribute fill |
|---|---|---|---|
| **`jordan_national.sqlite`** | **56,854** | **PRODUCTION** — the national build (6 portals, 12 governorates). The API defaults to this. All shipped outputs (`app/engine/sample_output.json`, `app/engine/outputs/*.json`) are generated from it. | view 77% · finish 8% · floor 12% (text-mined) · elevation/night-lights/density/POI-distance on geocoded rows (Phase 2) |
| `jordan_re.sqlite` | 854 | **PILOT (reference only)** — the original Amman-only demo with hand-enriched attributes. Kept so the earlier build is reproducible. **Not** the source of any production number. | richly enriched (small sample) |

## Rebuild the production DB

```bash
python scrapers/ingest_national.py         # 6 portals -> canonical listings CSV
python scrapers/enrich_from_text.py        # mine descriptions -> view/finish/floor/parking (C2)
python scrapers/enrich_spatial.py          # DEM/VIIRS/GHS-POP/OSM -> spatial features (Phase 2)
python scrapers/dos_costs.py               # DOS -> construction cost floor
python db/init_db.py  --db db/jordan_national.sqlite
python db/load_csv.py data/processed/listings_national_20260708.csv   --db db/jordan_national.sqlite --table listings
python db/load_csv.py data/processed/cost_benchmarks_dos_20260708.csv --db db/jordan_national.sqlite --table cost_benchmarks
python db/load_csv.py data/processed/macro_construction_cost_dos.csv  --db db/jordan_national.sqlite --table macro_series
python scrapers/gen_map_layers.py          # map circles + POIs
python -m scrapers.emit_national           # precomputed, provenance-stamped outputs
```

Every generated output carries a `provenance` block (source DB, listings row count,
snapshot hash, git SHA) so a number can always be traced to the snapshot that produced it.
