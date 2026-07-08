"""Regenerate the frontend map layers from the NATIONAL data so the map matches the engine.

Fixes the "only 5 regions" gap: builds neighborhood circles for the top Amman submarkets
(centroids computed from real listing coordinates) and refreshes the POI layer from the
national OSM extract. Writes into app/web/public/data/ — no frontend code changes needed;
the map already draws every polygon in neighborhoods.geojson as a clickable, labelled circle.

Outputs:
  app/web/public/data/neighborhoods.geojson   (top-N Amman submarkets, circles)
  app/web/public/data/poi.geojson             (national OSM POIs, Amman extent)
  data/processed/map_neighborhoods.txt        (the exact names, for emit_national.py)
"""

from __future__ import annotations

import csv
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

LISTINGS = Path("data/processed/listings_national_20260708.csv")
OSM_POIS = Path("D:/Rubikon Labs/Project on Jordan/Data/OSM_Geofabrik_Jordan/csv/pois.csv")
# Pipeline source-of-truth: the frontend's prepare-data.mjs copies these from
# data/processed/ -> app/web/public/data/ on every dev/build.
OUT_DATA = Path("data/processed")
NAMES_OUT = Path("data/processed/map_neighborhoods.txt")

TOP_N = 36            # how many Amman submarkets to draw
MIN_GEOCODED = 15     # min geocoded apt listings to trust a centroid
RADIUS_KM = 0.5
# Amman bbox for the POI extent (keeps the map coherent with the Amman camera)
AMMAN_BBOX = (31.70, 32.15, 35.72, 36.05)  # lat_min, lat_max, lon_min, lon_max


def circle(lat: float, lon: float, r_km: float, n: int = 28) -> list[list[float]]:
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    ring = []
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        ring.append([round(lon + dlon * math.cos(a), 6), round(lat + dlat * math.sin(a), 6)])
    return ring


def build_neighborhoods() -> list[str]:
    pts: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in csv.DictReader(open(LISTINGS, encoding="utf-8-sig")):
        if r["property_type"] == "apartment" and r["district"] == "Amman" and r["lat"] and r["lng"]:
            try:
                lat, lon = float(r["lat"]), float(r["lng"])
            except ValueError:
                continue
            if AMMAN_BBOX[0] < lat < AMMAN_BBOX[1] and AMMAN_BBOX[2] < lon < AMMAN_BBOX[3]:
                pts[r["neighborhood"]].append((lat, lon))
    good = {n: v for n, v in pts.items() if len(v) >= MIN_GEOCODED}
    top = sorted(good.items(), key=lambda kv: -len(kv[1]))[:TOP_N]

    feats = []
    names = []
    for name, v in top:
        lat = st.median([p[0] for p in v])
        lon = st.median([p[1] for p in v])
        feats.append({
            "type": "Feature",
            "properties": {
                "neighborhood": name, "name_ar": "", "source": "approximate_circle",
                "approximate": "True", "centered_on": "listing_median",
                "radius_km": str(RADIUS_KM), "listing_count": len(v),
            },
            "geometry": {"type": "Polygon", "coordinates": [circle(lat, lon, RADIUS_KM)]},
        })
        names.append(name)
    (OUT_DATA / "neighborhoods.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
        encoding="utf-8")
    NAMES_OUT.write_text("\n".join(names), encoding="utf-8")
    print(f"neighborhoods.geojson: {len(feats)} Amman submarkets (was 5)")
    return names


def poi_category(subtype: str) -> str | None:
    s = (subtype or "").lower()
    if "worship" in s or "mosque" in s:
        return "mosque"
    if "university" in s or "college" in s:
        return "university"
    if "school" in s or "kindergarten" in s:
        return "school"
    if "hospital" in s or "clinic" in s or "doctors" in s or "pharmacy" in s:
        return "hospital"
    if "mall" in s or "supermarket" in s or "marketplace" in s or "department_store" in s:
        return "mall"
    if "park" in s or "garden" in s or "playground" in s:
        return "park"
    if "bus_station" in s or "bus_stop" in s or "station" in s or "terminal" in s or "taxi" in s:
        return "transport"
    return None


def build_pois() -> None:
    feats = []
    for r in csv.DictReader(open(OSM_POIS, encoding="utf-8-sig")):
        cat = poi_category(r.get("subtype") or r.get("category"))
        if not cat or not r.get("lat") or not r.get("lon"):
            continue
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except ValueError:
            continue
        if not (AMMAN_BBOX[0] < lat < AMMAN_BBOX[1] and AMMAN_BBOX[2] < lon < AMMAN_BBOX[3]):
            continue
        feats.append({
            "type": "Feature",
            "properties": {
                "poi_id": f"osm_{r.get('osm_id','')}", "category": cat,
                "name": r.get("name_en") or r.get("name") or "",
                "name_ar": r.get("name_ar") or "", "neighborhood": "",
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })
    (OUT_DATA / "poi.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
        encoding="utf-8")
    from collections import Counter
    print(f"poi.geojson: {len(feats)} POIs (was 984) — {dict(Counter(f['properties']['category'] for f in feats))}")


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    names = build_neighborhoods()
    build_pois()
    print("top submarkets:", ", ".join(names[:12]), "...")


if __name__ == "__main__":
    main()
