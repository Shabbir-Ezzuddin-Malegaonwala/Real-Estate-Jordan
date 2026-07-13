"""Area Monitoring / Market-Explorer data.

Everything the Monitoring dashboard graphs is computed HERE, server-side, and returned ready to
plot — the frontend only draws bars/points, it does no math. That keeps every number traceable to
the engine (no browser-side heuristics that can drift from the backend) and nothing is fabricated:
where an area has too little data for a graph, that graph comes back empty and the UI says so.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Optional

from . import config
from .data import DataBundle
from .stats import median, robust_keep


def _histogram(values: list[float], n_bins: int = 8) -> list[dict[str, Any]]:
    """Equal-width bins over the price/m² values → [{low, high, count}]. 'Where prices land.'"""
    vals = sorted(v for v in values if v)
    if len(vals) < 3:
        return []
    lo, hi = vals[0], vals[-1]
    if hi <= lo:
        return [{"low": round(lo), "high": round(hi), "count": len(vals)}]
    width = (hi - lo) / n_bins
    bins: list[dict[str, Any]] = []
    for i in range(n_bins):
        b_lo, b_hi = lo + i * width, lo + (i + 1) * width
        if i == n_bins - 1:  # last bin is inclusive on the top edge
            count = sum(1 for v in vals if b_lo <= v <= b_hi)
        else:
            count = sum(1 for v in vals if b_lo <= v < b_hi)
        bins.append({"low": round(b_lo), "high": round(b_hi), "count": count})
    return bins


def _yearly_median(sales: list, min_year: int) -> list[dict[str, Any]]:
    """Median price/m² per calendar year (dated, plausible sales only) → [{year, median, n}].
    Years with no dated sales are simply absent — the UI shows the gap honestly, never interpolates."""
    by_year: dict[int, list[float]] = {}
    for l in sales:
        if (l.listing_date and l.price_per_m2
                and l.price_per_m2 >= config.MIN_PLAUSIBLE_SALE_PPM2
                and l.listing_date.year >= min_year):
            by_year.setdefault(l.listing_date.year, []).append(l.price_per_m2)
    return [{"year": y, "median": round(median(by_year[y]), 1), "n": len(by_year[y])}
            for y in sorted(by_year)]


def _by_portal(sales: list) -> list[dict[str, Any]]:
    """Listing count per source portal → [{portal, count}]. 'Where the data comes from.'"""
    c = Counter((l.portal or "unknown") for l in sales)
    return [{"portal": p, "count": n} for p, n in c.most_common()]


_PEER_MIN_SALE = 30  # only rank areas with enough sale depth for a trustworthy median


def peer_comparison(bundle: DataBundle, opp_scores: list[dict],
                    selected_key: str) -> list[dict[str, Any]]:
    """Cross-area comparison rows for the leaderboards + scatter: each area's real median price/m²,
    its opportunity score, and sale depth. Only areas with enough sale listings are ranked (so a
    fluke n=2 area or a garbage 120k row can't top the board); the selected area is always kept.
    All computed here — the browser only renders it."""
    per_area: dict[str, list[float]] = {}
    for l in bundle.sales():
        if l.price_per_m2 and l.price_per_m2 >= config.MIN_PLAUSIBLE_SALE_PPM2:
            per_area.setdefault(l.neighborhood.strip().lower(), []).append(l.price_per_m2)
    listings: dict[str, int] = {}
    for l in bundle.listings:
        k = (l.neighborhood or "").strip().lower()
        if k:
            listings[k] = listings.get(k, 0) + 1

    out: list[dict[str, Any]] = []
    for o in opp_scores:
        k = o["area"].strip().lower()
        prices = per_area.get(k)
        if not prices or (len(prices) < _PEER_MIN_SALE and k != selected_key):
            continue
        out.append({
            "name": o["area"],
            "median_price": round(median(prices), 1),
            "opportunity": o["score"],
            "n_sale": len(prices),
            "listings": listings.get(k, 0),
            "is_selected": k == selected_key,
        })
    return out


def area_monitoring(bundle: DataBundle, neighborhood: str,
                    as_of: Optional[date] = None) -> dict[str, Any]:
    """All Monitoring-dashboard graph data for one area, fully computed. Each block is plot-ready."""
    key = neighborhood.strip().lower()
    sales = [l for l in bundle.sales() if l.neighborhood.strip().lower() == key]
    ppm2 = [l.price_per_m2 for l in sales
            if l.price_per_m2 and l.price_per_m2 >= config.MIN_PLAUSIBLE_SALE_PPM2]
    # Trim the extreme tails (a few bad rows at 10k+ JD/m²) so the histogram shows the real
    # spread instead of one giant bar. Same robust filter the comp engine uses.
    keep = robust_keep(ppm2, config.MIN_PLAUSIBLE_SALE_PPM2)
    ppm2_typical = [v for v, k in zip(ppm2, keep) if k]

    # Rank vs every other area, by median sale price/m².
    per_area: dict[str, list[float]] = {}
    for l in bundle.sales():
        if l.price_per_m2 and l.price_per_m2 >= config.MIN_PLAUSIBLE_SALE_PPM2:
            per_area.setdefault(l.neighborhood.strip().lower(), []).append(l.price_per_m2)
    medians = {k: median(v) for k, v in per_area.items() if v}
    my_median = medians.get(key)
    price_rank: Optional[dict[str, Any]] = None
    if my_median and len(medians) > 1:
        below = sum(1 for m in medians.values() if m < my_median)
        price_rank = {
            "median": round(my_median, 1),
            "percentile": round(below / (len(medians) - 1) * 100),
            "of_n": len(medians),
            "all_medians": sorted(round(m) for m in medians.values()),  # for the distribution strip
        }

    return {
        "neighborhood": neighborhood,
        "n_sale": len(sales),
        "n_typical": len(ppm2_typical),
        "price_histogram": _histogram(ppm2_typical),
        "yearly_median": _yearly_median(sales, min_year=2015),
        "by_portal": _by_portal(sales)[:8],
        "price_rank": price_rank,
    }
