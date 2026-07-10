# HTML Documentation Dashboard — Build Report

**Owner:** HTML-docs agent · **Date:** 2026-07-07 · **Deliverable:** `docs/dashboard/index.html`

A single self-contained HTML "live engineering dashboard" that lets any engineer or the manager
understand the whole project by opening one file. All numbers are pulled from the workstream reports
under `docs/` — none invented.

## Deliverable

- **`docs/dashboard/index.html`** — 1 file, ~66 KB, no external dependencies (inline CSS + JS, inline
  SVG pipeline diagram and bar charts). Opens directly in any browser, no server needed.
- **`docs/dashboard/assets/`** — 11 embedded PNG screenshots (copied from repo root + `docs/`).

## Sections included (20)

1. Executive Summary · 2. Current Progress · 3. Current Metrics · 4. System Architecture
(inline SVG pipeline: Sources → Collection → Database → Feature Engineering → Evidence Engine →
Decision Engine → API → Frontend) · 5. Data Pipeline · 6. Database & Provenance Model ·
7. Evidence Engine · 8. Decision Engine (5 sub-engines + real per-neighborhood output table) ·
9. Current Status (done vs pending, honest) · 10. Completed Work · 11. Pending Work ·
12. Research Status · 13. Collected Datasets (POIs, listings coverage, roads, macro, land use) ·
14. Source Inventory · 15. Data Quality (fill-rate bars) · 16. Known Limitations & Blocked Sources ·
17. Screenshots (11, captioned) · 18. Roadmap · 19. Version History · 20. Team Responsibilities.

## Visual / UX

- **Light default, high-contrast**, with a **dark toggle** (respects `prefers-color-scheme`, persists
  choice in `localStorage`). Directly addresses the earlier "dark-only was hard to read" complaint.
- Sticky side-nav, enterprise status-page aesthetic, one accent color, tabular numerics.
- **Consistent status legend** used throughout: DONE / IN PROGRESS / PENDING / BLOCKED (+ FALLBACK).
- Responsive; wide tables and the SVG diagram scroll inside their own containers.

## Screenshots embedded (11)

`shot-light`, `shot-dark` (both themes), `shot-overview`, `shot-interactive`, `shot-form`
(978→1,155 recompute), `shot-khalda` (map-click), `shot-waterfall`, `shot-comparables`,
`shot-narrative`, `shot-future-empty` (honest awaiting-data state), `shot-zoning`. Each captioned
with what it shows. Sourced from `amman-dashboard-initial.png`, `interactive-01-initial.png`,
`interactive-03-khalda.png`, and `docs/frontend-verify-*.png` (no Playwright run — existing PNGs copied).

## Real numbers used (sourced, not invented)

854 listings (Bayut 600 + OpenSooq 254; 492 sale / 362 rent; 815 with price/m²) · 984 POIs
(mosque 407, school 224, park 141, hospital 108, mall 53, university 31, transport 20) · 5 districts ·
2,558 roads (secondary 1,160 / primary 673 / trunk 660 / motorway 65) · 2,244 land-use polygons
(OSM fallback) · macro_series 1,927 (CBJ 1,377 + DoS 540 + DLS 10) · engine 16/16 tests ·
per-neighborhood recommendation table · fill rates (seller_type 100% … view ~0%, total_floors 0%).

## Marked PENDING / BLOCKED (honest)

- **PENDING (empty tables, research load in progress):** `projects`, `cost_benchmarks`,
  `evidence_items`, `neighborhood_profiles` — flagged across Status, Pending Work, Research Status.
- **BLOCKED (geo-blocked, fallbacks labelled):** DLS transactions (dls.gov.jo), GAM zoning + FAR
  (ammancitygis.gov.jo), CBJ index post-2021-Q3 (statisticaldb.cbj.gov.jo), data.gov.jo.
- Asking-not-transaction prices, per-listing view/parking unavailability, and confounded univariate
  premiums are all stated in the Limitations section.

## Verification

- Structure validated: valid `<!DOCTYPE html>`; tag balance OK (20/20 sections, 11/11 figures,
  10/10 tables, 1/1 svg, style/script balanced).
- All 11 `assets/*.png` image references resolve to real files under `docs/dashboard/assets/`.
- Theme toggle present and wired; renders top-to-bottom with no broken sections.
- Not rendered via Playwright (another agent is using it) — verified by static structural checks.

## Refresh note

Data-aware but static. When the four deep-research tables load, regenerate the counts in Sections 3,
6, 12, 13 and the app's "awaiting data" panels light up. The file is plain HTML with clearly labelled
number cells — easy to update in place.

## Refresh #1 — 2026-07-07 (enriched dataset)

The data landed. In-place number refresh (structure/theme/screenshots kept). All figures re-verified
directly against `db/jordan_re.sqlite`, not just the message:

- **Listings 854 → 24,471** (Bayut 23,521 + Property4321 696 + OpenSooq 254; 24,217 geocoded;
  17,436 sale / 7,035 rent; 19,836 with price/m²).
- **DB coverage 5/9 → 9/9.** Research tables loaded: projects 6, evidence_items 14,
  neighborhood_profiles 5, cost_benchmarks 10 (land-price; construction-cost JD/m² still a gap → marked PARTIAL).
- **Engine re-run:** confidence rose (Abdoun M0.61→H0.76, Shmeisani →H0.74, Khalda H0.77); Abdoun
  premium 1,540→1,299 (premiums now grounded in comps). The per-neighborhood table was restructured to
  show comp depth (engine pool: Khalda 1,086, Dabouq 1,066, Sweifieh 984, Abdoun 917, Shmeisani 177) +
  before→now confidence — I did **not** fabricate new min/rec/premium bands I could not verify; the note
  states bands re-derive per run.
- **Source inventory:** 94 deduped sources (`docs/master-source-inventory.csv`).
- **Screenshots:** added `shot-help.png` (in-app Help panel, light); light/dark already embedded.
- Sections updated: Executive Summary, Progress bars, Current Metrics, Database, Decision Engine,
  Collected Datasets, Source Inventory, Research Status, Data Quality, Current Status, Completed/Pending,
  Version History.
- **Honesty preserved:** construction-cost gap, per-listing view/parking, CBJ 2021-Q3, DLS/GAM geo-block
  all still surfaced. Fill-rate card relabelled "enrichment sample" (pool-wide rates for the new bundle
  being re-measured) rather than implying 24,471-wide coverage.
- Re-validated: 20/20 sections, 12/12 figures, 10/10 tables, all 12 images resolve, tags balanced.

## Refresh #2 — 2026-07-07 (final engine bands, post-dedup)

Team lead supplied the final per-neighborhood bands after a near-duplicate comp dedup (422 cross-posted
listings collapsed, 1% rule). Dropped them into the Decision Engine table (replacing the "bands re-derive
per run" placeholder) and aligned the confidence figures elsewhere:

| Neighborhood | min | rec | premium | conf |
|---|---|---|---|---|
| Abdoun | 650 | 991 | 1,333 | H 0.76 |
| Dabouq | 596 | 840 | 1,084 | M 0.68 |
| Sweifieh | 534 | 821 | 1,108 | M 0.69 |
| Khalda | 522 | 634 | 746 | H 0.77 |
| Shmeisani | 332 | 511 | 690 | H 0.70 |

Dedup context noted (tightened Dabouq 0.65→0.68, refined Shmeisani/Abdoun; Sweifieh/Khalda unchanged).
Confidence values in the Collected Datasets card and Executive Summary aligned to these finals. Re-validated clean.
