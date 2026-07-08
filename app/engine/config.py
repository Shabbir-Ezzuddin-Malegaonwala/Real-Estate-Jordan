"""Methodology parameters — ALGORITHM knobs and DOCUMENTED assumptions only.

HARD RULE (MASTER-PLAN 2d-2): this file contains NO attribute pricing weights.
There is no `view -> +8%` here and there never will be. Every attribute premium
(view, floor, parking, age, finish, size) is DERIVED from the market at runtime by
`adjustment.py` and carries its own method + sample size + confidence.

What lives here instead:
  * comparable-selection knobs (what counts as "recent", "similar size") — from the
    client PDF's sales-comparison section, not a price.
  * the ask-to-transaction gap — an explicitly DOCUMENTED assumption (client PDF,
    5-15%), applied uniformly and surfaced as its own sourced evidence object.
  * confidence-scoring weights — these size the *reliability* score, never the price.
"""

from __future__ import annotations

# --- Comparable selection (client PDF 2.1: recency 6-12 mo ideal; thin markets 12-18) ---
RECENCY_WINDOW_MONTHS = 18       # widest age a listing may have and still be a comp
IDEAL_RECENCY_MONTHS = 12        # beyond this a comp is "stale" and gets time-adjusted
SIZE_BAND_TOLERANCE = 0.45       # prefer comps within +/-45% of subject area_m2
SIZE_BAND_WIDEN_STEP = 0.25      # relax band by this much when too few comps
MIN_COMPS = 3                    # below this the market is "thin" (PDF: reliability drops)
MIN_COMPS_FULL_CONFIDENCE = 8    # at/above this, data density stops penalising confidence
TARGET_COMPS = 12                # stop selecting once we have this many strong comps

# --- Near-duplicate collapse (comparable_analysis.collapse_near_duplicates) ---
# Portal data is heavily cross-syndicated: the SAME physical unit is posted on Bayut,
# OpenSooq and Facebook (and relisted over time) under different listing_ids. Counting it
# N times over-weights that price and inflates confidence (QA OBS-3). Real cross-posts in
# the corpus are near-EXACT (identical bedrooms, area and price); this tight tolerance on
# BOTH area and price/m² absorbs only rounding/formatting noise, so two genuinely distinct
# units that merely look similar (e.g. 172 vs 175 m²) are never merged. Rows collapse only
# when bedrooms are known-and-equal AND both area and price/m² fall within tolerance.
DEDUP_TOLERANCE = 0.01

# --- Paired-differential derivation (adjustment.py) ---
MIN_PAIR_GROUP = 3               # need >=3 listings on each side to derive a premium
MIN_SLOPE_POINTS = 6            # need >=6 (x,y) points to fit a continuous slope

# --- Adjustment caps (client PDF: "large adjustments reduce reliability").
# Adjustments are summed ADDITIVELY (appraisal-grid convention), each bounded, and the
# net bounded again. Univariate premiums are confounded until a multivariate hedonic
# model exists (Phase 2, needs 300-500 txns); caps keep v1 adjustments modest and honest.
CATEGORICAL_ADJ_CAP = 0.20       # max |adjustment| for one categorical attribute
CONTINUOUS_ADJ_CAP = 0.12        # max |adjustment| for floor / age
SIZE_ADJ_CAP = 0.10              # max |adjustment| for the per-m² size curve
NET_ADJ_CAP = 0.40               # max |sum of adjustments| for a single comp
NET_ADJ_RELIABILITY_FLAG = 0.30  # comps beyond this net adjustment are flagged low-reliability

# Reconciliation weight = recency / (FLOOR + gross_adjustment). A larger floor caps how
# much a single near-identical comp can dominate the weighted mean (max/min ratio ~3x).
RECONCILIATION_WEIGHT_FLOOR = 0.20

# --- Submarket-median anchor (recommendation._reconcile_to_submarket) ---
# The top-N similarity shortlist is a small, high-variance draw. Once the corpus is dense
# (50k+ portal rows) it can settle on an unrepresentative price pocket and pull the point
# estimate off the submarket's true centre in EITHER direction. When the pool is a genuine
# super-set of the selection, the comp value is blended toward the pool's robust median by
# inverse-variance weighting (each estimate counts as 1/SE² — no price constant). Engage only
# once the pool is at least twice the selection; below that the comps already ARE the
# submarket and its median adds nothing.
ANCHOR_MIN_POOL = 2 * TARGET_COMPS

# --- Ask-to-transaction calibration (DOCUMENTED assumption, client PDF; NOT derived) ---
# Asking prices sit above transaction prices; the PDF documents a 5-15% gap.
# Applied uniformly to the asking-derived value and surfaced as sourced evidence.
ASK_TO_TX_GAP_LOW = 0.05
ASK_TO_TX_GAP_HIGH = 0.15
ASK_TO_TX_SOURCE = {
    "name": "Client methodology PDF — Real Estate Pricing Strategies",
    "url": "internal://Real Estate Pricing Strategies.pdf",
    "capture_date": "2026-07-07",
}

# --- Outlier plausibility (raw portal data carries 0-price and whole-building placeholders) ---
# Below these price/m² floors a "sale"/"rent" row is a data error, not a market signal.
# Above the floor, a log-space MAD filter (stats.robust_keep) trims the extreme tails so
# medians and the comp set are not distorted.
MIN_PLAUSIBLE_SALE_PPM2 = 250.0    # premium Amman submarkets never transact below this
MIN_PLAUSIBLE_RENT_PPM2 = 1.0      # monthly rent per m²

# --- Time adjustment: CBJ index must actually cover a period near `as_of` ---
# The index publishes with a lag (real data ends 2021-Q3). If the latest index is more
# than this many months before the run date, time-adjustment is DISABLED (never adjust a
# comp backward to a stale index) and the gap is surfaced as a caveat, not fabricated.
INDEX_STALE_MONTHS = 15

# --- Income approach ---
# Required gross yield is DERIVED from the market (median annual rent / median sale ppm2).
# This documented floor only guards the divide-by-zero / no-rental-data case and is
# surfaced as low-confidence evidence when used.
FALLBACK_REQUIRED_GROSS_YIELD = 0.065

# Portal rent quotes mix MONTHLY and ANNUAL asking prices with no period field (Jordanian
# portals, OpenSooq especially, quote annual rent ~60% of the time). Amman monthly apartment
# rent tops out around 12-15 JD/m²/month even for luxury; annual quotes land ~12× higher, so
# the rent/m² distribution is bimodal with a natural valley near here. A raw rent/m² above this
# cap is read as an annual quote and divided by 12; if still above the cap it is a sale-price
# contamination and dropped. DOCUMENTED heuristic (histogram valley), not a price weight.
RENT_MONTHLY_MAX_PPM2 = 15.0

# --- Confidence scoring weights (size the RELIABILITY score, never the price) ---
CONFIDENCE_WEIGHTS = {
    "data_density": 0.28,       # how many comps
    "dispersion": 0.24,         # spread of adjusted comps
    "recency": 0.18,            # how fresh the comps are
    "method_agreement": 0.18,   # do comparison / cost / income converge
    "source_quality": 0.12,     # H/M/L trust of the comp sources
}
CONFIDENCE_H_THRESHOLD = 0.70
CONFIDENCE_M_THRESHOLD = 0.45

# Future-signal saturation for the decomposed-confidence "future_signals" component: the
# development score (Σ proximity×timeline×source_trust, evidence.future_signal_evidence) at or
# above which the future story counts as fully evidenced (maps to 100/100). A reliability-scale
# knob, NOT a price weight — the score itself is derived from collected evidence_items at runtime.
FUTURE_SIGNAL_SATURATION = 3.0

# Confidence-interval half-width floor/ceiling as a fraction of the point estimate.
# The actual width is data-driven (weighted comp dispersion); these only bound it so a
# freak-tight or freak-wide sample never produces an absurd range.
CI_MIN_HALF_WIDTH = 0.04
CI_MAX_HALF_WIDTH = 0.35

# Thin-market irreducible uncertainty: a handful of near-identical comps gives FALSE
# precision. Below MIN_COMPS, floor the interval's base uncertainty so the range honestly
# reflects that few comps cannot pin a price tightly (PDF: thin markets are less reliable).
THIN_MARKET_BASE_UNCERTAINTY = 0.15

# --- Similarity ranking (orders comps for selection; reconciliation weight is separate
#     and derived from each comp's own adjustment footprint in adjustment.py) ---
SIMILARITY_WEIGHTS = {
    "size": 0.35,
    "recency": 0.25,
    "attribute_match": 0.25,
    "distance": 0.15,
}

TARGET_NEIGHBORHOODS = ["Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"]

# Ordinal ladder for finish quality (used to derive per-step premium, not to price it).
FINISH_LADDER = ["basic", "standard", "high", "luxury"]
