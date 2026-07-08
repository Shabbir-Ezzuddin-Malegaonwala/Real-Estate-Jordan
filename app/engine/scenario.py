"""Scenario Engine — re-run the pricing engine under builder overrides and report the delta.

The engine is already parameterised, so most levers are just a different Subject. The three
levers the engine has no direct Subject field for are applied by transforming the DataBundle in
documented, explainable ways — never by nudging a price directly:

  * construction_cost_delta_pct → scales the cost_benchmarks the cost-approach FLOOR is built
    from (flows through `_cost_floor` into min-safe and method-agreement).
  * metro_delay_years          → pushes out the expected_year of infrastructure evidence, so the
    future-signal timeline certainty (evidence._timeline_certainty) drops — a weaker future tag.
  * launch_delay_months        → advances `as_of`, ageing every comparable (recency falls, stale
    comps may get CBJ time-adjusted).

Returns {base, scenario, deltas, explanation}. Nothing is fabricated: an override that changes
nothing yields a zero delta.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Optional

from . import builder
from .data import CostBenchmark, DataBundle, EvidenceItem
from .models import RecommendationResult, Subject
from .pipeline import recommend

# Subject fields a scenario override maps to directly (engine-native levers).
_SUBJECT_LEVERS = ("finish_quality", "parking", "view", "bedrooms", "building_age_years")


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    # clamp day to a safe 28 so no month-length overflow (day precision is irrelevant here)
    return date(year, month, min(d.day, 28))


def _scale_costs(costs: list[CostBenchmark], delta_pct: float) -> list[CostBenchmark]:
    f = 1 + delta_pct / 100.0
    out = []
    for c in costs:
        out.append(replace(c,
                           low=None if c.low is None else round(c.low * f, 1),
                           high=None if c.high is None else round(c.high * f, 1)))
    return out


def _delay_infra(items: list[EvidenceItem], years: int) -> list[EvidenceItem]:
    out = []
    for it in items:
        if it.type == "infrastructure" and it.expected_year is not None:
            out.append(replace(it, expected_year=it.expected_year + years))
        else:
            out.append(it)
    return out


def _pct_delta(base: float, scenario: float) -> Optional[float]:
    if not base:
        return None
    return round((scenario - base) / base * 100, 2)


def _component_change(base: RecommendationResult, scenario: RecommendationResult,
                      name: str) -> Optional[float]:
    b = base.confidence_components.get(name, {}).get("score")
    s = scenario.confidence_components.get(name, {}).get("score")
    if b is None or s is None:
        return None
    return round(s - b)


def simulate(base_subject: Subject, bundle: DataBundle, overrides: dict[str, Any],
             as_of: Optional[date] = None,
             base_total_floors: Optional[int] = None) -> dict[str, Any]:
    as_of = as_of or bundle.as_of or date.today()
    base = recommend(base_subject, bundle, as_of)

    applied: list[str] = []
    subj_over: dict[str, Any] = {}
    for f in _SUBJECT_LEVERS:
        v = overrides.get(f)
        if v is not None and v != getattr(base_subject, f, None):
            subj_over[f] = v
            applied.append(f"{f} → {v}")
    if overrides.get("target_floor") is not None:
        subj_over["floor_level"] = overrides["target_floor"]
        applied.append(f"target_floor → {overrides['target_floor']}")
    scenario_subject = replace(base_subject, **subj_over)

    scenario_bundle = bundle
    cost_delta = overrides.get("construction_cost_delta_pct")
    if cost_delta:
        scenario_bundle = replace(scenario_bundle,
                                  cost_benchmarks=_scale_costs(bundle.cost_benchmarks, cost_delta))
        applied.append(f"construction cost {cost_delta:+.0f}% → cost-approach floor")
    metro_delay = overrides.get("metro_delay_years")
    if metro_delay:
        scenario_bundle = replace(scenario_bundle,
                                  evidence_items=_delay_infra(bundle.evidence_items, metro_delay))
        applied.append(f"metro/infra delayed {metro_delay}y → weaker future-signal timeline")

    scenario_as_of = as_of
    launch_delay = overrides.get("launch_delay_months")
    if launch_delay:
        scenario_as_of = _add_months(as_of, launch_delay)
        scenario_bundle = replace(scenario_bundle, as_of=scenario_as_of)
        applied.append(f"launch delayed {launch_delay} months → evidence ages")

    scenario = recommend(scenario_subject, scenario_bundle, scenario_as_of)

    if overrides.get("apply_height_view_premium"):
        floor = overrides.get("target_floor")
        if floor is None:
            floor = base_subject.floor_level
        floors = overrides.get("floors") if overrides.get("floors") is not None else base_total_floors
        scenario = builder.apply_height_view_premium(scenario, floor, floors)
        prem = scenario.method_values.get("height_view_premium", {})
        applied.append(f"height/city-view premium (builder assumption) +{prem.get('fraction', 0) * 100:.1f}%")

    deltas = {
        "recommended_pct": _pct_delta(base.recommended_price_jd_m2,
                                      scenario.recommended_price_jd_m2),
        "min_safe_pct": _pct_delta(base.min_safe_price_jd_m2, scenario.min_safe_price_jd_m2),
        "premium_pct": _pct_delta(base.premium_price_jd_m2, scenario.premium_price_jd_m2),
        "confidence_change": round(scenario.confidence_numeric - base.confidence_numeric, 3),
        # Future signals justify POSITIONING, not a point premium — so levers like metro_delay
        # move this component, not the price. Surfaced so the effect is not invisible.
        "future_signals_change": _component_change(base, scenario, "future_signals"),
    }
    if not applied:
        explanation = "No overrides supplied — scenario equals base."
    else:
        rec_d = deltas["recommended_pct"]
        move = "unchanged" if not rec_d else f"{rec_d:+.1f}% recommended price"
        explanation = ("Applied: " + "; ".join(applied) + f". Net effect: {move}, confidence "
                       f"{deltas['confidence_change']:+.3f}. Every lever flows through the "
                       "engine's own evidence — no price was set by hand.")

    return {
        "base": base.to_dict(),
        "scenario": scenario.to_dict(),
        "deltas": deltas,
        "explanation": explanation,
        "levers_applied": applied,
    }
