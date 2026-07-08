# Backend Intelligence Layer — Report & Endpoint Contracts

**Author:** backend-intel (agent) · **Date:** 2026-07-08 · **Deadline gate:** 2026-07-09
**Scope:** turn the pricing engine into a DECISION engine — five additive capabilities, each an
engine function + a clean-JSON API endpoint. Additive only; the 100+ baseline tests still pass;
no hardcoded pricing weights; every number sourced/explainable; degrades gracefully.

**Verification:** `python -m pytest` — **engine 91 passed** (incl. `NoHardcodedWeights` scan over
the three new modules + `RealDbInvariantFuzz`), **API 57 passed** (against the live 52,647-row
server). New suites: `tests/test_engine_intel.py`, `tests/test_intel_endpoints.py` (wired into
`tests/run_all.py`). The one non-green in `run_all` is the Playwright E2E, which drives the SPA the
frontend team is mid-rebuild on (selector `aside[aria-label="Analysis panel"]`) — not a backend
regression; `/recommend` is a strict superset of the prior contract.

**Files (owned):** `app/engine/{confidence,recommendation,models,config}.py` (edits),
`app/engine/{builder,scenario,opportunity}.py` (new), `app/api/main.py` (5 endpoints),
`tests/test_engine_intel.py`, `tests/test_intel_endpoints.py`, this report.

---

## 1. Decomposed confidence — extends `POST /recommend`

The overall confidence is unchanged; `confidence.components` now decomposes it into five
product-facing signals, each `0-100 + reason`. A signal that cannot be computed is `null` with a
reason — never fabricated. Mapping to internal reliability sub-signals:

| Component | Source signal | Null when |
|---|---|---|
| `data_coverage` | comp count vs full-confidence threshold | — |
| `comp_quality` | adjusted-comp dispersion (tighter = better) | — |
| `gov_evidence` | CBJ price-index freshness + cost-benchmark presence | no index AND no cost bench |
| `future_signals` | development score (evidence_items) / saturation 3.0 | no matching evidence collected |
| `market_freshness` | mean comparable age vs ideal recency | comps carry no listing dates |

Also: `POST /recommend` accepts **`apply_height_view_premium: bool`** (see §4). Response
`confidence` block (Khalda example):

```json
"confidence": {
  "label": "H", "numeric": 0.744, "interval_jd_m2": [473.5, 913.8],
  "components": {
    "data_coverage":    {"score": 100, "reason": "12 comparable(s) after outlier filtering; full weight at 8+"},
    "comp_quality":     {"score": 26,  "reason": "adjusted comparables vary 26% (tighter = higher quality)"},
    "gov_evidence":     {"score": 50,  "reason": "CBJ price index present but lagged; no construction-cost floor"},
    "future_signals":   {"score": 16,  "reason": "development score 0.48 from collected infrastructure/policy evidence (saturates at 3.0)"},
    "market_freshness": {"score": 98,  "reason": "average comparable age ~0 months (ideal ≤12)"}
  }
}
```

Every other `/recommend` field is unchanged.

---

## 2. `POST /scenario` — what-if simulation

Re-runs the engine under builder overrides and reports the delta. Engine-native levers change the
Subject; the three non-Subject levers transform the **evidence** in documented ways (never a
hand-set price):

- `construction_cost_delta_pct` → scales `cost_benchmarks` (flows through the cost-approach floor → min-safe).
- `metro_delay_years` → pushes out infrastructure `expected_year` → lower future-signal timeline certainty.
- `launch_delay_months` → advances `as_of` → comps age (recency falls; stale comps may get CBJ time-adjusted).

**Request** (base subject = the `/recommend` fields; overrides nested):

```json
{
  "neighborhood": "Abdoun", "area_m2": 175, "finish_quality": "standard",
  "floor_level": 3, "total_floors": 20,
  "overrides": {
    "target_floor": 16, "floors": 20, "finish_quality": "luxury",
    "parking": "covered", "view": "city", "bedrooms": 3, "building_age_years": 0,
    "construction_cost_delta_pct": 15, "metro_delay_years": 4,
    "launch_delay_months": 0, "apply_height_view_premium": true
  }
}
```

**Response:** `{ base, scenario, deltas, explanation, levers_applied }` where `base`/`scenario` are
full `RecommendationResult` objects.

```json
"deltas": {
  "recommended_pct": 10.26, "min_safe_pct": -0.65, "premium_pct": 11.0,
  "confidence_change": -0.004, "future_signals_change": -2
},
"levers_applied": ["finish_quality → luxury", "target_floor → 16",
  "construction cost +15% → cost-approach floor",
  "metro/infra delayed 4y → weaker future-signal timeline",
  "height/city-view premium (builder assumption) +11.0%"],
"explanation": "Applied: … Net effect: +10.3% recommended price, confidence -0.004. Every lever flows through the engine's own evidence — no price was set by hand."
```

Note: `future_signals_change` exists because future signals justify **positioning**, not a point
premium — so `metro_delay_years` moves that component (16→14…), not the price. Empty `overrides`
→ zero deltas. Uncovered submarket → `422 {detail}`; out-of-range lever → `422 {detail}`.

---

## 3. `POST /residual-land-value` — builder land price ceiling

Straight from the client Pricing PDF: `GDV − construction − fees − finance − profit = residual`.
Fees on construction, finance on (construction + fees), profit on GDV — each basis stated.

**Request** (only `neighborhood` + `buildable_area_m2` required):

```json
{
  "neighborhood": "Abdoun", "buildable_area_m2": 1200,
  "property_type": "apartment", "finish_quality": "high",
  "gdv_per_m2": 1100, "construction_cost_per_m2": 520,
  "finance_pct": 0.06, "professional_fees_pct": 0.05, "developer_profit_pct": 0.20
}
```

- `gdv_per_m2` omitted → defaults to the **engine recommended price/m²** (sourced), `gdv_per_m2_defaulted: true`.
- `construction_cost_per_m2` omitted → **median of available `cost_benchmarks` midpoints** (sourced); if none exist → `422` (never invented).
- The three pct are documented builder assumptions with defaults (6% / 5% / 20%), overridable.

**Response:**

```json
{
  "neighborhood": "Abdoun", "buildable_area_m2": 1200.0,
  "inputs": { "gdv_per_m2": 1100.0, "construction_cost_per_m2": 520.0,
              "finance_pct": 0.06, "professional_fees_pct": 0.05, "developer_profit_pct": 0.2,
              "gdv_per_m2_defaulted": false, "construction_cost_defaulted": false },
  "breakdown": [
    {"label": "Gross development value (GDV)", "value_jd": 1320000.0, "basis": "1100 JD/m² × 1200 m²"},
    {"label": "less Construction cost",        "value_jd": -624000.0, "basis": "520 JD/m² × 1200 m²"},
    {"label": "less Professional fees",        "value_jd": -31200.0,  "basis": "5% of construction (assumption)"},
    {"label": "less Finance cost",             "value_jd": -39312.0,  "basis": "6% of construction + fees (assumption)"},
    {"label": "less Developer profit",         "value_jd": -264000.0, "basis": "20% of GDV (assumption)"}
  ],
  "gdv_total_jd": 1320000.0,
  "residual_land_value_total_jd": 361488.0,
  "residual_land_value_per_m2_jd": 301.2,
  "viable": true,
  "explanation": "Max supportable land price ≈ 361,488 JD (301 JD per buildable m²): GDV 1,320,000 − construction 624,000 − fees 31,200 − finance 39,312 − profit 264,000.",
  "sources": [ /* engine + cost_benchmarks when defaulted */ ],
  "assumptions": [ "Residual method … client PDF.", "finance/fees/profit are builder assumptions …" ]
}
```

Negative residual → `viable: false` + an explanation (never crashes). The `breakdown` line values
sum exactly to `residual_land_value_total_jd` (GDV positive, deductions negative).

> Data note: with defaults, Abdoun's noisy `cost_benchmarks` (mixed land/sale rows) yields a
> construction cost (~898) close to GDV, so the default run flags `viable:false` honestly. Builders
> should pass their real `construction_cost_per_m2`.

---

## 4. Height / city-view premium — builder ASSUMPTION (explicit, not derived)

Portals do not publish view, so the engine cannot derive it (surfaced as a data caveat). Instead a
**configurable ramp**: 0% at/below floor 5, linear to a **15% ceiling** at the top floor (or a
reference top of `threshold + 10` when `total_floors` is unknown). Exposed via
`apply_height_view_premium: true` on **`/recommend`** and in **`/scenario`** overrides.

When applied it uplifts `recommended`/`premium` and the confidence interval (min-safe floor
untouched) and appends an evidence row with the parameter visible:

```json
{
  "factor": "Builder assumption: height / city-view premium",
  "adjustment": "+11.5%",
  "confidence": "Low",
  "method": "configurable ramp — 0% ≤ floor 5, linear to 15% ceiling at the top floor",
  "datasets": ["builder assumption (not derived)"],
  "sources": [{"name": "Builder-configurable assumption (view not published by portals)", "url": "internal://builder-assumption/height-view-premium", "capture_date": "assumption"}],
  "category": "current_state",
  "explanation": "Builder height/city-view premium +11.5%: floor 18 is 76% of the way from threshold 5 to top floor 22, ramped linearly to the assumed 15% ceiling. BUILDER ASSUMPTION."
}
```

`method_values.height_view_premium` echoes `{fraction, floor_level, total_floors, assumption:{max_premium_pct, floor_threshold, reference_span_floors, basis}}`.

---

## 5. `GET /opportunity` + `GET /areas`

### `GET /opportunity` — "where should I build" heatmap feed

Per covered area: `score 0-100` + five components, each `{score|null, reason}`, blended with
**documented, exposed, tunable** weights (v1 heuristic). A null component is dropped and its
weight redistributed (`weights_used` shows the applied weights). Scores are min-max **relative to
the covered set** (except `future_signals`, absolute to saturation).

| Component | Derived from |
|---|---|
| `price_level` | median sale price/m² (relative standing) |
| `price_growth` | recent (≤12mo) vs older (12–36mo) median sale price/m²; null if < 8 dated sales each side |
| `demand_density` | population density + night-light (`neighborhood_geocontext`) |
| `supply_pressure` | active listing + competing-project inventory, **inverted** (low pressure scores high) |
| `future_signals` | development score (`evidence_items`) / saturation 3.0 |

**Response:**

```json
{
  "version": "v1-heuristic",
  "note": "Composite = documented, tunable weights over five derived components. A null component is dropped and its weight redistributed. Scores are relative to the covered set (min-max), for a map heatmap.",
  "weights": {"price_level":0.25,"price_growth":0.2,"demand_density":0.25,"supply_pressure":0.15,"future_signals":0.15},
  "as_of": "2026-07-08",
  "areas": [
    {
      "area": "Shmeisani", "score": 67.4,
      "components": {
        "price_level":     {"score": 20,  "reason": "median sale ~852 JD/m² (relative to covered set)"},
        "price_growth":    {"score": 100, "reason": "recent vs 12–36mo median +15.8%"},
        "demand_density":  {"score": 100, "reason": "pop density ~42,322/km², night-light ~118 (activity proxy)"},
        "supply_pressure": {"score": 100, "reason": "active supply proxy 664 (listings + projects); low pressure scores high"},
        "future_signals":  {"score": 16,  "reason": "development score 0.48 (saturates at 3.0)"}
      },
      "weights_used": {"price_level":0.25,"price_growth":0.2,"demand_density":0.25,"supply_pressure":0.15,"future_signals":0.15},
      "centroid_lat": 31.97348, "centroid_lng": 35.896883
    }
    /* … one per covered area, ranked high→low … */
  ]
}
```

Current ranking (live DB): Shmeisani 67.4, Abdoun 57.2, Dabouq 43.1, Sweifieh 36.8, Khalda 15.3.
Structured for more areas — extend the covered set (districts table) and it scales.

### `GET /areas` — neighborhood catalogue (search / dropdown)

Every neighborhood we hold listings for, `covered` (supported product submarket with a centroid)
vs context, sorted covered-first then by volume. `unknown` excluded.

```json
{
  "covered_count": 5, "total_count": 958,
  "areas": [
    {"name": "Abdoun", "listing_count": 4391, "sale_listing_count": 1538, "covered": true,  "centroid_lat": 31.948833, "centroid_lng": 35.89266},
    {"name": "Shafa Badran", "listing_count": 1431, "sale_listing_count": 1276, "covered": false, "centroid_lat": null, "centroid_lng": null}
  ]
}
```

---

## 6. Documented assumptions & knobs (all surfaced in responses, none a derived price)

- `config.FUTURE_SIGNAL_SATURATION = 3.0` — dev-score → 0-100 scaling (reliability, not price).
- `builder.HEIGHT_VIEW_PREMIUM_MAX = 0.15`, `HEIGHT_VIEW_FLOOR_THRESHOLD = 5`, `HEIGHT_VIEW_REFERENCE_SPAN = 10` — builder assumption, overridable per request, echoed in the evidence.
- `builder.{FINANCE,PROFESSIONAL_FEES,DEVELOPER_PROFIT}_PCT_DEFAULT = 0.06 / 0.05 / 0.20` — residual defaults, overridable.
- `opportunity.OPPORTUNITY_WEIGHTS` — v1 heuristic composite weights, exposed in every response.

The HARD RULE stands: **no attribute→fraction pricing map** exists in any engine module — the
`NoHardcodedWeights` scan runs over `builder.py`, `scenario.py`, `opportunity.py` and passes.

---

## 7. Errors & graceful degradation

- Uncovered submarket → `422 {detail: "No data for …; covered: […]"}` on `/scenario`, `/residual-land-value`.
- Invalid body (negative area, out-of-range lever, missing required) → `422 {detail}` (Pydantic), never `500`.
- Missing inputs the engine can't safely default (no cost benchmark, unpriceable submarket for GDV) → `422 {detail}` asking for the value explicitly — never invented.
- Null/uncomputable component → `null` + reason, weight redistributed; scores stay finite/ordered/bounded.
