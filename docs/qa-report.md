# QA Report — Jordan Real Estate Intelligence Platform

**Author:** QA / Test engineer (agent)  ·  **Date:** 2026-07-07  ·  **Deadline gate:** 2026-07-09
**Scope:** adversarial, re-runnable edge-case suite across engine + API + frontend.
**Verdict:** Ship-ready for the API-guarded path. **1 real crash bug** (engine-only, `area_m2=0`),
plus 3 lower-severity validation / data-quality observations. No invariant violations found in a
600-subject fuzz of the live database.

---

## 1. Results at a glance

| Suite | File | Result | Server needed |
|-------|------|--------|---------------|
| Engine edge cases | `tests/test_engine_edge_cases.py` | **35 passed, 1 xfailed** | none |
| Engine baseline (pre-existing) | `app/engine/test_pipeline.py` | **21 passed** | none |
| API edge cases | `tests/test_api_edge_cases.py` | **39 passed** | API @ :8000 |
| E2E frontend | `tests/e2e_frontend.py` | **6 passed, 2 skipped, 0 failed** (0 uncaught JS errors) | web @ :5173 + API |

**Totals:** 101 passed · 1 xfail (documents BUG-1) · 2 E2E skips (both environmental/by-design) · 0 unexpected failures.

The `xfail` is intentional: it encodes the desired "degrade, not crash" behavior for `area_m2=0`.
It stays green today and flips to an **unexpected pass** the moment the engine is hardened — the
signal to delete the marker.

### Re-run everything

```bash
# from repo root C:\Rubicon\Real-Estate-Jordan
python tests/run_all.py
```

### Re-run a single suite

```bash
python -m pytest tests/test_engine_edge_cases.py -v            # no server
python -m uvicorn app.api.main:app --port 8000                # then, in another shell:
python -m pytest tests/test_api_edge_cases.py -v
cd app/web && npm run dev                                      # serves :5173, then:
pip install playwright && python -m playwright install chromium
python tests/e2e_frontend.py
```

Overrides: `JORDAN_API_URL` (default `http://127.0.0.1:8000`), `JORDAN_WEB_URL`
(default `http://localhost:5173`).

**Environment note:** the API was **not running** when I started (`/health` → connection refused).
I launched it myself (`uvicorn app.api.main:app --host 0.0.0.0 --port 8000`, DB
`db/jordan_re.sqlite`, 854 listings, 5 neighborhoods) to run the API + E2E suites. The frontend dev
server on :5173 was already up. I changed **no product code**.

---

## 2. Bugs found

### BUG-1 — `area_m2=0` crashes the engine (`ZeroDivisionError`)  ·  Severity: **Medium**

The engine is documented to "degrade, not crash." A zero subject area divides by zero instead.

- **Location:** `app/engine/comparable_analysis.py:91` (`_size_similarity`:
  `rel = abs(l.area_m2 - subject.area_m2) / subject.area_m2`). The same file's `_size_ok` (line 44)
  divides by `subject.area_m2` too.
- **Repro (engine):**
  ```python
  from datetime import date
  from app.engine.fixtures import load_sample_bundle
  from app.engine.models import Subject
  from app.engine.pipeline import recommend
  recommend(Subject(neighborhood="Abdoun", property_type="apartment", area_m2=0),
            load_sample_bundle(), date(2026, 7, 7))
  # -> ZeroDivisionError: float division by zero
  ```
- **Reachability:** **Not** reachable via the HTTP API today — `RecommendRequest.area_m2` is
  `Field(175, gt=0)`, so the API returns `422` for `area_m2=0` (verified). The crash bites any
  **non-API caller**: batch jobs, notebooks, a future service, or the offline precompute emitter.
  The `gt=0` guard is therefore load-bearing and must never be relaxed without first hardening the engine.
- **Suggested fix (for the tech lead, not applied):** treat `area_m2 in (None, 0)` uniformly as
  "size unknown" in `_size_similarity` / `_size_ok` (return `None` / `True` respectively when
  `subject.area_m2` is falsy), mirroring the existing `is None` guard.
- **Test:** `tests/test_engine_edge_cases.py::AreaBoundaries::test_zero_area_degrades_not_crashes`
  (`@unittest.expectedFailure`).

---

## 3. Lower-severity observations (validation & data-quality gaps)

These are not crashes; they are silent-acceptance / methodology gaps worth a decision. All are
covered by tests that currently **pass** (they assert "no crash / stays finite"); the concern is
logged here rather than red-gating the push.

### OBS-1 — Negative subject area is silently priced  ·  Severity: **Low**

`recommend(area_m2=-50)` returns a normal **M-confidence** band (~1205 JD/m²). A physically
impossible input yields a confident answer. The API blocks it (`gt=0` → 422), so this is an
engine-contract gap only. Recommend rejecting/normalizing `area <= 0` at the engine boundary.

### OBS-2 — Non-finite subject area (`inf` / `nan`) is silently accepted  ·  Severity: **Low**

`area_m2=float('nan')` and `float('inf')` both return a finite normal band (identical to a huge-area
case — the value is effectively ignored). NaN/Inf reaching a pricing routine is a data-corruption
smell that should fail fast, not be silently swallowed. (Not reachable via JSON API — JSON can't
encode `Infinity`/`NaN`.) Tests: `AreaBoundaries::test_nonfinite_area_does_not_crash`.

### OBS-3 — No near-duplicate comparable de-duplication  ·  Severity: **Low (data-quality/methodology)**

The engine counts each row in the comp pool independently. Exact `listing_id` duplicates are blocked
by the DB primary key, **but** the same physical unit cross-posted across Bayut / OpenSooq / Facebook
(different IDs, same price/area/location) is counted multiple times, over-weighting it and inflating
confidence. Probe: injecting 5 copies of one high comp moved the recommendation **+17%** (891 → 1044
JD/m²) and shifted confidence (0.79 → 0.62). CMA best practice treats each arms-length property once
(see research §5). A fuzzy dedupe on `(neighborhood, property_type, round(price), round(area), lat, lng)`
before weighting would close this. This is a real risk for portal data, which is heavily cross-syndicated.

### OBS-4 — Empty submarket/type returns `200` with an all-zero band  ·  Severity: **Info (by design)**

For a submarket+type with no plausible comps, `/recommend` returns `200` with
`recommended_price_jd_m2 = 0` and an honest "No comparable listings" risk (the engine's
`_empty_result`). The frontend would render a `0 JD/m²` band. This is honest, not wrong — noting it
so the frontend renders a "cannot price" state rather than a literal zero. **Note:** the live DB
actually carries villa/land/commercial rows, so all 5×4 submarket/type combinations priced in the
fuzz; this only manifests for a genuinely empty combination.

---

## 4. What was verified to be solid (balance)

- **Real-DB fuzz:** 600 random valid subjects (5 submarkets × 4 property types × varied area/floor/
  view/finish/age) → **0 crashes, 0 invariant violations**; band always finite & ordered
  (`min ≤ rec ≤ premium`), confidence `∈ [0,1]`, interval strictly brackets the point estimate. A
  deterministic 300-subject version is baked into the suite (`RealDbInvariantFuzz`).
- **Outlier robustness:** 0-price, ~0-price, whole-building (~133 JD/m²), and negative-price rows are
  filtered by the plausibility floor + log-space MAD; a single extreme-high comp (9000 JD/m²) moves
  the recommendation **< 20%**.
- **Stale CBJ index (ending 2021-Q3, run in 2026):** time-adjustment is correctly **disabled** (no
  backward extrapolation) and surfaced as an "index not current" caveat — exactly the honest-data
  behavior. A current index correctly time-adjusts >12-month-old comps and evidences it against the CBJ series.
- **No hardcoded pricing weights:** source scan across **every** engine module finds no
  attribute→fraction map or `_MULT` table; and premiums provably **change with the data** (behavioral
  test), so they are genuinely derived, not constants.
- **Evidence integrity:** every applied comp adjustment carries a structured evidence object;
  attribute-premium evidence cites an **external** portal URL; no evidence source URL is empty or the
  `"unknown"` placeholder.
- **API hardening:** every malformed / out-of-range / bad-enum / missing-field input → `422` with a
  `detail` (never `500`); malformed JSON → `422`; a SQL-injection-style neighborhood → `422` and the
  server stays healthy afterward; unknown routes → `404`; `GET /recommend` → `405`; unknown extra
  fields ignored; **20 concurrent POSTs all `200`**; CORS `allow-origin` present for
  `http://localhost:5173` on both preflight and actual POST.
- **Frontend E2E:** page loads with **0 uncaught JS exceptions**; all 5 neighborhoods selectable and
  produce **different** prices (Abdoun 1321, Dabouq 1211, Sweifieh 1248, Khalda 808, Shmeisani 907);
  editing size/finish/view **recomputes live** (1448 → 1342); theme toggle flips `<html data-theme>`;
  Help/About drawer opens and closes. Screenshots in `tests/screenshots/`.

---

## 5. E2E steps not run (honest disclosure)

| Step | Status | Why |
|------|--------|-----|
| Outside-coverage "no data" toast | **SKIP** | Could not deterministically land an off-coverage click on the MapLibre canvas headlessly (zoomed out + tried 3 candidate points). Wiring is verified by code inspection: `App.tsx` `onOutside` → `Toast` with the exact copy *"No data for this location — select a covered submarket (…)"* and `MapView` fires it when a click hits no `nbhd-fill` feature. Re-runnable in a headed browser. |
| Offline fallback badge | **SKIP** | Only meaningful with the API down; the API was up (Live-API badge asserted instead). To exercise: stop :8000 and reload — the badge should read "Offline · precomputed" and field edits stop changing numbers (offline path returns precomputed per-neighborhood results by design). |

The frontend was stable during the run; all non-skipped assertions executed. If the frontend is
updated by another agent, re-run `python tests/e2e_frontend.py` — it is self-contained and idempotent.

---

## 6. Edge cases researched (with sources)

**(a) Real-estate valuation / CMA pricing** — informed the thin-market, outlier, arms-length,
property-comparability, and stale-comp tests:
- Thin markets / few comps lose precision (rural, slow, rezoned, unique) → widen radius & time window.
- Exclude non-arms-length (short sales, foreclosure, inter-family) and ultra-luxury/distressed outliers.
- Price/m² unreliable when comparing dissimilar property types → don't mix types.
- Data-quality: not all sales syndicate cleanly → **duplicate / missing** records skew a CMA (→ OBS-3).

Sources: [HomeLight](https://www.homelight.com/blog/how-do-i-get-a-comparative-market-analysis/) ·
[ListWithClever](https://listwithclever.com/real-estate-blog/comparative-market-analysis-real-estate/) ·
[FasterCapital](https://fastercapital.com/topics/comparative-market-analysis-(cma).html/1) ·
[Rocket Mortgage](https://www.rocketmortgage.com/learn/comparative-market-analysis) ·
[EffectiveAgents](https://www.effectiveagents.com/resources/how-to-read-a-comparative-market-analysis-cma-consumers-guide) ·
[Freedonia](https://www.freedoniagroup.com/blog/what-is-comparative-market-analysis) ·
[Chase](https://www.chase.com/personal/mortgage/education/buying-a-home/comparative-market-analysis-guide) ·
[Mass.gov](https://www.mass.gov/info-details/re62rc25-comparative-market-analysis-cma) ·
[Zillow](https://www.zillow.com/learn/comparative-market-analysis/)

**(b) JSON REST API + map/dashboard web app** — informed the malformed-JSON, boundary-value,
bad-enum, missing-field, injection, concurrency/race, CORS, and method-not-allowed tests:
- Malformed JSON (missing brackets, trailing commas, special chars) is a top cause of API errors.
- Test valid/invalid/missing/edge input; date formats, null handling, number precision, nesting.
- Stateless APIs must handle interleaved concurrent requests with no race conditions.
- CORS must work across origins; enforce origin validation + server-side safeguards.
- Missing required fields and malformed bodies need **explicit** tests — edge cases are ~40% of prod incidents.

Sources: [Site24x7](https://www.site24x7.com/learn/rest-api-errors-troubleshooting-guide.html) ·
[StackHawk](https://www.stackhawk.com/blog/what-is-rest-api-testing-tools-and-best-practices-for-success/) ·
[APIPark](https://apipark.com/techblog/en/how-to-qa-test-an-api-a-complete-guide/) ·
[JSONtoTable](https://jsontotable.org/blog/web-api-testing/rest-api-testing-best-practices) ·
[DreamFactory (CORS)](https://blog.dreamfactory.com/how-to-debug-cors-errors-in-api-testing) ·
[ACCELQ](https://www.accelq.com/blog/common-api-testing-mistakes/) ·
[DEV: 45 ways to break an API](https://dev.to/zvone187/45-ways-to-break-an-api-server-negative-tests-with-examples-4ok3) ·
[Medium: REST error scenarios](https://medium.com/@rabiyireh/common-error-scenarios-to-test-in-restapi-eaccea5ce829)

---

## 7. Coverage map (brief → tests)

| Brief requirement | Test(s) |
|---|---|
| thin market (few/zero comps) | `ThinAndEmptyMarket` (zero, single, two-comp) |
| all-attributes-unknown | `UnknownAttributes::test_all_attributes_unknown_prices_and_flags` |
| extreme area (1, 100000) / negative / zero | `AreaBoundaries::*` (zero = **BUG-1** xfail) |
| single comparable | `ThinAndEmptyMarket::test_single_comparable_prices_but_flags_thin` |
| outlier-heavy (0-price, whole-building) | `OutlierRobustness::*` |
| stale-comp time-adj, CBJ ending 2021-Q3 | `TimeAdjustment::test_stale_index_2021q3_disables_time_adjustment` |
| empty cost/projects/evidence → degrade | `EmptyAuxTables::*` |
| confidence widens in thin markets | `ThinAndEmptyMarket::test_confidence_interval_widens_as_market_thins` |
| NO hardcoded pricing weights | `NoHardcodedWeights::*` (source scan + behavioral) |
| every adjustment has evidence w/ real source_url | `HardInvariants::test_every_*` |
| API 422s (uncovered/negative/bad-enum/missing/empty/malformed) | `Validation422::*` |
| response schema == db-contract §4 | `ResponseSchema::*` |
| prices finite positive, min≤rec≤premium | `ResponseSchema::test_prices_finite_positive_and_ordered` |
| concurrent POSTs, CORS for :5173 | `CorsAndConcurrency::*` |
| E2E: load, 5 neighborhoods, recompute, theme, help, no-data, offline | `tests/e2e_frontend.py` (2 steps skipped, §5) |

---

**Bottom line:** the platform is robust across the entire API-reachable input space (600-subject fuzz
clean). Fix **BUG-1** (or keep the `gt=0` API guard as the sole barrier and document it), and decide
on **OBS-3** (cross-portal duplicate dedup) before scaling the listing corpus. Everything else is
green and re-runnable via `python tests/run_all.py`.
