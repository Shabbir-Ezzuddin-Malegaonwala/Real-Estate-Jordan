"""Pure-stdlib numeric helpers. No numpy so the engine runs anywhere Python 3.13 does."""

from __future__ import annotations

import math
from datetime import date
from statistics import median as _median
from typing import Optional, Sequence


def median(xs: Sequence[float]) -> Optional[float]:
    vals = [x for x in xs if x is not None]
    return _median(vals) if vals else None


def mean(xs: Sequence[float]) -> Optional[float]:
    vals = [x for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def weighted_mean(xs: Sequence[float], ws: Sequence[float]) -> Optional[float]:
    num = sum(x * w for x, w in zip(xs, ws))
    den = sum(ws)
    return num / den if den else None


def weighted_std(xs: Sequence[float], ws: Sequence[float]) -> float:
    mu = weighted_mean(xs, ws)
    den = sum(ws)
    if mu is None or den == 0:
        return 0.0
    var = sum(w * (x - mu) ** 2 for x, w in zip(xs, ws)) / den
    return math.sqrt(max(var, 0.0))


def coeff_of_variation(xs: Sequence[float]) -> float:
    vals = [x for x in xs if x is not None]
    if len(vals) < 2:
        return 0.0
    mu = mean(vals)
    if not mu:
        return 0.0
    sd = (sum((x - mu) ** 2 for x in vals) / (len(vals) - 1)) ** 0.5
    return sd / mu


def ols_slope(points: Sequence[tuple[float, float]]) -> Optional[float]:
    """Least-squares slope dy/dx. None if degenerate (no x variation)."""
    pts = [(x, y) for x, y in points if x is not None and y is not None]
    n = len(pts)
    if n < 2:
        return None
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in pts)
    return sxy / sxx


def months_between(earlier: date, later: date) -> float:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month) + (later.day - earlier.day) / 30.0


def quarter_of(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def haversine_km(a_lat, a_lng, b_lat, b_lng) -> Optional[float]:
    if None in (a_lat, a_lng, b_lat, b_lng):
        return None
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lng - a_lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def pct(fraction: float) -> str:
    return f"{'+' if fraction >= 0 else ''}{fraction * 100:.1f}%"


def to_monthly_rent(ppm2: Optional[float], cap: float) -> Optional[float]:
    """Normalise a rent price/m² to a MONTHLY figure. Portal rent quotes mix monthly and
    annual with no period field; a value above `cap` is an annual quote (÷12), and one still
    above `cap` afterwards is sale-price contamination (dropped). See config.RENT_MONTHLY_MAX_PPM2."""
    if ppm2 is None or ppm2 <= 0:
        return None
    monthly = ppm2 if ppm2 <= cap else ppm2 / 12.0
    return monthly if monthly <= cap else None


def robust_keep(values: Sequence[float], floor: float, k: float = 3.5) -> list[bool]:
    """Boolean keep-mask: drop <= floor, then log-space MAD outlier rejection.

    Real-estate price/m² is right-skewed, so outliers are judged in log space (a 3×
    median reads the same distance as a 1/3× median). Robust to the 0-price and
    whole-building placeholders in the raw portal data. Small samples: floor only.
    """
    logs = [math.log(v) for v in values if v is not None and v > floor]
    if len(logs) < 6:
        return [v is not None and v > floor for v in values]
    med = _median(logs)
    dev = _median([abs(x - med) for x in logs]) or 1e-9
    lo, hi = med - k * 1.4826 * dev, med + k * 1.4826 * dev
    keep = []
    for v in values:
        if v is None or v <= floor:
            keep.append(False)
        else:
            keep.append(lo <= math.log(v) <= hi)
    return keep
