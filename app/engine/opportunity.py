"""Opportunity Engine — a "where should I build" composite over covered submarkets (v1).

Each area gets a 0-100 opportunity score from five transparent components, blended with weights
that are DEFINED and EXPOSED here (a v1 heuristic, tunable — never hidden price magic). Every
component is derived from collected data; a component that cannot be computed for an area is
returned null (with a reason) and its weight is redistributed over the available ones, so the
composite stays finite and honest. Feeds the map heatmap.

Components:
  price_level      median sale price/m², min-max across the covered set (relative standing)
  price_growth     recent vs older median sale price/m² within the area (None if too sparse)
  demand_density   population density + night-light proxy (neighborhood_geocontext)
  supply_pressure  active listing + competing-project inventory, inverted (low pressure scores high)
  future_signals   development score from evidence_items (proximity × timeline × source trust)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from . import config
from .data import DataBundle
from .models import Subject
from .stats import median, months_between, robust_keep
from . import evidence as _evidence

# v1 heuristic composite weights — DEFINED and EXPOSED (not derived, not hidden). Tune freely.
OPPORTUNITY_WEIGHTS = {
    "price_level": 0.25,
    "price_growth": 0.20,
    "demand_density": 0.25,
    "supply_pressure": 0.15,
    "future_signals": 0.15,
}
_GROWTH_MIN_SAMPLE = 8       # min sales on each side of the window to trust a growth number
_GROWTH_RECENT_MONTHS = 12   # "recent" window
_GROWTH_OLDER_MONTHS = 36    # "older" window ceiling (12–36 mo back)
_PROJECT_SUPPLY_WEIGHT = 20  # each competing project counts as this many listings of supply


def _area_sales(bundle: DataBundle, key: str) -> list[float]:
    raw = [l.price_per_m2 for l in bundle.sales() if l.neighborhood.strip().lower() == key]
    keep = robust_keep(raw, config.MIN_PLAUSIBLE_SALE_PPM2)
    return [v for v, k in zip(raw, keep) if k]


def _growth_raw(bundle: DataBundle, key: str, as_of: date) -> Optional[float]:
    recent, older = [], []
    for l in bundle.sales():
        if l.neighborhood.strip().lower() != key or not l.listing_date:
            continue
        if l.price_per_m2 is None or l.price_per_m2 < config.MIN_PLAUSIBLE_SALE_PPM2:
            continue
        age = months_between(l.listing_date, as_of)
        if 0 <= age <= _GROWTH_RECENT_MONTHS:
            recent.append(l.price_per_m2)
        elif _GROWTH_RECENT_MONTHS < age <= _GROWTH_OLDER_MONTHS:
            older.append(l.price_per_m2)
    if len(recent) < _GROWTH_MIN_SAMPLE or len(older) < _GROWTH_MIN_SAMPLE:
        return None
    m_old = median(older)
    if not m_old:
        return None
    return (median(recent) - m_old) / m_old * 100


def _supply_raw(bundle: DataBundle, key: str) -> float:
    listings = sum(1 for l in bundle.listings if l.neighborhood.strip().lower() == key)
    projects = sum(1 for p in bundle.projects
                   if p.neighborhood.strip().lower() == key
                   and p.status in ("selling", "construction", "planned"))
    return listings + projects * _PROJECT_SUPPLY_WEIGHT


def _normalize(raw: dict[str, Optional[float]], invert: bool = False
               ) -> dict[str, Optional[float]]:
    vals = [v for v in raw.values() if v is not None]
    if not vals:
        return {a: None for a in raw}
    lo, hi = min(vals), max(vals)
    out: dict[str, Optional[float]] = {}
    for a, v in raw.items():
        if v is None:
            out[a] = None
        elif hi == lo:
            out[a] = 50.0
        else:
            s = (v - lo) / (hi - lo) * 100
            out[a] = 100 - s if invert else s
    return out


def _component(score: Optional[float], reason: str) -> dict:
    return {"score": None if score is None else round(score), "reason": reason}


def _composite(components: dict[str, dict]) -> float:
    num = den = 0.0
    for name, w in OPPORTUNITY_WEIGHTS.items():
        s = components[name]["score"]
        if s is not None:
            num += w * s
            den += w
    return round(num / den, 1) if den else 0.0


def opportunity_scores(bundle: DataBundle, areas: list[str],
                       as_of: Optional[date] = None,
                       centroids: Optional[dict[str, tuple]] = None) -> list[dict[str, Any]]:
    """Score every covered area against the others. Returns a list ranked high→low.

    `centroids` (lower-cased area → (lat, lng)) is echoed onto each row for the heatmap.
    """
    as_of = as_of or bundle.as_of or date.today()
    centroids = centroids or {}
    keys = {a: a.strip().lower() for a in areas}
    geo = {a: bundle.geocontext_for(a) for a in areas}

    price_raw = {a: (median(_area_sales(bundle, keys[a])) or None) for a in areas}
    growth_raw = {a: _growth_raw(bundle, keys[a], as_of) for a in areas}
    pop_raw = {a: (geo[a].median_population_density if geo[a] else None) for a in areas}
    light_raw = {a: (geo[a].median_nightlight if geo[a] else None) for a in areas}
    supply_raw = {a: _supply_raw(bundle, keys[a]) for a in areas}

    price_n = _normalize(price_raw)
    growth_n = _normalize(growth_raw)
    pop_n = _normalize(pop_raw)
    light_n = _normalize(light_raw)
    supply_n = _normalize(supply_raw, invert=True)

    have_evidence = bool(bundle.evidence_items)
    out: list[dict[str, Any]] = []
    for a in areas:
        dev = _evidence.future_signal_evidence(bundle.evidence_items, Subject(neighborhood=a))[1]
        demand_parts = [x for x in (pop_n[a], light_n[a]) if x is not None]
        demand = sum(demand_parts) / len(demand_parts) if demand_parts else None

        components = {
            "price_level": _component(
                price_n[a],
                f"median sale ~{price_raw[a]:.0f} JD/m² (relative to covered set)"
                if price_raw[a] else "no plausible sale listings"),
            "price_growth": _component(
                growth_n[a],
                f"recent vs 12–36mo median {growth_raw[a]:+.1f}%"
                if growth_raw[a] is not None
                else f"< {_GROWTH_MIN_SAMPLE} dated sales each side of the window — not scorable"),
            "demand_density": _component(
                demand,
                (f"pop density ~{pop_raw[a]:,.0f}/km²"
                 if pop_raw[a] is not None else "no density")
                + (f", night-light ~{light_raw[a]:.0f}" if light_raw[a] is not None else "")
                + " (activity proxy)" if demand is not None
                else "no neighborhood_geocontext row"),
            "supply_pressure": _component(
                supply_n[a],
                f"active supply proxy {supply_raw[a]:.0f} (listings + projects); "
                "low pressure scores high"),
            "future_signals": _component(
                min(100.0, dev / config.FUTURE_SIGNAL_SATURATION * 100) if have_evidence else None,
                f"development score {dev} (saturates at {config.FUTURE_SIGNAL_SATURATION})"
                if have_evidence else "no evidence_items collected"),
        }
        weights_used = {n: round(w, 4) for n, w in OPPORTUNITY_WEIGHTS.items()
                        if components[n]["score"] is not None}
        total_w = sum(weights_used.values()) or 1.0
        weights_used = {n: round(w / total_w, 4) for n, w in weights_used.items()}
        lat, lng = centroids.get(keys[a], (None, None))
        out.append({
            "area": a,
            "score": _composite(components),
            "components": components,
            "weights_used": weights_used,
            "centroid_lat": lat,
            "centroid_lng": lng,
        })
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


def area_catalog(bundle: DataBundle, covered: set[str],
                 centroids: dict[str, tuple]) -> list[dict[str, Any]]:
    """Every neighborhood we hold listings for, flagged covered (a supported submarket with a
    centroid) vs context (present in the corpus but not a first-class product area). For the
    search box / dropdown. Sorted covered-first then by listing volume."""
    agg: dict[str, dict] = {}
    for l in bundle.listings:
        name = (l.neighborhood or "").strip()
        if not name or name.lower() == "unknown":
            continue
        a = agg.setdefault(name, {"name": name, "listing_count": 0, "sale_listing_count": 0})
        a["listing_count"] += 1
        if l.listing_type == "sale" and l.price_per_m2:
            a["sale_listing_count"] += 1
    covered_lc = {c.strip().lower() for c in covered}
    out = []
    for name, a in agg.items():
        key = name.lower()
        is_covered = key in covered_lc
        lat, lng = centroids.get(key, (None, None))
        out.append({**a, "covered": is_covered,
                    "centroid_lat": lat, "centroid_lng": lng})
    out.sort(key=lambda r: (not r["covered"], -r["listing_count"]))
    return out
