# Friend Data Bundle — Inventory & Harvest

**Bundle:** `data/research-data/frnd/Data-20260707T135524Z-3-001.zip` (271 MB, 371 files, ~561 MB uncompressed)
**Extracted to:** `data/research-data/frnd/extracted/Data/`
**Harvested (ready-to-use) to:** `data/raw/friend/` (27 files, 65.6 MB)
**Produced:** 2026-07-07

## What this bundle is

14 source folders, one per data source. Each folder holds a scraper (`.py`), a `README.md`,
run logs, and — the valuable part — **already-produced output data**. We do **not** re-run any
scraper; we harvest the data that is already sitting in the `output/` / `downloads/` / `csv/`
folders.

**File breakdown:** 298 DATA files · 15 scraper/code · 21 docs · 37 logs.
Of the 298 DATA files, 220 are the DOS building-license `.xls` pile (one small file per
year/quarter/table). The other ~78 carry the bulk of the value.

---

## Source-by-source inventory

Value rating is for **our pricing/AVM platform** specifically.

| Source folder | What it is | Source URL(s) | Key DATA files (rows / size) | Value |
|---|---|---|---|---|
| **Bayut_Jordan** | Full Bayut Jordan listing dump via Algolia. Asking prices, **per-listing lat/lon (100%)**, 41 cols incl. beds/baths/area/plot/furnishing/completion/agent. | bayut.jo | `ads.csv` **23,522 listings** / 14.3 MB · `ads_raw.jsonl` 115 MB (raw) · `locations.csv` 693 · `categories.csv` 20 | **HIGH** |
| **OpenSooq_Jordan** | OpenSooq for-sale + for-rent, from `__NEXT_DATA__`. 40 cols incl. beds/baths/area/furnishing/floor/building_age + seller. City/neighborhood IDs but **no lat/lon**. | jo.opensooq.com | `for-sale.csv` **14,899** / 12.3 MB · `for-rent.csv` **5,898** / 4.8 MB · raw jsonl 38+16 MB · `cities.csv` 14 | **HIGH** |
| **EurekaJo** | EurekaJo portal, all 7 categories × sale/rent. Beds/baths/area/floors. Arabic title/location (needs transliteration). No coords. | eurekajo.com | `eureka_listings.csv` **6,938** / 2.7 MB | **HIGH** |
| **Homes_Jordan** | homes-jordan.com sale + rent, 19 cols, built-up + plot area, reference code key. Amman-centric. No coords. | homes-jordan.com | `sale.csv` **3,171** / 1.5 MB · `rent.csv` **693** / 0.3 MB | **HIGH** |
| **Property4321_Jordan** | 4321property.com — **only portal with per-listing coordinates** (56% have lat/lng). Multi-governorate (Amman, Irbid, Aqaba, Balqa, Madaba, Zarqa, Mafraq). Rich specs where published. | 4321property.com | `property4321_listings.csv` **1,235** (696 geocoded) / 0.36 MB | **HIGH** (spatial anchor) |
| **AbuJudom_Jordan** | abujudom.com — premium Amman inventory (Abdoun, Dair Ghbar, Shmeisani…). 21 cols. No coords. | abujudom.com | `abujudom_listings.csv` **500** / 0.3 MB | **MEDIUM** |
| **Copernicus_DEM_Jordan** | GLO-30 DSM → elevation/slope/aspect grid, ~1.1 km, clipped to Jordan. Range −427 m (Dead Sea) to 1,687 m. **Powers view/elevation features we lack.** `--points` mode joins elevation to any coord CSV. | AWS `copernicus-dem-30m` | `jordan_dem_grid.csv` **84,419 cells** (`lon,lat,elevation_m,slope_deg,aspect_deg`) / 2.4 MB | **HIGH** (new feature) |
| **GHS_POP_Jordan** | GHS-POP R2023A population grid, ~925 m, clipped to Jordan. Total ≈ 11.42 M (matches census). Multitemporal epochs available (growth features). | JRC/Copernicus (CC BY 4.0) | `jordan_ghs_pop_grid.csv` **121,578 cells** (`lon,lat,population,pop_density_per_km2`) / 3.4 MB · source `.tif` 74 MB | **HIGH** |
| **VIIRS_NightLights_Jordan** | NPP-VIIRS-like nighttime-lights radiance grid, ~500 m. Proxy for affluence/commercial vitality — Jordan has **no neighborhood income data**, so this fills that gap. Multi-year (2020–2024). | Harvard Dataverse `10.7910/DVN/YGIVCD` | `jordan_viirs_ntl_grid.csv` **418,368 cells** (`lon,lat,ntl_radiance`) / 10 MB · source zip 91 MB | **HIGH** |
| **OSM_Geofabrik_Jordan** | OSM Jordan flattened to CSV per layer, WGS84 points/centroids. POIs, places, admin boundaries, buildings, roads, landuse. Arabic + English names in separate cols. | Geofabrik (ODbL) | `pois.csv` **9,167** · `places.csv` **2,754** · `admin_boundaries.csv` **1,350** · `landuse.csv` **9,823** · `buildings.csv` **230,925** / 10 MB · `roads.csv` **161,382** / 62 MB | **HIGH** (POI/geo enrich) |
| **OpenData_Jordan_Portal** | Jordan national CKAN portal harvest. **Re-hosts the geo-blocked DLS transaction data.** Contains the official Real-Estate Price Index, mortgage transactions, DLS annual reports + newsletters, and housing-policy PDFs. 34 files, manifest included. | opendata.gov.jo | `DLS price index xlsx` · `mortgage transactions xlsx` · 15+ DLS/housing PDFs · `manifest.csv` | **HIGH** (official/transaction) |
| **DLS_Jordan_Annual_Reports** | DLS annual report PDFs (EN 2012–2018). Trading volumes & values by governorate & property type — but **PDF, needs extraction**. NOTE: folder also contains a stray `jordan-260704.osm.pbf` (32 MB, the OSM source for the OSM folder). | dls.gov.jo (geo-blocked) | 7 EN annual-report PDFs (0.8–4.4 MB each) | **MEDIUM** (PDF) |
| **DOS_Jordan_Building_Licenses** | Dept. of Statistics building-license indicators — # licenses, area, estimated cost, by year/quarter 2004–2026. **Supply/construction-side macro series.** 220 HTML-based `.xls` (read via `pandas.read_html`). | dos.gov.jo | 220 `.xls` (quarterly + yearly, Table1 counts/area/cost, Table2 by building type) | **MEDIUM** (supply macro) |
| **Aqaba_ASEZ_LandUse** | Zoning + land-use polygons for the Aqaba Special Economic Zone. Regulatory/zoning layer for the Aqaba submarket only. GeoJSON WGS84. Some Arabic fields mojibake; English clean. | ArcGIS `d7f591c9…` (ASEZA) | `Zoning.geojson` 89 · `Iqlim_Landuse.geojson` 100 · `GeneralLanduse.geojson` 18 · `District.geojson` 8 | **MEDIUM** (Aqaba only) |

---

## Real transaction prices? Per-listing view/elevation?

- **Real transaction prices:** No *per-property* transaction records anywhere. But the bundle
  **does** contain real **official aggregate transaction-side data** (our biggest gap):
  - `dls_real_estate_price_index_by_governorate_2016-2018.xlsx` — DLS Real Estate Price Index,
    per governorate (Amman, Irbid, Zarqa, Balqa…), **annual 2016–2018 + quarterly 2017/2018**.
    This is the series to calibrate asking→transaction and apply time adjustment.
  - `dls_mortgage_transactions_by_directorate_2017-2018.xlsx` — **# of mortgage transactions and
    total value in JOD** per land directorate (Amman lands, West Amman, Aqaba, Naour, Salt…) for
    2017 and 2018. Real transaction volume + value, aggregate by directorate.
  - DLS annual-report + newsletter PDFs (in OpenData + DLS folders) hold more trading volume/value
    tables, but locked in PDF.
  - **All listing portals are asking prices, not sale prices** — apply the usual asking→sale discount.
- **Per-listing view/elevation:** No portal publishes it. It is **derivable**: run the DEM grid's
  `--points` mode (or a nearest-cell join) against any geocoded listing CSV to attach
  `elevation_m` / `slope_deg` / `aspect_deg`. Same pattern attaches population density and
  nighttime-lights. **Property4321 (696 geocoded) and Bayut (23,522, 100% geocoded)** are the
  ready join targets.

---

## Harvested files → schema mapping

Everything below was copied to `data/raw/friend/`.

### `data/raw/friend/listings/` → **`listings`** table (asking-price comparables)
| File | Records | Coords | Notes |
|---|---:|---|---|
| `bayut_ads.csv` | 23,522 | ✅ 100% | Richest + fully geocoded. Primary comparable source. |
| `opensooq_for_sale.csv` | 14,899 | ❌ (city/neigh IDs) | Largest sale set; geocode by neighborhood. |
| `opensooq_for_rent.csv` | 5,898 | ❌ | Rental comparables / yield. |
| `eureka_listings.csv` | 6,938 | ❌ | Arabic location — transliterate. |
| `homes_jordan_sale.csv` | 3,171 | ❌ | Built-up + plot area. |
| `homes_jordan_rent.csv` | 693 | ❌ | |
| `property4321_listings.csv` | 1,235 | ✅ 56% | Widest governorate spread; spatial anchor. |
| `abujudom_listings.csv` | 500 | ❌ | Premium Amman. |
| `bayut_locations.csv` / `opensooq_cities.csv` | 693 / 14 | — | Location reference dictionaries. |

**~56,856 listings total across 6 portals.** Dedupe against our existing listings before merge
(portals overlap on agent-posted stock).

### `data/raw/friend/geo/` → **`poi`** + new **elevation/demand** feature layers
| File | Rows | Feeds |
|---|---:|---|
| `copernicus_dem_grid.csv` | 84,419 | **NEW elevation/view feature** (elevation, slope, aspect) |
| `ghs_pop_grid.csv` | 121,578 | demand / population-density signal |
| `viirs_nightlights_grid.csv` | 418,368 | affluence / commercial-activity signal (income proxy) |
| `osm_pois.csv` | 9,167 | `poi` table (schools, hospitals, banks, worship, fuel…) |
| `osm_places.csv` | 2,754 | locality gazetteer for geocoding |
| `osm_admin_boundaries.csv` | 1,350 | governorate/district boundaries |
| `osm_landuse.csv` | 9,823 | `zoning_plots` proxy / landuse context |
| `osm_buildings.csv` | 230,925 | building density feature |
| `jordan_adm0_boundary.geojson` | 1 | national clip boundary |

### `data/raw/friend/official/` → **`macro_series`** (+ transaction calibration)
| File | Feeds |
|---|---|
| `dls_real_estate_price_index_by_governorate_2016-2018.xlsx` | `macro_series` — price index, asking→sale + time adjustment |
| `dls_mortgage_transactions_by_directorate_2017-2018.xlsx` | `macro_series` — transaction count + value by directorate |
| `dls_land_type_table_2020.xlsx` | reference — land-type classification |
| `opendata_portal_manifest.csv` | index of all 34 OpenData files + source URLs |

### `data/raw/friend/zoning/` → **`zoning_plots`** (Aqaba submarket only)
`aqaba_zoning.geojson` (89) · `aqaba_iqlim_landuse.geojson` (100) · `aqaba_general_landuse.geojson` (18) · `aqaba_districts.geojson` (8)

---

## Recommended integration order

1. **Bayut + Property4321 listings** → `listings`. Both geocoded, so they immediately enable the
   coordinate joins. Highest comparable value, lowest friction.
2. **DEM + GHS-POP + VIIRS grids** → join to the geocoded listings (nearest-cell) to add
   **elevation/slope/aspect (new view feature), population density, nighttime-lights**. This is the
   single biggest capability gain — features we currently lack.
3. **OpenSooq + Homes + Eureka + AbuJudom listings** → `listings`, after building a
   neighborhood→coordinate geocoder from `osm_places.csv` + `bayut_locations.csv` (these portals
   lack coords). Dedupe across portals.
4. **OSM POIs / places / boundaries** → `poi` + geocoding gazetteer (supports step 3).
5. **DLS price index + mortgage transactions xlsx** → `macro_series`. Calibrates asking→sale and
   adds the only real transaction-side signal. Small, high value.
6. **DOS building licenses (220 xls)** → aggregate to a `macro_series` supply/construction time
   series (needs a `pandas.read_html` parse+concat pass). Deferred — medium value, needs work.
7. **Aqaba zoning + DLS/newsletter PDFs** → submarket/`zoning_plots` and PDF-extraction backlog.
   Lowest priority; Aqaba-only / locked in PDF.

---

## ⚠️ Large files — keep OUT of git

These live in `extracted/` and were **not** copied to `data/raw/friend/` (except grids that are
themselves the deliverable). Add `data/research-data/frnd/` to `.gitignore`.

| File | Size | Note |
|---|---:|---|
| `Data-20260707T135524Z-3-001.zip` | 271 MB | original bundle |
| `Bayut_Jordan/output/ads_raw.jsonl` | 115 MB | raw backup; `bayut_ads.csv` is the usable form |
| `VIIRS_NightLights_Jordan/tiles/2024_Version2.zip` | 91 MB | source raster; grid CSV already extracted |
| `GHS_POP_Jordan/tiles/…R6_C22.tif` | 74 MB | source raster; grid CSV already extracted |
| `OSM_Geofabrik_Jordan/csv/roads.csv` | 62 MB | full LINESTRING geometry; **not copied** — pull selectively if needed |
| `OpenSooq for-sale_raw.jsonl / for-rent_raw.jsonl` | 38 / 16 MB | raw backups |
| `DLS_Jordan_Annual_Reports/jordan-260704.osm.pbf` | 32 MB | OSM source pbf (misfiled here) |

Note: `osm_buildings.csv` (10 MB) and `viirs_nightlights_grid.csv` (10 MB) were copied — usable as-is,
but sizeable; consider Git LFS or keeping them under an ignored `data/raw/` path.
