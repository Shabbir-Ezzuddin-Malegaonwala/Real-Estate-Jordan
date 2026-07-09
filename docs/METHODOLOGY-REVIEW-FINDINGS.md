# Methodology Review — Findings & Remediation Backlog

**Subject:** Jordan Real Estate Pricing Engine (`app/engine/`)
**Reviewer role:** Chief Data Scientist / Quantitative Economist (independent scientific review)
**Date:** 2026-07-09
**Purpose of this file:** A severity-ranked, actionable defect list. Each finding is self-contained: what is wrong, where, why it matters, and a concrete fix directive. Intended to be handed to an implementing LLM/engineer. Work top-down: **Critical → High → Medium → Low.**

> **One-line verdict:** The engineering is disciplined and unusually honest, but the science rests on a dataset that does not contain the variables the method prices, calibrated to a market it has never been tested against. Today the outputs are *evidence-anchored asking-price summaries*, **not** defensible market valuations. Fix the Critical items before any number is shown to an investor as a "valuation."

---

## How to use this document

- Every finding has an ID (`C1`, `H3`, …), a severity, a location, and a **FIX** block.
- **FIX** blocks are written as direct instructions. Where a full fix needs data that does not exist yet (e.g. transaction prices), the directive says what to do *in the interim* (label, disclaim, or gate) so the system stops overstating.
- Do **not** delete the honesty that already exists (caveats, disabled time-adjustment, thin-market floors). Several fixes are about making the *outputs and docs* match the *data reality*, not about adding false confidence.

### Severity definitions
| Severity | Meaning |
|---|---|
| **CRITICAL** | Invalidates the core claim (that these are defensible prices) or ships results that cannot be reproduced from the real data. Blocks deployment. |
| **HIGH** | Materially biases the price or its uncertainty; a knowledgeable reviewer would reject on this alone. |
| **MEDIUM** | Weakens rigor, robustness, or interpretability; fixable without new data. |
| **LOW** | Hygiene, documentation, and future-proofing. |

---

## Evidence base (measured, not assumed)

Profiled directly from the shipped artifacts on 2026-07-09:

- `data/processed/listings_national_20260708.csv` — **n = 56,854** (sale 40,874 / rent 15,976).
- Attribute fill rate, **national CSV**: price 89.9%, area 76.8%, lat/lng 42.6%, listing_date 41.4%, building_age 7.4%, **floor_level 3.3%**, **finish_quality 0.02% (13 rows)**, **view 0%**, **parking 0%**, **elevator 0%**.
- Target submarkets (apartment sale): Khalda 1,359 · Abdoun 958 · Dabouq 488 · Sweifieh 281 · Shmeisani 227. In **all five**, floor/view/parking/elevator = **0** populated.
- **Two databases exist:** `db/jordan_re.sqlite` (854 rows, hand-enriched: elevator 854, finish 221, parking 326, floor 351, view 24) vs `db/jordan_national.sqlite` (56,854 rows, enrichment collapsed: view 0, parking 0, elevator 0, finish 13).
- `db/jordan_national.sqlite`: `derived_premiums` and `recommendations` tables are **empty** — the national data has never produced a recommendation.
- Published `app/engine/outputs/*.json` (e.g. `abdoun.json`: recommended 927, premium 1540, finish n_luxury=155) were generated from the **854-row pilot**, not the national data.
- `data/processed/macro_cbj_price_index.csv` ends **2021-Q3**; with `INDEX_STALE_MONTHS = 15` and a 2026 run date, time-adjustment is **disabled** at runtime.

---

# CRITICAL

### C1 — Showcased results are generated from a different (854-row pilot) database than the shipped "national" data, and are not reproducible
- **Where:** `app/engine/outputs/*.json`, `docs/engine-report.md` §6b, `db/jordan_re.sqlite` vs `db/jordan_national.sqlite`.
- **Problem:** The demo outputs and the headline 5-neighborhood price table come from the 854-row enriched pilot (`jordan_re.sqlite`), where attributes are richly populated. The production dataset (`jordan_national.sqlite`, 56,854 rows) has ~0% attribute fill and has **never** produced a recommendation (`recommendations`/`derived_premiums` tables empty). A reviewer handed the national DB cannot regenerate any published number.
- **Impact:** Reproducibility failure at the level of the *claims*. An investor who re-runs the pipeline on the "real" data gets a materially thinner, mostly-unadjusted result — or nothing. This alone fails an audit.
- **FIX:**
  1. Run the engine end-to-end on `jordan_national.sqlite` and regenerate `app/engine/outputs/*.json` from it. Whatever it produces (even degraded) is the honest output.
  2. Rewrite `docs/engine-report.md` §6b as a table labeled **"Pilot DB (854 rows, enriched) — illustrative only"** and add a second table **"National DB (56,854 rows) — production"** with the real regenerated numbers.
  3. Stamp every output JSON with the source DB filename + a content hash of the listings snapshot and the row count it was built from (see C4).
  4. If the pilot DB is kept for demos, rename it explicitly (`jordan_re_PILOT_enriched.sqlite`) and add a `README` in `db/` explaining the two-DB distinction.

### C2 — The adjustment grid (the system's headline feature) is inert on production data
- **Where:** `app/engine/adjustment.py` (`_categorical_schedule` L50, `_continuous_premium` L104), gated by `config.MIN_PAIR_GROUP=3` / `MIN_SLOPE_POINTS=6`.
- **Problem:** view/parking/elevator/finish are 0% populated nationally and 0% in all five target submarkets, so `_categorical_schedule` returns `{}`, the citywide fallback also returns `{}` (0 populated citywide), and no categorical adjustment is ever applied. floor_level (3.3%) rarely clears the slope minimum. The much-advertised "every premium derived from the market" reduces, in production, to at most size (and occasionally age) — i.e. the price is ≈ neighborhood median × (1 − flat gap).
- **Impact:** The core methodological claim is practically vacuous on the real data. "Derives nothing" is not "derives from the market."
- **FIX (in priority order):**
  1. **Restore attribute enrichment at national scale.** The 854-row pilot proves description-parsing can populate finish/parking/floor/etc. Re-run that enrichment (`scrapers/enrich_bayut.py`, `reenrich_bayut_from_csv.py`) over the full Bayut corpus and backfill `jordan_national.sqlite`. This is the single highest-leverage fix.
  2. Add a **coverage gate at the engine boundary:** for each requested submarket, compute and emit `attribute_coverage = {field: fill_rate}`. If a priced attribute is <X% populated, mark its premium `not_derivable` and **surface it in the output** rather than silently producing `{}`.
  3. Report, per recommendation, **which adjustments actually fired vs. which were unavailable**, so a reader can see the grid is thin when it is thin.

### C3 — No validation against realized transactions anywhere; "16/16 tests" are contract tests, not accuracy tests
- **Where:** `app/engine/test_pipeline.py`, `docs/engine-report.md` §8.
- **Problem:** There is no train/test split, no cross-validation, no back-test against a single realized sale price. The passing tests verify software behavior ("every adjustment has an evidence object", "no hardcoded weights", "thin market widens range") — they say nothing about whether prices are correct. No RMSE/MAE/MAPE/calibration exists because there is no ground truth.
- **Impact:** **No accuracy claim in this system is currently falsifiable.** The estimand ("recommended price") has no loss function.
- **FIX:**
  1. Acquire ground truth: DLS transaction micro-data if obtainable; otherwise even a few dozen broker-confirmed closings. Store in a new `transactions` table.
  2. Build a validation harness (`app/engine/validation/`) that back-tests `recommended_price_jd_m2` vs realized prices using **spatial-block cross-validation** (not random CV — see H5), reporting MAE, MAPE, median APE, and bias by submarket and price tier.
  3. **Interim, before ground truth exists:** run the *synthetic-recovery test the fixtures were literally built for* (`fixtures/_generate_fixtures.py` bakes a known DGP). Report the % error between injected and recovered premiums as the only currently-honest accuracy figure, and label it "synthetic recovery, not market validation."
  4. In all docs/outputs, stop implying the green test suite is evidence of pricing accuracy.

### C4 — Outputs are not version-pinned to the data snapshot that produced them
- **Where:** `RecommendationResult` (`app/engine/models.py`), `app/engine/outputs/*.json`.
- **Problem:** Nothing ties a specific output to a specific listings snapshot, row count, or code revision. Combined with C1 (two DBs), this is how the pilot numbers got presented as production.
- **Impact:** Non-reproducible provenance; silent data swaps go undetected.
- **FIX:** Add to every `RecommendationResult`: `data_source_file`, `listings_snapshot_hash`, `listings_row_count`, `engine_version`/git SHA, and `n_comps_used`. Refuse to emit an output without them.

---

# HIGH

### H1 — Flat 10% ask-to-transaction gap applied uniformly is the largest unforced assumption and is almost certainly false as a constant
- **Where:** `config.py:49` (`ASK_TO_TX_GAP_LOW/HIGH`), `recommendation.py:77` (midpoint applied uniformly).
- **Problem:** The gap between asking and transaction price is not a constant — it is a function of liquidity, cycle phase, price tier, and property type. It widens for overpriced luxury stock and soft markets, compresses in hot supply-constrained segments. Applying a flat 10% makes the model *most wrong in the luxury tail where the developer's margin is decided.* A ±5 pp error on the gap is a ±5% error on every emitted price — larger than most attribute adjustments the engine works hard to derive.
- **Impact:** Systematic, segment-correlated bias in the headline number; the dominant uncertainty is collapsed to a point and thrown away.
- **FIX:**
  1. Make the gap **segment- and tier-varying**: at minimum a lookup by (property_type × price tier), ideally estimated from asking-vs-transaction pairs once DLS/broker data lands (ties to C3).
  2. **Propagate its uncertainty** instead of collapsing to the midpoint: carry the full 5–15% (or wider for luxury) through to the confidence interval (see H4).
  3. **Interim proxy:** use time-on-market (if scraped) or listing age as a per-listing signal of negotiability rather than one global constant.

### H2 — Listing-survivorship / selection bias: asking listings over-represent overpriced, slow-moving stock
- **Where:** Data foundation (`comparable_analysis.neighborhood_pool`, all pooling).
- **Problem:** The sample is *properties currently for sale*. Well-priced units sell fast and leave the sample; what remains is biased toward the overpriced tail. The model treats the surviving listings as an unbiased basis for value. No correction exists.
- **Impact:** Upward bias in the comparison anchor, partially and inconsistently offset by the flat ask-to-tx gap — two uncontrolled biases pointing opposite directions.
- **FIX:**
  1. Where `listing_date` + capture history exist, model **time-on-market** and down-weight or discount stale-on-market listings (they signal overpricing).
  2. When transaction data lands, estimate the listing→sale selection correction directly (Heckman-style or simple realized/asking ratio by segment).
  3. Document the bias explicitly in `_data_caveats` output until corrected.

### H3 — Univariate premiums are confounded; the intended finish-residualization control is silently inert
- **Where:** `adjustment.py:94-133` (`_finish_residuals`, `_continuous_premium`).
- **Problem:** The code residualizes price/m² by finish class before fitting floor/age/size slopes — a genuinely good idea. But finish_quality is ~0% populated, so `finish_med` is empty and `control = base` for every row: the control does nothing, and the slopes are raw univariate confounded estimates (high-floor units are also newer/more luxurious, etc.). The report concedes confounding but the mitigating control does not actually run.
- **Impact:** Derived slopes attribute co-varying quality to floor/age/size; signs can even be perverse on small samples (see M1).
- **FIX:**
  1. Fix the input data (C2) so the residualization has something to control on.
  2. Replace the ad-hoc partial control with a **small multivariate fit** (see M3) even at v1 volumes via pooling — this de-confounds properly instead of one-covariate-at-a-time.
  3. Until then, flag every continuous premium in the output as `confounded_univariate` (the confidence cap at Medium is good; make the confound explicit in the evidence object text).

### H4 — The "80% confidence interval" is an uncalibrated dispersion band
- **Where:** `confidence.py:84-98` (`_interval`), narrative text `recommendation.py:267`.
- **Problem:** The interval half-width = weighted comp dispersion widened as confidence falls, bounded 4–35%. It is *labeled* an "80% interval" in the narrative, but nothing demonstrates that 80% of realized prices fall inside it — there are no realized prices. The dominant uncertainty (the ask→tx gap, H1) is not even in it.
- **Impact:** Unearned probabilistic claim; decision-makers will read "80%" as calibrated coverage.
- **FIX:**
  1. Stop calling it an "80% interval" until coverage is empirically verified. Relabel as **"evidence-dispersion range (uncalibrated)"** in narrative and UI.
  2. Fold ask→tx-gap uncertainty and (where relevant) time-staleness into the band.
  3. Once ground truth exists (C3), calibrate: report empirical coverage vs nominal and adjust the widening function so the label is true.

### H5 — No spatial handling: micro-location (the dominant Amman price driver) barely enters the model, and any future CV must be spatial
- **Where:** `comparable_analysis.py:117-121` (`_distance_similarity`, 5 km linear decay), neighborhood-bin filtering; POI/road/zoning data collected but unused in pricing.
- **Problem:** Intra-Amman price variation is dominated by micro-location, yet location enters only as (a) a categorical neighborhood filter and (b) a 5 km similarity tie-breaker for the 42% of listings with coordinates. `poi.geojson`/`roads.geojson`/`zoning.geojson` feed the map but not the price. Spatial autocorrelation of residuals is never tested (no Moran's I), and comps drawn from the same submarket mean any random-CV validation will be optimistically leaky.
- **Impact:** Large omitted spatial structure; understated uncertainty; future validation invalid if it uses random folds.
- **FIX:**
  1. Price location: add distance-to-CBD/arterials and POI-density as **features/covariates**, not just ranking terms.
  2. Add a spatial diagnostic (Moran's I on residuals) to the validation harness.
  3. Mandate **spatial block CV** in C3's harness.
  4. Roadmap: spatial random effect / kriging / GWR (see M3).

### H6 — Cross-check approaches rest on citywide medians and a single cost benchmark, undermining the "triangulation raises confidence" claim
- **Where:** `recommendation.py:40-68` (`_income_ceiling` uses citywide median rent / citywide median sale), `_cost_floor` (one `cost_benchmarks` row nationally).
- **Problem:** The income ceiling's required yield mixes all specs and locations (an Abdoun luxury yield derived from a Zarqa-inclusive citywide ratio is meaningless for Abdoun). The cost floor rests on a single national benchmark. So two of the three "independent" approaches are weak or near-constant, making apparent convergence uninformative.
- **Impact:** `method_agreement` confidence component is inflated by approaches that aren't genuinely independent or local.
- **FIX:**
  1. Derive required yield **per submarket × property_type** where local rent+sale coverage allows; fall back to citywide only with the existing confidence downgrade, and say so.
  2. Collect multiple cost benchmarks by spec class/governorate; until then, treat the cost floor as low-confidence and don't let it silently set `min_safe`.

### H7 — Time dimension is uncorrected: index-based time-adjustment is disabled and no macro covariate replaces it
- **Where:** `adjustment.py:204-245`, `config.INDEX_STALE_MONTHS=15`, CBJ index ends 2021-Q3.
- **Problem:** For a 2026 run, time-adjustment is disabled (correct — don't extrapolate a stale index). But the consequence is that comps up to 18 months old are compared at face value and ~5 years of market movement between the index end and today are uncorrected, with nothing filling the gap. The model is effectively blind to the cycle.
- **Impact:** Cycle/regime bias; a 2026 launch priced off 2023–2025 asking medians with no time normalization.
- **FIX:**
  1. Source a fresher price signal: DLS quarterly transaction volumes/prices, or construct an in-house repeat-listing / hedonic time index from the scraped snapshots (capture_date history).
  2. Feed recent macro (lending rate, permits/supply) as trend context.
  3. Keep the "disabled not extrapolated" behavior, but add a **high-severity risk flag** when comps span a period with no index coverage.

---

# MEDIUM

### M1 — No economic-plausibility gate on derived premiums (sign/monotonicity unchecked)
- **Where:** `adjustment.py` (premium derivation), `normalize_comp`.
- **Problem:** OLS slopes and paired differentials on tiny samples can produce economically perverse signs (negative size or age-appreciation premium as a sampling artifact). Caps bound magnitude, not sign.
- **FIX:** Add a monotonicity/sign gate: reject or zero-out premiums whose sign violates economic priors (e.g. age should not increase value ceteris paribus), and log the rejection as evidence. Make priors explicit and documented.

### M2 — Reconciliation weights and adjustment caps are hand-set constants presented as method
- **Where:** `config.py` (`CATEGORICAL_ADJ_CAP=0.20`, `CONTINUOUS_ADJ_CAP=0.12`, `SIZE_ADJ_CAP=0.10`, `NET_ADJ_CAP=0.40`, `RECONCILIATION_WEIGHT_FLOOR=0.20`), `adjustment.py:321`.
- **Problem:** These directly bound the answer (when a cap binds, the price is partly the cap) yet are unjustified and unvalidated. Appraisal convention permits caps, but they should not read as derived.
- **FIX:** (a) Document the provenance of each constant; (b) add a sensitivity analysis to the validation harness sweeping each cap and reporting price sensitivity; (c) report per-recommendation whether any cap bound and by how much.

### M3 — Replace/augment the grid with a hierarchical Bayesian hedonic (works below the 300-txn threshold via pooling)
- **Where:** methodology choice; roadmap currently defers all hedonic to "Phase 2, needs 300–500 transactions."
- **Problem:** The 300–500 rule is for *unpooled OLS*. A hierarchical model with neighborhood-level partial pooling and a spatial random effect is *designed* to work below that threshold, de-confounds attributes jointly, borrows strength across sparse submarkets far better than the current "citywide fallback + one-notch downgrade," and yields honest joint uncertainty.
- **FIX:** Prototype a penalized/Bayesian hedonic on the populated fields (price, area, coords, date, bedrooms, +enriched attributes once C2 lands) and benchmark it against the grid in the C3 harness. Keep the grid as the explainable presentation layer if it validates comparably.

### M4 — Cross-portal duplicate / relisting inflation not handled in the pricing pool
- **Where:** `comparable_analysis.neighborhood_pool`, ingestion.
- **Problem:** The same unit relisted across Bayut/OpenSooq and across months inflates apparent comp density and biases medians toward repeatedly-pushed listings.
- **FIX:** Add near-duplicate detection (fuzzy match on area+beds+price+coords+description hash) before pooling; keep the most recent instance; report dedup counts in selection notes.

### M5 — Neighborhood bins are unvalidated as homogeneous price zones (MAUP)
- **Where:** neighborhood filtering throughout; boundaries from GAM/OSM polygons.
- **Problem:** Results shift with boundary definition (modifiable areal unit problem); the five submarkets are administrative/colloquial, not statistically homogeneous.
- **FIX:** Add a boundary-sensitivity test (perturb boundaries / try alternative partitions) to the harness; longer term, prefer continuous spatial modeling (M3/H5) over hard bins.

### M6 — Portal heterogeneity pooled with only an informational chip
- **Where:** pooling of Bayut (agency/premium) + OpenSooq (private/noisier) sales; `seller_type` surfaced as "market composition" only.
- **Problem:** Systematic level/quality differences between portals are not corrected, only described.
- **FIX:** Add a portal (and seller_type) fixed effect to any regression-based estimate, or stratify medians by portal and reconcile explicitly.

### M7 — Luxury outliers may be trimmed by the MAD filter exactly where upside lives
- **Where:** `stats.robust_keep` (`stats.py:85`), `config.MIN_PLAUSIBLE_SALE_PPM2`.
- **Problem:** Log-space MAD trimming can drop genuine ultra-prime units as "outliers," biasing the premium tier downward in the segments developers most care about.
- **FIX:** Distinguish data-error outliers (0-price, whole-building placeholders) from genuine high-value tails; use a one-sided/asymmetric rule or a higher upper cutoff for known-luxury submarkets; report how many rows were trimmed and their value range.

---

# LOW

### L1 — Narrative rhetoric outruns the evidence
- **Where:** `recommendation.py:258-287` ("within a defensible range", "raise later, never cut", "80% interval").
- **FIX:** Soften to match data strength; label outputs "evidence-anchored estimate, not a valuation" until Critical items are closed. Keep the excellent provenance/traceability.

### L2 — `total_floors` unavailable, so "floor" is absolute, not position-in-building
- **Where:** `adjustment.py:37` (`_FLOOR_NOTE`).
- **FIX:** Attempt to parse total_floors during enrichment; until then keep the honest note (already present) and treat the floor premium as low-confidence.

### L3 — No experiment tracking / data lineage register
- **Where:** repo-wide.
- **FIX:** Add a lightweight run register (date, DB hash, code SHA, row counts, output IDs). Complements C4.

### L4 — Synthetic fixtures embed a known DGP but recovery error is never reported
- **Where:** `fixtures/_generate_fixtures.py`, `test_pipeline.py`.
- **FIX:** Emit a numeric injected-vs-recovered premium error report as part of the test/validation output (this is nearly free and is the most honest accuracy figure available pre-ground-truth).

### L5 — 57% of listings lack coordinates; spatial features silently skipped for them
- **Where:** OpenSooq rows, `_distance_similarity` returns None.
- **FIX:** Geocode from neighborhood/address text where possible; report coordinate coverage per submarket; ensure the confidence score reflects reduced spatial information rather than treating missing distance as neutral.

---

## Suggested remediation order (dependency-aware)

1. **C1 + C4** — regenerate outputs from the national DB, version-pin them, correct the docs. (Stops the overstatement immediately; low effort.)
2. **C2** — re-run attribute enrichment at national scale. (Unblocks the entire adjustment grid; highest leverage.)
3. **H1 + H4** — segment-varying ask-to-tx gap with uncertainty propagated into a relabeled range.
4. **C3** — acquire ground truth + build the spatial-block validation harness; run L4 synthetic recovery in the interim.
5. **H2, H3, H6, H7** — selection bias, de-confounding, local cross-checks, time signal.
6. **H5 + M3** — price location; prototype hierarchical hedonic; benchmark against the grid.
7. **Medium then Low** — robustness, plausibility gates, hygiene.

## Definition of done (deployment gate)
A price may be presented as a **valuation** (not an "estimate") only when: outputs reproduce from the production DB (C1/C4); the adjustment grid actually fires on real data (C2); accuracy is measured out-of-sample against realized prices with spatial CV (C3); the ask-to-tx gap is segment-varying with propagated uncertainty (H1/H4); and the reported interval's empirical coverage matches its label (H4).
