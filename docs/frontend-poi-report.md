# Frontend — POI Amenity Layers + "What's Nearby" Panel

**Date:** 2026-07-08 · **Owner:** Frontend agent · **Scope:** POI/amenity demo wave
**Gate:** `tsc --noEmit` clean · `vite build` clean · Playwright-verified · 0 app console errors

The map now shows 9,444 POIs across 9 toggleable amenity categories + water/green/major-roads
overlays, and every selected area gets a transparent "What's nearby" breakdown. This is the visible
demo capability: a builder/agent/buyer can SEE schools/malls/parks/transport near an area.

---

## 1. What shipped

**Map layers + grouped control (`components/MapLayers.tsx`, `lib/mapPoiLayers.ts`, `lib/poi.ts`)**
- 9 amenity categories (Education, Health, Shopping, Food & Leisure, Recreation, Religious,
  Transport, Services, Negatives) — each a coloured point layer with a distinct colour + emoji icon
  in the control legend.
- 3 geographic overlays: Water, Green/parks, Major roads.
- Grouped, collapsible control (Amenities / Geography / Analytical) with colour dots + icons + a
  per-row loading indicator.
- **Performance:** points render only from zoom ≥ 11.5 ("Points appear as you zoom in"); each
  category's geojson is **lazy-fetched on first toggle-on** and cached (survives theme swaps without
  refetch); **Water (8.4 MB) is lazy-loaded with a "loading…" state**; default is Transport +
  Education only, so first load is informative but not cluttered.
- POI points sit above overlay fills (z-order enforced); clicking a point shows a name +
  subcategory + neighbourhood popup.

**"What's nearby" panel (`components/NearbyAmenities.tsx`, `area_amenities.json`)**
- Grouped amenity counts for the selected area with icons + a group subtotal, e.g. Abdoun: Health 2
  (1 hospital, 1 pharmacy), Shopping 4, Food & Leisure 23 (17 restaurants), Recreation 12, plus
  Services, Transport, Negatives + "67 POIs mapped".
- **Honest:** a 0 renders as "none" muted (e.g. "none Schools", "none Stadiums", "none Churches") —
  never hidden.
- "Nearest airport: Amman Airport · 9.9 km" and "Main highway: 0.04 km".
- Shown in Step 1 (Opportunity) and Step 3 (Market), inside the existing builder-first 7-step app.

**Data (`scripts/prepare-data.mjs`)**
- Copies the 9 `poi_*` + `water`/`green`/`major_roads` geojson into `public/data/`.
- Converts `data/processed/area_amenities.csv` → `public/data/area_amenities.json` (290 areas, keyed
  by neighborhood) via a dependency-free CSV parser — read client-side, no backend change.

---

## 2. Wired vs mocked

Everything is client-side and live — no backend dependency. Category/overlay geojson served from
`public/data/`; amenity counts from the generated JSON. The old single 984-POI layer was retired
(superseded by the 9 categories; default off).

---

## 3. Verification (`tests/verify_poi.py`)

Production build on `:4173`. **0 app console errors** (only CARTO basemap tiles fail — sandbox
network block; they render underneath in a real deploy). Confirmed: nearby panel + airport row
present. Screenshots `tests/screenshots/poi_*`:

- `01_default_layers` — Transport + Education on, uncluttered, zoomed
- `02_more_categories` — Health/Shopping/Religious toggled on, points appear
- `03_nearby_amenities` — Abdoun "What's nearby" with honest "none" zeros + airport/highway
- `04_water_layer` — Water overlay lazy-loaded
- `05_all_layers` — all 9 categories + overlays on, still legible (distinct colours)

**Perf notes:** minzoom gating + per-category lazy load + default-2-categories keep it responsive;
the all-on 9,444-point stress view rendered fine. Water's 8.4 MB stays off until toggled. On a real
(non-sandboxed) network the CARTO basemap renders beneath the amenity layers.

---

## 4. Honesty

Zero counts show "none" (muted), not hidden. Point popups show the real OSM name/subcategory. No
fabricated amenities. Negatives (graveyards, etc.) are shown as their own honest category.
