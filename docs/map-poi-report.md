# Nationwide POI & Geographic-Feature Collection — Map Data Report

**Date:** 2026-07-08 · **Source:** OpenStreetMap via Overpass API (free, no key) · **Collector:** `scrapers/osm_jordan_poi.py`
**Scope:** All of Jordan (`area["ISO3166-1"="JO"]`), batched by category, deduped by OSM element.

---

## 1. What was collected

**9,444 POIs** across the whole country (up from the 984-row Amman-only `poi` table — a ~10× increase),
plus three geographic-feature layers (water, green, major roads) and a per-neighborhood amenity summary.

Every row keeps full provenance: `source_name=OpenStreetMap`, `source_url` = the element's OSM URL,
`capture_date=2026-07-08`, `evidence_category=gis`, `confidence=M`. Nothing fabricated; unnamed OSM
features are labelled `unnamed <subcategory>` rather than dropped.

### POIs by category (map layer = one file)

| Category | Count | GeoJSON layer |
|----------|------:|---------------|
| transport | 1,933 | `poi_transport.geojson` |
| food_leisure | 1,723 | `poi_food_leisure.geojson` |
| recreation | 1,467 | `poi_recreation.geojson` |
| religious | 1,182 | `poi_religious.geojson` |
| services | 748 | `poi_services.geojson` |
| education | 653 | `poi_education.geojson` |
| health | 632 | `poi_health.geojson` |
| shopping | 599 | `poi_shopping.geojson` |
| negative | 507 | `poi_negative.geojson` |
| **Total** | **9,444** | |

### POIs by governorate (real OSM admin_level=4 boundary join)

Amman 4,292 · Irbid 1,357 · Aqaba 910 · Zarqa 752 · Ma'an 473 · Mafraq 465 · Balqa 291 ·
Karak 234 · Jarash 228 · Madaba 199 · Ajlun 144 · Tafilah 93 · unknown 6.

### Subcategory highlights

parking 1,205 · mosque 857 · restaurant 830 · school 507 · pitch 475 · supermarket 466 ·
cafe 445 · fuel 427 · park 422 · hotel 389 · industrial 331 · atm 312 · pharmacy 311 ·
bank 283 · attraction 267 · hospital 201 · bus_stop 182 · viewpoint 181 · police 118 ·
power_plant 106 · mall 70 · church 65 · university 57 · airport 20 … (48 subcategories total).

### Geographic-feature layers

| Layer | Features | File | Tags collected |
|-------|---------:|------|----------------|
| Water | 8,659 | `water.geojson` | `waterway=river/stream`, `natural=water`, `landuse=reservoir` |
| Green | 1,095 | `green.geojson` | `natural=wood`, `landuse=forest`, `leisure=park/garden` |
| Major roads | 3,864 | `major_roads.geojson` | `highway=motorway/trunk/primary` (lines) |

---

## 2. Database

Two new tables (added to `db/schema.sql`, created idempotently by `db/init_db.py` — the frozen
`poi` table and its 7-category enum are untouched, so the engine is unaffected):

### `poi_extended` — 9,444 rows
`poi_id (PK), category, subcategory, name, name_ar, lat, lng, governorate, neighborhood,
osm_type, osm_id` + universal (`evidence_category, language`) + provenance.
`category` enum: education, health, shopping, food_leisure, recreation, religious, transport,
services, negative, unknown. `subcategory` is free text (48 values). Indexed on category,
subcategory, neighborhood, governorate.

### `area_amenities` — 290 rows (one per Voronoi neighborhood)
Per-neighborhood amenity counts within the neighborhood's Voronoi cell + distances:

```
neighborhood (PK), governorate, centroid_lat, centroid_lng, is_covered,
schools_n, universities_n, hospitals_n, pharmacies_n, malls_n, supermarkets_n,
restaurants_n, cafes_n, hotels_n, parks_n, playgrounds_n, stadiums_n, sports_n,
mosques_n, churches_n, banks_n, atms_n, fuel_n, transport_n, police_n, negatives_n,
total_poi_n, nearest_airport, km_to_airport, km_to_highway,
source_name, source_url, capture_date, collected_by, confidence, notes
```

Counts are point-in-cell (shapely); `km_to_airport`/`km_to_highway` are haversine from the cell
centroid to the nearest airport POI / nearest major-road vertex.

**Spot check (the 5 covered target neighborhoods):**

| Neighborhood | schools | hospitals | malls | restaurants | cafes | banks | mosques | total | km→airport | km→highway |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Shmeisani | 1 | 3 | 1 | 19 | 19 | 23 | 4 | 188 | 8.8 | 0.4 |
| Sweifieh | 4 | 0 | 4 | 11 | 13 | 4 | 2 | 90 | 12.4 | 0.45 |
| Abdoun | 0 | 1 | 1 | 17 | 5 | 5 | 1 | 67 | 9.9 | 0.04 |
| Khalda | 8 | 1 | 0 | 1 | 1 | 5 | 1 | 39 | 14.0 | 1.38 |
| Dabouq | 5 | 0 | 0 | 3 | 3 | 4 | 1 | 38 | 17.8 | 2.4 |

(Shmeisani's 23 banks / 19 cafes match its reality as Amman's commercial-office core.)

---

## 3. Files produced

- **Per-category POI layers:** `data/processed/poi_{education,health,shopping,food_leisure,recreation,religious,transport,services,negative}.geojson`
- **Geographic layers:** `data/processed/{water,green,major_roads}.geojson`
- **DB-load CSVs:** `data/processed/poi_extended.csv` (9,444), `data/processed/area_amenities.csv` (290)
- **Load reports:** `data/processed/load_report_poi_extended.txt`, `..._area_amenities.txt` (0 rejected each)
- **Raw Overpass cache:** `data/raw/osm/jordan/*.json` (re-runnable; `--refresh` forces re-fetch) + `summary.json`
- **Frontend:** all 12 layers copied to `app/web/public/data/` and added to `app/web/scripts/prepare-data.mjs` (18/18 layers ready)

---

## 4. Method notes & honesty

- **Batched by category** (9 POI queries + governorates + water + green + roads = 13 Overpass calls),
  6 s politeness sleep between calls, 429/504 exponential backoff, three-mirror fallback. Raw JSON
  cached so re-runs cost no network.
- **Neighborhood** join uses the existing 290-cell Voronoi surface; POIs outside all cells get
  `neighborhood=other` but still a real governorate. **Governorate** join uses real OSM
  admin_level=4 boundaries (only 6 of 9,444 fell outside every boundary → `unknown`).
- Arabic religion tags (`مسلم`, `الاسلام`) normalized to `mosque`; `christian`→`church`. Genuine
  other faiths (`buddhist`, `multifaith`) kept as-is rather than forced.
- Distances are centroid-based approximations (haversine), suitable for a "near X" display, not
  routing.

## 5. Verification

- All 12 GeoJSON layers validated (shapely) — **all valid**.
- DB load: 9,444 + 290 rows, **0 rejected**.
- `python tests/run_all.py`: engine suites **105 passed**, API suites **77 passed**. The Playwright
  e2e (Analysis panel) is a live-app runtime check unrelated to this data work — the new layers are
  served (HTTP 200) but are not yet referenced by app source, so they cannot affect page rendering.

## 6. Next step (frontend, not in scope here)

The layers are staged and served; wiring MapLibre toggle controls + the left-panel "nearby
amenities" read from `area_amenities` is a frontend task. Data contract is stable and documented above.
