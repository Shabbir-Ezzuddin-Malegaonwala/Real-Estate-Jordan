"""The seven grounded tools the agent may call.

Each tool returns a JSON string (so the model receives structured, citable data)
whose payload always includes a `source` block. The SSE layer inspects the raw
tool output to drive UI activity indicators, citation chips and engine cards.
"""

from __future__ import annotations

import json
from statistics import median
from typing import Optional

from langchain_core.tools import tool

# NOTE: engine_bridge MUST be imported before anything from `app.engine`, because
# importing it is what puts the recommendation repo on sys.path (see its header).
from .engine_bridge import get_engine
from app.engine.config import MIN_PLAUSIBLE_SALE_PPM2  # noqa: E402  (order matters)
from app.engine.stats import robust_keep  # noqa: E402

# Portal data carries whole-building / mis-keyed placeholders (e.g. area_m2 = 1,
# price 3.5M JD/m2). A real apartment/villa is never this small — drop them so
# they can't surface as "comparables".
_MIN_COMP_AREA_M2 = 25.0

from .calc import calculate as _calculate
from .geo import geocode_address as _geocode
from .search import web_search as _web_search
from .sql_tool import query_data as _query_data


def _j(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


@tool
def list_neighborhoods() -> str:
    """List priceable Jordan submarkets with comp depth (sale-listing count) and
    median price/m². Call before pricing/comparing to see what the engine covers."""
    engine = get_engine()
    all_areas = engine.areas(min_sales=5)
    # Return the best-sampled ~40 to keep the payload small; note the full count.
    top = engine.areas(min_sales=30)[:40]
    areas = [{"neighborhood": a.name, "sale_comps": a.sale_count,
              "median_price_jd_m2": a.median_price_per_m2} for a in top]
    return _j({
        "total_priceable": len(all_areas),
        "showing_top": len(areas),
        "neighborhoods": areas,
        "note": "More submarkets exist; name one directly to price it.",
        "source": {"name": "Canonical DB (jordan_re.sqlite) listings", "kind": "database"},
    })


@tool
def get_recommendation(
    neighborhood: str,
    property_type: str = "apartment",
    area_m2: float = 175.0,
    bedrooms: Optional[int] = None,
    floor_level: Optional[int] = None,
    finish_quality: Optional[str] = None,
    building_age_years: Optional[int] = None,
    view: Optional[str] = None,
    parking: Optional[str] = None,
) -> str:
    """The ONLY source of price numbers. Evidence-backed launch price for a
    property in a Jordan neighbourhood: min-safe/recommended/premium band (JD/m2),
    confidence + interval, coverage flags, top comps, provenance. property_type =
    apartment|villa|land|commercial. For a specific address, geocode_address first
    then pass its nearest_priceable_neighborhood. Never state a price not from here."""
    engine = get_engine()
    result = engine.price(
        neighborhood, property_type=property_type, area_m2=area_m2, bedrooms=bedrooms,
        floor_level=floor_level, finish_quality=finish_quality,
        building_age_years=building_age_years, view=view, parking=parking,
    )
    return _j(result)


@tool
def get_comparables(neighborhood: str, limit: int = 8) -> str:
    """Recent comparable SALE listings in a Jordan area (price/m2, area, beds,
    view, source URL, coords). Use for 'what's on the market' / raw evidence."""
    engine = get_engine()
    area = engine.resolve(neighborhood)
    if area is None:
        return _j({"error": "neighborhood_not_found", "requested": neighborhood,
                   "did_you_mean": [a.name for a in engine.areas(min_sales=50)[:12]]})
    key = area.key
    candidates = [
        l for l in engine.bundle.sales()
        if (l.neighborhood or "").strip().lower() == key
        and l.price_per_m2 and l.price_per_m2 >= MIN_PLAUSIBLE_SALE_PPM2
        and l.area_m2 and l.area_m2 >= _MIN_COMP_AREA_M2
    ]
    # Trim outliers exactly the way the pricing engine does (log-space MAD), so
    # mis-keyed / whole-building placeholders never surface as "comparables".
    mask = robust_keep([l.price_per_m2 for l in candidates], MIN_PLAUSIBLE_SALE_PPM2)
    rows = [l for l, keep in zip(candidates, mask) if keep]
    rows.sort(key=lambda l: str(l.listing_date or ""), reverse=True)
    ppm2 = [l.price_per_m2 for l in rows]
    comps = [
        {
            "price_per_m2": round(l.price_per_m2, 1),
            "area_m2": l.area_m2,
            "bedrooms": l.bedrooms,
            "view": l.view,
            "listing_date": l.listing_date.isoformat() if l.listing_date else None,
            "lat": l.lat,
            "lng": l.lng,
            "source": {"name": l.source_name, "url": l.listing_url},
        }
        for l in rows[:min(limit, 10)]
    ]
    return _j({
        "neighborhood": area.name,
        "total_comps": len(rows),
        "median_price_jd_m2": round(median(ppm2), 1) if ppm2 else None,
        "comparables": comps,
        "centroid": ([area.centroid_lng, area.centroid_lat] if area.centroid_lat else None),
        "source": {"name": "Canonical DB (jordan_re.sqlite) listings", "kind": "database"},
    })


@tool
def query_data(question: str) -> str:
    """Read-only SQL analytics over the canonical DB for any market/statistical
    figure that ISN'T a launch price: rental yields, DoS building costs, macro
    series (CBJ policy rate, USD/JOD, CPI, RE price index, transaction volumes),
    POIs, listing stats, geo-context. Returns rows + the SQL used. Ask precisely,
    e.g. 'latest CBJ policy rate from macro_series'."""
    return _j(_query_data(question))


@tool
def geocode_address(address: str) -> str:
    """Resolve a Jordan address/place to {lat, lng, nearest_priceable_neighborhood}
    via OpenStreetMap/Nominatim. ALWAYS call before pricing a specific address so
    you price the right submarket and the map can fly there."""
    return _j(_geocode(address))


@tool
def web_search(query: str) -> str:
    """Web search for CURRENT/time-sensitive info (rate moves, USD/JOD, inflation,
    regulations, permits, area news, projects). Returns results with source URLs +
    dates to cite. Use for 'now/recent/this year' or post-cutoff events, and cite
    the URLs. If empty, say you couldn't find current info rather than guessing."""
    return _j(_web_search(query))


@tool
def calculate(expression: str) -> str:
    """MUST be used for EVERY calculation (totals, yields, margins, residual land
    value, %, unit conversions) — no mental math. Substitute concrete numbers
    first, e.g. calculate('964.2 * 180'). Rejects non-math expressions."""
    return _j(_calculate(expression))


ALL_TOOLS = [
    list_neighborhoods,
    get_recommendation,
    get_comparables,
    query_data,
    geocode_address,
    web_search,
    calculate,
]
