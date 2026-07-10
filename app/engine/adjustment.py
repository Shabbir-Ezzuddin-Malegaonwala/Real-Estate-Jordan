"""Adjustment Engine — derives attribute premiums FROM the market, then normalises comps.

HARD RULE (MASTER-PLAN 2d-2): there is not a single hardcoded attribute premium in
this file. Categorical premiums (view, parking, elevator, finish) come from paired
median differentials across the comp pool; continuous premiums (floor, age, size) come
from an OLS slope of price/m2 against the attribute. Each premium is emitted as a
DerivedPremium carrying its method, sample size, and confidence, recomputed every run.

Comps are then normalised toward the subject: first time-adjusted with the CBJ index
(Adjusted = Original x currentIndex / indexAtSale), then attribute-adjusted using the
derived premiums, exactly per the client PDF adjustment grid.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from . import config
from .data import PriceIndex
from .models import ComparableRecord, DerivedPremium, Listing, Subject
from .stats import (coeff_of_variation, median, months_between, ols_slope,
                    quarter_of, pct)

_CATEGORICAL = {
    "view": "View",
    "parking": "Covered parking",
    "elevator": "Elevator",
    "finish_quality": "Finish quality",
    "furnishing": "Furnishing",
}
_CONTINUOUS = {
    "floor_level": "Floor level",
    "building_age_years": "Building age",
    "area_m2": "Size (per m²)",
    # NB: DEM elevation is NOT a within-submarket premium — portals geocode to the
    # submarket centroid, so elevation has ~zero intra-submarket variance. It varies
    # BETWEEN submarkets, so it is surfaced as neighborhood-level context (see
    # recommendation._spatial_context) and would enter a cross-submarket hedonic (Phase 3).
}
# Neither portal exposes total_floors, so this is absolute floor, not floor-position-in-building.
_FLOOR_NOTE = "absolute floor_level (total_floors unavailable from portals)"
_KNOWN_UNKNOWN = {"unknown", "u", "", None}


def _confidence_from(sample: int, dispersion: float) -> str:
    if sample >= config.MIN_COMPS_FULL_CONFIDENCE and dispersion < 0.25:
        return "High"
    if sample >= config.MIN_PAIR_GROUP + 2 and dispersion < 0.40:
        return "Medium"
    return "Low"


def _categorical_schedule(pool: list[Listing], attr: str, label: str,
                          computed_date: str, neighborhood: str,
                          property_type: str) -> tuple[dict[str, float], list[DerivedPremium]]:
    """Median differential of each level vs the pool's modal baseline level."""
    by_level: dict[str, list[float]] = {}
    for l in pool:
        lvl = getattr(l, attr)
        if lvl in _KNOWN_UNKNOWN:
            continue
        by_level.setdefault(lvl, []).append(l.price_per_m2)

    known = {lvl: v for lvl, v in by_level.items() if len(v) >= config.MIN_PAIR_GROUP}
    if len(known) < 2:
        return {}, []

    baseline = max(known, key=lambda k: len(known[k]))
    base_med = median(known[baseline])
    schedule = {baseline: 0.0}
    records: list[DerivedPremium] = []
    if not base_med:
        return {}, []

    for lvl, vals in known.items():
        if lvl == baseline:
            continue
        frac = (median(vals) - base_med) / base_med
        disp = max(coeff_of_variation(vals), coeff_of_variation(known[baseline]))
        conf = _confidence_from(min(len(vals), len(known[baseline])), disp)
        schedule[lvl] = frac
        records.append(DerivedPremium(
            factor=f"{label}: {lvl} vs {baseline}",
            derived_premium=round(frac, 4),
            method=f"paired median differential (n_{lvl}={len(vals)}, n_{baseline}={len(known[baseline])})",
            source="listings (portal asking prices)",
            confidence=conf,
            sample_size=len(vals) + len(known[baseline]),
            computed_date=computed_date,
            neighborhood=neighborhood,
            property_type=property_type,
            notes=f"baseline={baseline}",
        ))
    return schedule, records


def _finish_residuals(pool: list[Listing]) -> dict[str, float]:
    """Median price/m² per finish class — used to strip the dominant confounder from
    continuous slopes so floor/age/size don't just re-measure the finish mix."""
    by_finish: dict[str, list[float]] = {}
    for l in pool:
        if l.finish_quality not in _KNOWN_UNKNOWN and l.price_per_m2:
            by_finish.setdefault(l.finish_quality, []).append(l.price_per_m2)
    return {k: median(v) for k, v in by_finish.items() if len(v) >= config.MIN_PAIR_GROUP}


def _continuous_premium(pool: list[Listing], attr: str, label: str,
                        computed_date: str, neighborhood: str,
                        property_type: str) -> tuple[Optional[float], Optional[DerivedPremium]]:
    """Fraction of pool-median price/m2 gained per unit of the attribute (OLS slope).

    Fitted on price/m² residualised by finish class (a cheap partial control) so the
    slope reflects the attribute itself, not its correlation with finishing spec.
    """
    finish_med = _finish_residuals(pool)
    base = median([l.price_per_m2 for l in pool if l.price_per_m2])
    if not base:
        return None, None
    pts = []
    for l in pool:
        x = getattr(l, attr)
        if x is None or l.price_per_m2 is None:
            continue
        control = finish_med.get(l.finish_quality, base)
        residual = l.price_per_m2 - control + base  # re-centre on pool base
        pts.append((float(x), residual))
    if len(pts) < config.MIN_SLOPE_POINTS:
        return None, None
    slope = ols_slope(pts)
    if slope is None:
        return None, None
    frac_per_unit = slope / base
    disp = coeff_of_variation([y for _, y in pts])
    # Univariate slopes on confounded observational data are never "High" — a stable
    # multivariate estimate is Phase 2. Cap at Medium to avoid overstating certainty.
    conf = "Medium" if _confidence_from(len(pts), disp) == "High" else _confidence_from(len(pts), disp)
    note = "fraction of median price/m² per unit"
    if attr == "floor_level":
        note += f"; {_FLOOR_NOTE}"
    rec = DerivedPremium(
        factor=label,
        derived_premium=round(frac_per_unit, 5),
        method=f"OLS slope of price/m² vs {attr} (n={len(pts)})",
        source="listings (portal asking prices)",
        confidence=conf,
        sample_size=len(pts),
        computed_date=computed_date,
        neighborhood=neighborhood,
        property_type=property_type,
        notes=note,
    )
    return frac_per_unit, rec


class PremiumSet:
    """Everything derived from one neighborhood+type pool, ready to apply to comps."""

    def __init__(self):
        self.categorical: dict[str, dict[str, float]] = {}
        self.continuous: dict[str, float] = {}
        self.records: list[DerivedPremium] = []
        self.suppressed: list[str] = []   # premiums dropped by the plausibility gate (M1)

    def as_records(self) -> list[dict]:
        return [r.to_dict() for r in self.records]


# Economic priors (review M1). Ordinal quality tiers must be monotone non-decreasing in
# price; age must not raise value. A derived premium violating its prior is a small-sample /
# noisy-label artifact (e.g. text-mined "luxury" over-applied as marketing) — we DROP it
# rather than ship an economically perverse adjustment.
_FINISH_RANK = {"basic": 0, "standard": 1, "high": 2, "luxury": 3}


def _apply_plausibility_gate(ps: "PremiumSet") -> None:
    sched = ps.categorical.get("finish_quality")
    if sched:
        pts = sorted((_FINISH_RANK[k], v) for k, v in sched.items() if k in _FINISH_RANK)
        if len(pts) >= 2 and any(pts[i][1] > pts[i + 1][1] + 1e-9 for i in range(len(pts) - 1)):
            ps.categorical.pop("finish_quality")
            ps.records = [r for r in ps.records if r.factor != "Finish quality"]
            ps.suppressed.append(
                "Finish quality — derived schedule was non-monotonic across tiers "
                "(higher tier priced below a lower one), economically implausible on the "
                "noisy text-mined label; not applied.")
    age = ps.continuous.get("building_age_years")
    if age is not None and age > 0:
        ps.continuous.pop("building_age_years")
        ps.records = [r for r in ps.records if r.factor != "Building age"]
        ps.suppressed.append(
            "Building age — derived slope was positive (age raising value); economically "
            "implausible ceteris paribus, not applied.")


_DOWNGRADE = {"High": "Medium", "Medium": "Low", "Low": "Low"}


def _to_citywide(rec: DerivedPremium) -> DerivedPremium:
    rec.confidence = _DOWNGRADE.get(rec.confidence, "Low")
    rec.neighborhood = "citywide"
    rec.notes = (rec.notes + "; " if rec.notes else "") + "citywide fallback — submarket sample insufficient"
    return rec


def derive_premiums(pool: list[Listing], subject: Subject, as_of: date,
                    citywide: Optional[list[Listing]] = None) -> PremiumSet:
    """Derive premiums from the submarket pool; fall back to the citywide pool (flagged,
    confidence-downgraded) for attributes too sparse in the submarket to derive locally."""
    computed = as_of.isoformat()
    ps = PremiumSet()
    for attr, label in _CATEGORICAL.items():
        schedule, recs = _categorical_schedule(
            pool, attr, label, computed, subject.neighborhood, subject.property_type)
        if not schedule and citywide:
            schedule, recs = _categorical_schedule(
                citywide, attr, label, computed, "citywide", subject.property_type)
            recs = [_to_citywide(r) for r in recs]
        if schedule:
            ps.categorical[attr] = schedule
            ps.records.extend(recs)
    for attr, label in _CONTINUOUS.items():
        frac, rec = _continuous_premium(
            pool, attr, label, computed, subject.neighborhood, subject.property_type)
        if rec is None and citywide:
            frac, rec = _continuous_premium(
                citywide, attr, label, computed, "citywide", subject.property_type)
            if rec is not None:
                rec = _to_citywide(rec)
        if rec is not None:
            ps.continuous[attr] = frac
            ps.records.append(rec)
    _apply_plausibility_gate(ps)   # M1: drop economically perverse premiums
    return ps


def index_is_current(index: PriceIndex, as_of: date,
                     indicator: str = "cbj_repi_apartment") -> bool:
    """The index must cover a period near `as_of`, else time-adjustment is unsafe."""
    latest = index.latest(indicator)
    if latest is None:
        return False
    return months_between(_quarter_to_date(latest[0]), as_of) <= config.INDEX_STALE_MONTHS


def _quarter_to_date(period: str) -> date:
    period = period.strip()
    if "-Q" in period:
        y, q = period.split("-Q")
        return date(int(y), (int(q) - 1) * 3 + 1, 1)
    return date(int(period[:4]), 1, 1)


def _time_adjust(comp: Listing, index: PriceIndex, as_of: date,
                 indicator: str) -> tuple[float, Optional[dict]]:
    ppm2 = comp.price_per_m2
    if comp.listing_date is None or not index.has(indicator):
        return ppm2, None
    if not index_is_current(index, as_of, indicator):
        return ppm2, None  # stale index — degrade gracefully, never adjust backward
    age_months = months_between(comp.listing_date, as_of)
    if age_months <= config.IDEAL_RECENCY_MONTHS:
        return ppm2, None
    at_sale = index.value_at(quarter_of(comp.listing_date), indicator)
    latest = index.latest(indicator)
    if not at_sale or latest is None:
        return ppm2, None
    factor = latest[1] / at_sale
    adjusted = ppm2 * factor
    entry = {
        "factor": "Time (market movement)",
        "adjustment": pct(factor - 1),
        "method": f"CBJ index {quarter_of(comp.listing_date)}->{latest[0]} "
                  f"({at_sale:.1f}->{latest[1]:.1f})",
        "from_ppm2": round(ppm2, 1),
        "to_ppm2": round(adjusted, 1),
    }
    return adjusted, entry


def _categorical_adj(attr: str, schedule: dict[str, float],
                     subject: Subject, comp: Listing) -> Optional[float]:
    s_lvl, c_lvl = getattr(subject, attr), getattr(comp, attr)
    if s_lvl in _KNOWN_UNKNOWN or c_lvl in _KNOWN_UNKNOWN or s_lvl == c_lvl:
        return None
    if s_lvl not in schedule and c_lvl not in schedule:
        return None
    return schedule.get(s_lvl, 0.0) - schedule.get(c_lvl, 0.0)


def _continuous_adj(attr: str, frac_per_unit: float,
                    subject: Subject, comp: Listing) -> Optional[float]:
    s_val, c_val = getattr(subject, attr), getattr(comp, attr)
    if s_val is None or c_val is None or s_val == c_val:
        return None
    return frac_per_unit * (float(s_val) - float(c_val))


def normalize_comp(comp: Listing, subject: Subject, premiums: PremiumSet,
                   index: PriceIndex, as_of: date, similarity: float,
                   indicator: str = "cbj_repi_apartment") -> ComparableRecord:
    original = comp.price_per_m2
    time_adjusted, time_entry = _time_adjust(comp, index, as_of, indicator)
    adjustments: list[dict] = []
    if time_entry:
        adjustments.append(time_entry)

    signed: list[float] = []
    for attr, label in _CATEGORICAL.items():
        schedule = premiums.categorical.get(attr)
        if not schedule:
            continue
        adj = _categorical_adj(attr, schedule, subject, comp)
        if adj is None or abs(adj) < 1e-9:
            continue
        adj = _clip(adj, config.CATEGORICAL_ADJ_CAP)
        signed.append(adj)
        adjustments.append({
            "factor": label, "adjustment": pct(adj), "method": "derived median differential",
            "detail": f"comp={getattr(comp, attr)} -> subject={getattr(subject, attr)}",
        })

    for attr, label in _CONTINUOUS.items():
        frac = premiums.continuous.get(attr)
        if frac is None:
            continue
        adj = _continuous_adj(attr, frac, subject, comp)
        if adj is None or abs(adj) < 1e-9:
            continue
        cap = config.SIZE_ADJ_CAP if attr == "area_m2" else config.CONTINUOUS_ADJ_CAP
        adj = _clip(adj, cap)
        signed.append(adj)
        adjustments.append({
            "factor": label, "adjustment": pct(adj), "method": "derived OLS slope",
            "detail": f"comp={getattr(comp, attr)} -> subject={getattr(subject, attr)}",
        })

    # Additive appraisal-grid net (not multiplicative — avoids compounding blow-ups),
    # then bound the net so a heavily-different comp cannot dominate.
    net = sum(signed)
    net_capped = _clip(net, config.NET_ADJ_CAP)
    if abs(net) > config.NET_ADJ_CAP + 1e-9:
        adjustments.append({
            "factor": "Net adjustment cap", "adjustment": pct(net_capped - net),
            "method": f"net |adjustment| capped at {config.NET_ADJ_CAP*100:.0f}% (comp too dissimilar)",
            "detail": f"raw net {pct(net)} -> {pct(net_capped)}",
        })
    value = time_adjusted * (1 + net_capped)

    gross = abs(net_capped)
    recency_factor = _recency_factor(comp, as_of)
    # Fewer/smaller adjustments earn more weight (PDF), but a single near-identical comp
    # must not dominate — the denominator floor caps the max/min weight ratio to ~3x.
    weight = recency_factor / (config.RECONCILIATION_WEIGHT_FLOOR + gross)
    if gross > config.NET_ADJ_RELIABILITY_FLAG:
        weight *= 0.5  # low-reliability comp per PDF: large adjustments reduce reliability
    return ComparableRecord(
        listing_id=comp.listing_id,
        neighborhood=comp.neighborhood,
        area_m2=comp.area_m2,
        original_ppm2=round(original, 1),
        time_adjusted_ppm2=round(time_adjusted, 1),
        adjusted_ppm2=round(value, 1),
        gross_adjustment=round(gross, 4),
        reconciliation_weight=round(weight, 4),
        similarity=round(similarity, 3),
        listing_date=comp.listing_date.isoformat() if comp.listing_date else None,
        adjustments=adjustments,
        source={"name": comp.source_name, "url": comp.source_url,
                "capture_date": comp.capture_date.isoformat() if comp.capture_date else "unknown"},
        seller_type=comp.seller_type,
        bedrooms=comp.bedrooms, bathrooms=comp.bathrooms, floor_level=comp.floor_level,
        building_age_years=comp.building_age_years, view=comp.view, parking=comp.parking,
        furnishing=comp.furnishing, price_jd=comp.price_jd,
    )


def _recency_factor(comp: Listing, as_of: date) -> float:
    if comp.listing_date is None:
        return 0.6
    age = months_between(comp.listing_date, as_of)
    return max(0.3, 1.0 - age / (config.RECENCY_WINDOW_MONTHS * 1.5))


def _clip(x: float, cap: float) -> float:
    return max(-cap, min(cap, x))
