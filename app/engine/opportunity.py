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
"""

from __future__ import annotations

import bisect
from datetime import date
from typing import Any, Optional

from . import config
from .data import DataBundle
from .models import Subject
from .pipeline import recommend
from .stats import median, months_between, robust_keep
from . import evidence as _evidence

# v1 heuristic composite weights — DEFINED and EXPOSED (not derived, not hidden). Tune freely.
OPPORTUNITY_WEIGHTS = {
    "price_level": 0.30,
    "price_growth": 0.25,
    "demand_density": 0.30,
    "supply_pressure": 0.15,
}

# Builder Decision-Readiness dimensions — a broader, builder-facing framing on top of the
# opportunity components. v1 heuristic weights, DEFINED + EXPOSED + tunable. Dimensions we cannot
# yet source honestly are returned score=null (never fabricated) and their weight is redistributed.
READINESS_WEIGHTS = {
    "market_potential": 0.22,
    "demand": 0.20,
    "competition": 0.16,
    "future_growth": 0.12,
    "infrastructure": 0.10,
    "regulatory_readiness": 0.08,
    "pricing_confidence": 0.08,
    "construction_feasibility": 0.04,
}
_ENRICH_REASON = "data not yet available - pending area-intelligence enrichment"
_CONF_LABEL = {"H": "high", "M": "medium", "L": "low"}
_STD_READINESS_AREA_M2 = 175.0
_GROWTH_MIN_SAMPLE = 8       # min sales on each side of the window to trust a growth number
_GROWTH_RECENT_MONTHS = 12   # "recent" window
_GROWTH_OLDER_MONTHS = 36    # "older" window ceiling (12–36 mo back)
_PROJECT_SUPPLY_WEIGHT = 20  # each competing project counts as this many listings of supply

# --- Like-for-like price growth (mix-adjusted, adaptive window) ---
# Growth is measured by comparing SIMILAR units (same size band + bedroom count) across two
# equal-length periods, so a change in the mix of what got listed can't masquerade as price
# movement. The window adapts to the data: try year-over-year first, then 6-month, then 3-month
# (recent [0,W] vs prior (W,2W]); use the shortest that has enough matched pairs.
# (recent_max, older_min, older_max, label) in months. recent = [0, recent_max]; older =
# (older_min, older_max]. The older window is WIDE on purpose: the dated corpus is clustered
# with multi-year gaps, so an adjacent equal-length window often lands in an empty stretch —
# the trend needs the older side to reach back far enough to actually contain sales.
_GROWTH_WINDOWS = (
    (12, 12, 36, "recent year vs 1–3 yr ago"),
    (6, 6, 36, "recent 6mo vs up to 3 yr ago"),
)
_GROWTH_MIN_BUCKET = 3       # min matched sales per size/bed bucket on EACH side to trust it
_GROWTH_SIZE_BAND_M2 = 50    # like-for-like size buckets, 50 m² wide
_GROWTH_MIN_OVERALL = 5      # min dated sales each side for the unadjusted fallback


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


def _bucket_area_stats(bundle: DataBundle, as_of: date) -> dict[str, dict]:
    """One pass over listings + projects → per-neighborhood aggregates for scoring.

    Replaces the previous per-area rescans (_area_sales / _growth_raw / _supply_raw each
    walked the whole corpus for every area — O(areas × listings)). With hundreds of covered
    areas that made /opportunity time out; this is a single O(listings) pass instead.
    """
    stats: dict[str, dict] = {}

    def bucket(key: str) -> dict:
        return stats.setdefault(key, {"sales": [], "dated": [], "listings": 0, "projects": 0,
                                      "pop": [], "ntl": []})

    for l in bundle.listings:
        key = (l.neighborhood or "").strip().lower()
        if not key:
            continue
        b = bucket(key)
        b["listings"] += 1
        # Demand proxies are carried per-listing (enrich_spatial): aggregate them here so
        # Sale demand works from the national corpus even when neighborhood_geocontext is absent.
        if l.pop_density is not None:
            b["pop"].append(l.pop_density)
        if l.ntl_radiance is not None:
            b["ntl"].append(l.ntl_radiance)
        if l.listing_type == "sale" and l.price_per_m2:
            b["sales"].append(l.price_per_m2)
            # Keep dated, plausibly-priced sales with the attributes needed for
            # like-for-like growth: (months ago, price/m², size, bedrooms).
            if l.listing_date and l.price_per_m2 >= config.MIN_PLAUSIBLE_SALE_PPM2:
                b["dated"].append((months_between(l.listing_date, as_of),
                                   l.price_per_m2, l.area_m2, l.bedrooms))
    for p in bundle.projects:
        if p.status in ("selling", "construction", "planned"):
            key = (p.neighborhood or "").strip().lower()
            if key:
                bucket(key)["projects"] += 1
    return stats


def _percentile_ranks(raw: dict[str, Optional[float]], invert: bool = False
                      ) -> dict[str, Optional[float]]:
    """Rank each area against the rest (0–100 = share of areas with a lower value). Robust to
    outliers — one huge area can't compress everyone else the way min-max does. `invert` flips
    it so a LOW raw value scores HIGH (used for competition: fewer listings = more room)."""
    vals = sorted(v for v in raw.values() if v is not None)
    n = len(vals)
    out: dict[str, Optional[float]] = {}
    for a, v in raw.items():
        if v is None:
            out[a] = None
        elif n <= 1:
            out[a] = 50.0
        else:
            pr = bisect.bisect_left(vals, v) / (n - 1) * 100  # % of areas strictly below
            out[a] = 100 - pr if invert else pr
    return out


def _lfl_key(sale: tuple) -> tuple:
    """Like-for-like bucket key for a dated sale (_, _, area_m2, bedrooms): (size band, beds)."""
    area = sale[2]
    band = None if not area else int(area // _GROWTH_SIZE_BAND_M2)
    return (band, sale[3])


def _like_for_like_growth(recent: list[tuple], older: list[tuple]) -> Optional[tuple]:
    """Median price/m² change between two periods, computed WITHIN matched size/bed buckets and
    combined by sample weight — so composition shifts don't masquerade as price movement.
    Returns (growth_pct, n_matched_buckets) or None if no bucket has enough on both sides."""
    rb: dict[tuple, list] = {}
    ob: dict[tuple, list] = {}
    for s in recent:
        rb.setdefault(_lfl_key(s), []).append(s[1])
    for s in older:
        ob.setdefault(_lfl_key(s), []).append(s[1])
    num = den = 0.0
    matched = 0
    for k, rlist in rb.items():
        olist = ob.get(k)
        if not olist or len(rlist) < _GROWTH_MIN_BUCKET or len(olist) < _GROWTH_MIN_BUCKET:
            continue
        m_old = median(olist)
        if not m_old:
            continue
        g = (median(rlist) - m_old) / m_old * 100
        w = min(len(rlist), len(olist))
        num += g * w
        den += w
        matched += 1
    if den == 0:
        return None
    return num / den, matched


def _growth_reason(gi: Optional[dict]) -> str:
    if gi is None:
        return "not enough dated sales to measure a trend yet"
    if gi["method"] == "like-for-like":
        n = gi["buckets"]
        return (f"like-for-like {gi['window']}: {gi['pct']:+.1f}% "
                f"(median across {n} size/bed bucket{'s' if n != 1 else ''})")
    return (f"{gi['window']}: {gi['pct']:+.1f}% "
            "(unadjusted median — too sparse for like-for-like matching)")


def _overall_growth(recent: list[tuple], older: list[tuple]) -> Optional[float]:
    """Unadjusted median price/m² change — the fallback when the dated data is too sparse to
    match like-for-like buckets. Composition-biased, so it is labelled as unadjusted."""
    if len(recent) < _GROWTH_MIN_OVERALL or len(older) < _GROWTH_MIN_OVERALL:
        return None
    m_old = median([s[1] for s in older])
    if not m_old:
        return None
    return (median([s[1] for s in recent]) - m_old) / m_old * 100


def _growth_adaptive(dated: list[tuple]) -> Optional[dict]:
    """Tiered, adaptive-window growth. Preference order:
      1. mix-adjusted like-for-like, at the LONGEST window that supports it (year → 6mo → 3mo);
      2. else an unadjusted median comparison, at the longest window with enough dated depth.
    Returns {pct, window, method, buckets} or None."""
    windows = [(label, [s for s in dated if 0 <= s[0] <= rmax],
                [s for s in dated if omin < s[0] <= omax])
               for rmax, omin, omax, label in _GROWTH_WINDOWS]
    for label, recent, older in windows:
        lfl = _like_for_like_growth(recent, older)
        if lfl is not None:
            return {"pct": lfl[0], "window": label, "method": "like-for-like", "buckets": lfl[1]}
    for label, recent, older in windows:
        ov = _overall_growth(recent, older)
        if ov is not None:
            return {"pct": ov, "window": label, "method": "unadjusted", "buckets": None}
    return None


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


def _dim(score: Optional[float], reason: str, confidence: str) -> dict:
    return {"score": None if score is None else round(score), "reason": reason,
            "confidence": confidence}


def _pricing_confidence(bundle: DataBundle, area: str, as_of: date) -> tuple[Optional[float], str]:
    """Reuse the decision engine's own confidence on a standard subject for the area."""
    r = recommend(Subject(neighborhood=area, property_type="apartment",
                          area_m2=_STD_READINESS_AREA_M2), bundle, as_of)
    if r.recommended_price_jd_m2 <= 0:
        return None, r.confidence_label
    return r.confidence_numeric * 100, r.confidence_label


def _readiness(price_level: Optional[float], demand: Optional[float],
               competition: Optional[float], pricing_pct: Optional[float],
               pricing_label: str, construction_cost: Optional[float] = None,
               median_sale: Optional[float] = None, asez_count: int = 0) -> dict[str, Any]:
    mp_parts = [x for x in (price_level, demand) if x is not None]
    market_potential = sum(mp_parts) / len(mp_parts) if mp_parts else None

    # Construction feasibility = build-cost headroom (sale price vs the DoS cost FLOOR). Since the
    # floor understates real turnkey build, this reads optimistic -> confidence medium, not high.
    if construction_cost and median_sale:
        headroom = max(0.0, min(100.0, (median_sale - construction_cost) / median_sale * 100))
        construction_dim = _dim(
            headroom,
            f"sale ~{median_sale:.0f} vs DoS build floor ~{construction_cost:.0f} JD/m2 "
            f"({headroom:.0f}% headroom; floor understates turnkey, so optimistic)", "medium")
    else:
        construction_dim = _dim(None, _ENRICH_REASON, "low")

    # Regulatory readiness: only non-null where a documented tenure regime exists (Aqaba/ASEZ).
    if asez_count > 0:
        regulatory_dim = _dim(
            90, f"ASEZ documented foreign-ownership regime ({asez_count} official rules): "
                "non-Jordanian ownership permitted with resale locks - high regulatory clarity "
                "(v1 heuristic)", "medium")
    else:
        regulatory_dim = _dim(None, _ENRICH_REASON, "low")

    dims = {
        "market_potential": _dim(market_potential, "price level + demand proxy (portal + geocontext)",
                                 "medium" if market_potential is not None else "low"),
        "demand": _dim(demand, "population/night-light activity + listing density",
                       "medium" if demand is not None else "low"),
        "competition": _dim(competition,
                            "competitor projects + listing supply (low pressure = higher readiness)",
                            "medium" if competition is not None else "low"),
        "future_growth": _dim(None, _ENRICH_REASON, "low"),
        "infrastructure": _dim(None, _ENRICH_REASON, "low"),
        "regulatory_readiness": regulatory_dim,
        "pricing_confidence": _dim(
            pricing_pct,
            (f"decision-engine confidence '{pricing_label}' on a standard "
             f"{_STD_READINESS_AREA_M2:.0f} m2 subject" if pricing_pct is not None
             else "computed per selected area on demand (not run for the bulk heatmap)"),
            _CONF_LABEL.get(pricing_label, "low")),
        "construction_feasibility": construction_dim,
    }
    num = den = 0.0
    used = {}
    for k, w in READINESS_WEIGHTS.items():
        s = dims[k]["score"]
        if s is not None:
            num += w * s
            den += w
            used[k] = w
    overall_score = round(num / den, 1) if den else None
    tot = sum(used.values()) or 1.0
    weights_used = {k: round(w / tot, 4) for k, w in used.items()}
    confs = [dims[k]["confidence"] for k in used]
    overall_conf = ("low" if not confs or "low" in confs
                    else "high" if all(c == "high" for c in confs) else "medium")
    overall = _dim(overall_score,
                   f"weighted mean over {len(used)} computable dimension(s); "
                   f"{len(READINESS_WEIGHTS) - len(used)} pending enrichment", overall_conf)
    return {"overall": overall, "dimensions": dims, "weights": READINESS_WEIGHTS,
            "weights_used": weights_used, "version": "v1-heuristic"}


def opportunity_scores(bundle: DataBundle, areas: list[str],
                       as_of: Optional[date] = None,
                       centroids: Optional[dict[str, tuple]] = None) -> list[dict[str, Any]]:
    """Score every covered area against the others. Returns a list ranked high→low.

    `centroids` (lower-cased area → (lat, lng)) is echoed onto each row for the heatmap.
    """
    as_of = as_of or bundle.as_of or date.today()
    centroids = centroids or {}
    keys = {a: a.strip().lower() for a in areas}

    # Single O(listings) pass, then every per-area stat is a dict lookup.
    stats = _bucket_area_stats(bundle, as_of)
    empty = {"sales": [], "dated": [], "listings": 0, "projects": 0, "pop": [], "ntl": []}

    def _st(a: str) -> dict:
        return stats.get(keys[a], empty)

    def _kept_sales(a: str) -> list[float]:
        raw = _st(a)["sales"]
        keep = robust_keep(raw, config.MIN_PLAUSIBLE_SALE_PPM2)
        return [v for v, k in zip(raw, keep) if k]

    price_raw = {a: (median(_kept_sales(a)) or None) for a in areas}
    growth_info = {a: _growth_adaptive(_st(a)["dated"]) for a in areas}
    growth_raw = {a: (growth_info[a]["pct"] if growth_info[a] else None) for a in areas}
    pop_raw = {a: (median(_st(a)["pop"]) or None) for a in areas}
    light_raw = {a: (median(_st(a)["ntl"]) or None) for a in areas}
    # Competition = the area's own active-listing count, but ranked by PERCENTILE (not min-max)
    # so one huge market (Abdoun ~3.5k listings) can't distort every other area's score. There
    # is no project-supply data yet, so the proxy is listings only (projects re-added when live).
    supply_raw = {a: float(_st(a)["listings"]) for a in areas}

    # All components are percentile-ranked (not min-max): a single garbage outlier — e.g. an
    # area whose median "sale" is 120,000 JD/m² from a bad row — must not crush every real area
    # to ~0. Rank asks "how does this area stand vs the others", which is robust to such tails.
    price_n = _percentile_ranks(price_raw)
    growth_n = _percentile_ranks(growth_raw)
    pop_n = _percentile_ranks(pop_raw)
    light_n = _percentile_ranks(light_raw)
    supply_n = _percentile_ranks(supply_raw, invert=True)

    out: list[dict[str, Any]] = []
    for a in areas:
        demand_parts = [x for x in (pop_n[a], light_n[a]) if x is not None]
        demand = sum(demand_parts) / len(demand_parts) if demand_parts else None

        components = {
            "price_level": _component(
                price_n[a],
                f"median sale ~{price_raw[a]:.0f} JD/m² (relative to covered set)"
                if price_raw[a] else "no plausible sale listings"),
            "price_growth": _component(growth_n[a], _growth_reason(growth_info[a])),
            "demand_density": _component(
                demand,
                (f"pop density ~{pop_raw[a]:,.0f}/km²"
                 if pop_raw[a] is not None else "no density")
                + (f", night-light ~{light_raw[a]:.0f}" if light_raw[a] is not None else "")
                + " (activity proxy, from listings)" if demand is not None
                else "no pop-density / night-light on this area's listings yet"),
            "supply_pressure": _component(
                supply_n[a],
                f"{supply_raw[a]:.0f} active listings (percentile-ranked vs all areas; "
                "fewer listings = less competition = higher score)"),
        }
        weights_used = {n: round(w, 4) for n, w in OPPORTUNITY_WEIGHTS.items()
                        if components[n]["score"] is not None}
        total_w = sum(weights_used.values()) or 1.0
        weights_used = {n: round(w / total_w, 4) for n, w in weights_used.items()}
        # Pricing confidence is a FULL recommend() per area — far too heavy to run for
        # every covered area on this bulk/heatmap endpoint. It is left pending here and
        # filled in for the single SELECTED area on the client (from its live result).
        cc = bundle.construction_cost
        build_cost = cc.amman_jd_m2 if cc else None
        asez_n = len(asez_rules_for(bundle, keys[a]))
        readiness = _readiness(price_n[a], demand, supply_n[a], None, "unknown",
                               construction_cost=build_cost, median_sale=price_raw[a],
                               asez_count=asez_n)
        lat, lng = centroids.get(keys[a], (None, None))
        out.append({
            "area": a,
            "score": _composite(components),
            "components": components,
            "weights_used": weights_used,
            "readiness": readiness,
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


# --- Feasibility (build-readiness) dimensions --------------------------------------------------
# A broad, honest feasibility structure. Each dimension reports what we can source and marks the
# rest not_available (never invented). Extensible: as GAM zoning / environmental / legal datasets
# are collected, flip a dimension from not_available to partial/available.

def _dim_status(status: str, detail: str, sources: list[dict],
                value: Optional[dict] = None) -> dict:
    out = {"status": status, "detail": detail, "sources": sources}
    if value is not None:
        out["value"] = value
    return out


def asez_rules_for(bundle: DataBundle, key: str) -> list:
    """ASEZ foreign-ownership / land-tenure policy rules attached to this submarket (Aqaba)."""
    return [it for it in bundle.evidence_items
            if it.type == "policy" and it.impact_area.strip().lower() == key]


def feasibility_for(bundle: DataBundle, area: str, zoning: Optional[dict] = None,
                    construction: Optional[dict] = None) -> dict[str, Any]:
    """Broad build-feasibility read for one submarket. `zoning` (from the caller) carries the
    picked zoning proxy (official ASEZ for Aqaba, OSM elsewhere); `construction` carries the
    official DoS cost floor. ASEZ policy rules are read from the bundle."""
    key = area.strip().lower()
    sales = [l.price_per_m2 for l in bundle.sales()
             if l.neighborhood.strip().lower() == key
             and l.price_per_m2 and l.price_per_m2 >= config.MIN_PLAUSIBLE_SALE_PPM2]

    asez = asez_rules_for(bundle, key)
    if asez:
        value = {"foreign_ownership_rules": len(asez)}
        srcs = []
        if zoning and zoning.get("kind") == "asez" and zoning.get("plot_count"):
            value["official_zoning_polygons"] = zoning["plot_count"]
            if zoning.get("source"):
                srcs.append(zoning["source"])
        srcs += [{"name": it.source_name, "url": it.source_url,
                  "capture_date": it.capture_date or "unknown"} for it in asez]
        regulatory = _dim_status(
            "available",
            f"Official ASEZ zoning + foreign-ownership regime ({len(asez)} rules): non-Jordanian "
            "ownership permitted with resale locks; land sale/lease governed by ASEZ regulation "
            "(ASEZA official).",
            _dedupe(srcs), value)
    elif zoning and zoning.get("plot_count"):
        regulatory = _dim_status(
            "partial",
            "OSM-derived land-use plots exist citywide but are not attributed to this "
            "neighborhood; per-area FAR / max-height / zone class pending GAM official data.",
            [zoning["source"]] if zoning.get("source") else [],
            {"osm_landuse_plots_citywide": zoning["plot_count"]})
    else:
        regulatory = _dim_status(
            "not_available",
            "Per-area zoning (FAR, max height, zone class) pending GAM official data.", [])

    if construction and construction.get("value"):
        construction_dim = _dim_status(
            "available",
            f"Official DoS building-licence filed construction cost ({construction.get('authority', '')}) "
            "- a conservative FLOOR that understates full turnkey build; per-area geotechnical "
            "assessment still pending.",
            [construction["source"]] if construction.get("source") else [],
            {"construction_cost_jd_m2": round(construction["value"], 1),
             "authority": construction.get("authority"), "basis": "filed-licence floor"})
    else:
        construction_dim = _dim_status(
            "not_available", "No official construction-cost series available.", [])

    if sales:
        operational = _dim_status(
            "available",
            "Active resale market observed from portal listings.",
            [{"name": "Portal listings", "url": "internal://listings",
              "capture_date": bundle.as_of.isoformat()}],
            {"median_sale_jd_m2": round(median(sales), 1), "sale_listing_count": len(sales)})
    else:
        operational = _dim_status(
            "not_available", "No plausible sale listings for this submarket.", [])

    dims = {
        "regulatory_zoning": regulatory,
        "construction_engineering": construction_dim,
        "operational_market": operational,
        "environmental": _dim_status(
            "not_available", "Environmental / geotechnical data not yet collected.", []),
        "legal": _dim_status(
            "not_available", "Title / legal due-diligence data not yet collected.", []),
        "financial": _dim_status(
            "not_available",
            "Financing terms / mortgage / transfer-tax data not yet collected.", []),
    }
    summary = {"available": 0, "partial": 0, "not_available": 0}
    for d in dims.values():
        summary[d["status"]] += 1
    return {"neighborhood": area, "dimensions": dims, "summary": summary,
            "note": "Honest feasibility scaffold — dimensions flip to partial/available as "
                    "datasets are enriched; empties are never fabricated."}


def _dedupe(sources: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in sources:
        k = (s.get("name"), s.get("url"))
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out[:8]
