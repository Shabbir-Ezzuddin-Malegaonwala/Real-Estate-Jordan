# Brutal Pre-Push Code Review — Engine + Frontend Changes

**Reviewer:** Claude (adversarial). **Date:** 2026-07-07.
**Scope:** `app/api/main.py`, `app/engine/{pipeline,recommendation,comparable_analysis,config}.py`, and the frontend theme/help changes.
**Method:** read every changed line, reconstructed the dedup clustering by hand, probed the real 22 MB SQLite DB (all 5 submarkets), ran both engine test suites (63 passed).

**Verdict: GO** for this session's four logic changes — they are correct, complete, and well-tested. One genuine 500-crash exists in `main.py` but it is **pre-existing and untouched** by this session; fix it opportunistically since the file is already open, but it does not invalidate the reviewed work.

---

## Findings (ranked)

### HIGH-1 — `/comparables` 500-crashes on Khalda (PRE-EXISTING, not introduced this session)
**`app/api/main.py:168`**
```python
rows.sort(key=lambda l: l.listing_date or "", reverse=True)
```
`listing_date` is `date | None`. When a submarket has both dated and undated sale rows, the key mixes `date` and `str` → `TypeError: '<' not supported between instances of 'datetime.date' and 'str'`.

**Confirmed on real data:** Khalda has 1085 dated + 1 undated qualifying sale row → `GET /comparables?neighborhood=Khalda` returns 500. Abdoun/Sweifieh/Dabouq/Shmeisani currently have 0 undated rows so they happen to work, but any future undated Khalda-style row in the others reintroduces it.

**Why it's not a blocker for this push:** the line is **not in the diff** (only the `Coverage` class and the `_neighborhoods_with_sales` removal changed in this file). It's a latent bug the session neither caused nor touched.

**Fix:** `rows.sort(key=lambda l: l.listing_date or date.min, reverse=True)` (import `date`). Add a test hitting `/comparables` for a submarket with a mixed dated/undated pool.

---

### LOW-1 — Dedup collapses genuinely-identical data points, not just cross-posts (INFORMATIONAL — behaves as designed)
**`app/engine/comparable_analysis.py:71-74`**
`_same_unit` merges any two rows with equal known bedrooms + area within 1% + price/m² within 1%. Two *genuinely distinct* apartments that share those three values collapse into one.

**Assessed as acceptable, not a defect.** I dumped the actual Khalda clusters: they are overwhelmingly exact cross-posts (identical beds/area/price, several with literal duplicate `listing_id`s like `bayut-elitejo2` twice). Even in the rare case two real units carry identical (beds, area, price/m²), their data points are identical, so the **median is unchanged** — only the comp *count* drops, which is exactly the OBS-3 confidence-inflation this change is meant to kill. Collapse rate on real pools: Khalda 187/772 (24%), Sweifieh 114/683, Abdoun 78/538 — all driven by real syndication. No action needed.

---

### LOW-2 — Seed-anchored greedy clustering can under-collapse a chained trio
**`app/engine/comparable_analysis.py:57-65`**
Candidates are compared only to the cluster *seed* (smallest area). If A~B and B~C are each within tol but A~C is not (a 3-way chain straddling the 1% band), C is not pulled into A's cluster and starts its own. This *under*-collapses. Deterministic (total sort order + `listing_id` tiebreak), never crashes, and irrelevant in practice because real cross-posts are near-exact (sub-0.1% apart), not chained across the band edge. Leave as-is; single-linkage would be the alternative but risks the opposite (over-collapse). Documenting only.

---

### LOW-3 — Dedup is O(k²) on same-area spikes
**`app/engine/comparable_analysis.py:57`**
The inner scan is bounded by the `area > seed.area/(1-tol)` break, so cost is quadratic only within one 1%-wide area band. Round-number spikes (e.g. many 200 m² units) create such bands. **Measured worst case on the real DB: 6 ms (Khalda, 772 rows).** Runs once per `/recommend`. Non-issue at this data scale; note only if the corpus grows 10×.

---

### LOW-4 — HelpPanel has no focus trap
**`app/web/src/components/HelpPanel.tsx`**
The drawer sets `role="dialog" aria-modal="true"`, focuses the close button, and handles Escape — good. It does **not** trap Tab, so keyboard focus can wander to the map/form behind the scrim. Minor a11y gap, not a logic bug. Optional polish.

---

## What I tried to break and could **not** (verified correct)

- **Coverage = the 5 targets.** `districts` table holds exactly `Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani`; all 5 have sale listings, so coverage resolves to 5. Normalization is consistent on both sides (`name.strip().lower()` vs `l.neighborhood.strip().lower()`), `if l.neighborhood` guards empty strings, and `resolve()` returns the canonical district spelling that `neighborhood_pool` then matches — so no covered-with-sales submarket is wrongly excluded and no uncovered one leaks in. `resolve()`→`None`→422 path intact. The `_abdun`/`Amman`/`Rabyeh` rows (previously exposed under the old all-sales logic) are now correctly excluded — that is the intended narrowing, consistent with the "five premium submarkets" product framing.
- **Area guard is complete.** `pipeline.py:31-36` catches `0`, negative, `inf`, `nan` (via `math.isfinite`), returns `unpriceable`; `None` correctly falls through to price-without-size. It is the first statement after `as_of`, so no path uses `subject.area_m2` before it. Matches `AreaBoundaries` tests (all pass).
- **`unpriceable()` is well-formed.** Populates every `RecommendationResult` field with finite scalars, `[0.0, 0.0]` interval, one `"high"` risk factor via `_risk` (`{factor, severity, detail}` — verified shape), empty comps/evidence, `method_values.selection_notes=[]`. `to_dict()` serialises; `json.dumps` succeeds in tests. `_empty_result` now delegates to it with no behavioural change. No downstream KeyError — the zero-comp path already emitted this exact shape.
- **Dedup crash-safety.** `neighborhood_pool` filters `and l.price_per_m2`, guaranteeing `area_m2 > 0` and `price_per_m2 > 0` for every pooled row, so the sort key and `_within` never see `None`; `_within` also has an explicit `hi == 0` guard. Empty pool → `([], 0)`. The early-break bound is mathematically exactly the negation of `_within` on area (verified: `_within(seed,cand)` true ⇔ `cand.area ≤ seed.area/(1-tol)`), so no valid match is skipped and no invalid one scanned.
- **Time-adjustment test preserved.** The stale-comp tests build pools via `pool_around`, which leaves `bedrooms=None`; `_same_unit` refuses to collapse unknown-bedroom rows, so those comps survive dedup untouched. Not luck — it is the conservative unknown-bedrooms rule doing its job.
- **Determinism.** Total sort order `(area, price/m², listing_id)` + stable sort + `max` tiebreak on `(completeness, date, listing_id)` → identical output for identical input, including literal duplicate rows.
- **Project rules.** No hardcoded pricing weights added (`DEDUP_TOLERANCE=0.01` is a dedup tolerance, not an attribute premium; `NoHardcodedWeights` scan passes). Evidence-object + real-`source_url` invariants still hold (`HardInvariants` passes). No secrets in the diff; `.gitignore` additions correctly exclude bulky raw source dirs while whitelisting the committed geocoded CSV.
- **Frontend theme/map logic.** `useTheme` persists explicit choice and only follows the OS when unset. The `setStyle({diff:false})` → `once("style.load")` re-add path is sound: sources are dropped and unconditionally re-added, DOM markers survive and are restyled, layer-scoped click/hover handlers persist across `setStyle` (correct maplibre behaviour), and selection/view are restored from refs. `esc()` sanitises all popup HTML.

---

## Test evidence
`python -m pytest tests/test_engine_edge_cases.py app/engine/test_pipeline.py -q` → **63 passed** (10.7 s), including the new `NearDuplicateCollapse` class and the `AreaBoundaries` guard tests.

**Recommendation: GO.** Ship the four logic changes. Fold the HIGH-1 `/comparables` one-line fix into the same push since `main.py` is already being committed.
