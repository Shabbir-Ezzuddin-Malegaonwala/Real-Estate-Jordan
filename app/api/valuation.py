"""Seller property valuation from a dropped pin.

Market value comes from the nearest geocoded comparable listings (asking prices
calibrated toward transaction level) — the pin's exact lat/lng drives it. The
cost breakdown (land + construction + fees/tax) is informational: it shows what
went into the property, from the real re_* tables. Nothing is fabricated; when a
figure isn't available it is omitted.

Self-contained: opens the canonical DB directly (JORDAN_RE_DB), so it doesn't
depend on the engine's in-memory bundle.
"""
from __future__ import annotations
import math
import os
import sqlite3
import statistics as st
from typing import Any

_DB = os.environ.get("JORDAN_RE_DB", os.path.join(os.path.dirname(__file__), "..", "..", "db", "jordan_re.sqlite"))

# asking -> transaction calibration (Jordan portals list above sale level)
_ASK_TO_TX = 0.90
_MIN_COMPS = 6
_RADII_KM = [1.0, 2.0, 3.0, 5.0]

# finish label -> the finish_class families in re_construction_costs
_FINISH_CLASSES = {
    "basic": ("economy_turnkey", "finishing_only_economy"),
    "standard": ("standard_turnkey", "finishing_only_standard", "good_turnkey"),
    "high": ("deluxe_turnkey", "finishing_only_deluxe", "luxury_turnkey"),
}


def _num(x: Any) -> float | None:
    try:
        if x is None or str(x).strip().upper() == "NULL":
            return None
        return float(x)
    except (ValueError, TypeError):
        return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _nearby_ppm2(c: sqlite3.Connection, lat: float, lng: float) -> tuple[list[float], float | None, int]:
    """Return (ppm2 list, radius used, comp count) — expands the radius until enough comps."""
    for radius in _RADII_KM:
        dlat = radius / 111.0
        dlng = radius / (111.0 * max(0.2, math.cos(math.radians(lat))))
        rows = c.execute(
            "SELECT lat, lng, price_jd, area_m2 FROM listings "
            "WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ? "
            "AND price_jd > 0 AND area_m2 > 0 AND property_type = 'apartment' "
            "AND listing_type = 'sale'",  # sale only — rent listings would crater ppm2
            (lat - dlat, lat + dlat, lng - dlng, lng + dlng),
        ).fetchall()
        ppm2 = [
            (p / a)
            for (la, ln, p, a) in rows
            if _haversine_km(lat, lng, la, ln) <= radius and 50 < (p / a) < 4000
        ]
        if len(ppm2) >= _MIN_COMPS:
            return ppm2, radius, len(ppm2)
    return ppm2, _RADII_KM[-1], len(ppm2)  # best effort at the widest radius


def _construction_cost_per_m2(c: sqlite3.Connection, finish: str) -> float | None:
    classes = _FINISH_CLASSES.get(finish, _FINISH_CLASSES["standard"])
    mids: list[float] = []
    for cls in classes:
        for lo, hi in c.execute(
            "SELECT cost_min_jd, cost_max_jd FROM re_construction_costs WHERE finish_class = ?", (cls,)
        ):
            lo_n, hi_n = _num(lo), _num(hi)
            if lo_n and hi_n:
                mids.append((lo_n + hi_n) / 2)
            elif lo_n:
                mids.append(lo_n)
    return round(st.median(mids)) if mids else None


def _nearest_area(c: sqlite3.Connection, lat: float, lng: float) -> str | None:
    best, bestd = None, 1e9
    for name, la, ln in c.execute(
        "SELECT neighborhood, centroid_lat, centroid_lng FROM area_amenities WHERE centroid_lat IS NOT NULL"
    ):
        try:
            d = _haversine_km(lat, lng, float(la), float(ln))
        except (ValueError, TypeError):
            continue
        if d < bestd:
            best, bestd = name, d
    return best


def _land_price_per_m2(c: sqlite3.Connection, area: str | None) -> float | None:
    if not area:
        return None
    row = c.execute(
        "SELECT price_typical_jd_m2, price_min_jd_m2, price_max_jd_m2 FROM re_land_prices "
        "WHERE canonical_neighborhood = ? OR area_en = ? LIMIT 1", (area, area)
    ).fetchone()
    if not row:
        return None
    typ, lo, hi = _num(row[0]), _num(row[1]), _num(row[2])
    if typ:
        return typ
    if lo and hi:
        return round((lo + hi) / 2)
    return lo or hi


def _transfer_tax_pct(c: sqlite3.Connection) -> float | None:
    """Land-department transfer/registration fee as a % of value, if recorded."""
    for fee, value, unit, basis in c.execute(
        "SELECT fee_en, value, unit, basis FROM re_soft_costs_fees"
    ):
        blob = f"{fee} {unit} {basis}".lower()
        v = _num(value)
        if v and ("transfer" in blob or "registration" in blob) and ("%" in blob or "percent" in blob or "pct" in blob):
            return v
    return None


def value_property(
    lat: float, lng: float, total_area_m2: float, finish: str = "standard",
    mode: str = "building", flats: int | None = None, flat_area_m2: float | None = None,
    plot_area_m2: float | None = None,
) -> dict[str, Any]:
    c = sqlite3.connect(_DB)
    try:
        ppm2_list, radius, n_comps = _nearby_ppm2(c, lat, lng)
        area = _nearest_area(c, lat, lng)
        if not ppm2_list:
            return {"ok": False, "reason": "No comparable sales found near this location.",
                    "nearest_area": area, "comps": 0}

        ask_median = st.median(ppm2_list)
        value_per_m2 = round(ask_median * _ASK_TO_TX)
        lo = round(st.quantiles(ppm2_list, n=4)[0] * _ASK_TO_TX) if n_comps >= 4 else round(value_per_m2 * 0.85)
        hi = round(st.quantiles(ppm2_list, n=4)[2] * _ASK_TO_TX) if n_comps >= 4 else round(value_per_m2 * 1.15)

        # headline value depends on what the seller is valuing
        if mode == "flat":
            unit_area = flat_area_m2 or (total_area_m2 / flats if flats else total_area_m2)
            headline_area = unit_area
        else:
            headline_area = total_area_m2
        value = round(value_per_m2 * headline_area)

        # informational cost breakdown (what it's built from)
        cc_m2 = _construction_cost_per_m2(c, finish)
        construction = round(cc_m2 * total_area_m2) if cc_m2 else None
        land_m2 = _land_price_per_m2(c, area)
        land = round(land_m2 * plot_area_m2) if (land_m2 and plot_area_m2) else None
        tax_pct = _transfer_tax_pct(c)
        transfer_tax = round(value * tax_pct / 100) if tax_pct else None

        out: dict[str, Any] = {
            "ok": True,
            "mode": mode,
            "nearest_area": area,
            "comps": n_comps,
            "comp_radius_km": radius,
            "value_per_m2": value_per_m2,
            "value_per_m2_low": lo,
            "value_per_m2_high": hi,
            "headline_area_m2": round(headline_area),
            "estimated_value_jd": value,
            "value_low_jd": round(lo * headline_area),
            "value_high_jd": round(hi * headline_area),
        }
        if mode == "building" and flats:
            out["per_flat_value_jd"] = round(value / flats)
            out["flats"] = flats
        breakdown = {}
        if construction is not None:
            breakdown["construction_jd"] = construction
            breakdown["construction_per_m2"] = cc_m2
        if land is not None:
            breakdown["land_jd"] = land
            breakdown["land_per_m2"] = land_m2
        if transfer_tax is not None:
            breakdown["transfer_tax_jd"] = transfer_tax
            breakdown["transfer_tax_pct"] = tax_pct
        if breakdown:
            out["cost_breakdown"] = breakdown
        return out
    finally:
        c.close()
