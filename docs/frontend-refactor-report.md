# Frontend Refactor — Builder-First, 7-Step Journey

**Date:** 2026-07-08 · **Owner:** Frontend agent · **Scope:** SCOPE-FROZEN wave (exactly the 7 items)
**Gate:** `tsc --noEmit` clean · `vite build` clean · Playwright-verified · 0 API console errors

Consolidated from 3 role modes into ONE builder-first product: two entry points → a 7-step builder
journey over the same map + evidence base. Agent/Buyer value moved into outputs (Sales step).

---

## 1. What shipped (the 7 frozen items)

| # | Item | Result |
|---|------|--------|
| 1 | Drop role selector | Removed. Deleted `RoleSelector`, `lib/role.ts`, the 3 workspace files, `AskPanel`. One builder user. |
| 2 | Landing = two entry points | `Landing.tsx`: **Explore Opportunities** → opportunity map (step 1); **Evaluate My Land** → jumps to Feasibility (step 2) with the area search. Equally prominent. |
| 3 | 7-step journey stepper | `Stepper.tsx` — numbered non-linear tracker: Opportunity, Feasibility, Market, Economics, Pricing, Sales, Monitoring; shows "Step N of 7 · question". `steps/StepContent.tsx` routes each. |
| 4 | Decision Readiness (8-dim + Overall) | `DecisionReadiness.tsx` — live from expanded `/opportunity.readiness`; each dim a bar + reason + confidence; **null dims render muted "data not yet available", never zero**. |
| 5 | Sales = 2 outputs | `steps/SalesStep.tsx` — Executive Summary (builder) + Sales Narrative (copy-ready), composed client-side from evidence, labelled drafts, copy buttons. Investor Memorandum = Phase-2 note. |
| 6 | Scenario + compare | Kept the what-if `ScenarioPanel`; added `ScenarioCompare.tsx` — 3 presets side-by-side table via `POST /scenario/compare`. Both in the Pricing step. |
| 7 | AI Copilot | `Copilot.tsx` — scaffolded, framed with the trust rule: "grounded in our data — if the evidence isn't there, it says 'I don't know'." Dashboard-first (present on every step). No fake answers. |

Feasibility step (`steps/FeasibilityStep.tsx`) reads `GET /feasibility` with honest partial/awaiting
states + source chips. Monitoring step is a light data-vintage panel with an explicit Phase-2 note —
no fabricated alerts.

---

## 2. Wired to live vs mocked

All three new contracts went live during the build and are wired + verified:

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /opportunity` (expanded `readiness`) | **LIVE** | `{overall, dimensions:{key:{score,reason,confidence}}}` adapted to the 9-dim board; 4 dims come back `score:null` → honest "data not yet available". |
| `GET /feasibility?neighborhood` | **LIVE** | Keyed dict `{regulatory_zoning, construction_engineering, operational_market, environmental, legal, financial}` each `{status, detail, sources}`; statuses map to OK / Partial / Awaiting. |
| `POST /scenario/compare` | **LIVE** | Body `{scenarios:[{label, overrides}]}` (min 2); response `{base, scenarios:[{label, result}]}`. |
| `/recommend`, `/residual-land-value`, `/scenario`, `/opportunity`, `/areas` | **LIVE** | Unchanged, still wired. |

Every path keeps a transparent local fallback (deterministic scenario/residual math, local
readiness derivation, honest feasibility empties) that auto-swaps if an endpoint is down.

---

## 3. Contract fixes made during wiring (for the record)

Built against the brief; the live shapes differed — adapted client-side in `lib/intel.ts`:

1. `/scenario/compare` requires each scenario as `{label, overrides:{…}}` (not flattened) and **≥2
   scenarios** — was returning 422 until fixed. Response uses `scenarios[].result` (recommendation
   shape, `*_price_jd_m2`), not `columns`.
2. `/opportunity.readiness` is an object `{overall, dimensions:{…}}` with dim keys
   `regulatory_readiness` / `construction_feasibility` (I'd assumed `regulatory` / `construction`) —
   `adaptReadiness()` maps them; null scores preserved.
3. `/feasibility.dimensions` is a keyed object (not array) using `detail` (not `reason`) and a
   `value` object on some dims — guarded so only primitive values display (fixed an "[object Object]"
   render). Status vocabulary includes `partial`.
4. Kept the `fixText()` UTF-8 guard on all live strings (belt-and-suspenders; backend-intel is
   cleaning the source).

---

## 4. Verification (Playwright — `tests/verify_refactor.py`)

Against the production build on `:4173` (CORS-allowed) + live API on `:8000`. **0 API console
errors** (only CARTO basemap tiles fail — network-blocked in the sandbox; they render underneath in
a real deploy). Asserted: `explore=True, evaluate=True, role_selector_present=False`, honest nulls
present. Screenshots `tests/screenshots/refactor_*`:

- `01_landing` — two entry points, no role selector
- `02_explore_opportunity` — 290-area heatmap + Step 1 of 7
- `03_decision_readiness` — live 8-dim board, Overall 51, `n/a` on the 4 pending dims + Copilot trust rule
- `04_step2_feasibility` — live feasibility (Partial / OK / Awaiting) with source chips
- `04_step3_market` … `04_step7_monitoring` — every step navigates
- `05_pricing_scenario_compare` — what-if + engine compare table (Height +13.3%, Premium +10.1%, Cost +0.1%)
- `04_step6_sales` — Executive Summary + Sales Narrative drafts
- `06_evaluate_entry_feasibility` — "Evaluate My Land" lands on Feasibility

---

## 5. Honesty guarantees kept

- Null readiness dims → "data not yet available", never zero; low-data areas carry the caveat.
- Feasibility shows Partial/Awaiting with sources — no fabricated green lights.
- Monitoring states change-alerts are Phase 2 — no fake alerts.
- Sales drafts are labelled "composed from the evidence — no facts added".
- Copilot says it will answer "I don't know" when evidence is missing.
- Context areas still show the honest "no structured pricing yet" state (no fabricated price).

Scope was held to exactly the 7 items — no features added beyond the list.
