# Frontend Rebuild — Adaptive Intelligence Platform

**Date:** 2026-07-08 · **Owner:** Frontend agent (Claude Code) · **Scope:** `app/web/`
**Build gate:** `tsc --noEmit` clean · `vite build` clean · Playwright verified · 0 app console errors

The valuation-form tool is now an **adaptive, decision-first intelligence platform**: one map + one
evidence base, reshaped by role (Builder / Agent / Buyer). The working engine wiring, MapLibre,
light/dark theme, and evidence rendering were kept and built on — nothing was thrown away.

---

## 1. What shipped

| # | Feature | Files |
|---|---------|-------|
| 1 | **Role selector + adaptive workspace** — first screen picks a lens; persists; header switcher | `components/RoleSelector.tsx`, `lib/role.ts`, `App.tsx` |
| 2 | **Builder (hero): opportunity heatmap** — Jordan map coloured by opportunity score; click area → intelligence | `components/MapView.tsx`, `lib/mapStyle.ts`, `components/OpportunityLegend.tsx` |
| 3 | **Area Intelligence** — opportunity score ring + 5-driver breakdown (with per-driver reasons) | `components/OpportunityMeter.tsx`, `workspaces/BuilderWorkspace.tsx` |
| 4 | **Residual Land Value** — max defensible land price + full breakdown (reveal under "Evaluate a project here") | `components/ResidualLandValue.tsx` |
| 5 | **Scenario What-if** — floors / target-floor / finish / construction cost / metro delay / launch delay → base vs scenario + deltas + explanation | `components/ScenarioPanel.tsx` |
| 6 | **Decomposed confidence** — overall + 5 component bars with reasons (replaces single H/M/L) | `components/ConfidenceBreakdown.tsx` |
| 7 | **Expandable evidence** — every adjustment-waterfall row expands to method, datasets, all sources, confidence | `components/AdjustmentWaterfall.tsx` |
| 8 | **Area search** — autocomplete over 958 areas; covered vs context-only honestly flagged | `components/AreaSearch.tsx` |
| 9 | **Ask (scaffolded)** — captures the question, states plainly the grounded assistant is pending; never fakes an answer | `components/AskPanel.tsx` |
| 10 | **Agent workspace** — valuation band + evidence + client-ready sales narrative (composed from evidence, copy button) | `workspaces/AgentWorkspace.tsx`, `lib/narrative.ts` |
| 11 | **Buyer workspace** — plain-language "is it fair / is the area good / what to watch" + future signals | `workspaces/BuyerWorkspace.tsx`, `lib/narrative.ts` |
| 12 | **Map resilience** — vector + choropleth render even when the basemap CDN is unreachable | `lib/mapStyle.ts`, `components/MapView.tsx` |

New contract + adapter layer: `lib/intel.ts` (all new endpoints, live adapters, local fallbacks,
mojibake guard). New types in `types.ts`. `lib/adaptEngine.ts` extended for `confidence.components`.

---

## 2. Wired to live vs mocked

Everything is **wired to live** and confirmed against the running API — with a transparent local
fallback that auto-swaps if an endpoint is down. Provenance is always shown in the UI
(`Live API` / `engine` / `engine-scored` vs `locally computed` / `estimated locally`).

| Endpoint | Status | UI provenance |
|----------|--------|---------------|
| `POST /recommend` (+ `confidence.components`) | **LIVE** | "engine-decomposed" |
| `GET /areas` (958 areas) | **LIVE** | "958 areas · 5 with structured data" |
| `GET /opportunity` (score + 5 components + reasons) | **LIVE** | "engine-scored" |
| `POST /scenario` (levers → base/scenario/deltas) | **LIVE** | "engine" + "Applied: … Net effect …" |
| `POST /residual-land-value` (breakdown + residual) | **LIVE** | "engine" |
| `/health`, `/neighborhoods` | **LIVE** | "Live API" badge |
| Voronoi surface + opportunity heatmap (`neighborhoods_voronoi.geojson` + `opportunity_heatmap.geojson`, 290 cells) | **LIVE** — gap-free choropleth across all 290 cells; the 5 covered circles overlay as engine-covered markers; the old 5 circles remain as the safety-net fallback | choropleth spans all areas; low-n cells muted |
| Grounded AI "Ask" | **SCAFFOLDED** — input wired to a TODO; no fake answers | "assistant · coming soon" |

Local fallback (used only if an endpoint 404s / errors): residual + scenario are deterministic
formulae (exact), opportunity is a stated heuristic over real portal counts, confidence components
derive from comps/evidence/band-width. All labelled `local`.

---

## 3. Contract mismatches found (for the backend agent)

Built against the briefing contract; the live shapes differ. I adapted client-side in `lib/intel.ts`
so the UI is stable — but flagging so the contract/docs can be reconciled:

1. **UTF-8 double-encoding (mojibake) in ALL new-endpoint strings** — `²`→`Â²`, `→`→`â†'`, `×`→`Ã—`.
   Affects `/opportunity` reasons, `/scenario` `levers_applied`/`explanation`, `/recommend`
   `confidence.components` reasons, `/residual` `basis`. **Please emit proper UTF-8.** I added a
   defensive `fixText()` that repairs it client-side, but the source should be fixed.
2. `GET /areas` → `{ covered_count, total_count, areas: [...] }` (not a bare array). No
   `median_price_per_m2`, `name_ar`, or `context` fields (I derive `context = !covered` and merge
   medians from `/neighborhoods`).
3. `GET /opportunity` → `{ version, note, weights, as_of, areas: [...] }`; each component is
   `{ score, reason }` (not a flat number); `score` is a float. (Contract implied flat numbers.)
4. `POST /scenario` → `base`/`scenario` use `*_price_jd_m2` keys; `deltas` is an aggregate object
   `{ recommended_pct, … }` (percent, not decimal) + `levers_applied: string[]`. No per-lever pct,
   so the UI renders applied levers as labelled rows and reads the headline delta from the bands.
5. `POST /residual-land-value` → percentages are **fractions 0–1** (`finance_pct: 0.06`), fields are
   `professional_fees_pct` / `developer_profit_pct`, and `property_type` + `finish_quality` +
   `gdv_per_m2` are required. Response is `{ breakdown: [...], gdv_total_jd,
   residual_land_value_total_jd, residual_land_value_per_m2_jd, viable }`. My UI sends
   percentage-point inputs and converts.

---

## 4. Map resilience change (notable)

The basemap used external CARTO raster tiles + a glyph CDN as **required** style resources, so
MapLibre's `load` event stalled whenever that CDN was slow/blocked — leaving the whole map (roads,
POIs, choropleth) blank. Restructured to a background-only base style (no external required
resource) with the CARTO raster attached afterwards as a best-effort bottom layer + an idempotent
`isStyleLoaded` fallback installer. Result: the analytical map + opportunity choropleth render
immediately over the theme background even offline; tiles fill in when reachable. This is why the
verification screenshots show the choropleth without a basemap (the sandbox blocks the tile CDN) —
in a normal deployment the CARTO tiles render underneath.

---

## 5. Verification (Playwright, python — `tests/verify_rebuild.py`)

Ran against the production build served on `:4173` (a CORS-allowed origin) with the live API on
`:8000`. **0 app console errors** (only CARTO tile requests fail — network-blocked here).
Screenshots in `tests/screenshots/rebuild_*`:

- `01_role_selector` — the three-lens first screen
- `02_builder_heatmap` — opportunity choropleth (Shmeisani green / Khalda red / others amber) + roads + POIs + labels
- `03_area_intelligence` — LIVE API, opportunity meter with engine reasons, launch band, confidence
- `04_confidence_breakdown` — engine-decomposed 5 components
- `05_residual_land_value` — engine residual (max land 550,400 / 275 JD per buildable m²)
- `06a/06b_scenario` — construction cost +20% → recommended 964 → 1,061 (+10.1%), engine-explained
- `07_evidence_expanded` — an adjustment row drilled into method + datasets + 8 source chips + cross-checks
- `08_agent_narrative` — client-ready sales narrative + comparables
- `09_buyer_summary` — fair-price / area / future-signals + scaffolded Ask
- `11_builder_dark_heatmap` — choropleth in dark theme

---

## 5b. Voronoi map + opportunity heatmap (added after the geo agent delivered)

Wired `data/processed/neighborhoods_voronoi.geojson` (290 gap-free cells across 15 governorates) +
`opportunity_heatmap.geojson` (same cells + baked score/components/raw-inputs). `prepare-data.mjs`
now copies both into `public/data/`.

- **Layer hierarchy:** official GAM (absent) → **Voronoi (ACTIVE)** → 5 circles (safety-net fallback).
  The choropleth colours all 290 cells by opportunity score; the 5 covered submarkets keep their
  circle markers on top.
- **Low-n caveat handled (per the geo agent's warning):** `supply_pressure` inflates data-thin
  cells, so 188 of 290 cells (listing_count < 10) are **muted on the map** (confidence-as-opacity:
  low-n cells drop to 0.12 vs 0.5) and **flagged in the panel** — a thin cell shows a `LOW DATA · n=X`
  badge, "Too thin to rank", the driver reason "only N listings — scarcity is noise here", and
  "shown for context, not ranked as an opportunity". Ranking sorts low-data cells to the bottom. A
  4-listing cell can never headline as a build opportunity (verified: "Tareq" n=3 →
  `rebuild_14_context_area`).
- **Click behaviour:** covered cell → full engine recommendation; context cell → area intelligence
  (opportunity meter) + honest "no structured pricing yet" state, never a fabricated price. Every
  clicked cell gets a selection outline (works for all 290, not just the 5).
- Opportunity data merges the baked heatmap (all 290, `source: heatmap`) with the live engine
  `/opportunity` (the 5 covered, richer reasons, `source: live`); listing_count carries across so
  low-n muting still applies to the covered set.

Screenshots: `rebuild_12_voronoi_heatmap` (full choropleth), `rebuild_14_context_area` (low-data
context state).

## 6. Honesty guarantees kept

- No fabricated numbers: context-only areas show `NoStructuredData` (awaiting state), never a price.
- Source chips on every fact; evidence rows drill to method + sources + datasets.
- Every derived figure labels its provenance (`live` vs `local`, `engine` vs `estimated locally`).
- Builder floor→city-view + finish premiums are explicitly labelled **builder assumptions**, not
  listing-derived (matching the documented engine limit).
- Offline data fallback intact; accessibility preserved (labels, `aria-*`, keyboard, `role="tab"`).

---

## 7. Follow-ups

- Backend: fix UTF-8 encoding (§3.1); optionally add `median_price_per_m2`/`context` to `/areas`.
- Geo: drop `neighborhoods_voronoi.geojson` + `opportunity_heatmap.geojson` into `public/data/` →
  choropleth auto-upgrades from 5 circles to gap-free polygons across all areas (loader already wired).
- AI: wire `AskPanel` to the grounded assistant endpoint when the LLM service + key land.
- Bundle is ~1 MB (MapLibre) — consider a manual chunk split later; not blocking.
