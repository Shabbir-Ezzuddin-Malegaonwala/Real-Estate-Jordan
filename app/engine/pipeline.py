"""Single entrypoint: recommend(subject, data_bundle) -> RecommendationResult.

Order: Sources → (DataBundle) → Comparable Analysis → Adjustment → Evidence →
Confidence → Recommendation. All business logic stays inside this package.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional

from . import adjustment, comparable_analysis, config, recommendation
from .data import DataBundle
from .models import RecommendationResult, Subject
from .stats import robust_keep


def _citywide_pool(sales: list, subject: Subject) -> list:
    """Same-property-type sales across all submarkets, outlier-filtered — the fallback
    basis when a submarket is too sparse to derive an attribute premium locally."""
    raw = [l for l in sales if l.property_type == subject.property_type and l.price_per_m2]
    keep = robust_keep([l.price_per_m2 for l in raw], config.MIN_PLAUSIBLE_SALE_PPM2)
    return [l for l, k in zip(raw, keep) if k]


def recommend(subject: Subject, data_bundle: DataBundle,
              as_of: Optional[date] = None) -> RecommendationResult:
    as_of = as_of or data_bundle.as_of or date.today()

    area = subject.area_m2
    if area is not None and (not math.isfinite(area) or area <= 0):
        return recommendation.unpriceable(
            subject, as_of, "Invalid subject area",
            f"Subject area_m2={area!r} is not a positive finite number; cannot price. "
            "Provide a positive area, or leave it unset to price without a size adjustment.")

    sales = data_bundle.sales()

    scored, notes = comparable_analysis.select_comparables(sales, subject, as_of)

    pool = comparable_analysis.neighborhood_pool(sales, subject)
    premiums = adjustment.derive_premiums(pool, subject, as_of, _citywide_pool(sales, subject))

    comps = [adjustment.normalize_comp(listing, subject, premiums,
                                       data_bundle.price_index, as_of, sim)
             for listing, sim in scored]
    comps.sort(key=lambda c: c.reconciliation_weight, reverse=True)

    return recommendation.assemble(subject, data_bundle, comps, premiums, notes, as_of, pool)
