"""Typed records shared across the five sub-engines.

The public output (`RecommendationResult`) serialises to the exact shape the
`recommendations` table in db/schema.sql persists and the frontend consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import date
from typing import Any, Optional


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw or str(raw).strip().lower() in ("", "unknown", "none"):
        return None
    try:
        return date.fromisoformat(str(raw).strip()[:10])
    except ValueError:
        return None


def _num(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "unknown":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _int(raw: Any) -> Optional[int]:
    v = _num(raw)
    return int(v) if v is not None else None


@dataclass
class Listing:
    """One asking-price record (frozen `listings` schema; price_per_m2 derived)."""

    listing_id: str
    portal: str
    listing_url: str
    listing_type: str
    property_type: str
    neighborhood: str
    price_jd: Optional[float]
    area_m2: Optional[float]
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor_level: Optional[int] = None
    total_floors: Optional[int] = None
    view: str = "unknown"
    parking: str = "unknown"
    building_age_years: Optional[int] = None
    furnishing: str = "unknown"
    elevator: str = "unknown"
    finish_quality: str = "unknown"
    seller_type: str = "unknown"
    listing_date: Optional[date] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    # Phase 2 spatial features (from enrich_spatial.py)
    elevation_m: Optional[float] = None
    ntl_radiance: Optional[float] = None
    pop_density: Optional[float] = None
    dist_school_km: Optional[float] = None
    dist_hospital_km: Optional[float] = None
    dist_mall_km: Optional[float] = None
    source_name: str = "unknown"
    source_url: str = "unknown"
    capture_date: Optional[date] = None
    confidence: str = "unknown"

    @property
    def price_per_m2(self) -> Optional[float]:
        if self.price_jd is None or not self.area_m2:
            return None
        return self.price_jd / self.area_m2

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Listing":
        g = row.get
        return cls(
            listing_id=g("listing_id", ""),
            portal=g("portal", "unknown"),
            listing_url=g("listing_url", "unknown"),
            listing_type=(g("listing_type") or "unknown").strip().lower(),
            property_type=(g("property_type") or "unknown").strip().lower(),
            neighborhood=(g("neighborhood") or "").strip(),
            price_jd=_num(g("price_jd")),
            area_m2=_num(g("area_m2")),
            bedrooms=_int(g("bedrooms")),
            bathrooms=_int(g("bathrooms")),
            floor_level=_int(g("floor_level")),
            total_floors=_int(g("total_floors")),
            view=(g("view") or "unknown").strip().lower(),
            parking=(g("parking") or "unknown").strip().lower(),
            building_age_years=_int(g("building_age_years")),
            furnishing=(g("furnishing") or "unknown").strip().lower(),
            elevator=(g("elevator") or "unknown").strip().lower(),
            finish_quality=(g("finish_quality") or "unknown").strip().lower(),
            seller_type=(g("seller_type") or "unknown").strip().lower(),
            listing_date=_parse_date(g("listing_date")),
            lat=_num(g("lat")),
            lng=_num(g("lng")),
            elevation_m=_num(g("elevation_m")),
            ntl_radiance=_num(g("ntl_radiance")),
            pop_density=_num(g("pop_density")),
            dist_school_km=_num(g("dist_school_km")),
            dist_hospital_km=_num(g("dist_hospital_km")),
            dist_mall_km=_num(g("dist_mall_km")),
            source_name=g("source_name", "unknown"),
            source_url=g("source_url", "unknown"),
            capture_date=_parse_date(g("capture_date")),
            confidence=(g("confidence") or "unknown").strip(),
        )


@dataclass
class Subject:
    """The property to be priced. Attributes mirror the listing vocabulary."""

    neighborhood: str
    property_type: str = "apartment"
    area_m2: Optional[float] = None
    bedrooms: Optional[int] = None
    floor_level: Optional[int] = None
    view: str = "unknown"
    parking: str = "unknown"
    building_age_years: Optional[int] = 0
    finish_quality: str = "unknown"
    furnishing: str = "unknown"
    elevator: str = "unknown"
    lat: Optional[float] = None
    lng: Optional[float] = None
    elevation_m: Optional[float] = None   # defaulted to submarket median in pipeline
    location_id: Optional[str] = None


@dataclass
class DerivedPremium:
    """A market-derived attribute premium. `derived_premium` is a fraction (0.08=+8%)."""

    factor: str
    derived_premium: float
    method: str
    source: str
    confidence: str
    sample_size: int
    computed_date: str
    neighborhood: Optional[str] = None
    property_type: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceObject:
    """MASTER-PLAN 2d structured evidence object. Nothing prices without one."""

    factor: str
    adjustment: str
    confidence: str
    method: str
    datasets: list[str]
    sources: list[dict[str, str]]
    category: str  # current_state | future_signal
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComparableRecord:
    """A selected comp with its normalisation trail."""

    listing_id: str
    neighborhood: str
    area_m2: Optional[float]
    original_ppm2: float
    time_adjusted_ppm2: float
    adjusted_ppm2: float
    gross_adjustment: float          # sum of |per-attribute adjustments|
    reconciliation_weight: float
    similarity: float
    listing_date: Optional[str]
    adjustments: list[dict[str, Any]]
    source: dict[str, str]
    seller_type: str = "unknown"
    # what the listing actually consists of (for the "hover to see the listing" UI)
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor_level: Optional[int] = None
    building_age_years: Optional[int] = None
    view: str = "unknown"
    parking: str = "unknown"
    furnishing: str = "unknown"
    price_jd: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["price_per_m2"] = self.original_ppm2  # db-contract §4 alias
        d["adjustments_applied"] = [a["factor"] for a in self.adjustments
                                    if a["factor"] not in ("Time (market movement)",
                                                           "Net adjustment cap")]
        return d


@dataclass
class ConfidenceResult:
    label: str
    numeric: float
    interval_low_ppm2: float
    interval_high_ppm2: float
    components: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationResult:
    """Exact contract for db/schema.sql `recommendations` + the frontend panel."""

    location_id: Optional[str]
    neighborhood: str
    property_type: str
    min_safe_price_jd_m2: float
    recommended_price_jd_m2: float
    premium_price_jd_m2: float
    confidence_label: str
    confidence_numeric: float
    confidence_interval_jd_m2: list[float]
    narrative: str
    evidence_objects: list[dict[str, Any]]
    comparables: list[dict[str, Any]]
    risk_factors: list[dict[str, Any]]
    alternative_scenarios: list[dict[str, Any]]
    method_values: dict[str, Any]
    computed_date: str
    # Product-facing decomposition of the overall confidence (0-100 per component + reason).
    # Defaulted so the unpriceable/empty paths need not supply it.
    confidence_components: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        # Shape matches docs/db-contract.md §4 exactly: nested `confidence`; scalars map to
        # the recommendations table columns; the *_json arrays persist as-is.
        return {
            "location_id": self.location_id,
            "neighborhood": self.neighborhood,
            "property_type": self.property_type,
            "min_safe_price_jd_m2": self.min_safe_price_jd_m2,
            "recommended_price_jd_m2": self.recommended_price_jd_m2,
            "premium_price_jd_m2": self.premium_price_jd_m2,
            "confidence": {
                "label": self.confidence_label,
                "numeric": self.confidence_numeric,
                "interval_jd_m2": self.confidence_interval_jd_m2,
                "components": self.confidence_components,
            },
            "evidence_objects": self.evidence_objects,
            "comparables": self.comparables,
            "risk_factors": self.risk_factors,
            "alternative_scenarios": self.alternative_scenarios,
            "narrative": self.narrative,
            "computed_date": self.computed_date,
            "method_values": self.method_values,
        }
