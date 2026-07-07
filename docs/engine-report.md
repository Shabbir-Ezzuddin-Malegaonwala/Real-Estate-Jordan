# Decision Engine — Architecture & Contract

**Owner:** Pricing/Decision Engine Engineer · **Status:** v1 complete, tests green (16/16)
**Package:** `app/engine/` · **Entrypoint:** `app.engine.recommend(subject, data_bundle) -> RecommendationResult`
**Deps:** Python 3.13 standard library only (no numpy/pandas — small-data, runs anywhere).

The engine turns collected **evidence** into an evidence-backed launch-price band. It embodies
the client's methodology PDF (sales-comparison adjustment grid + cost-approach floor +
income-approach ceiling + reconciliation + confidence-as-a-range) and MASTER-PLAN §2d/§2d-2.
**All business logic lives here** — never in the frontend or the database.

---

## 1. Pipeline

```
Sources → Collection → Database → (DataBundle) → Comparable Analysis → Adjustment
        → Evidence → Confidence → Recommendation → RecommendationResult (JSON)
```

`pipeline.recommend()` is the only entrypoint. It never touches the DB; a caller loads the
relevant rows into a `DataBundle` (see `data.py`) — from fixtures today, from a DB export
tomorrow. This is the wait-free contract: the engine is built against the schema, not a live DB.

## 2. The five sub-engines

| # | Module | Responsibility | Key output |
|---|--------|----------------|-----------|
| 1 | `comparable_analysis.py` | Select same-submarket/type sale comps; relax size band when thin; rank by similarity | ranked comps + selection notes |
| 2 | `adjustment.py` | **Derive** attribute premiums from the pool; time-adjust stale comps; normalise each comp to the subject | `ComparableRecord` per comp + `DerivedPremium` records |
| 3 | `evidence.py` | Wrap every applied lever + context factor as a structured evidence object | `EvidenceObject[]` |
| 4 | `confidence.py` | Score reliability (density, dispersion, recency, method-agreement, source quality); produce a range | `ConfidenceResult` (H/M/L + numeric + interval) |
| 5 | `recommendation.py` | Reconcile comparison value + cost floor + income ceiling → min/recommended/premium + narrative + risks + scenarios | `RecommendationResult` |

Supporting: `models.py` (typed records + frozen-schema parsing), `data.py` (`DataBundle` loaders),
`stats.py` (pure-stdlib median / weighted mean+std / OLS slope / haversine / quarter), `config.py`
(methodology knobs and documented assumptions — **no attribute premiums**).

## 3. How premiums are derived — proof nothing is hardcoded

**HARD RULE (MASTER-PLAN §2d-2): there is not one hardcoded attribute premium in the engine.**

- **Categorical** (view, parking, elevator, finish): paired **median differential** across the
  comp pool. Each non-baseline level's median price/m² is compared to the pool's modal-baseline
  median; the fraction is the derived premium. Baseline chosen from the data, not assumed.
- **Continuous** (floor, building age, size/m²): **OLS slope** of price/m² against the attribute,
  fitted on values **residualised by finish class** — a cheap partial control so a floor/age/size
  slope reflects the attribute itself, not its correlation with finishing spec. Expressed as a
  fraction of the pool-median price/m² per unit.
- **Time**: `Adjusted = Original × currentIndex / indexAtSale` using the CBJ residential index.
  The magnitude comes entirely from CBJ data; the formula is the client PDF's, not a weight.

Every premium is emitted as a `DerivedPremium` carrying `{factor, derived_premium, method,
source, confidence, sample_size, computed_date}` and is recomputed every run. These map directly
to the `derived_premiums` table in `db/schema.sql`.

**Adjustments are capped and additive** (appraisal-grid convention), per the PDF warning that
"large adjustments reduce reliability": each factor is bounded, the net per comp is bounded
(±40%), and a comp needing a large net adjustment is down-weighted as low-reliability. This
prevents the compounding blow-ups that univariate premiums otherwise cause on correlated data.

Two guardrails enforce the rule automatically in `test_pipeline.py`:
- **runtime:** every derived premium must have `sample_size > 0` and a `method` naming a data
  technique ("differential" or "slope"), never "hardcoded".
- **source scan:** `adjustment.py`, `recommendation.py`, `evidence.py` are scanned for any
  attribute→fraction map (e.g. `{"city": 1.08}`) or DGP multiplier table — none may exist. Those
  tables live **only** in the fixture generator, which is test data, not engine logic.

### Known limitation (honest, documented)
Univariate paired differentials are **confounded** on correlated attributes (e.g. panoramic-view
units are also high-floor/luxury), so raw view/finish premiums read high and are flagged **Low**
confidence. True de-confounding is a **multivariate hedonic model — explicitly Phase 2** in both
the client PDF (needs 300–500 transactions) and the MASTER-PLAN. v1 keeps adjustments modest via
caps + reconciliation weighting and surfaces the uncertainty rather than hiding it.

## 4. Reconciliation (the three approaches)

- **Sales comparison** (anchor): reconciliation-weighted mean of the normalised comps. Weight is
  **derived from each comp's own adjustment footprint** — fewer/smaller adjustments ⇒ more weight
  (PDF rule), times a recency factor. Then the documented **ask-to-transaction gap** (client PDF,
  5–15%, applied at its midpoint) converts asking-level to transaction-level.
- **Cost floor**: replacement construction cost for the subject's finish class (new-build
  depreciation ≈ 0), from `cost_benchmarks`. A rational buyer won't pay below rebuild cost → sets
  `min_safe`.
- **Income ceiling**: `annual local rent/m² ÷ required gross yield`, where the required yield is
  **derived** from citywide rents vs sales (falls back to a documented yield only if no citywide
  data). Above this, investment buyers stop clearing.
- **Outputs**: `min_safe = max(cost floor, lower confidence band)`, `recommended = reconciled
  comparison value`, `premium = upper confidence band` (raised toward the income ceiling if
  investors support it; future signals justify positioning *here*, never a fabricated number
  above the evidenced range).

Convergence of the three raises confidence; divergence becomes a surfaced **risk** — exactly the
PDF's integrated framework.

## 5. Confidence as a first-class range

`confidence.py` scores five inputs (data density, dispersion, recency, cross-method agreement,
source quality) into a numeric 0–1 → H/M/L. The **interval** half-width is data-driven (weighted
comp dispersion) widened as confidence falls, bounded 4–35%. **Thin markets get an uncertainty
floor** so a handful of near-identical comps cannot produce false precision (verified by test).

## 6. JSON contract (`RecommendationResult`)

Emitted to `app/engine/sample_output.json` — the **Frontend Engineer's data contract**. Keys map
onto the `recommendations` table in `db/schema.sql`:

| JSON key | DB column |
|----------|-----------|
| `min_safe_price_jd_m2` / `recommended_price_jd_m2` / `premium_price_jd_m2` | same |
| `confidence_label` / `confidence_numeric` | same |
| `narrative` | `narrative` |
| `evidence_objects` | `evidence_objects_json` |
| `comparables` | `comparables_json` |
| `risk_factors` | `risk_factors_json` |
| `alternative_scenarios` | `alternative_scenarios_json` |
| `neighborhood` / `property_type` / `location_id` / `computed_date` | same |
| `confidence_interval_jd_m2`, `method_values` | extra engine context (interval, derived premiums, confidence components, dev score, selection notes) |

Each **evidence object** is `{factor, adjustment, confidence, method, datasets[], sources[{name,
url, capture_date}], category(current_state|future_signal), explanation}` (MASTER-PLAN §2d). The
frontend renders these as the adjustment-grid waterfall with source chips; `category` splits the
Current-State and Future-Signals panels.

## 6b. Real database integration (2026-07-07 update)

The engine now runs on the live `db/jordan_re.sqlite` (854 listings across the 5 submarkets).

**What changed in `data.py`:** added `load_bundle_from_sqlite(db_path, as_of)` — reads `listings`,
`cost_benchmarks`, `evidence_items`, `projects`, and `macro_series` via stdlib `sqlite3` into a
`DataBundle`. The long CBJ indicator name `Real estate price index - Buildings - Apartment` is
mapped to the engine's canonical `cbj_repi_apartment` key (residential as fallback). Missing/empty
tables degrade to empty lists. Reconciled against `docs/db-contract.md`; the emitted JSON now
matches §4 exactly (nested `confidence`, `risk_factors` as `{factor,severity,detail}` objects,
scenarios as `{name,recommended_price_jd_m2,rationale}`, comps expose `price_per_m2` +
`adjustments_applied`).

**Real-data robustness added:**
- **Outlier filter** (`stats.robust_keep`): a plausibility floor (250 JD/m² sale) plus a log-space
  MAD filter removes the 0-price, 20 000-JD-"sale", 100 000-JD/m² and whole-building placeholders
  in the raw portal data, applied to the comp pool and to the income-approach medians.
- **Index staleness guard**: the CBJ index ends 2021-Q3; time-adjustment is disabled (never
  extrapolated) when the index doesn't cover the run period, and the gap is surfaced as a caveat.
- **Reconciliation weight floor**: caps how much a single near-identical comp can dominate the
  weighted mean (~3× max/min ratio).
- **Continuous-slope confidence capped at Medium**: univariate slopes on confounded observational
  data are never reported as High.
- **Data-availability caveats**: `cost_benchmarks`, `projects`, `evidence_items` are still being
  collected, so cost floor / competition / future signals are unavailable; the engine runs
  comparison + income-only and emits explicit `risk_factors` for each gap rather than fabricating.

**Real caveats that materially weakened v1 recommendations (honest disclosure):**
- `view`, `parking`, `finish_quality` are ~100% `unknown` in the current listings → categorical
  premiums cannot be derived yet (Bayut detail-enrichment pass pending). Only size/floor/age
  adjustments apply. A simple re-run picks up the enriched data when it lands.
- No cost benchmarks → minimum-safe rests on the comparison band, not a rebuild-cost floor.
- No future-signal items → premium tier rests on the comparison band, not an appreciation story.
- OpenSooq rows have no coordinates → distance-to-POI similarity is skipped for them (handled, no error).

**Real output (enriched-attributes run, representative 175 m² luxury/unfurnished new-build):**

| Neighborhood | min-safe | recommended | premium | confidence | comps |
|--------------|---------:|------------:|--------:|:----------:|:-----:|
| Abdoun | 603 | 927 | 1540 | M (0.61) | 12 |
| Dabouq | 624 | 888 | 1151 | H (0.74) | 11 |
| Sweifieh | 528 | 812 | 1246 | M (0.65) | 12 |
| Khalda | 535 | 649 | 763 | H (0.85) | 12 |
| Shmeisani | 366 | 538 | 929 | M (0.64) | 12 |

Latest run: all 5 factors (Building age, Finish quality, Floor level, Furnishing, Size) derive in
every submarket (finish/furnishing via citywide fallback where local coverage is thin). Parking
still cannot derive — after outlier-filtering only ~1 usable 'open' listing remains citywide, below
the paired-differential minimum. `seller_type` reached 100% but is intentionally NOT a property
premium (it would double-count the ask-to-transaction calibration, and no 'developer' rows exist).
Instead it is surfaced as an informational **Market composition** evidence chip (e.g. "83%
agent-listed, 17% private — a predominantly agency-brokered comp set") — market texture only,
explicitly not a price adjustment.

Recommended values track the raw neighborhood medians once the documented ask-to-transaction gap
(−10%), the size effect, and the enriched finish/furnishing adjustments are accounted for (an
unfurnished subject is normalised below furnished comps — an evidenced signal). Every value is
traceable to real Bayut/OpenSooq listing IDs with source URLs.

**Attribute-enrichment re-run (2026-07-07, enriched listing attributes in DB):**
- **Now deriving & in the waterfall:** Floor level and Building age (locally, real coverage
  n≈23–50 per submarket); Finish quality (Abdoun locally n=47; other submarkets via a **citywide
  fallback** — flagged, confidence-downgraded — because local finish coverage is too thin); and a
  new **Furnishing** factor (Abdoun locally n=28; others local/citywide). Premiums apply only to the
  subset of selected comps that actually carry the attribute (enrichment is 12–38% coverage), so
  the waterfall shows them on fewer comps for now; richness grows as enrichment continues.
- **Citywide fallback:** when a submarket is too sparse to derive an attribute, the premium is
  derived from all same-type sales, tagged `neighborhood="citywide"`, notes "citywide fallback —
  submarket sample insufficient", and its confidence downgraded one notch.
- **Still not derivable (surfaced as caveats, not fabricated):** `parking` — only 'covered' is ever
  recorded (never 'none'/'open'), so no paired differential can be formed; `view` — neither portal
  exposes it (attaches at neighborhood level from R7 qualitative research, not per comp);
  `elevator` — effectively all 'u'. The floor-premium method notes it uses absolute `floor_level`
  because `total_floors` is 0% (no floor-position-within-building).
- **Confidence vs the prior run:** essentially unchanged (Abdoun 0.65→0.62, Dabouq 0.70, Sweifieh
  0.64→0.65, Khalda 0.83, Shmeisani 0.63→0.64) — the added premiums refine values without moving the
  reliability score, because they are modest and several are citywide-fallback Low.

## 6c. Output shape for the frontend (5 neighborhoods)

`python -m app.engine.emit_sample` writes, from a real pipeline run:
- **`app/engine/outputs/<neighborhood>.json`** — one `RecommendationResult` (db-contract §4) per
  submarket: `abdoun.json`, `dabouq.json`, `sweifieh.json`, `khalda.json`, `shmeisani.json`.
- **`app/engine/sample_output.json`** — combined `{ generated_at, source, neighborhoods: { Abdoun: {...}, ... } }`
  so the frontend can demo selecting any of the 5.

## 7. Fixtures

`app/engine/fixtures/` (all rows labelled **SYNTHETIC** in `notes`; realistic Amman magnitudes,
not collected facts). Regenerate with `python app/engine/fixtures/_generate_fixtures.py`.

- `sample_listings.csv` — 44 sale + 9 rent rows across the 5 submarkets; frozen `listings` header.
  Abdoun is rich (happy path), Dabouq intentionally thin (2 comps, low-confidence path), three
  Abdoun comps are stale-but-selectable (time-adjustment path).
- `sample_cost_benchmarks.csv`, `sample_evidence.csv` (future signals), `sample_projects.csv`
  (competitors), `sample_index.csv` (CBJ apartment index — real through 2021-Q3, synthetically
  extended to 2026-Q2 for testing, clearly flagged).

The generator uses a **known** data-generating process (view/parking/finish/floor/age/size
premiums baked into prices) so the Adjustment Engine has genuine signal to *rediscover* — proving
the derivation works end-to-end without ever reading those weights.

## 8. Tests — requirement-driven (`app/engine/test_pipeline.py`)

Run: `python -m unittest app.engine.test_pipeline` (or `python -m pytest app/engine/test_pipeline.py`).

| Requirement | Test |
|-------------|------|
| Happy path — full contract, ordered band, plausible price | `HappyPath.*` |
| Every applied adjustment has an evidence object with a source | `test_every_applied_adjustment_has_evidence_with_source`, `test_every_evidence_object_carries_a_source` |
| No hardcoded weights (runtime + source scan) | `NoHardcodedWeights.*` |
| Thin market → low confidence + risk + wider range | `ThinMarket.*` |
| Stale comps → CBJ time-adjustment applied + evidenced | `StaleComps.*` |
| Missing attributes → graceful, risk surfaced, no crash | `MissingAttributes.*` |
| Confidence range produced (H/M/L + numeric + low<point<high) | `Confidence.*` |
| JSON contract keys + serialisable | `HappyPath.test_contract_keys_present`, `test_output_is_json_serialisable` |

**Result:** 16/16 passing.

## 9. How to run

```bash
# tests
python -m unittest app.engine.test_pipeline

# regenerate the frontend data contract
python -m app.engine.emit_sample      # -> app/engine/sample_output.json

# use in code
from datetime import date
from app.engine.fixtures import load_sample_bundle   # or build a DataBundle from DB rows
from app.engine.models import Subject
from app.engine import recommend

bundle = load_sample_bundle()
subject = Subject(neighborhood="Abdoun", property_type="apartment", area_m2=170,
                  floor_level=5, view="city", parking="covered",
                  building_age_years=0, finish_quality="high")
result = recommend(subject, bundle)     # -> RecommendationResult
print(result.recommended_price_jd_m2, result.confidence_label)
```

## 10. Sample output

- **Real run:** `app/engine/sample_output.json` (combined, 5 neighborhoods) +
  `app/engine/outputs/<neighborhood>.json`. Numbers in §6b; every value traceable to real
  Bayut/OpenSooq listing IDs with source URLs, all four data-gap caveats surfaced.
- **Synthetic reference** (rich attributes, for the full-feature demo incl. view/finish premiums,
  time-adjustment, competition and future signals): regenerate with the fixtures via a `Subject`
  in `load_sample_bundle()` — see §7. The synthetic path exercises every evidence type the real
  data will produce once view/parking/finish enrichment and the cost/projects/evidence tables land.
