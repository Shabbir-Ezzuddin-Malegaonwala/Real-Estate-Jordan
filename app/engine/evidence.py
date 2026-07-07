"""Evidence Engine — wraps every adjustment and context factor as a structured object.

MASTER-PLAN 2d: nothing enters the recommendation without an evidence object of shape
{factor, adjustment, confidence, method, datasets[], sources[], category, explanation}.
These render as the adjustment-grid waterfall rows and their source chips.
"""

from __future__ import annotations

from typing import Optional

from .adjustment import PremiumSet, _CATEGORICAL, _CONTINUOUS
from .data import EvidenceItem, Project
from .models import EvidenceObject, Subject
from .stats import median, pct
from . import config

_PORTAL_DATASET = "listings"


def _premium_record(premiums: PremiumSet, needle: str):
    for r in premiums.records:
        if r.factor == needle or r.factor.startswith(needle + ":"):
            return r
    return None


def _strongest_record(premiums: PremiumSet, label: str):
    recs = [r for r in premiums.records if r.factor == label or r.factor.startswith(label + ":")]
    return max(recs, key=lambda r: abs(r.derived_premium), default=None)


def premium_evidence(premiums: PremiumSet, subject: Subject, comps: list,
                     comp_sources: list[dict]) -> list[EvidenceObject]:
    """One waterfall row per attribute lever actually used to normalise the comps.

    Coverage guarantee: every categorical/continuous factor applied to any comp gets an
    evidence object, so nothing prices without one (MASTER-PLAN 2d).
    """
    out: list[EvidenceObject] = []
    chips = _dedupe_sources(comp_sources)
    applied = {a["factor"] for c in comps for a in c.adjustments}

    for attr, label in _CATEGORICAL.items():
        schedule = premiums.categorical.get(attr)
        if not schedule:
            continue
        s_lvl = getattr(subject, attr)
        subj_frac = schedule.get(s_lvl, 0.0) if s_lvl not in ("unknown", "u", None) else 0.0
        if label not in applied and abs(subj_frac) < 1e-9:
            continue
        rec = _premium_record(premiums, f"{label}: {s_lvl}") or _strongest_record(premiums, label)
        at_baseline = abs(subj_frac) < 1e-9
        expl = (f"Subject sits at the submarket-typical {label.lower()}; comps differing on "
                f"this attribute were adjusted by the derived differential."
                if at_baseline else
                f"Subject's {label.lower()} ('{s_lvl}') lists {pct(subj_frac)} vs the typical "
                f"unit in {subject.neighborhood}, from matched-pair evidence.")
        out.append(EvidenceObject(
            factor=f"{label} ({s_lvl})" if not at_baseline else f"{label}",
            adjustment=pct(subj_frac),
            confidence=rec.confidence if rec else "Low",
            method=rec.method if rec else "paired median differential",
            datasets=[_PORTAL_DATASET], sources=chips, category="current_state",
            explanation=expl,
        ))

    for attr, label in _CONTINUOUS.items():
        frac = premiums.continuous.get(attr)
        if frac is None or (label not in applied):
            continue
        s_val = getattr(subject, attr)
        rec = _premium_record(premiums, label)
        out.append(EvidenceObject(
            factor=label,
            adjustment=f"{pct(frac)} per unit",
            confidence=rec.confidence if rec else "Low",
            method=rec.method if rec else "OLS slope",
            datasets=[_PORTAL_DATASET], sources=chips, category="current_state",
            explanation=f"Each unit of {label.lower()} moves price/m² by {pct(frac)} "
                        f"(finish-controlled regression); subject value = {s_val}.",
        ))
    return out


def time_evidence(comps: list, index_source: dict, applied: bool) -> Optional[EvidenceObject]:
    if not applied:
        return None
    fracs = []
    for c in comps:
        for a in c.adjustments:
            if a["factor"] == "Time (market movement)":
                fracs.append(float(a["adjustment"].replace("%", "")) / 100.0)
    if not fracs:
        return None
    return EvidenceObject(
        factor="Time (market movement)",
        adjustment=pct(median(fracs)),
        confidence="High",
        method="CBJ Real Estate Price Index — Adjusted = Original × currentIndex / indexAtSale",
        datasets=["macro_series (CBJ index)"],
        sources=[index_source] if index_source else [],
        category="current_state",
        explanation="Stale comparables were re-based to today using the official CBJ "
                    "residential price index, removing time bias per the client methodology.",
    )


def ask_gap_evidence() -> EvidenceObject:
    mid = (config.ASK_TO_TX_GAP_LOW + config.ASK_TO_TX_GAP_HIGH) / 2
    return EvidenceObject(
        factor="Ask-to-transaction calibration",
        adjustment=pct(-mid),
        confidence="Medium",
        method=f"documented assumption: asking prices sit "
               f"{config.ASK_TO_TX_GAP_LOW*100:.0f}–{config.ASK_TO_TX_GAP_HIGH*100:.0f}% "
               f"above transactions (client PDF)",
        datasets=["client methodology PDF"],
        sources=[config.ASK_TO_TX_SOURCE],
        category="current_state",
        explanation="Portal prices are asking prices, not sales. A documented "
                    f"{config.ASK_TO_TX_GAP_LOW*100:.0f}–{config.ASK_TO_TX_GAP_HIGH*100:.0f}% "
                    "gap is applied to estimate the transaction level.",
    )


def cost_floor_evidence(benchmark, floor_ppm2: float) -> Optional[EvidenceObject]:
    if benchmark is None:
        return None
    return EvidenceObject(
        factor="Cost approach floor",
        adjustment=f"{floor_ppm2:.0f} JD/m²",
        confidence="Medium" if benchmark.confidence in ("H", "High") else "Low",
        method="Value = replacement construction cost − depreciation (new-build ≈ 0)",
        datasets=["cost_benchmarks"],
        sources=[{"name": benchmark.source_name, "url": benchmark.source_url,
                  "capture_date": benchmark.capture_date or "unknown"}],
        category="current_state",
        explanation=f"A rational buyer will not pay below the cost to rebuild: "
                    f"{benchmark.spec_class} construction ≈ {floor_ppm2:.0f} JD/m². "
                    "This sets the minimum-safe price.",
    )


def income_ceiling_evidence(ceiling_ppm2: float, yield_used: float, method: str,
                            confidence: str, sources: list[dict]) -> EvidenceObject:
    return EvidenceObject(
        factor="Income approach ceiling",
        adjustment=f"{ceiling_ppm2:.0f} JD/m²",
        confidence=confidence,
        method=method,
        datasets=["listings (rentals)"],
        sources=sources,
        category="current_state",
        explanation=f"Investment buyers cap price at rent ÷ required yield "
                    f"({yield_used*100:.1f}%). Above ≈ {ceiling_ppm2:.0f} JD/m² the unit "
                    "stops clearing to investors.",
    )


def future_signal_evidence(items: list[EvidenceItem], subject: Subject
                           ) -> tuple[list[EvidenceObject], float]:
    """Future Signals pipeline: development score = Σ proximity×timeline×source_conf."""
    out: list[EvidenceObject] = []
    score = 0.0
    n = subject.neighborhood.strip().lower()
    conf_w = {"H": 1.0, "High": 1.0, "M": 0.6, "Medium": 0.6, "L": 0.3, "Low": 0.3}
    for it in items:
        area = it.impact_area.strip().lower()
        if area != n and area != "citywide":
            continue
        proximity = 1.0 if area == n else 0.4
        timeline = _timeline_certainty(it)
        src = conf_w.get(it.confidence, 0.3)
        weight = proximity * timeline * src
        score += weight
        stated = it.expected_effect if it.expected_effect not in ("", "unknown") else \
            "no price impact stated by source (interpretation by engine)"
        out.append(EvidenceObject(
            factor=f"Future signal: {it.title}",
            adjustment="positioning (no point premium)",
            confidence=it.confidence if it.confidence in ("H", "M", "L") else "Low",
            method="future-signal weighting (proximity × timeline certainty × source trust)",
            datasets=["evidence_items"],
            sources=[{"name": it.source_name, "url": it.source_url,
                      "capture_date": it.capture_date or "unknown"}],
            category="future_signal",
            explanation=f"{it.summary or it.title}. Stated effect: {stated}. "
                        "Supports holding the launch at the top of the observed range.",
        ))
    return out, round(score, 3)


def _timeline_certainty(it: EvidenceItem) -> float:
    if it.expected_year is None:
        return 0.4
    horizon = it.expected_year - 2026
    if horizon <= 0:
        return 1.0
    if horizon <= 2:
        return 0.8
    if horizon <= 5:
        return 0.5
    return 0.3


def competition_evidence(projects: list[Project], subject: Subject) -> Optional[EvidenceObject]:
    n = subject.neighborhood.strip().lower()
    rivals = [p for p in projects
              if p.neighborhood.strip().lower() == n
              and p.status in ("selling", "construction", "planned")
              and p.launch_price_jd_m2]
    if not rivals:
        return None
    med = median([p.launch_price_jd_m2 for p in rivals])
    return EvidenceObject(
        factor="Competitive positioning",
        adjustment=f"{med:.0f} JD/m² median rival launch",
        confidence="Medium",
        method=f"competitor launch prices within submarket (n={len(rivals)})",
        datasets=["projects"],
        sources=_dedupe_sources([{"name": p.source_name, "url": p.source_url,
                                  "capture_date": p.capture_date or "unknown"} for p in rivals]),
        category="current_state",
        explanation=f"{len(rivals)} competing project(s) launch near {med:.0f} JD/m² in "
                    f"{subject.neighborhood}; the recommendation is positioned against this band.",
    )


def market_composition_evidence(comps: list) -> Optional[EvidenceObject]:
    """Informational CONTEXT chip — seller-type mix of the comps. NOT a price lever.

    Gives a builder market texture (mostly brokered vs private) without touching the price.
    """
    known = [c.seller_type for c in comps if c.seller_type not in ("unknown", None)]
    if len(known) < 3:
        return None
    total = len(known)
    counts = {}
    for s in known:
        counts[s] = counts.get(s, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    mix = ", ".join(f"{round(100 * n / total)}% {s}-listed" for s, n in ranked)
    dominant = ranked[0][0]
    texture = {"agent": "a predominantly agency-brokered comp set",
               "private": "a predominantly private-seller comp set",
               "developer": "a developer-led comp set"}.get(dominant, "a mixed comp set")
    return EvidenceObject(
        factor="Market composition (context)",
        adjustment="context — not a price adjustment",
        confidence="High",
        method=f"seller-type share of the {total} comps",
        datasets=[_PORTAL_DATASET],
        sources=_dedupe_sources([c.source for c in comps]),
        category="current_state",
        explanation=f"Of the comparables driving this estimate, {mix} — {texture}. "
                    "Provided as market texture; it does not move the price.",
    )


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in sources:
        key = (s.get("name"), s.get("url"))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out[:8]
