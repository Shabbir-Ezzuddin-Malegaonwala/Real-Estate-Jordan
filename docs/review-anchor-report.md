# Adversarial Review — Submarket-Median Anchor (`_reconcile_to_submarket`)

**Reviewer:** Engine review agent · **Date:** 2026-07-08 · **Verdict: GO (with two required follow-ups noted, neither a blocker)**

Scope: the one pricing-logic change — `app/engine/recommendation.py:34` `_reconcile_to_submarket`, wired at `recommendation.py:111`, gated by `config.py:63` `ANCHOR_MIN_POOL`, fed `pool` from `pipeline.py:50`.

Verified empirically on the real 52,647-row DB (`db/jordan_re.sqlite`). `python tests/run_all.py`: engine **66 passed**, API **39 passed**. E2E **5 passed / 1 failed / 2 skipped** — see Finding H1 (the failure is NOT caused by this change).

---

## Attribute-sensitivity check (the key risk) — RESULT

Same submarket (Abdoun), several very different subjects, anchor engaged (λ=0.974):

| subject | comp_draw (carries attributes) | reconciled rec | anchor |
|---|---|---|---|
| 80 m² / fl2 / basic | 1083 | 912.6 | 1071 |
| 175 m² / fl3 / luxury | 825 | 918.1 | 1071 |
| 250 m² / fl15 / luxury | 1142 | 963.7 | 1071 |
| 250 m² / fl15 / **basic** | 1142 | 963.7 | 1071 |

Single-variable sweeps (Abdoun): **size 60→300 m²** moves rec 965→954 (~3%, non-monotonic); **floor 0→25** moves rec 938→947 (~3%, non-monotonic).

A/B (anchor ON vs gate raised to disable): size 80/150/250 → ON = 966/949/958 (2% spread); OFF = 850/1006/962 (**18% spread**).

**Interpretation — this is NOT a flatten-to-constant, and the anchor is not destroying a real signal:**
- The recommended still moves and roughly tracks the subject via `adj_mult = comp_draw/comp_raw`. Because `adjusted_ppm2 = time_adjusted·(1+net_capped)` (`adjustment.py:315`) and `comp_raw` is the subject-independent time-adjusted mean, `reconciled = comp_draw·[λ·anchor/comp_raw + (1-λ)]` — the subject's attribute response passes through as a multiplicative factor, it is not zeroed.
- The 18%→3% compression is compressing mostly **selection noise**: the anchor-OFF response is itself non-monotonic (850/1006/962 — a 250 m² unit "priced" above an 80 m² one is selection variance, not a real curve). The genuine *derivable* attribute signal is small by construction: size cap 10%, floor cap 12%, and **finish/view premiums are not derivable at all** from the current corpus (that is why 250/luxury == 250/basic exactly). The anchor removes the noise and leaves the small real signal. That matches the change's stated thesis and the root-cause table in `engine-tune-report.md`.

Bottom line on Risk #3: the engine is not "a median lookup masquerading as pricing" — but attribute response on the *recommended* is genuinely compressed to ~3–5%, and the client will notice small movement. Acceptable given the data, but see H1 for the deliverable-level symptom.

---

## Findings (ranked)

### HIGH

**H1 — Client-facing headline number does not move on attribute edits (real, but ORTHOGONAL to this change).**
The E2E test that failed ("editing size/finish/view … 1376.0 → 1376.0") is reading the **premium** tier. `premium` is pinned to `income_ceiling` (`recommendation.py:143`), which is computed from the submarket rent median ÷ derived yield and is **size/floor/finish-independent by construction** — I confirmed premium = 1376.4 for every size 60→300 in Abdoun. This is pre-existing income-approach behaviour, **not** the anchor: the anchor only touches `comparison_asking`/`recommended`. So this change does not cause the E2E failure, but the deliverable currently demos a flat headline. The tune report's claim of "E2E 6 passed … attribute edits still recompute live" (§5) is stale/inaccurate against the current run — flag for honesty. **Required follow-up (separate from this push): decide which tier the UI headlines, or make premium attribute-aware.**

### MEDIUM

**M1 — λ is structurally pinned near 1 for every covered submarket; the "inverse-variance adaptivity" is largely theoretical in the operating regime.**
`var_anchor = pstdev(pool)²/n_pool` with n_pool ≈ hundreds vs `var_comp = weighted_std²/12`; n_pool ≫ n_comp (~65×) forces λ high regardless of comp quality. Measured λ: Abdoun 0.974, Dabouq 0.980, Sweifieh 0.993, Khalda 0.975, Shmeisani 0.835 — the anchor sets the level in all five. This is disclosed in the report (§6, "λ ≈ 0.95–0.97") and is defensible (a dense pool IS more precise for the *level*), but the "thin/noisy pool yields to the comps" behaviour effectively only exists below the gate, not via λ. Not a bug; know that in practice this is "anchor·adj_mult, always" for covered submarkets.

**M2 — the anchor term's SE ignores `adj_mult` uncertainty (and median-vs-mean SE).**
`var_anchor` is the SE² of the raw pool *mean*, but the value blended is `median(pool)·adj_mult`. The uncertainty of `adj_mult` (a 12-comp ratio) and the median-vs-mean factor (~1.25×) are omitted, so λ is marginally over-stated. Second-order; does not affect ordering or finiteness. No action required.

### LOW

**L1 — gate compares the *cleaned* count, not raw `len(pool)`.** `recommendation.py:47` gates on `len(anchor_vals)` (post-`robust_keep`) ≥ 24, while `config.py:63` comment and `engine-tune-report.md` §3 say "len(pool) ≥ ANCHOR_MIN_POOL / pool at least twice the selection." A raw pool of 26 with 3 outliers → 23 kept → no-op. Behaviourally fine (arguably more correct), but the docs are imprecise. One-line doc fix.

**L2 — covered submarket with <24 same-type sales silently keeps the OLD behaviour.** Acceptable and noted in the report; just confirming it is intentional. No target submarket hits this (all five engage).

---

## Checklist verified

- **Div-by-zero / degenerate:** all paths guarded. var=0 (all comps equal) → `weighted_std`=0 → `var_comp<=0` returns `comp_draw`. All-equal pool → `pstdev`=0 → `var_anchor<=0` returns. n=1 → `len(comps)<2` returns. `comp_raw`=0/None → `if not comp_raw` returns. `adj_mult`∈[0.6,1.4] (net capped ±0.40), always finite/positive. `pool`≥24 at the `pstdev` call, never empty. **No division by zero reachable.**
- **Off-by-one:** engages at cleaned-count ≥ 24, no-op at ≤ 23. Correct, no off-by-one. Below gate returns `(comp_draw, None)` → `anchor` is None → old path byte-for-byte (fixtures pools ≤ 18 untouched → 66 engine tests unchanged and green).
- **Invariants:** 300-subject random real-DB fuzz across all five submarkets — **0 violations**: all finite, all `min_safe ≤ recommended ≤ premium`, all positive.
- **No hardcoded price weight:** `ANCHOR_MIN_POOL = 2×TARGET_COMPS` (a count); λ derived at runtime from variances. `NoHardcodedWeights` scan passes.
- **Explainability honest:** reconciliation surfaced via `selection_notes` (`recommendation.py:113`), `method_values.submarket_anchor_ppm2` + `comparison_comp_draw` (`:126`), and one narrative sentence (`:317`). No fabricated evidence object; every applied adjustment still carries its sourced object.
- **Report numbers reproduce:** Abdoun rec 918, Dabouq 950, Sweifieh 839, Khalda 671, Shmeisani 696 — match `engine-tune-report.md` §4 exactly.

---

## Verdict: **GO**

The math is sound, no reachable divide-by-zero, invariants hold on a 300-subject real-DB fuzz, tests are green (66+39), no hardcoded weights, and the reconciliation is surfaced honestly. The anchor stabilises the *level* and passes the subject's (small, data-limited) attribute response through `adj_mult`; it removes selection noise rather than a real signal. It does **not** flatten to a constant and does **not** divide by zero — the two stated blocker conditions are not met.

Two things the team lead should know before/after the push (neither blocks it): **H1** — the UI headlines the income-driven premium, which is size-independent and makes the demo look non-interactive; this is pre-existing, not caused by the anchor, and the tune report's E2E claim is stale. **M1** — λ is near 1 for all covered submarkets, so in practice the anchor always sets the level; that is disclosed and defensible.
