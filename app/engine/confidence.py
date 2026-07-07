"""Confidence Engine — scores recommendation RELIABILITY and produces a range.

Distinct from source-trust (which is per-row collection metadata). Inputs, per the
client PDF confidence-score table: data density, price dispersion, recency, cross-method
agreement, and source quality. Output: H/M/L + numeric + a confidence interval whose
width is driven by the actual weighted dispersion of the adjusted comps.
"""

from __future__ import annotations

from . import config
from .models import ComparableRecord, ConfidenceResult
from .stats import months_between, weighted_std
from datetime import date


def _density_score(n: int) -> float:
    if n >= config.MIN_COMPS_FULL_CONFIDENCE:
        return 1.0
    if n <= 1:
        return 0.1
    span = config.MIN_COMPS_FULL_CONFIDENCE - 1
    return round(0.1 + 0.9 * (n - 1) / span, 3)


def _dispersion_score(cv: float) -> float:
    return round(max(0.0, 1.0 - cv / 0.35), 3)  # cv >= 35% -> 0


def _recency_score(comps: list[ComparableRecord], as_of: date) -> float:
    ages = []
    for c in comps:
        if c.listing_date:
            ages.append(months_between(date.fromisoformat(c.listing_date), as_of))
    if not ages:
        return 0.5
    avg = sum(ages) / len(ages)
    return round(max(0.0, 1.0 - avg / config.RECENCY_WINDOW_MONTHS), 3)


def _agreement_score(method_values: dict) -> float:
    vals = [v for v in (method_values.get("comparison"),
                        method_values.get("cost_floor"),
                        method_values.get("income_ceiling")) if v]
    if len(vals) < 2:
        return 0.5
    spread = (max(vals) - min(vals)) / (sum(vals) / len(vals))
    return round(max(0.0, 1.0 - spread / 0.6), 3)  # >60% spread -> 0


def _source_score(comps: list[ComparableRecord]) -> float:
    # confidence chip lives on each comp's source; infer from portal trust proxy.
    trust = {"H": 1.0, "High": 1.0, "M": 0.6, "Medium": 0.6, "L": 0.3, "Low": 0.3}
    scores = [trust.get(c.source.get("confidence", "M"), 0.6) for c in comps]
    return round(sum(scores) / len(scores), 3) if scores else 0.5


def score(comps: list[ComparableRecord], adjusted_cv: float, method_values: dict,
          point_ppm2: float, as_of: date) -> ConfidenceResult:
    components = {
        "data_density": _density_score(len(comps)),
        "dispersion": _dispersion_score(adjusted_cv),
        "recency": _recency_score(comps, as_of),
        "method_agreement": _agreement_score(method_values),
        "source_quality": _source_score(comps),
    }
    w = config.CONFIDENCE_WEIGHTS
    numeric = round(sum(w[k] * components[k] for k in w), 3)

    if numeric >= config.CONFIDENCE_H_THRESHOLD:
        label = "H"
    elif numeric >= config.CONFIDENCE_M_THRESHOLD:
        label = "M"
    else:
        label = "L"

    low, high = _interval(comps, point_ppm2, numeric, adjusted_cv)
    return ConfidenceResult(label=label, numeric=numeric,
                            interval_low_ppm2=round(low, 1),
                            interval_high_ppm2=round(high, 1),
                            components=components)


def _interval(comps: list[ComparableRecord], point: float, numeric: float,
              adjusted_cv: float) -> tuple[float, float]:
    """Half-width = observed weighted dispersion widened as confidence falls."""
    if comps:
        wstd = weighted_std([c.adjusted_ppm2 for c in comps],
                            [c.reconciliation_weight for c in comps])
        base = wstd / point if point else adjusted_cv
    else:
        base = adjusted_cv
    if len(comps) < config.MIN_COMPS:
        base = max(base, config.THIN_MARKET_BASE_UNCERTAINTY)  # no false precision
    widen = 1.0 + (1.0 - numeric)          # low confidence -> up to 2x width
    half = base * widen
    half = max(config.CI_MIN_HALF_WIDTH, min(config.CI_MAX_HALF_WIDTH, half))
    return point * (1 - half), point * (1 + half)
