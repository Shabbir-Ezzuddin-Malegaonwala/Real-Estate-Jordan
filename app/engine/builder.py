"""Builder-facing decision levers — EXPLICIT documented assumptions, never data-derived.

Two things the portals cannot give a builder and that the market therefore cannot derive:

  1. A height / city-view premium. Neither Bayut nor OpenSooq publishes "view", so the
     Adjustment Engine cannot derive a view premium per listing (surfaced as a data caveat
     in every recommendation). A builder still needs to reason about top-floor uplift, so we
     offer a CONFIGURABLE assumption — a transparent ramp with the parameter shown — clearly
     labelled BUILDER ASSUMPTION, not a derived number.

  2. A residual land valuation. Straight from the client Pricing PDF: the most a developer can
     pay for land is GDV minus construction, finance, fees and required profit.

Every function here returns its own assumptions inline so nothing is a hidden constant. These
are builder inputs, NOT attribute pricing weights — the HARD RULE (no derived-premium constants)
lives in config.py / adjustment.py and is untouched.
"""

from __future__ import annotations

from typing import Any, Optional

from .models import EvidenceObject, RecommendationResult

# --- Height / city-view premium (BUILDER ASSUMPTION — configurable, surfaced) ---
HEIGHT_VIEW_PREMIUM_MAX = 0.15      # top-floor uplift ceiling; overridable per request
HEIGHT_VIEW_FLOOR_THRESHOLD = 5     # at/below this floor: no premium (no view advantage yet)
HEIGHT_VIEW_REFERENCE_SPAN = 10     # floors above threshold to reach max when total_floors unknown

# --- Residual land value defaults (documented builder assumptions; all overridable) ---
FINANCE_PCT_DEFAULT = 0.06          # finance cost as a fraction of (construction + fees)
PROFESSIONAL_FEES_PCT_DEFAULT = 0.05  # design/engineering/permits as a fraction of construction
DEVELOPER_PROFIT_PCT_DEFAULT = 0.20   # required profit as a fraction of GDV


def height_view_premium(floor_level: Optional[int], total_floors: Optional[int] = None,
                        max_premium: float = HEIGHT_VIEW_PREMIUM_MAX,
                        threshold: int = HEIGHT_VIEW_FLOOR_THRESHOLD,
                        reference_span: int = HEIGHT_VIEW_REFERENCE_SPAN) -> dict[str, Any]:
    """Linear height/city-view uplift: 0% at/below `threshold`, ramping to `max_premium` at the
    top floor (or `threshold + reference_span` when total_floors is unknown). Pure assumption —
    the return carries every parameter so the caller can show exactly how the number was formed.
    """
    assumption = {
        "max_premium_pct": round(max_premium * 100, 2),
        "floor_threshold": threshold,
        "reference_span_floors": reference_span,
        "basis": "builder assumption — portals do not publish view; NOT data-derived",
    }
    if floor_level is None or floor_level <= threshold or max_premium <= 0:
        return {"fraction": 0.0, "floor_level": floor_level, "total_floors": total_floors,
                "assumption": assumption,
                "explanation": (
                    f"No height/city-view premium applied (floor "
                    f"{floor_level if floor_level is not None else 'unknown'} ≤ threshold "
                    f"{threshold}).")}
    top = total_floors if (total_floors and total_floors > threshold) else threshold + reference_span
    progress = min(1.0, (floor_level - threshold) / (top - threshold))
    fraction = round(max_premium * progress, 4)
    span_note = (f"top floor {total_floors}" if (total_floors and total_floors > threshold)
                 else f"reference top {top} (total_floors unknown)")
    return {
        "fraction": fraction, "floor_level": floor_level, "total_floors": total_floors,
        "assumption": assumption,
        "explanation": (
            f"Builder height/city-view premium +{fraction * 100:.1f}%: floor {floor_level} is "
            f"{progress * 100:.0f}% of the way from threshold {threshold} to {span_note}, "
            f"ramped linearly to the assumed {max_premium * 100:.0f}% ceiling. BUILDER ASSUMPTION."),
    }


def height_view_evidence(premium: dict[str, Any]) -> EvidenceObject:
    """Surface the height premium as an assumption row with the parameter visible."""
    a = premium["assumption"]
    return EvidenceObject(
        factor="Builder assumption: height / city-view premium",
        adjustment=f"+{premium['fraction'] * 100:.1f}%",
        confidence="Low",
        method=(f"configurable ramp — 0% ≤ floor {a['floor_threshold']}, linear to "
                f"{a['max_premium_pct']:.0f}% ceiling at the top floor"),
        datasets=["builder assumption (not derived)"],
        sources=[{"name": "Builder-configurable assumption (view not published by portals)",
                  "url": "internal://builder-assumption/height-view-premium",
                  "capture_date": "assumption"}],
        category="current_state",
        explanation=premium["explanation"],
    )


def apply_height_view_premium(result: RecommendationResult, floor_level: Optional[int],
                              total_floors: Optional[int] = None,
                              max_premium: float = HEIGHT_VIEW_PREMIUM_MAX,
                              threshold: int = HEIGHT_VIEW_FLOOR_THRESHOLD,
                              reference_span: int = HEIGHT_VIEW_REFERENCE_SPAN
                              ) -> RecommendationResult:
    """Uplift recommended/premium (and the confidence interval, to keep it around the point) by
    the builder height premium, and append the assumption as an evidence row. The min-safe floor
    is left untouched — an assumption never lowers the protected floor. No-op when fraction is 0.
    """
    premium = height_view_premium(floor_level, total_floors, max_premium, threshold, reference_span)
    frac = premium["fraction"]
    result.method_values = {**result.method_values, "height_view_premium": premium}
    if frac <= 0 or result.recommended_price_jd_m2 <= 0:
        return result
    scale = 1 + frac
    result.recommended_price_jd_m2 = round(result.recommended_price_jd_m2 * scale, 1)
    result.premium_price_jd_m2 = round(max(result.premium_price_jd_m2 * scale,
                                           result.recommended_price_jd_m2), 1)
    lo, hi = result.confidence_interval_jd_m2
    result.confidence_interval_jd_m2 = [round(lo * scale, 1), round(hi * scale, 1)]
    result.evidence_objects = result.evidence_objects + [height_view_evidence(premium).to_dict()]
    return result


def residual_land_value(buildable_area_m2: float, gdv_per_m2: float,
                        construction_cost_per_m2: float,
                        finance_pct: float = FINANCE_PCT_DEFAULT,
                        professional_fees_pct: float = PROFESSIONAL_FEES_PCT_DEFAULT,
                        developer_profit_pct: float = DEVELOPER_PROFIT_PCT_DEFAULT,
                        gdv_source: Optional[dict] = None,
                        cost_source: Optional[dict] = None,
                        gdv_defaulted: bool = False,
                        cost_defaulted: bool = False) -> dict[str, Any]:
    """Residual land valuation (client Pricing PDF): the most a developer can pay for the land is

        GDV − construction − professional fees − finance − required profit.

    Fees are taken on construction, finance on (construction + fees), profit on GDV — each basis
    is stated in the breakdown so nothing is opaque. All percentages are documented builder
    assumptions the caller can override. Returns totals, per-m² land price, and the full ladder.
    """
    gdv_total = gdv_per_m2 * buildable_area_m2
    construction_total = construction_cost_per_m2 * buildable_area_m2
    professional_fees = professional_fees_pct * construction_total
    finance_cost = finance_pct * (construction_total + professional_fees)
    developer_profit = developer_profit_pct * gdv_total
    residual_total = (gdv_total - construction_total - professional_fees
                      - finance_cost - developer_profit)
    residual_per_m2 = residual_total / buildable_area_m2 if buildable_area_m2 else 0.0

    def line(label: str, value: float, basis: str) -> dict:
        return {"label": label, "value_jd": round(value, 1), "basis": basis}

    return {
        "buildable_area_m2": buildable_area_m2,
        "inputs": {
            "gdv_per_m2": round(gdv_per_m2, 1),
            "construction_cost_per_m2": round(construction_cost_per_m2, 1),
            "finance_pct": finance_pct,
            "professional_fees_pct": professional_fees_pct,
            "developer_profit_pct": developer_profit_pct,
            "gdv_per_m2_defaulted": gdv_defaulted,
            "construction_cost_defaulted": cost_defaulted,
        },
        "breakdown": [
            line("Gross development value (GDV)", gdv_total,
                 f"{gdv_per_m2:.0f} JD/m² × {buildable_area_m2:.0f} m²"),
            line("less Construction cost", -construction_total,
                 f"{construction_cost_per_m2:.0f} JD/m² × {buildable_area_m2:.0f} m²"),
            line("less Professional fees", -professional_fees,
                 f"{professional_fees_pct * 100:.0f}% of construction (assumption)"),
            line("less Finance cost", -finance_cost,
                 f"{finance_pct * 100:.0f}% of construction + fees (assumption)"),
            line("less Developer profit", -developer_profit,
                 f"{developer_profit_pct * 100:.0f}% of GDV (assumption)"),
        ],
        "gdv_total_jd": round(gdv_total, 1),
        "residual_land_value_total_jd": round(residual_total, 1),
        "residual_land_value_per_m2_jd": round(residual_per_m2, 1),
        "viable": residual_total > 0,
        "explanation": (
            f"Max supportable land price ≈ {residual_total:,.0f} JD "
            f"({residual_per_m2:,.0f} JD per buildable m²): GDV {gdv_total:,.0f} − construction "
            f"{construction_total:,.0f} − fees {professional_fees:,.0f} − finance {finance_cost:,.0f} "
            f"− profit {developer_profit:,.0f}." + ("" if residual_total > 0 else
            " Negative residual: construction, finance, fees and required profit exceed GDV — "
            "the land cannot support this program at these inputs.")),
        "sources": [s for s in (gdv_source, cost_source) if s],
        "assumptions": [
            "Residual method and cost-approach floor — client 'Real Estate Pricing Strategies' PDF.",
            "finance_pct / professional_fees_pct / developer_profit_pct are builder assumptions "
            "(defaults shown); override per deal.",
        ],
    }
