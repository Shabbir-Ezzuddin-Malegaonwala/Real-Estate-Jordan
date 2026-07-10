# Engine Fix Report — BUG-1 (area_m2) + OBS-3 (near-duplicate comps)

**Author:** Decision-Engine agent · **Date:** 2026-07-07 · **Scope:** `app/engine/` only
**Verdict:** Both findings fixed. All suites green (engine 63, API 39, E2E 6/2-skip). No
hardcoded weights; every adjustment still carries a sourced evidence object.

---

## FIX 1 — BUG-1: `area_m2 <= 0` / non-finite no longer crashes or silently prices

### What changed
One guard at the single engine entrypoint (`pipeline.recommend`). `area_m2` is `None`
(size unknown — a valid state) OR a positive finite number; anything else (`0`, negative,
`inf`, `nan`) is corrupt input and the engine refuses to emit a confident band, returning a
well-formed **cannot-price** result with an explanatory risk factor.

- `app/engine/pipeline.py:31-37` — the guard (added `import math`).
- `app/engine/recommendation.py:288-303` — new public `unpriceable(...)` helper (honest
  zero band + one risk factor); `_empty_result` now delegates to it (no behaviour change).

```python
# pipeline.recommend, right after as_of is resolved
area = subject.area_m2
if area is not None and (not math.isfinite(area) or area <= 0):
    return recommendation.unpriceable(
        subject, as_of, "Invalid subject area",
        f"Subject area_m2={area!r} is not a positive finite number; cannot price. ...")
```

### Why "cannot-price" and not `raise` / not "coerce to size-unknown"
- Matches the codebase's existing "degrade, not crash" error style (`_empty_result`), and
  the QA xfail asserted a **finite result**, not an exception.
- Matches the QA report's own recommendation: OBS-1 "reject `area <= 0` at the engine
  boundary", OBS-2 non-finite "should fail fast, not be silently swallowed." A cannot-price
  result with a `high`-severity risk factor is that loud, honest signal.
- Raising `ValueError` would have broken two **passing** tests
  (`test_negative_area_does_not_crash`, `test_nonfinite_area_does_not_crash`) that I was
  scoped not to touch; cannot-price keeps them green (0.0 is finite, ≥ 0).
- `None` is untouched — it legitimately means "size not supplied"; the engine prices per-m²
  without a size adjustment (existing `test_none_area`, still green).
- API path unchanged: `RecommendRequest.area_m2 = Field(175, gt=0)` still 422s these before
  they reach the engine. This guard is defense-in-depth for non-API callers (batch, emit,
  notebooks, future services).

### Test
`tests/test_engine_edge_cases.py::AreaBoundaries::test_zero_area_degrades_not_crashes` —
xfail removed; now loops `{0, -50, inf, nan}` asserting finite band, `recommended == 0`, and
an explanatory area risk factor.

---

## FIX 2 — OBS-3: near-duplicate comparable collapse

### The problem, quantified
The same physical unit is cross-posted across Bayut/OpenSooq/Facebook (and relisted over
time) under different `listing_id`s. Each copy was counted independently in the comp pool,
over-weighting that price and inflating confidence. Collapsed per covered submarket (real
DB, apartment sale pool):

| Submarket | pool | unique after collapse | **collapsed** |
|-----------|-----:|----------------------:|--------------:|
| Abdoun    | 538  | 460 | **78** |
| Dabouq    | 300  | 261 | **39** |
| Sweifieh  | 683  | 569 | **114** |
| Khalda    | 772  | 585 | **187** |
| Shmeisani | 93   | 89  | **4** |

**422 duplicate rows collapsed** across the five submarkets.

### The rule (deterministic, documented, conservative)
`app/engine/comparable_analysis.py:35-83` — `collapse_near_duplicates(pool)`, called inside
`select_comparables` **before** recency/size filtering and ranking (`:110-116`).

Two same-submarket, same-type sale rows collapse to one only when **all** hold:
- **bedrooms known-and-equal** (if either is unknown → never collapse — conservative);
- **area within `DEDUP_TOLERANCE`** (config, **1%**);
- **price/m² within `DEDUP_TOLERANCE`** (1%).

Representative of each cluster = **most-complete**, then **most-recent**, then highest
`listing_id` (fully deterministic). The collapse count is surfaced in
`method_values.selection_notes` so it is explainable/traceable, e.g.
*"39 near-duplicate cross-posting(s) collapsed (same beds, area & price/m2 within 1%)"*.

### Why 1%, not the suggested ~2%
Calibrated to the actual corpus: real cross-posts are **near-EXACT** (identical bedrooms,
area and price — 313 exact groups / 548 rows in the covered submarkets). A 1% band absorbs
only rounding/formatting noise. At 2% the rule over-collapsed a genuinely distinct pair in
the sample fixtures (172 m² vs 175 m², a stale comp the time-adjustment test depends on) —
exactly the "do not over-collapse distinct units" failure the brief warned against. 1% keeps
real dedup power (422 rows) while merging nothing distinct. `config.py:26-34`.

### Tests
`tests/test_engine_edge_cases.py::NearDuplicateCollapse` (6 tests): cross-post collapses to
one; distinct price not collapsed; different bedrooms not collapsed; unknown bedrooms never
collapse; representative is the most-complete row; and an integration test that 5 cross-posted
copies of a high unit move the recommendation < 6%.

---

## Before / after (real DB, `python -m app.engine.emit_sample`)

| Submarket | min/rec/prem BEFORE | conf | comps | → | min/rec/prem AFTER | conf | comps |
|-----------|---------------------|------|------:|---|--------------------|------|------:|
| Abdoun    | 625 / 962 / 1299 | H 0.76 | 12 | → | 650 / 991 / 1333 | H 0.76 | 12 |
| Dabouq    | 585 / 875 / 1165 | M 0.65 | 11 | → | 596 / 840 / 1084 | M 0.68 | 10 |
| Sweifieh  | 534 / 821 / 1108 | M 0.69 | 12 | → | 534 / 821 / 1108 | M 0.69 | 12 |
| Khalda    | 522 / 634 / 746  | H 0.77 | 12 | → | 522 / 634 / 746  | H 0.77 | 12 |
| Shmeisani | 379 / 537 / 695  | H 0.74 | 12 | → | 332 / 511 / 690  | H 0.70 | 12 |

Reading: shifts are modest and directionally correct. **Sweifieh/Khalda are unchanged** —
their top-12 most-similar comps were already distinct, so removing duplicates elsewhere in
the pool didn't touch the selected set. **Dabouq** tightened (rec −4%, confidence 0.65→0.68,
band narrower) — de-duplicating removed inflated dispersion. **Shmeisani** eased (rec −5%,
0.74→0.70). All bands stay finite and ordered (`min ≤ rec ≤ premium`); every adjustment
still carries a sourced evidence object (verified: 0 empty/`unknown` source URLs).

---

## Invariants re-confirmed
- **No hardcoded weights** — `NoHardcodedWeights` (source scan of every engine module +
  behavioural) still green. `DEDUP_TOLERANCE` is a *selection* knob (like `SIZE_BAND_TOLERANCE`),
  not a price weight.
- **Evidence integrity** — `HardInvariants` green; emitted outputs carry non-empty external
  source URLs on every evidence object.
- **Determinism** — collapse is seeded in sorted order with a deterministic representative pick.

## Files changed
- `app/engine/pipeline.py` — area guard (+`import math`).
- `app/engine/recommendation.py` — `unpriceable(...)` helper; `_empty_result` delegates to it.
- `app/engine/comparable_analysis.py` — `collapse_near_duplicates(...)` + helpers; wired into
  `select_comparables`.
- `app/engine/config.py` — `DEDUP_TOLERANCE = 0.01` (documented).
- `tests/test_engine_edge_cases.py` — flipped BUG-1 xfail; new `NearDuplicateCollapse` class.

## Test results
- Engine edge + baseline: **63 passed** (was 56 passed + 1 xfail; +6 dedup tests, xfail eliminated).
- API edge: **39 passed**. E2E frontend: **6 passed, 2 skipped** (environmental, unchanged).
- Single entrypoint: `python tests/run_all.py` → all suites OK.
