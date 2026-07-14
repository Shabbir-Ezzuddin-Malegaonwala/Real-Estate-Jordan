# Development Plan — feature/dashboard (real build)

**Branch:** `feature/dashboard` (from `version-3` = friend's `main`). **Demos A–G = reference only.** Base = the friend's working React + Tailwind + MapLibre app; we **restructure the shell** to the Demo-G layout and **reuse his components**. Scalable, maintainable, clean pattern — not a static site.

## 0. Principles (non-negotiable)
Radical simplicity · progressive disclosure · every word plain · **prices only go up** · decision-first (one conclusion, then detail) · sources in a corner · market-intel = a weekly *signal* · responsive · white+blue, ≤2 accents (`#0072B2`/`#D55E00`), IBM Plex Sans Arabic · every element has a valid reason + logical flow + pre-thought edge cases.

## 1. Target architecture (component hierarchy)
```
AppShell (responsive grid; independent toggles)
├─ TopBar         search(dropdown+narrow+LLM-fallback) · nav-toggle · panel-toggle · LIVE · account-dropdown
├─ Sidebar        categories → subcategories (collapsible)
├─ InfoPanel      renders the active view (decision-first)
│   ├─ PricingView      Launch price · Comparable evidence · Price trend
│   ├─ CostProfitView   Land value(RLV) · Profit margin · Build cost
│   ├─ MarketView       Competitors · Market news · trend
│   ├─ LocationView     Amenities(verdicts) · Infrastructure
│   ├─ AssistantView    New chat · Chat history (open & continue, per-user)
│   └─ SettingsView     language · theme · notifications · account
├─ MapRegion      MapView(all areas) + linked detail card + right MapControls
└─ ui/            Card·Tile·StatusPill·PriceBand·DecisionBanner·charts/*·Tooltip (shared primitives)
```

## 2. Reuse map (friend's component → our view)
| Our view | Reuse from friend | Endpoint |
|---|---|---|
| Pricing | PriceBands, Comparables, AdjustmentWaterfall, ConfidenceBadge | `POST /recommend`, `GET /comparables` |
| Cost & Profit | ResidualLandValue, ScenarioPanel | `POST /residual-land-value`, `POST /scenario` |
| Market | MarketCharts, (area-monitoring) | `GET /area-monitoring`, market-intel |
| Location | NearbyAmenities, MapLayers, OpportunityMeter | `GET /opportunity`, `/areas` |
| Map | MapView, MapLayers, OpportunityLegend | `GET /areas`, geo layers |
| Search/subject | AreaSearch, SubjectForm | `GET /areas`, `/neighborhoods` |
**Retire from the shell:** Stepper (→ Sidebar), StepContent/steps/* (→ Views), Landing (keep as entry).

## 3. Charts (build a small SVG primitives module — no heavy dep)
`ui/charts/`: **Sparkline** (price trend), **BandBar** (safe→premium), **HBarList** (area/competitor comparison — Power-BI "position"), **Donut** (unit-mix / cost split), **ColumnChart** (monthly changes), **MarginBar** (cost vs profit). Rule (BI): pick the *right* chart per data; no pie/gauge for comparisons; ≤2 accents; every chart has a one-line caption + "view data".

## 4. Map plan (next major phase — critical)
- **All areas, not 5:** load every priceable area (~40 with a price) + choropleth by price; POIs (~86k) clustered, shown on zoom, by category (schools/universities/hospitals/transport/shopping/…), each with a hover tooltip. Reuse friend's MapView + MapLayers.
- **Linked card:** select area (search/sidebar/pin) → map focuses + detail card (price, range, amenity verdicts).
- **Right MapControls sidebar:** category toggles, opportunity heat, roads.
- Drive-time later; topography later.

## 5. Backend (keep clean & connected)
Reuse the engine as-is (works). Front↔back sync: one API layer (`lib/useEngine`) so a change on one side reflects on the other. Wire live numbers (no mock). Populate `recommendations`. Auth + per-user chat memory = a later sub-phase (architecture from AI-Studio project). LLM assistant = scoped skills layer + internet fallback (later).

## 6. Phased build (one by one, proper hierarchy)
- **Phase 1 — Foundation (parallel):** design tokens + `ui/` primitives + `ui/charts/*`; global store (selected area/unit/view/chat) + `useEngine` API hooks.
- **Phase 2 — Shell:** AppShell, TopBar (search+account), Sidebar (categories/subcategories), InfoPanel router, MapRegion container, responsive, independent toggles. Landing → shell.
- **Phase 3 — Views (parallel, one file each):** PricingView, CostProfitView, MarketView, LocationView, AssistantView, SettingsView — composing reused components, wired to endpoints.
- **Phase 4 — Map:** all-area coverage, linked card, MapControls, POI categories + tooltips.
- **Phase 5 — Integration & polish:** wire to live backend, responsive pass, a11y, Arabic/RTL, decision banners, verdict framing, sources-in-corner.
- **Phase 6 — Assistant/auth (later):** chat memory, per-user accounts, LLM skills, internet fallback.

## 7. Team (agents, clean file ownership — no collisions)
- **DesignSystem** → `tailwind.config`, `src/ui/*`, `src/ui/charts/*`, `index.css`.
- **StateAPI** → `src/lib/store.ts`, `src/lib/useEngine.ts` (wraps existing lib/api, lib/intel).
- **ShellBuilder** (Phase 2) → `src/shell/*`, `App.tsx`.
- **ViewsBuilder(s)** (Phase 3) → `src/views/*` (one file per view).
- **MapBuilder** (Phase 4) → `src/map/*` (enhances MapView usage).
- **Lead (me)** → plan, integrate, verify (build passes, live smoke-test), gate quality.

## 8. Definition of done (per component)
Builds clean (`tsc && vite build`) · plain labels · decision-first · reuses friend's logic · wired to a real endpoint (or clearly stubbed) · responsive · ≤2 accents · has a valid reason. No element ships that we can't explain.
