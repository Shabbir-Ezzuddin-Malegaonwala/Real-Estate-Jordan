"""Comparable Analysis Engine — selects and ranks comparable listings.

Selection follows the client PDF sales-comparison discipline: same submarket and
property type, recent, similar size. Similarity ranks the shortlist; the final pricing
weight is NOT the similarity score — it is derived later from each comp's own adjustment
footprint (fewer/smaller adjustments = more weight), exactly as the PDF prescribes.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from . import config
from .models import Listing, Subject
from .stats import haversine_km, months_between, robust_keep


def neighborhood_pool(sales: list[Listing], subject: Subject) -> list[Listing]:
    """Same-submarket, same-type sale listings, outlier-filtered — basis for derivation.

    Raw portal data carries 0-price and whole-building placeholders; a plausibility floor
    plus a log-space MAD filter keeps medians and the comp set honest.
    """
    n = subject.neighborhood.strip().lower()
    t = subject.property_type.strip().lower()
    raw = [l for l in sales
           if l.neighborhood.strip().lower() == n
           and l.property_type == t
           and l.price_per_m2]
    keep = robust_keep([l.price_per_m2 for l in raw], config.MIN_PLAUSIBLE_SALE_PPM2)
    return [l for l, k in zip(raw, keep) if k]


def collapse_near_duplicates(pool: list[Listing]) -> tuple[list[Listing], int]:
    """Collapse the same physical unit cross-posted across portals into one comp.

    A unit re-posted on Bayut/OpenSooq/Facebook carries different listing_ids but the same
    bedrooms, area and price. Counting it N times over-weights that price and inflates
    confidence (QA OBS-3). Rows collapse only when they share bedrooms AND fall within
    config.DEDUP_TOLERANCE on both area and price/m² — tight enough that genuinely distinct
    units are never merged. The most-complete, then most-recent, then highest-id row
    represents each cluster, so selection stays deterministic. Returns (reps, n_collapsed).
    """
    order = sorted(range(len(pool)),
                   key=lambda i: (pool[i].area_m2, pool[i].price_per_m2, pool[i].listing_id))
    claimed = [False] * len(pool)
    reps: list[Listing] = []
    collapsed = 0
    tol = config.DEDUP_TOLERANCE
    for pos, i in enumerate(order):
        if claimed[i]:
            continue
        seed = pool[i]
        claimed[i] = True
        cluster = [seed]
        for j in order[pos + 1:]:
            if claimed[j]:
                continue
            cand = pool[j]
            if cand.area_m2 > seed.area_m2 / (1 - tol):
                break  # sorted by area: nothing further can match on size
            if _same_unit(seed, cand, tol):
                claimed[j] = True
                cluster.append(cand)
        collapsed += len(cluster) - 1
        reps.append(_most_representative(cluster))
    return reps, collapsed


def _same_unit(x: Listing, y: Listing, tol: float) -> bool:
    if x.bedrooms is None or y.bedrooms is None or x.bedrooms != y.bedrooms:
        return False
    return _within(x.area_m2, y.area_m2, tol) and _within(x.price_per_m2, y.price_per_m2, tol)


def _within(a: float, b: float, tol: float) -> bool:
    hi = max(abs(a), abs(b))
    return hi == 0 or abs(a - b) <= tol * hi


def _most_representative(cluster: list[Listing]) -> Listing:
    return max(cluster, key=lambda l: (_completeness(l), l.listing_date or date.min, l.listing_id))


def _completeness(l: Listing) -> int:
    numeric = (l.bedrooms, l.bathrooms, l.floor_level, l.total_floors,
               l.building_age_years, l.lat, l.lng)
    categorical = (l.view, l.parking, l.furnishing, l.elevator, l.finish_quality)
    return (sum(v is not None for v in numeric)
            + sum(c not in ("unknown", "u", None, "") for c in categorical))


def _within_recency(l: Listing, as_of: date) -> bool:
    if l.listing_date is None:
        return True  # undated asking listing; kept but scored down on recency
    return months_between(l.listing_date, as_of) <= config.RECENCY_WINDOW_MONTHS


def _size_ok(l: Listing, subject: Subject, tol: float) -> bool:
    if subject.area_m2 is None or l.area_m2 is None:
        return True
    return abs(l.area_m2 - subject.area_m2) <= tol * subject.area_m2


def select_comparables(sales: list[Listing], subject: Subject,
                       as_of: date) -> tuple[list[tuple[Listing, float]], list[str]]:
    """Return (comp, similarity) pairs plus human-readable selection notes."""
    pool = neighborhood_pool(sales, subject)
    pool, n_collapsed = collapse_near_duplicates(pool)
    notes: list[str] = []
    if n_collapsed:
        notes.append(f"{n_collapsed} near-duplicate cross-posting(s) collapsed "
                     f"(same beds, area & price/m2 within {config.DEDUP_TOLERANCE*100:.0f}%)")
    recent = [l for l in pool if _within_recency(l, as_of)]
    notes.append(f"{len(pool)} same-submarket {subject.property_type} listings; "
                 f"{len(recent)} within {config.RECENCY_WINDOW_MONTHS} months")

    tol = config.SIZE_BAND_TOLERANCE
    selected = [l for l in recent if _size_ok(l, subject, tol)]
    while len(selected) < config.MIN_COMPS and tol < 2.0 and len(selected) < len(recent):
        tol += config.SIZE_BAND_WIDEN_STEP
        selected = [l for l in recent if _size_ok(l, subject, tol)]
        notes.append(f"size band widened to +/-{tol*100:.0f}% to reach {config.MIN_COMPS} comps")

    if not selected:
        selected = recent or pool
        notes.append("fell back to full submarket pool (sparse market)")

    scored = [(l, _similarity(l, subject, as_of)) for l in selected]
    scored.sort(key=lambda p: p[1], reverse=True)
    scored = scored[:config.TARGET_COMPS]
    notes.append(f"{len(scored)} comps selected (ranked by similarity)")
    return scored, notes


def _similarity(l: Listing, subject: Subject, as_of: date) -> float:
    w = config.SIMILARITY_WEIGHTS
    size = _size_similarity(l, subject)
    recency = _recency_similarity(l, as_of)
    attr = _attribute_match(l, subject)
    dist = _distance_similarity(l, subject)
    parts = {"size": size, "recency": recency, "attribute_match": attr, "distance": dist}
    active = {k: v for k, v in parts.items() if v is not None}
    total_w = sum(w[k] for k in active)
    if total_w == 0:
        return 0.0
    return sum(w[k] * v for k, v in active.items()) / total_w


def _size_similarity(l: Listing, subject: Subject) -> Optional[float]:
    if subject.area_m2 is None or l.area_m2 is None:
        return None
    rel = abs(l.area_m2 - subject.area_m2) / subject.area_m2
    return max(0.0, 1.0 - rel)


def _recency_similarity(l: Listing, as_of: date) -> Optional[float]:
    if l.listing_date is None:
        return 0.5
    age = months_between(l.listing_date, as_of)
    return max(0.0, 1.0 - age / config.RECENCY_WINDOW_MONTHS)


def _attribute_match(l: Listing, subject: Subject) -> float:
    fields = ["view", "parking", "finish_quality", "elevator"]
    checked = matched = 0
    for f in fields:
        s, c = getattr(subject, f), getattr(l, f)
        if s in ("unknown", None) or c in ("unknown", "u", None):
            continue
        checked += 1
        matched += 1 if s == c else 0
    if subject.floor_level is not None and l.floor_level is not None:
        checked += 1
        matched += 1 if abs(subject.floor_level - l.floor_level) <= 1 else 0
    return matched / checked if checked else 0.5


def _distance_similarity(l: Listing, subject: Subject) -> Optional[float]:
    km = haversine_km(subject.lat, subject.lng, l.lat, l.lng)
    if km is None:
        return None
    return max(0.0, 1.0 - km / 5.0)  # 5km = different submarket, similarity 0
