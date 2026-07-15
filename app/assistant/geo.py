"""Address -> coordinates -> nearest priceable submarket.

Free by default: OpenStreetMap's Nominatim via geopy (no API key). Nominatim
etiquette requires a descriptive User-Agent, <=1 request/second, and country
scoping — all set here. Results are cached per-process so repeated lookups in a
session don't hammer the service.
"""

from __future__ import annotations

import threading
import time
from functools import lru_cache
from typing import Optional

from geopy.geocoders import Nominatim

from .config import NOMINATIM_USER_AGENT
from .engine_bridge import get_engine

_geocoder = Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=10)

# Serialise + rate-limit Nominatim calls to honour the <=1 req/s policy.
_lock = threading.Lock()
_last_call = [0.0]
_MIN_INTERVAL_S = 1.1


def _throttle() -> None:
    with _lock:
        wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


@lru_cache(maxsize=256)
def geocode_address(address: str) -> dict:
    query = (address or "").strip()
    if not query:
        return {"error": "empty_address"}

    # Bias to Jordan; append the country if the user didn't.
    q = query if "jordan" in query.lower() else f"{query}, Jordan"
    try:
        _throttle()
        loc = _geocoder.geocode(q, country_codes="jo", addressdetails=True, exactly_one=True)
    except Exception as e:
        return {"error": "geocoder_unavailable", "address": query, "detail": str(e)}

    if loc is None:
        return {
            "error": "address_not_found",
            "address": query,
            "message": "Nominatim could not resolve this address in Jordan.",
        }

    lat, lng = float(loc.latitude), float(loc.longitude)
    engine = get_engine()
    area = engine.nearest(lat, lng)
    return {
        "address": query,
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "display_name": loc.address,
        "nearest_priceable_neighborhood": area.name if area else None,
        "neighborhood_centroid": (
            [area.centroid_lng, area.centroid_lat] if area and area.centroid_lat else None
        ),
        "note": (
            f"Resolved to coordinates; nearest priceable submarket is '{area.name}'. "
            "Price against that neighbourhood." if area else
            "Resolved to coordinates, but no well-sampled priceable submarket is nearby — "
            "pricing here would be low-confidence."
        ),
        "source": {
            "name": "OpenStreetMap / Nominatim",
            "url": "https://nominatim.openstreetmap.org/",
            "kind": "geocoding",
        },
    }
