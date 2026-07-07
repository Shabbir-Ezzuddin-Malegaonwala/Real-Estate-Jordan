# GIS Data Extraction Report — Amman POIs, Boundaries & Roads

**Capture date:** 2026-07-07 · **Collected by:** gis-agent · **Source:** OpenStreetMap via Overpass API
**Script:** `scrapers/osm_overpass.py` (re-runnable; `--refresh` forces re-fetch, otherwise raw JSON is cached under `data/raw/osm/`)

## 1. Path taken

**Overpass API (primary) — succeeded. Geofabrik backup NOT needed.**

All four queries were served by the main endpoint `overpass-api.de`. Two operational notes:

- The default `requests` User-Agent triggers **HTTP 406** from Overpass. A descriptive `User-Agent` header is mandatory and is set in the script.
- Transient **429 / 504** responses occurred under load; the script retries with quadratic backoff and falls back across three mirrors (`overpass-api.de` → `overpass.kumi.systems` → `maps.mail.ru`). All queries eventually returned 200 from the primary.

Bounding box queried (EPSG:4326): **S 31.85, W 35.75, N 32.05, E 36.05** — covers the full Amman metro, not just the five target submarkets, so that distance-to-nearest-POI features can resolve to amenities that lie just outside a target neighborhood.

Geometry (point-in-polygon assignment, haversine nearest-neighbor, circle generation) is **pure Python** — no shapely/pyproj dependency, so the pipeline runs on a clean Python 3.13 install.

## 2. Output files (all EPSG:4326, UTF-8)

| File | Type | Count |
|------|------|-------|
| `data/processed/poi.geojson` | FeatureCollection (Point) | 984 |
| `data/processed/poi.csv` | Frozen POI schema | 984 |
| `data/processed/neighborhoods.geojson` | FeatureCollection (Polygon) | 5 |
| `data/processed/roads.geojson` | FeatureCollection (LineString) | 2,558 |

## 3. POIs by category (984 total)

| Category | Count | OSM tags mapped |
|----------|-------|-----------------|
| mosque | 407 | `amenity=place_of_worship` (all faiths — see caveat 5.2) |
| school | 224 | `amenity=school` |
| park | 141 | `leisure=park` |
| hospital | 108 | `amenity=hospital`, `amenity=clinic` |
| mall | 53 | `shop=mall`, `amenity=marketplace` |
| university | 31 | `amenity=university`, `amenity=college` |
| transport | 20 | `public_transport=station`, `railway=station` |

## 4. POIs by neighborhood

| Neighborhood | POIs | Boundary source |
|--------------|------|-----------------|
| Shmeisani | 64 | approximate circle (r=1.2 km) |
| Sweifieh | 41 | approximate circle (r=1.2 km) |
| Khalda | 40 | approximate circle (r=1.5 km) |
| Abdoun | 37 | approximate circle (r=1.2 km) |
| Dabouq | 12 | approximate circle (r=1.5 km) |
| other | 790 | outside all target circles / >2 km from any target center |

Assignment logic: point-in-polygon against the neighborhood polygons; if no hit, nearest target center within 2 km; else `other`. The large `other` bucket is expected and intentional — it holds real city-wide amenities the pricing engine still needs for distance features.

## 5. Boundaries — real vs approximate (important caveat)

**All 5 neighborhood boundaries are `approximate_circle`, NOT real OSM polygons.** OSM has essentially no administrative boundary polygons at neighborhood level inside the Amman bbox — the `admin_level=8..11` query returned exactly **one** relation (Sweileh, not a target). This is a known gap in OSM coverage for Amman and matches the risk anticipated in MASTER-PLAN.md §2c.

Mitigation applied: each circle is centered on the **real OSM `place=neighbourhood/town` node** for that name (confirmed present for all five), not on a hand-guessed coordinate. Properties record this: `source=approximate_circle`, `approximate=true`, `centered_on=osm_place_node`, plus the `radius_km` used. Radii are 1.2 km for the compact submarkets (Abdoun, Sweifieh, Shmeisani) and 1.5 km for the larger, lower-density ones (Dabouq, Khalda).

**Consumer guidance:** treat neighborhood assignment as approximate near circle edges. If GAM ArcGIS district polygons become reachable (currently geo-blocked per §7 risk 3), swap them in — the pipeline's `build_neighborhoods` already prefers a real polygon whenever one matches a target name.

### 5.2 Other caveats

- **Worship bucket:** the frozen schema's POI category enum only offers `mosque` for places of worship, so all 407 `place_of_worship` nodes land in `mosque`. 27 non-Muslim ones (churches etc.) carry `religion=<x>` in `notes`. If the engine needs mosque-specific distance, filter on the note.
- **Marketplace / clinic mapping:** 15 `marketplace` nodes are bucketed as `mall` and 35 `clinic` nodes as `hospital` (nearest available category); both are flagged in `notes`.
- **Unnamed POIs:** 287 of 984 have no OSM name. Per the frozen "unknown, never blank" rule, `poi.csv` name = `unknown`; the GeoJSON keeps an empty string so MapLibre renders no label. An unnamed park/mosque is still a valid geographic amenity for distance features.
- **Possible node/way duplication:** a few large POIs may exist in OSM as both a node and a building way and thus appear twice. Deduplication is by `(osm_type, id)` only; proximity de-duping was judged over-engineering for v1. Impact on nearest-distance features is negligible.
- **Confidence:** every row is `confidence=M` — OSM is community data (per collection philosophy, this rates the source, not the evidence).

## 6. Roads (2,558 total)

| Class | Count |
|-------|-------|
| secondary | 1,160 |
| primary | 673 |
| trunk | 660 |
| motorway | 65 |

Full geometry (`out geom`) is preserved as LineStrings with `name`, `name_ar`, `highway`, `ref` properties — sufficient for the accessibility/road-proximity feature and map rendering.

## 7. Reproduce

```bash
cd C:\Rubicon\Real-Estate-Jordan
python scrapers/osm_overpass.py            # uses cached raw JSON
python scrapers/osm_overpass.py --refresh  # re-fetch from Overpass
```

Raw Overpass responses are cached under `data/raw/osm/` (`pois.json`, `boundaries.json`, `places.json`, `roads.json`, `summary.json`) for auditability.
