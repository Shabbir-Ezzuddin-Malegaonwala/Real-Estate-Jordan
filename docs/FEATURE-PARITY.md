# Feature parity — include EVERYTHING the friend's platform has

Rule (user, 2026-07-15): the fresh UI must cover **all** of the friend's platform's capabilities — his sections, his pricing/map logic, his rich components — not a simplified subset. Fold them into our clean dashboard (behind progressive disclosure where needed). Map his features → our sections:

## Verified-live status (2026-07-15, Playwright + live backend, 0 console errors)
Every section runs on **real engine data** (mock is offline fallback only). Verified end-to-end:
- **Pricing** ✅ launch price, comparable evidence, adjustment waterfall (✓/✗ factors), evidence/sources (tiered, deduped), confidence breakdown, risks, narrative, 90-day trend.
- **Cost & Profit** ✅ residual land value (input-driven `/residual-land-value`), profit margin, build cost, launch scenarios (min-safe/recommended/premium), buildability (`/feasibility`, honest "awaiting data").
- **Market** ✅ competitors (20), market news (30, sourced), key signals (YoY index), weekly brief — `/market-intelligence[/brief]` (pipeline tables folded into the tracked DB; endpoint hardened against a core-only DB).
- **Location** ✅ amenity verdicts (live POI counts); infrastructure shows an honest "none recorded yet" state.
- **Opportunity** ✅ where-to-build score + top-10 ranking over 198 areas + selected-area rank; heat overlay on the map.
- **Map** ✅ whole-Jordan coverage — **every area named** (~290 Voronoi cells, size-gated reveal), POI categories with counts, price choropleth + per-area price layer, linked detail card. Coverage widened 5 → **171 priceable areas**; ~80 carry map-ready centroids.
- **SubjectForm** ✅ customise area/floor/beds/finish → Apply reprices live (verified 973 → 918 JD/m²).
- **Search** ✅ 171 real areas; **Assistant** ✅ grounded LLM (OpenAI→Groq→Gemini) + Tavily web fallback; **Settings** ✅ real language toggle, rest honestly marked; account menu ✅; **responsive** ✅ (desktop + 390px mobile).

Remaining honest stubs (allowed by the DoD's "clearly stubbed"): infrastructure timeline, dark mode, email digest, real accounts + server-side chat history, and ~90 priceable areas that are named but lack a geocoded price dot.


| Friend's feature / component | Endpoint | Our section | Status |
|---|---|---|---|
| Launch price + band | `POST /recommend` | Pricing → Launch price | ✅ (mock) → wire real |
| Comparables table | (in /recommend) | Pricing → Comparable evidence | ✅ (mock) → wire real |
| **Adjustment waterfall** (price drivers ✓/✗ per factor) | (in /recommend) | Pricing → "Why this price" (expander) | ✅ live |
| **Evidence section** + **SourceChip** (sources) | (in /recommend) | Pricing → "Sources" corner/expander | ✅ live (deduped) |
| **Confidence breakdown** (data coverage, dispersion…) | (in /recommend) | Pricing → confidence detail (drill-only) | ✅ live |
| **Risk & narrative** | (in /recommend) | Pricing → risks (expander) | ✅ live |
| Residual land value | `POST /residual-land-value` | Cost & Profit → Land value | ✅ (mock) → wire real |
| Profit margin / build cost | (derived) | Cost & Profit | ✅ (mock) → wire real |
| **Scenario panel + Scenario compare** | `POST /scenario`, `/scenario/compare` | Cost & Profit → Scenarios | ⬜ ADD |
| **Opportunity** (where to build: score + heat + ranking) | `GET /opportunity` | **Opportunity (new top section)** | ⬜ ADD SECTION |
| **OpportunityMeter / OpportunityLegend** | `/opportunity` | Opportunity + map heat overlay | ⬜ ADD |
| Competitors | market-intel | Market → Competitors | ✅ (mock) → wire real |
| **Area monitoring** (what changed) | `GET /area-monitoring` | Market → Market news / monitoring | ✅ mock → wire real |
| **MarketCharts** (his chart set) | market data | Market (charts) | ⬜ reconcile with our ui/charts |
| **NearbyAmenities** | POIs | Location → Amenities (verdicts) | ✅ (mock) → wire real |
| Feasibility (structural) | `GET /feasibility` | Cost & Profit → Buildability | ⬜ ADD (honest "awaiting data") |
| **Real MapLibre MapView + MapLayers** (whole Jordan, all POIs, choropleth, opportunity heat) | geo + /areas | MapRegion | ✅ live |
| **SubjectForm** (custom size/beds/floor/finish inputs) | drives /recommend | TopBar or a "customise unit" panel | ⬜ ADD |
| Landing (Explore vs Evaluate entry) | — | entry | ⬜ decide (we open recommendation-first) |

## Next phases to reach parity
1. **Wire the real backend (replace mock):** an adapter `lib/realSource.ts` implementing the same `DataSource` from the engine endpoints (`/recommend`, `/residual-land-value`, `/opportunity`, `/area-monitoring`, `/areas`). Extend the contract where his data is richer (waterfall factors, evidence, risks, scenarios, opportunity score).
2. **Add the missing sections/subs:** Opportunity (new), Scenarios (Cost & Profit), and the Pricing expanders (waterfall / evidence / risk / confidence-breakdown), Buildability.
3. **Real map:** swap MapRegion's placeholder for the friend's `MapView` + `MapLayers` (MapLibre, whole-Jordan areas + POIs + opportunity heat).
4. **SubjectForm:** let the builder customise the unit (feeds /recommend).
5. Keep it simple on the FACE (progressive disclosure) — his depth lives behind expanders/drill, per the manager's rules.

Test each addition with Playwright + live backend (see [[build-testing-setup]]).
