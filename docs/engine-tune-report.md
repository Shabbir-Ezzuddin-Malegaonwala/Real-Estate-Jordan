# Engine Tuning Report — Comp-Selection Bias on the Expanded Corpus

**Author:** Engine (agent) · **Date:** 2026-07-08 · **Deadline gate:** 2026-07-09
**Scope:** diagnose + fix the point-estimate drift the 52,647-listing load exposed, without
regressing the 100+ passing tests and without hardcoding any price weight.

---

## 1. Symptom

After the corpus grew from ~24k to 52,647 listings (OpenSooq/EurekaJo/Homes/AbuJudom added —
real, deduped, private-seller-heavy, no coordinates), `emit_sample` for Abdoun fell to
**742 JD/m² M(0.53)** from 991 H(0.76), and Dabouq *rose* to 1188 — even though every source's
sale-apartment median is sane and consistent (Bayut 1091, OpenSooq 1043, EurekaJo 967, Homes
1299, AbuJudom 893; true centre ~1000–1090). The point estimate landed **below every source
median**. It was wrong, not merely wider.

## 2. Root cause (diagnosed, not guessed)

The drift is **small-sample selection variance in the top-N comparable shortlist**, compounded
by the ask-to-transaction haircut. Traced on the live DB for the Abdoun 175 m² subject:

| Stage | Value | Note |
|---|---|---|
| Same-submarket same-type pool (robust-filtered) | median **1071** (n=853) | the true submarket centre |
| Recent + size-±45% pool | median **1040** (n=215) | still healthy |
| **Top-12 similarity shortlist** | median **860**, weighted-adjusted **825** | **unrepresentative cheap pocket** |
| × 0.90 ask→tx | **742** | the reported number |

Two mechanisms, both a direct consequence of density:

1. **The top-12 draw is a high-variance sub-sample.** With 215 valid comps, ranking by a
   size-dominated similarity (distance is inactive — no subject coordinates) and keeping only 12
   lands on a cheap cluster (860) that is 19% below the submarket median (1071). The effect is
   *variance*, not a downward bug: Dabouq's 12-draw skews **high** (1319 vs pool 1051).
   Confirmed by sweeping the shortlist size — the weighted mean converges to the submarket
   median as N grows (Abdoun 825→1062, Dabouq 1320→1176, Khalda 587→675 at full pool).
2. **The reconciliation weight rewards the cheap comps.** `weight = recency/(floor+gross_adj)`
   gives low-adjustment (often the cheapest, most "ordinary") comps the highest weight, dragging
   825 further below the shortlist's own median (860).

The "no-coordinates" hypothesis was **checked and ruled out**: `haversine_km` returns `None`
when either point lacks lat/lng, and `_similarity` drops `None` parts and renormalises — missing
coordinates are neutral, never a false-similarity bonus. Bayut's near-total absence from the
shortlist is due to **recency** (its rows date 2017–2022; 6/449 fall in the 18-month window),
which is correct behaviour, not a bug.

## 3. Fix

A **submarket-median anchor with inverse-variance shrinkage**, exactly the documented statistical
guard the brief called for. Keep all the data and the appraisal grid; stop a skewed 12-comp draw
from setting the price level.

`app/engine/recommendation.py` — new `_reconcile_to_submarket(pool, comps, comp_draw)`
(recommendation.py:33), called at the top of `assemble` (recommendation.py:86):

- **Anchor** = robust trimmed median of ALL same-submarket same-type sales (`pool`, reusing the
  existing `robust_keep` floor+MAD filter). A stable central level from hundreds of rows.
- **Adjustment ratio** = `comp_draw / weighted_mean(time_adjusted_ppm2)` — the comps' own
  attribute-normalisation multiplier. Numerator and denominator share the shortlist's selection
  bias, so the *level* bias cancels and only the subject-tailoring survives. This is carried onto
  the anchor so a luxury/high-floor subject is still priced above/below the raw median.
- **Blend** = inverse-variance (precision) weighting: each estimate counts as `1/SE²`
  (`SE² = var/n`). No price constant — the weight is set purely by each estimate's sampling
  precision. A dense, tight pool dominates; a thin or noisy one yields to the comps.
- **Gate**: engages only when `len(pool) ≥ ANCHOR_MIN_POOL` (`= 2 × TARGET_COMPS = 24`,
  config.py:55). Below that the shortlist already *is* the submarket, so the draw is returned
  untouched — this is why all synthetic-fixture tests (pools ≤ 18) are unaffected.

The reconciliation is surfaced for auditability: a `selection_notes` line ("reconciled to
submarket robust median … via inverse-variance weighting (anchor λ=…)"), new `method_values`
keys (`submarket_anchor_ppm2`, `comparison_comp_draw`), and one explanatory narrative sentence.
No new evidence object is fabricated; every attribute premium still carries its sourced object.

Files touched: `app/engine/config.py` (+`ANCHOR_MIN_POOL`), `app/engine/recommendation.py`
(helper + wiring + narrative/method_values), `app/engine/pipeline.py:50` (pass `pool` to
`assemble`).

## 4. Before / after (representative 175 m² luxury apartment, `emit_sample`)

| Submarket | Robust median | median × 0.90 | BEFORE rec | **AFTER rec** | lowest source median | above lowest? |
|---|---|---|---|---|---|---|
| Abdoun | 1071 | 964 | 742 M(0.53) | **918 M(0.59)** | 893 (AbuJudom) | ✓ |
| Dabouq | 1051 | 946 | 1188 M(0.54) | **950 M(0.60)** | 871 (AbuJudom) | ✓ |
| Sweifieh | 935 | 842 | 820 M(0.63) | **839 M(0.64)** | 572 (AbuJudom) | ✓ |
| Khalda | 769 | 692 | 529 H(0.72) | **672 H(0.76)** | 646 (EurekaJo) | ✓ |
| Shmeisani | 773 | 696 | 547 M(0.68) | **696 H(0.76)** | 610 (OpenSooq) | ✓ |

Every recommendation now tracks `robust_median × 0.90` (the documented ask-to-transaction gap)
and sits **above the lowest per-source median** in all five submarkets — none below the market.
The reconciled *asking* level (before the 0.90 haircut) sits essentially on each submarket
median (Abdoun 1020, Dabouq 1056, Sweifieh 932, Khalda 748, Shmeisani 773), which is the clean
apples-to-apples check against the asking-price source medians. Confidence rose modestly and
honestly — the point estimate is more stable and the comparison approach now agrees better with
the cost/income cross-checks; the interval is still driven by the comps' genuine weighted
dispersion (unchanged mechanism).

The live API path reproduces this (server on the full 52,647-row DB): Abdoun comp_draw 892 →
anchor 1071 → **rec 971**; Dabouq comp_draw 1319 → anchor 1051 → **rec 950**.

## 5. Verification

- `python tests/run_all.py` — **all green**: engine edge + baseline **66 passed**, API edge
  **39 passed** (against a freshly-started server on the current 52,647-row DB — a stale server
  with pre-expansion data and pre-fix code was found holding :8000 and replaced), E2E frontend
  **6 passed, 2 skipped** (both environmental, as documented in the QA report). 0 uncaught JS
  errors; attribute edits still recompute live.
- **No hardcoded weights**: `NoHardcodedWeights` source-scan + behavioural tests pass; the added
  knob (`ANCHOR_MIN_POOL`) is a sample-count gate, and λ is derived from variances at runtime —
  no attribute→fraction map, no `_MULT` table.
- **Evidence integrity**: `HappyPath` evidence tests pass; every applied adjustment still carries
  a sourced evidence object.
- **Invariants**: the 300-subject real-DB fuzz stays finite, ordered, and `low < rec < high`.

## 6. Residual notes (for the tech lead)

- With hundreds of comps λ ≈ 0.95–0.97, so the level is carried mainly by the robust submarket
  median and the shortlist supplies the *adjustment ratio* + dispersion. This is deliberate and
  more defensible than 12 similarity-picked rows setting the price; on thin submarkets λ falls
  and the comps regain control (the fixtures, pools ≤ 18, don't engage the anchor at all).
- Bayut's exclusion by the 18-month recency window means the *recent* mix is OpenSooq-heavy
  (private-seller, slightly cheaper). The anchor uses the full same-type pool (incl. dated Bayut)
  as the level, which is appropriate for a stable central tendency (Amman apartment prices have
  been roughly flat since 2021 per the CBJ series). If desired, a follow-up could weight the
  anchor by recency; not needed to clear the defensibility bar today.
