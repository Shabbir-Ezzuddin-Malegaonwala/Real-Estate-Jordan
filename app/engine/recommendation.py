"""Recommendation Engine — reconciles the three approaches into the launch-price band.

Sales comparison (weighted adjusted comps) is the anchor for active residential markets.
The cost approach sets the floor (never sell below rebuild cost); the income approach
sets the investor ceiling (rent ÷ required yield). Convergence raises confidence;
divergence becomes a surfaced risk — exactly the client PDF's integrated framework.
"""

from __future__ import annotations

from datetime import date
from statistics import pstdev
from typing import Optional

from . import config, confidence, evidence
from .adjustment import index_is_current
from .data import DataBundle
from .models import ComparableRecord, Listing, RecommendationResult, Subject
from .stats import coeff_of_variation, median, robust_keep, weighted_mean, weighted_std


def _clean(values: list[float], floor: float) -> list[float]:
    keep = robust_keep(values, floor)
    return [v for v, k in zip(values, keep) if k]


def _comparison_value(comps: list[ComparableRecord]) -> Optional[float]:
    if not comps:
        return None
    return weighted_mean([c.adjusted_ppm2 for c in comps],
                         [c.reconciliation_weight for c in comps])


def _reconcile_to_submarket(pool: list[Listing], comps: list[ComparableRecord],
                            comp_draw: float) -> tuple[float, Optional[dict]]:
    """Stabilise the comp-selected value against the submarket's robust median.

    The top-N similarity shortlist is a small, high-variance draw from a large pool; once the
    corpus is dense it can settle on an unrepresentative price pocket and pull the point
    estimate off the submarket's true centre (in either direction). The robust median of ALL
    same-submarket same-type sales is a far steadier level. The two are blended by
    inverse-variance (precision) weighting — each counts as 1/SE² — and the comps' own
    attribute-adjustment ratio is carried onto the anchor so subject tailoring survives. On a
    thin pool the comps already ARE the submarket, so the draw is returned untouched.
    """
    anchor_vals = _clean([l.price_per_m2 for l in pool], config.MIN_PLAUSIBLE_SALE_PPM2)
    if len(anchor_vals) < config.ANCHOR_MIN_POOL or len(comps) < 2:
        return comp_draw, None
    weights = [c.reconciliation_weight for c in comps]
    comp_raw = weighted_mean([c.time_adjusted_ppm2 for c in comps], weights)
    if not comp_raw:
        return comp_draw, None
    var_anchor = pstdev(anchor_vals) ** 2 / len(anchor_vals)
    var_comp = weighted_std([c.adjusted_ppm2 for c in comps], weights) ** 2 / len(comps)
    if var_anchor <= 0 or var_comp <= 0:
        return comp_draw, None
    anchor_ppm2 = median(anchor_vals)
    adj_mult = comp_draw / comp_raw                       # attribute normalisation; level bias cancels
    lam = (1 / var_anchor) / (1 / var_anchor + 1 / var_comp)   # anchor's precision share
    reconciled = lam * anchor_ppm2 * adj_mult + (1 - lam) * comp_draw
    note = (f"reconciled to submarket robust median {anchor_ppm2:.0f} JD/m² "
            f"(n={len(anchor_vals)} same-type sales) via inverse-variance weighting "
            f"(anchor λ={lam:.2f}) — guards against an unrepresentative comp shortlist")
    return round(reconciled, 1), {"anchor_ppm2": round(anchor_ppm2, 1), "lambda": round(lam, 3),
                                  "note": note}


def _cost_floor(bundle: DataBundle, subject: Subject):
    bench = bundle.cost_for(subject.finish_quality)
    if bench is None or bench.midpoint is None:
        return None, None
    return bench.midpoint, bench  # new-build depreciation ~ 0


def _income_ceiling(bundle: DataBundle, subject: Subject):
    n = subject.neighborhood.strip().lower()
    t = subject.property_type
    rf, sf = config.MIN_PLAUSIBLE_RENT_PPM2, config.MIN_PLAUSIBLE_SALE_PPM2
    local_rent = _clean([l.price_per_m2 for l in bundle.rentals()
                         if l.neighborhood.strip().lower() == n and l.property_type == t], rf)
    all_rent = _clean([l.price_per_m2 for l in bundle.rentals() if l.property_type == t], rf)
    all_sale = _clean([l.price_per_m2 for l in bundle.sales() if l.property_type == t], sf)
    if not local_rent:
        return None, None, None, None

    annual_local = median(local_rent) * 12
    if all_rent and all_sale and median(all_sale):
        req_yield = (median(all_rent) * 12) / median(all_sale)
        method = (f"income approach: annual rent ÷ derived market yield "
                  f"({req_yield*100:.1f}%, citywide rents vs sales)")
        conf = "Medium"
        sources = [{"name": "listings (rentals)", "url": "internal://listings",
                    "capture_date": bundle.as_of.isoformat()}]
    else:
        req_yield = config.FALLBACK_REQUIRED_GROSS_YIELD
        method = (f"income approach: annual rent ÷ documented required yield "
                  f"({req_yield*100:.1f}%, no citywide yield derivable)")
        conf = "Low"
        sources = [config.ASK_TO_TX_SOURCE]
    ceiling = annual_local / req_yield
    return ceiling, req_yield, method, (conf, sources)


def assemble(subject: Subject, bundle: DataBundle, comps: list[ComparableRecord],
             premiums, selection_notes: list[str], as_of: date,
             pool: list[Listing]) -> RecommendationResult:
    comp_draw = _comparison_value(comps)
    if comp_draw is None:
        return _empty_result(subject, as_of, selection_notes)

    comparison_asking, anchor = _reconcile_to_submarket(pool, comps, comp_draw)
    if anchor:
        selection_notes = selection_notes + [anchor["note"]]

    mid_gap = (config.ASK_TO_TX_GAP_LOW + config.ASK_TO_TX_GAP_HIGH) / 2
    comparison_tx = comparison_asking * (1 - mid_gap)
    recommended = comparison_tx

    cost_floor, bench = _cost_floor(bundle, subject)
    income_ceiling, req_yield, income_method, income_meta = _income_ceiling(bundle, subject)

    adjusted_cv = coeff_of_variation([c.adjusted_ppm2 for c in comps])
    method_values = {
        "comparison_asking": round(comparison_asking, 1),
        "comparison_comp_draw": round(comp_draw, 1),
        "submarket_anchor_ppm2": anchor["anchor_ppm2"] if anchor else None,
        "comparison": round(comparison_tx, 1),
        "cost_floor": round(cost_floor, 1) if cost_floor else None,
        "income_ceiling": round(income_ceiling, 1) if income_ceiling else None,
    }

    conf = confidence.score(comps, adjusted_cv, method_values, recommended, as_of)

    min_safe = conf.interval_low_ppm2
    if cost_floor:
        min_safe = max(min_safe, cost_floor)
    min_safe = min(min_safe, recommended)

    # Premium tier = top of the data-driven confidence band. Future signals justify
    # positioning HERE (not a fabricated number above the evidenced range). If investors
    # set a higher ceiling, allow the premium to reach it; never let it fall below rec.
    premium = conf.interval_high_ppm2
    if income_ceiling and income_ceiling > premium:
        premium = income_ceiling
    premium = max(premium, recommended)

    future_objs, dev_score = evidence.future_signal_evidence(bundle.evidence_items, subject)
    gov = {"index_present": bundle.price_index.has(),
           "index_current": index_is_current(bundle.price_index, as_of),
           "has_cost_floor": cost_floor is not None}
    conf_components = confidence.decompose(conf, comps, adjusted_cv, as_of, dev_score, gov)
    evidence_objs = _collect_evidence(subject, bundle, comps, premiums, bench, cost_floor,
                                      income_ceiling, req_yield, income_method, income_meta,
                                      future_objs)

    caveats = _data_caveats(bundle, subject, premiums, cost_floor, as_of)
    risks = _risk_factors(subject, comps, adjusted_cv, cost_floor, income_ceiling,
                          recommended, conf, method_values) + caveats
    scenarios = _scenarios(min_safe, recommended, premium, dev_score, conf)
    narrative = _narrative(subject, recommended, min_safe, premium, conf, comps,
                           method_values, dev_score, risks)

    return RecommendationResult(
        location_id=subject.location_id,
        neighborhood=subject.neighborhood,
        property_type=subject.property_type,
        min_safe_price_jd_m2=round(min_safe, 1),
        recommended_price_jd_m2=round(recommended, 1),
        premium_price_jd_m2=round(premium, 1),
        confidence_label=conf.label,
        confidence_numeric=conf.numeric,
        confidence_interval_jd_m2=[conf.interval_low_ppm2, conf.interval_high_ppm2],
        narrative=narrative,
        evidence_objects=[e.to_dict() for e in evidence_objs],
        comparables=[c.to_dict() for c in comps],
        risk_factors=risks,
        alternative_scenarios=scenarios,
        method_values={**method_values, "development_score": dev_score,
                       "confidence_components": conf.components,
                       "selection_notes": selection_notes,
                       "derived_premiums": premiums.as_records()},
        computed_date=as_of.isoformat(),
        confidence_components=conf_components,
    )


def _collect_evidence(subject, bundle, comps, premiums, bench, cost_floor,
                      income_ceiling, req_yield, income_method, income_meta, future_objs):
    comp_sources = [c.source for c in comps]
    objs = evidence.premium_evidence(premiums, subject, comps, comp_sources)
    applied_time = any(a["factor"] == "Time (market movement)"
                       for c in comps for a in c.adjustments)
    t = evidence.time_evidence(comps, bundle.price_index.source, applied_time)
    if t:
        objs.append(t)
    objs.append(evidence.ask_gap_evidence())
    cf = evidence.cost_floor_evidence(bench, cost_floor) if cost_floor else None
    if cf:
        objs.append(cf)
    if income_ceiling:
        conf, sources = income_meta
        objs.append(evidence.income_ceiling_evidence(
            income_ceiling, req_yield, income_method, conf, sources))
    comp_ev = evidence.competition_evidence(bundle.projects, subject)
    if comp_ev:
        objs.append(comp_ev)
    mix = evidence.market_composition_evidence(comps)
    if mix:
        objs.append(mix)
    geo = evidence.geocontext_evidence(bundle.geocontext_for(subject.neighborhood))
    if geo:
        objs.append(geo)
    objs.extend(future_objs)
    return objs


def _risk(factor: str, severity: str, detail: str) -> dict:
    return {"factor": factor, "severity": severity, "detail": detail}


def _risk_factors(subject, comps, cv, cost_floor, income_ceiling, recommended,
                  conf, method_values) -> list[dict]:
    risks = []
    if len(comps) < config.MIN_COMPS:
        risks.append(_risk("Thin comparable set", "high",
                           f"Only {len(comps)} comparable(s) after outlier filtering — low statistical support."))
    if cv > 0.30:
        risks.append(_risk("High price dispersion", "medium",
                           f"Adjusted comps vary {cv*100:.0f}% — the submarket is heterogeneous."))
    stale = sum(1 for c in comps if any(a['factor'] == 'Time (market movement)' for a in c.adjustments))
    if stale and stale >= len(comps) / 2:
        risks.append(_risk("Dated evidence base", "medium",
                           f"{stale}/{len(comps)} comps required time-adjustment."))
    # view/parking are covered by dedicated data caveats; only flag attributes the user
    # supplies and that the engine can actually derive.
    missing = [f for f in ("finish_quality", "furnishing")
               if getattr(subject, f, "unknown") in ("unknown", None)]
    if missing:
        risks.append(_risk("Subject attributes unknown", "low",
                           f"{', '.join(missing)} not supplied — those premiums could not be applied."))
    if cost_floor and cost_floor > recommended:
        risks.append(_risk("Thin development margin", "medium",
                           f"Cost floor ({cost_floor:.0f}) exceeds the comparison value ({recommended:.0f})."))
    if income_ceiling and income_ceiling < recommended:
        risks.append(_risk("Investor ceiling below price", "medium",
                           f"Income ceiling ({income_ceiling:.0f}) is below the recommended price — "
                           "investment buyers may not clear; sale depends on owner-occupiers."))
    if conf.components["method_agreement"] < 0.5:
        risks.append(_risk("Valuation methods diverge", "medium",
                           "Comparison, cost and income approaches disagree (PDF: divergence is informative)."))
    if conf.label == "L":
        risks.append(_risk("Low overall confidence", "high",
                           "Widen the range and gather more evidence before committing."))
    return risks or [_risk("No material risks", "low", "Methods broadly agree.")]


def _data_caveats(bundle: DataBundle, subject: Subject, premiums, cost_floor, as_of) -> list[dict]:
    """Surface dataset gaps that materially weakened this recommendation (real-data honesty)."""
    out = []
    if cost_floor is None:
        out.append(_risk("No cost-approach floor", "low",
                         "No construction-cost benchmark for this spec class — the minimum-safe "
                         "price rests on the comparison band alone."))
    from .adjustment import _CATEGORICAL
    missing = [label for attr, label in _CATEGORICAL.items() if attr not in premiums.categorical]
    if "View" in missing:
        out.append(_risk("View premium unavailable", "low",
                         "Bayut/OpenSooq do not expose view per listing — the view/aspect factor "
                         "will attach at neighborhood level from qualitative research (R7), not per comp."))
    if "Covered parking" in missing:
        out.append(_risk("Parking premium not derivable", "low",
                         "Listings are almost entirely 'covered' parking with too few usable "
                         "'open'/'none' rows to form a paired differential — parking is not adjusted."))
    other = [m for m in missing if m not in ("View", "Covered parking")]
    if other:
        out.append(_risk("Some attribute premiums limited", "low",
                         f"{', '.join(other)} too sparse to derive even citywide — not adjusted."))
    if not index_is_current(bundle.price_index, as_of):
        latest = bundle.price_index.latest()
        cover = latest[0] if latest else "none"
        out.append(_risk("Price index not current", "low",
                         f"CBJ index covers only through {cover}; time-adjustment of stale comps "
                         "is disabled rather than extrapolated."))
    if not bundle.evidence_items:
        out.append(_risk("No future-signal evidence", "low",
                         "No infrastructure/development items collected yet — the appreciation "
                         "story is not evidenced; premium tier rests on the comparison band."))
    return out


def _scenarios(min_safe, recommended, premium, dev_score, conf) -> list[dict]:
    return [
        {"name": "Minimum-safe launch", "recommended_price_jd_m2": round(min_safe, 1),
         "rationale": "Protects the floor and lower confidence band; fastest absorption. "
                      "Use under liquidity pressure or maturing construction finance (PDF §6)."},
        {"name": "Recommended launch", "recommended_price_jd_m2": round(recommended, 1),
         "rationale": "Reconciled market value; balances absorption speed and captured value. "
                      "Default: price at comps and negotiate from strength."},
        {"name": "Premium launch", "recommended_price_jd_m2": round(premium, 1),
         "rationale": f"Top of the evidenced range; leans on the future-signal story "
                      f"(development score {dev_score}). Enables the 'raise later, never cut' strategy "
                      "under strong demand."},
    ]


def _narrative(subject, recommended, min_safe, premium, conf, comps,
               method_values, dev_score, risks) -> str:
    lines = []
    lines.append(
        f"For a {subject.finish_quality if subject.finish_quality != 'unknown' else ''} "
        f"{subject.property_type} in {subject.neighborhood}"
        + (f" (~{subject.area_m2:.0f} m²)" if subject.area_m2 else "")
        + f", the recommended launch price is {recommended:.0f} JD/m², within a defensible "
        f"range of {min_safe:.0f}–{premium:.0f} JD/m² (confidence: {conf.label}, "
        f"{conf.numeric:.2f}; 80% interval {conf.interval_low_ppm2:.0f}–{conf.interval_high_ppm2:.0f})."
    )
    lines.append(
        f"This is anchored on {len(comps)} comparable listing(s), each normalised to the "
        f"subject with market-derived adjustments and calibrated from asking to transaction "
        f"level; comps needing fewer/smaller adjustments carried more weight."
    )
    anchor_ppm2 = method_values.get("submarket_anchor_ppm2")
    if anchor_ppm2:
        lines.append(
            f"To stay representative of the whole submarket, the comp value was reconciled "
            f"toward the robust median of all same-type sales (~{anchor_ppm2:.0f} JD/m² asking) "
            f"by statistical precision, so a dense pool anchors the price level while the comps "
            f"supply the subject-specific adjustments."
        )
    floor, ceil = method_values.get("cost_floor"), method_values.get("income_ceiling")
    cross = []
    if floor:
        cross.append(f"cost floor ≈ {floor:.0f}")
    if ceil:
        cross.append(f"income ceiling ≈ {ceil:.0f}")
    if cross:
        lines.append("Cross-checks: " + ", ".join(cross) +
                     ". Convergence supports the estimate; divergence is captured in the risks.")
    if dev_score > 0:
        lines.append(f"Future signals (development score {dev_score}) justify holding the "
                     "launch toward the top of the range and raising — never cutting — later.")
    lines.append(f"Key risk: {risks[0]['detail']}")
    return " ".join(lines)


def unpriceable(subject, as_of, factor: str, detail: str,
                narrative: Optional[str] = None, notes=None) -> RecommendationResult:
    """A well-formed 'cannot price' result: honest zero band, one explanatory risk factor."""
    return RecommendationResult(
        location_id=subject.location_id, neighborhood=subject.neighborhood,
        property_type=subject.property_type, min_safe_price_jd_m2=0.0,
        recommended_price_jd_m2=0.0, premium_price_jd_m2=0.0,
        confidence_label="L", confidence_numeric=0.0,
        confidence_interval_jd_m2=[0.0, 0.0],
        narrative=narrative or detail,
        evidence_objects=[], comparables=[],
        risk_factors=[_risk(factor, "high", detail)],
        alternative_scenarios=[],
        method_values={"selection_notes": notes or []},
        computed_date=as_of.isoformat(),
    )


def _empty_result(subject, as_of, notes) -> RecommendationResult:
    return unpriceable(
        subject, as_of, "No comparable listings",
        "No plausible comparables for this submarket — recommendation not possible.",
        narrative=("No comparable evidence available for "
                   f"{subject.neighborhood} {subject.property_type}; cannot price. "
                   "Collect listings for this submarket first."),
        notes=notes)
