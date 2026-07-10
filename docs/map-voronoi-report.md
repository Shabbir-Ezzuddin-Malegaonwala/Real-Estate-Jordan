# Map Reconstruction: Voronoi Layer + Opportunity Heatmap

**Date:** 2026-07-08
**Owner:** map/geo agent
**Build script:** `scrapers/build_voronoi.py` (scipy + shapely)
**Inputs (read-only):** `data/raw/friend/listings_friend_geocoded.csv`, `data/raw/friend/listing_geofeatures_clean.csv`
**Outputs:** `data/processed/neighborhoods_voronoi.geojson`, `data/processed/opportunity_heatmap.geojson`

---

## Why this exists

The old map drew 1.2–1.5 km approximate **circles** for only **5** neighbourhoods,
leaving gaps everywhere else and no coverage for the rest of the country. This
replaces that with a **gap-free tessellation of 290 neighbourhoods** derived from
real geocoded listings.

## Layer hierarchy (frontend should implement top-down, fall back on absence)

| Priority | Layer | File | `source` value | Status |
|----------|-------|------|----------------|--------|
| 1 | Official GAM polygons | _(none yet)_ | `official` | Geo-blocked — swap in later, architecture is ready |
| 2 | **Voronoi tessellation** | `neighborhoods_voronoi.geojson` | `voronoi` | **ACTIVE — best gap-free representation now** |
| 3 | Approximate circles | `neighborhoods.geojson` | `approximate_circle` | Kept as labelled fallback (5 neighbourhoods, untouched) |

The frontend renders the highest-priority layer available for a given
neighbourhood. Because Voronoi covers all 290 (incl. the 5), circles are only a
safety net; they were **not deleted**.

---

## Task 1 — Centroids

For every distinct `neighborhood` in the geocoded listing corpus we take the
**median lat/lng** of that neighbourhood's rows (median, not mean, so a few
mis-geocoded outliers don't drag the centre).

- **290 / 290** neighbourhoods received a centroid — the friend corpus is **100 %
  geocoded** (23,617 rows, all with lat/lng), so no neighbourhood needed the OSM
  place-node fallback. The OSM lookup (`data/raw/osm/places.json`, 180 nodes)
  remains wired in as the documented fallback for any future neighbourhood that
  arrives without coordinates.
- Governorate per neighbourhood = the most common `district` of its listings
  (spelling variants collapsed: `Maan`→`Ma\`An`, `Ajlun`→`Ajloun`,
  `Tafielah`→`Tafilah`).

## Task 2 — Voronoi tessellation

- `scipy.spatial.Voronoi` over the 290 centroids (computed in lng/lat plane).
- Unbounded outer cells are reconstructed into finite convex polygons (open
  ridges projected outward, vertices ordered around each cell's own centroid —
  ordering around a global centre was the bug that first left 7 % gaps).
- Every cell is **clipped to the buffered (~5 km) convex hull of all centroids**,
  so the map fills the inhabited extent with no ragged edges.
- Exact-duplicate centroids are jittered so the tessellation stays non-degenerate.

**Output properties** (`neighborhoods_voronoi.geojson`):
`neighborhood`, `governorate`, `centroid_lat`, `centroid_lng`, `listing_count`,
`source: "voronoi"`, `is_covered` (true only for the 5 engine neighbourhoods).

## Task 3 — Fallback circles

`neighborhoods.geojson` (the 5 approximate circles) is retained unchanged as the
priority-3 fallback layer. See hierarchy table above.

## Task 4 — Opportunity heatmap

`opportunity_heatmap.geojson` = the identical Voronoi polygons carrying a per-area
opportunity score. Property shape aligns with the backend `/opportunity` endpoint:
`{ score, price_level, demand_density, supply_pressure, growth, future_signals }`
plus the raw inputs (`price_per_m2`, `population_density`, `nightlight_intensity`,
`listing_count`) so the frontend can render the full breakdown.

### Score formula (v1 heuristic — transparent & tunable)

Each component is **min-max normalized to 0–100** across all areas, then:

```
score = 0.40 · demand_density
      + 0.35 · price_level
      + 0.25 · (100 − supply_pressure)      # scarce supply = room to enter
      + 0.00 · growth                        # reserved slot, no data yet
      + 0.00 · future_signals                # reserved slot, no data yet
```

| Component | Built from | Direction |
|-----------|-----------|-----------|
| `price_level` | median price/m² of the area's listings | higher = more valuable market |
| `demand_density` | mean of normalized `population_density` + `nightlight_intensity` (VIIRS/GHS-POP per-listing geofeatures); falls back to listing density if geo missing | higher = more demand |
| `supply_pressure` | active `listing_count` on market | higher = more competition (subtracted) |
| `growth` | — | reserved (0), e.g. permit/transaction trend |
| `future_signals` | — | reserved (0), e.g. planned infra, zoning changes |

Weights are constants at the top of `build_voronoi.py` — retune in one place.
When `growth`/`future_signals` data arrives, add their weights and rebalance.

### Known caveat (read before trusting the top of the list)

`supply_pressure` is min-max normalized on raw `listing_count`, so **data-thin
neighbourhoods (n = 1–4 listings) score near-max on the "scarce supply" term**
and can float to the top (e.g. Ras Al Ain, n=4). Low scrape coverage is not the
same as genuine market scarcity. **`listing_count` is included in every feature as
the data-confidence signal** — the frontend should down-weight, flag, or gray out
low-`listing_count` cells rather than present them as headline opportunities. The
5 engine-covered and other high-`n` areas (Shmeisani n=258, Al Thahir n=356) are
the trustworthy readings.

---

## Verification (all passing)

| Check | Result |
|-------|--------|
| Neighbourhoods with a centroid | **290 / 290** |
| Neighbourhoods tessellated (on the map) | **290** (was 5 → **58× more**) |
| — engine-covered (`is_covered=true`) | 5 |
| — context | 285 |
| Governorates represented | **15** |
| GeoJSON valid (shapely `is_valid`) | 290/290 both files |
| Polygons closed (first == last vertex) | 290/290, 0 unclosed |
| All required properties present | 290/290 both files |
| **Coverage of clip extent (zero-gap test)** | **100.00 %** |
| Inter-cell overlap area | **0 deg²** |
| Score range | 21.3 – 82.9 (mean 38.2) |

Governorate breakdown: Amman 151, Irbid 29, Zarqa 21, Al Salt 14, Balqa 13,
Madaba 12, Al Ghor 8, Mafraq 8, Karak 8, Jerash 6, Ma\`An 5, Ajloun 4, Tafilah 4,
Aqaba 4, Ramtha 3.

**Note on extent:** 206 centroids fall in the Amman metro; the remaining 84 span
the governorates above. The tessellation is national (single global Voronoi), so
far-southern seeds (Aqaba, Ma\`An) own large regional cells — geometrically
correct nearest-neighbour behaviour. The frontend can filter by `governorate` to
zoom to the dense Amman set.

## Rebuild

```
PYTHONUTF8=1 python scrapers/build_voronoi.py
```
