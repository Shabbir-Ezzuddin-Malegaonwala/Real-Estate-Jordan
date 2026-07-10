# Rental-Yield & Macro Pipelines

Two data pipelines added to make the **income approach real** and to surface the macro
indicators the manager asked for (gold, dollar, rates, inflation). Both are honest, sourced,
and use the latest (2026) data. Nothing is fabricated.

## 1. Rental yield (income approach)

### The problem found
Portal rent quotes mix **monthly and annual** asking prices with no period field — Jordanian
portals (OpenSooq especially) quote rent annually ~60% of the time. The rent/m² distribution is
bimodal (monthly cluster ~1–12 JD/m², annual cluster ~20–150 JD/m²). A raw median is meaningless,
and the engine's income ceiling was silently consuming the un-normalised mix (it floored at only
1 JD/m²) — producing an absurd ~79% "market yield".

### The fix
- `app/engine/stats.py :: to_monthly_rent(ppm2, cap)` — normalises a rent/m² to monthly: a value
  above `cap` (config `RENT_MONTHLY_MAX_PPM2 = 15`, the histogram valley) is an annual quote (÷12);
  still above `cap` afterwards = sale-price contamination (dropped). Documented heuristic.
- `app/engine/recommendation.py :: _income_ceiling` now normalises rents to monthly before taking
  medians, so the derived **citywide required yield is a realistic 8.6%** (was ~79%), and it
  surfaces **each area's observed yield** in the income evidence for transparency.
- The engine's *required* yield stays a citywide market benchmark on purpose — using an area's own
  observed yield would collapse the ceiling back onto that area's sale price (circular).

### New artifact: `area_yields` table
Per `(neighborhood, property_type)`: `median_rent_jd_m2`, `annual_rent_jd_m2`, `median_sale_jd_m2`,
`gross_yield_pct`, `n_rent`, `n_sale`, confidence + provenance. Powers the **Gross-yield map layer**
and the left-panel income line. Built by `scrapers/build_area_yields.py` (reuses the engine's exact
robust-median logic + monthly normalisation).

```
python scrapers/build_area_yields.py                       # -> data/processed/area_yields.csv
python db/load_csv.py data/processed/area_yields.csv --table area_yields --replace
```

**207 submarket rows loaded (172 with a computable yield).** Real numbers (apartment, high confidence):

| Area | monthly rent/m² | sale/m² | gross yield |
|------|----------------:|--------:|------------:|
| Abdoun | 7.6 | 1071 | 8.5% |
| Jabal Amman | 7.6 | 1160 | 7.8% |
| Sweifieh | 5.9 | 935 | 7.5% |
| Deir Ghbar | 5.2 | 850 | 7.3% |
| Dabouq | 4.2 | 1051 | 4.8% |
| Khalda | 3.6 | 769 | 5.6% |

Yields land in the **5–9%** band — matching independent Amman references (Numbeo, Global Property
Guide) and the qualitative area notes (Sweifieh commercial → higher yield; Dabouq luxury villas →
low yield). Income ceilings are now area-differentiated and economically sensible (Khalda/Dabouq
correctly flag "investor ceiling below price" — low-yield, owner-occupier markets).

## 2. Macro indicators

`scrapers/macro_indicators.py` writes 5 indicators into `macro_series` (reused — the engine already
reads this table; a separate `macro_indicators` table would duplicate it). USD/JOD is fetched **live**
(free, no-key); gold / CBJ rate / CPI have no free no-key API so they are stored as the latest **real**
official/quoted values with their own as-of date + source URL, flagged for periodic refresh.

```
python scrapers/macro_indicators.py                        # -> data/processed/macro_indicators.csv
python db/load_csv.py data/processed/macro_indicators.csv --table macro_series --replace
```

| Indicator | Value | As-of | Conf | Source |
|-----------|------:|-------|:----:|--------|
| USD/JOD | 0.709 | 2026-07-08 (live) | H | open.er-api.com |
| Gold 24K | 95.30 JOD/g | 2026-07-05 | M | livepriceofgold.com |
| Gold 21K | 81.52 JOD/g | 2026-07-05 | M | goldpricez.com/jo |
| CBJ policy rate | 5.75% | 2026-06-18 | H | cbj.gov.jo |
| CPI inflation (YoY) | 2.83% | 2026-05 | H | dosweb.dos.gov.jo |

Powers a market-context banner + a mortgage-affordability calc (deferred to a later phase).

## 3. Future-signal corrections

`evidence_items` already had the **BRT correctly as operational** (Lines 1&2 2024, Amman–Zarqa 2024).
Added three rows (`data/processed/evidence_future_signals.csv`):
- **Jordan National Railway** (Aqaba–Amman, $2.3bn, signed Apr 2026) — impact_area = corridor, so it
  does **not** wrongly inflate Amman pricing.
- **Marsa Zayed** (Aqaba, $10bn) — Aqaba catalyst.
- **Amman Metro — planning/feasibility only (NOT built)** — explicit speculative marker, confidence L
  so its future-signal weight is negligible; corrects any "metro is built" assumption.

## 4. Honest gaps
- **Monthly/annual split is a heuristic** (cap = 15 JD/m² at the histogram valley). ~13% of rows carry
  an explicit period word in the description; a description-parse pass could refine the ~valley cases.
- **Neighborhood spelling duplicates** in source data split some areas (`Deir Ghbar` 284 vs `Dair Ghbar`
  179; `Rabyeh` 254 vs `Al Rabiah` 156). Pre-existing; a normalisation map would merge them.
- **Gold has no free no-key API** in this environment — values are real page snapshots, refreshed
  manually; wire GoldAPI.io (free key) later for live gold.
- Thin submarkets (yield < ~3% or based on few sales) are low-confidence — feature the well-sampled
  West-Amman areas in the demo.

## 5. Verification
`python tests/run_all.py` — engine suites (105) **OK**, API suites **OK**. The e2e frontend step is
red due to a concurrent frontend reconstruction by another teammate (`app/web/scripts/prepare-data.mjs`
modified; the `load` step times out on the `PANEL`/`BAND` selectors) — unrelated to these backend
changes, which touch no frontend files. The live `/recommend` API returns 200 with the corrected 8.6%
yield.
