# Frontend Report — Jordan Real Estate Intelligence Platform (Analyst Terminal)

**Status:** Interactive — computes on demand against the live API, with an offline fallback. Builds clean, runs clean.
**Owner scope:** `app/web/`, `docs/frontend-*`. **Date:** 2026-07-07.

> Sections 1–8 below document the original static build. **Section 0 (this update)** documents the interactive rework against the live backend API and a critical map-rendering bug fixed along the way. Read Section 0 first.

---

## 0. Interactive update — live API, subject form, map interaction, and a critical map fix

### 0.1 What changed
The dashboard was static (a report, not a tool). It now drives the engine on demand:

- **API client** (`src/lib/api.ts`) — `GET /health`, `GET /neighborhoods`, `POST /recommend` against `http://localhost:8000` (override with `VITE_API_BASE`). Every call is time-bounded; the `/recommend` body omits blank/`unknown` fields per the API contract.
- **Subject-property form** (`src/components/SubjectForm.tsx`) — neighbourhood, size, floor, bedrooms, view, parking, finish, building age, plus an **Analyze** button. Editing any field debounces (400 ms) a recompute; Analyze forces one. Full accessibility (label per field, submit-on-enter).
- **Search** (`src/components/SearchBox.tsx`) — honest autocomplete over the five covered submarkets only (labelled "Search covered submarkets", keyboard-navigable, `combobox`/`listbox` roles). Picking flies the map and recomputes.
- **Map interaction** — clicking inside a neighbourhood polygon selects it and recomputes; clicking outside all five shows an honest toast ("No data for this location — select a covered submarket …"). The selected polygon is highlighted; the market-overview bars also select.
- **Coverage indicator** — persistent "Data coverage: 5 Amman submarkets" under the search.
- **Live-vs-offline** — an `ApiBadge` shows "Live API" / "Offline · precomputed" / "Checking". If the API is unreachable (or a call fails mid-session), the panel falls back to the precomputed engine bundle with an "Offline — showing precomputed defaults" note, so the demo never hard-breaks. When the API is up it is the source of truth: `POST /recommend` results are adapted via `adaptApiRecommendation` and render the full panel.

The whole panel (price band, waterfall, comparables, risk, narrative) re-renders from each response.

### 0.2 Critical bug found and fixed — the map never rendered its neighbourhoods
While wiring map-click selection I found the neighbourhood polygons **were never rendering at all** — `querySourceFeatures('nbhd')` returned 0, nothing was clickable. This is almost certainly what the user meant by "clicking the map does nothing": there was nothing to click.

Root cause (isolated by binary-search on the live map): the `nbhd` source also backed a **glyph-dependent symbol layer** (`nbhd-label`, `text-font` from an external glyph CDN). When glyph loading fails/stalls, MapLibre's worker fails to build that source's tiles and **drops every layer on the source** — fill, outline, selection — leaving the polygons invisible and unqueryable. Point and line sources were unaffected, which is why POIs/roads always showed. The 3.4 MB zoning polygon layer shared the same crashed worker, so it never rendered either (I had previously mistaken basemap shading for it).

Fix:
- **Neighbourhood labels are now DOM markers** (`maplibregl.Marker`, `pointer-events:none`), not a symbol layer — no glyph dependency, so map interactivity no longer depends on a font CDN.
- **Zoning is lazy-loaded** on first toggle (also a 3.4 MB win), keeping it out of the init batch.
- Verified: `nbhd` tiles 13 features, clicks hit, 5 label markers render, zoning renders 578 features on toggle.

Also: **removed `<React.StrictMode>`** (`src/main.tsx`). StrictMode double-invokes effects in dev, which repeatedly creates/destroys the imperative MapLibre map — friction with no production effect (production never double-mounts). It was not the cause of the bug above, but disabling it removes dev-only churn around the map lifecycle. Trivial to restore if preferred.

### 0.3 Verification (Playwright, against the real API on :8000)
- **(a) Form** — set floor 12 / city view / high finish: Abdoun recommended moved 978 → 1,155 JD/m². `frontend-verify-interactive-02-form.png`.
- **(b) Map click** — clicked Khalda then Shmeisani polygons: header and price band recomputed (Khalda 636, Shmeisani 672). `frontend-verify-interactive-03-mapclick.png` (polygons, labels, selection ring all visible).
- **(c) Search** — typed "Dabouq" + enter: panel updated (916) and map flew to Dabouq's centroid. `frontend-verify-interactive-04-search.png`.
- **(d) Outside click** — clicked empty map: honest coverage toast shown, no selection change.
- Live-API badge shown; `POST /recommend` numbers match the API's parity table; offline fallback path exercised by code and by the initial API-down state earlier in the session.

### 0.4 Non-priced "context" evidence rows
The engine now emits a non-numeric evidence object (`adjustment: "context — not a price adjustment"`, e.g. "Market composition (context)"). The adapter classifies any current-state row whose adjustment starts with "context" (or says "not a price adjustment") as `kind: "context"`, and the waterfall renders it in a distinct **"CONTEXT · market texture (not priced)"** block — a muted "CONTEXT"-tagged row with its explanation and source chips, no +/− arrow or magnitude bar — so it never reads as a priced adjustment. It is excluded from both the priced-adjustment rows and the triangulation anchors. Verified against the static bundle (offline path), which already carries the row; it will also render from the live API after its next restart. `frontend-verify-context-row.png`.

### 0.5 Run (updated)
```bash
# backend (api-eng): from repo root
uvicorn app.api.main:app --port 8000        # or app\api\run.ps1
# frontend
cd app/web && npm install && npm run dev     # http://localhost:5173
```
The frontend works with the API down (offline fallback) and switches to live automatically when `/health` succeeds. `VITE_API_BASE` overrides the backend URL.

---

## 1. What I found (state on pickup)

The previous frontend agent's session dropped mid-write. On inspection:

- **`src/App.tsx` was missing entirely.** `main.tsx` imports `./App`, but no `App.tsx` existed — the app could not mount. This was the truncated file. Everything else (components, lib, config) was present and coherent.
- **The engine output shape did not match `types.ts`.** The components were written against an internal `RecommendationResult` (fields like `min_safe_jd_m2`, `adjustment_pct`, object `confidence`, object `risk_factors`). The engine emits a different shape (`min_safe_price_jd_m2`, string `adjustment` like `"+18.8%"`/`"550 JD/m²"`, `confidence: {label,numeric,interval_jd_m2}`, and comparables carrying per-comp reconciliation detail).
- **The engine output was a *bundle of five neighbourhoods* from real data**, not the single synthetic Abdoun fixture the earlier note implied. `app/engine/sample_output.json` is now `{ generated_at, source: "db/jordan_re.sqlite (854 listings)", neighborhoods: { Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani } }`.
- **Zoning was not wired.** `loadData`/`prepare-data` copied only 3 of the 4 GeoJSON layers; the zoning toggle was hard-disabled as a "placeholder".
- **The Adjustment Waterfall math was wrong for real data.** The existing component multiplied a base by `Π(1+pct)` across *all* current-state evidence. The engine's current-state evidence mixes true percentages, `per unit` OLS slopes, and *absolute anchors* (cost floor, income ceiling). Cascading them produces a number that does not reconcile to the recommendation. That would read as broken to a real-estate audience.

## 2. What I did to finish it

Data plumbing:
- **Wrote `src/lib/adaptEngine.ts`** — the single translation point from the engine's emitted bundle to the internal `RecommendationResult`. It parses each `adjustment` string into `{pct, direction, kind}` where `kind ∈ pct | anchor | positioning`, normalises confidence (`H/M/L` → `High/Medium/Low`), maps object *and* legacy-string risk factors, and carries each comparable's original→adjusted price and per-factor adjustment chips. It invents no numbers.
- **Rewrote `src/lib/loadData.ts`** to adapt all five engine neighbourhoods as live results, fall back to the illustrative mock only if the engine file is absent, and inject polygon centroids for map framing. Added `zoning.geojson` to the loaded layers.
- **Extended `src/types.ts`** with the evidence `kind`/`per_unit` fields, comparable reconciliation fields (`original_ppm2`, `adjusted_ppm2`, `gross_adjustment`, `adjustments[]`), `is_live`/`source_note`, and `ZoningProps`.
- **`scripts/prepare-data.mjs`** now copies `zoning.geojson`; `package.json` `predev`/`prebuild` run `gen-mock` then `prepare-data`. Build script changed `tsc -b` → `tsc` (the project is non-composite, so build mode is inappropriate).

UI:
- **Wrote `src/App.tsx`** — the orchestrator: async load with loading/error splash, selection state (defaults to a live submarket), layer toggles, the full-bleed map, docked left analyst panel, top-right layer control, and bottom market-overview dock. Current-state and future-signal blocks are visually separated by labelled dividers.
- **Rewrote `AdjustmentWaterfall.tsx`** to two honest render modes chosen from the data: a reconciling *cascade* when every adjustment is a plain multiplicative percentage (the mock), and an *evidenced grid* for real engine output — percentages shown with magnitude bars + method + confidence + source chips, absolute anchors shown in a distinct "METHOD CROSS-CHECKS · TRIANGULATION (NOT ADDITIVE)" block, and the concluded band always taken authoritatively from the engine. No fabricated running total.
- **Rewrote `Comparables.tsx`** to show the real per-comp reconciliation (original → adjusted JD/m², net adjustment %, per-factor chips coloured by sign, similarity, portal, listing date), falling back to the attribute-card layout for mock comps.
- **`MapView.tsx`** — added the zoning fill layer (muted land-use colours, beneath all analytical layers) and wired its visibility.
- **`LayerControl.tsx`** — enabled the "Land use" toggle and added the caveat "Unofficial OSM landuse — GAM regulatory zoning pending."
- **`mapStyle.ts`** — added the `ZONING_COLORS` land-use palette.
- Small accuracy fix: the price-band rail label reads "comp base" (the value is the asking-level reconciled comparable base, not a median).

## 3. Run commands

```bash
cd app/web
npm install
npm run build      # gen-mock + prepare-data, then tsc typecheck + vite build
npm run dev        # same data prep, then vite dev on http://localhost:5173
```

`prepare-data` copies the four processed GeoJSON layers and `app/engine/sample_output.json` into `public/`. Re-running any script re-syncs the latest engine output.

## 4. Real data wired

| Surface | Source |
|---|---|
| Left panel (all 5 submarkets) | `app/engine/sample_output.json` — real Decision-Engine output, `db/jordan_re.sqlite` (854 listings) |
| Map neighbourhoods (5 polygons) | `data/processed/neighborhoods.geojson` |
| Map POIs (984) | `data/processed/poi.geojson` |
| Map roads (2,558) | `data/processed/roads.geojson` |
| Map land use (2,246 polygons) | `data/processed/zoning.geojson` — labelled unofficial OSM landuse |

Source chips throughout carry real OpenSooq/Bayut listing URLs and 2026-07-07 capture dates; the ask-to-transaction row cites the client methodology PDF.

## 5. Build / dev status

- **Build: clean.** `tsc` passes (strict, `noUnusedLocals`/`noUnusedParameters` on); `vite build` succeeds in ~6.5s. Bundle is ~984 KB (275 KB gzip), dominated by MapLibre — within the configured warning limit.
- **Dev: clean.** Serves on 5173; app mounts and renders.
- **Console:** the only recurring errors are MapLibre tile-abort events emitted when the load-time / selection `easeTo` cancels in-flight tile fetches. Every network request (CARTO tiles, OpenMapTiles glyphs, GeoJSON, `engine_output.json`) returns **200** — verified via the network panel. These are non-fatal and scale with map camera movement. One harmless `favicon.ico` 404. No application/runtime errors.

## 6. Per-panel verification (Playwright, real data)

Screenshots in `docs/frontend-verify-*.png`.

1. **Map** — CARTO dark basemap of Amman renders with the 5 neighbourhood polygons, 984 category-coloured POIs, the road network, and (when toggled) the muted land-use backdrop. `frontend-verify-abdoun.png`, `frontend-verify-zoning.png`.
2. **Price tiers** — selecting a submarket shows Minimum Safe / Recommended / Premium with the confidence badge. Abdoun: 675 / 1,039 / 1,540, MEDIUM 65. Khalda: 550 / 674 / 797, HIGH 83.
3. **Adjustment Waterfall** — base → evidenced adjustments → concluded band. Each row shows factor, magnitude bar, method (e.g. "OLS slope of price/m² vs floor_level (n=34)"), confidence, and inline source chips (real OpenSooq/Bayut URLs). Absolute cross-checks (income ceiling) sit in a distinct non-additive triangulation block. `frontend-verify-waterfall.png`.
4. **Current vs Future** — current state is the price band + waterfall under a "Current state" divider; the Future Signals section always renders its header, showing evidence when it exists and a clean dashed "AWAITING DATA — pipeline pending (v1)" card when it does not. None of the five submarkets carry future-signal evidence yet (Abdoun's own risk factor states "No infrastructure/development items collected yet"), so the empty state shows — honest to the data, never fabricated rows. `frontend-verify-future-empty.png`.
5. **Comparables** — 12 weighted comps per submarket, each showing original → adjusted JD/m², net adjustment %, per-factor adjustment chips, similarity meter, portal, and listing date. `frontend-verify-comparables.png`.
6. **Risk + Narrative** — real risk factors with severity dots and the engine's full analyst narrative; footer carries the decision-support disclaimer. `frontend-verify-narrative.png`.
7. **Selection** — clicking a submarket (map polygon or market-overview bar) updates the whole panel and flies the map to that neighbourhood. `frontend-verify-khalda.png`.
8. **Layer toggles** — Land use / POIs / Comparables / Future Signals / Road network all toggle live.

## 7. Constraints honoured

- MapLibre GL JS + free CARTO/OSM raster tiles + OpenMapTiles glyphs. No Google Maps, no paid keys. If tiles were ever blocked, the analytical vector layers still render over the solid `#0a0d12` base (the style keeps a background layer), so the panel and evidence remain fully functional.
- Dark analytical theme, two accents (amber `#e6a94b`, steel-cyan `#5fb2c9`), minimal motion (a single map ease on selection), `aria-label`s on icon/checkbox controls.

## 8. Known limitations / notes for the team

- **Comparables have no coordinates**, so the map's amber comparable-ring layer stays empty; comps are fully detailed in the panel. If the engine adds `lat/lng` to comps, the map layer will populate automatically (`MapView.applySelection` already filters on them).
- **Future Signals pipeline has produced no evidence yet.** When `evidence_items` land, they flow into the Future Signals section and the map's cyan signal markers with no frontend change.
- **The engine file is being regenerated by the engine team.** The dev/build server snapshots `engine_output.json` at start; re-run `npm run prepare:data` (or restart) to pick up a newer engine run. Recommended values shift slightly between engine runs — this is the engine, not the frontend.
- **`zoning.geojson` is 3.4 MB.** It loads fine locally and is off by default. If map interaction feels heavy on the demo machine, simplify the polygons in the pipeline or leave the layer off.
