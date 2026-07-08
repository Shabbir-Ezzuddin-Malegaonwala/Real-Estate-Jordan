"""Nationwide OSM/Overpass POI + geographic-feature extraction for all of Jordan.

Fetches Points-of-Interest (batched BY CATEGORY) and geographic features (water, green,
major roads, governorate boundaries) for the whole country from the free Overpass API,
then builds map-ready per-category GeoJSON layers under data/processed/ plus two load-ready
CSVs (poi_extended.csv, area_amenities.csv).

Design:
  * area["ISO3166-1"="JO"] scopes every query to Jordan; no bbox guesswork.
  * Raw Overpass JSON cached under data/raw/osm/jordan/ — re-runnable; --refresh forces re-fetch.
  * Polite rate-limiting (sleep between batches) + 429/504 backoff + mirror fallback.
  * Spatial joins use shapely + STRtree: neighborhood from the 290 Voronoi cells, governorate
    from real OSM admin_level=4 boundaries. Distances (airport / highway) via haversine.
  * Provenance intact on every row (source=OpenStreetMap, capture_date=today).

Usage:
    python scrapers/osm_jordan_poi.py            # cached raw reused where present
    python scrapers/osm_jordan_poi.py --refresh  # force re-fetch every batch
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import requests
from shapely.geometry import Point, shape
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "osm" / "jordan"
OUT_DIR = ROOT / "data" / "processed"
VORONOI = OUT_DIR / "neighborhoods_voronoi.geojson"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
HEADERS = {"User-Agent": "RubiconRealEstate-GIS/1.0 (husain.bhattiwala@rubikonlabs.com)"}
CAPTURE_DATE = date.today().isoformat()
SLEEP_BETWEEN = 6  # seconds between successful batches (politeness)

# --- POI taxonomy: (category, [(overpass_key, overpass_value, subcategory), ...]) ----------
# Each group is one Overpass query (a union of the listed tag filters), scoped to Jordan.
POI_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("education", [
        ("amenity", "school", "school"),
        ("amenity", "university", "university"),
        ("amenity", "college", "college"),
        ("amenity", "kindergarten", "kindergarten"),
    ]),
    ("health", [
        ("amenity", "hospital", "hospital"),
        ("amenity", "clinic", "clinic"),
        ("amenity", "pharmacy", "pharmacy"),
        ("amenity", "doctors", "doctors"),
    ]),
    ("shopping", [
        ("shop", "mall", "mall"),
        ("shop", "supermarket", "supermarket"),
        ("shop", "department_store", "department_store"),
        ("amenity", "marketplace", "marketplace"),
    ]),
    ("food_leisure", [
        ("amenity", "restaurant", "restaurant"),
        ("amenity", "cafe", "cafe"),
        ("amenity", "cinema", "cinema"),
        ("amenity", "theatre", "theatre"),
        ("tourism", "hotel", "hotel"),
        ("leisure", "fitness_centre", "fitness_centre"),
    ]),
    ("recreation", [
        ("leisure", "park", "park"),
        ("leisure", "playground", "playground"),
        ("leisure", "stadium", "stadium"),
        ("leisure", "sports_centre", "sports_centre"),
        ("leisure", "pitch", "pitch"),
        ("tourism", "attraction", "attraction"),
        ("tourism", "viewpoint", "viewpoint"),
    ]),
    ("religious", [
        ("amenity", "place_of_worship", "place_of_worship"),
    ]),
    ("transport", [
        ("highway", "bus_stop", "bus_stop"),
        ("amenity", "bus_station", "bus_station"),
        ("amenity", "taxi", "taxi"),
        ("amenity", "fuel", "fuel"),
        ("amenity", "parking", "parking"),
        ("railway", "station", "railway_station"),
        ("railway", "halt", "railway_halt"),
        ("aeroway", "aerodrome", "airport"),
    ]),
    ("services", [
        ("amenity", "bank", "bank"),
        ("amenity", "atm", "atm"),
        ("amenity", "police", "police"),
        ("amenity", "townhall", "townhall"),
        ("amenity", "courthouse", "courthouse"),
    ]),
    ("negative", [
        ("landuse", "industrial", "industrial"),
        ("man_made", "works", "works"),
        ("amenity", "grave_yard", "grave_yard"),
        ("landuse", "landfill", "landfill"),
        ("power", "plant", "power_plant"),
    ]),
]

# Which subcategory feeds which area_amenities counter (unlisted subcats only add to total).
COUNTER_MAP = {
    "school": "schools_n", "kindergarten": "schools_n",
    "university": "universities_n", "college": "universities_n",
    "hospital": "hospitals_n", "clinic": "hospitals_n",
    "pharmacy": "pharmacies_n",
    "mall": "malls_n", "department_store": "malls_n",
    "supermarket": "supermarkets_n", "marketplace": "supermarkets_n",
    "restaurant": "restaurants_n", "cafe": "cafes_n", "hotel": "hotels_n",
    "park": "parks_n", "playground": "playgrounds_n",
    "stadium": "stadiums_n", "sports_centre": "sports_n", "pitch": "sports_n",
    "mosque": "mosques_n", "church": "churches_n",
    "bank": "banks_n", "atm": "atms_n", "fuel": "fuel_n",
    "bus_stop": "transport_n", "bus_station": "transport_n", "taxi": "transport_n",
    "railway_station": "transport_n", "railway_halt": "transport_n", "airport": "transport_n",
    "police": "police_n",
    "industrial": "negatives_n", "works": "negatives_n", "grave_yard": "negatives_n",
    "landfill": "negatives_n", "power_plant": "negatives_n",
}


# --- Overpass fetch (cache + mirror fallback + backoff) ---------------------------------
def fetch(name: str, query: str, refresh: bool = False, max_retries: int = 4) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_DIR / f"{name}.json"
    if cache.exists() and not refresh:
        print(f"[cache] {name} -> {cache.name}")
        return json.loads(cache.read_text(encoding="utf-8"))

    last_err = None
    for endpoint in ENDPOINTS:
        host = endpoint.split("/")[2]
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.post(endpoint, data={"data": query}, headers=HEADERS, timeout=300)
                if r.status_code == 200:
                    data = r.json()
                    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                    print(f"[ok]  {name}: {len(data.get('elements', []))} elements via {host}")
                    return data
                if r.status_code in (429, 504, 502, 503):
                    wait = min(90, 8 * attempt * attempt)
                    print(f"[wait] {name}: HTTP {r.status_code} on {host}, retry in {wait}s")
                    time.sleep(wait)
                    continue
                print(f"[err] {name}: HTTP {r.status_code} on {host}: {r.text[:120]}")
                break
            except requests.RequestException as ex:
                last_err = ex
                wait = min(90, 8 * attempt * attempt)
                print(f"[wait] {name}: {type(ex).__name__} on {host}, retry in {wait}s")
                time.sleep(wait)
        print(f"[fail] {name}: giving up on {host}, trying next mirror")
    raise RuntimeError(f"All Overpass endpoints failed for {name}: {last_err}")


def q_pois(filters: list[tuple[str, str, str]]) -> str:
    body = "".join(f'  nwr["{k}"="{v}"](area.jo);\n' for k, v, _ in filters)
    return f'[out:json][timeout:300];\narea["ISO3166-1"="JO"]->.jo;\n(\n{body});\nout center tags;'


def q_lines(pairs: list[tuple[str, str]]) -> str:
    body = "".join(f'  way["{k}"="{v}"](area.jo);\n' for k, v in pairs)
    return f'[out:json][timeout:300];\narea["ISO3166-1"="JO"]->.jo;\n(\n{body});\nout geom;'


def q_areas(pairs: list[tuple[str, str]]) -> str:
    body = "".join(f'  nwr["{k}"="{v}"](area.jo);\n' for k, v in pairs)
    return f'[out:json][timeout:300];\narea["ISO3166-1"="JO"]->.jo;\n(\n{body});\nout geom;'


def q_governorates() -> str:
    return ('[out:json][timeout:300];\narea["ISO3166-1"="JO"]->.jo;\n'
            '(\n  relation["boundary"="administrative"]["admin_level"="4"](area.jo);\n);\nout geom;')


# --- Geometry helpers -------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def elem_center(el):
    if el["type"] == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center")
    if c:
        return c.get("lat"), c.get("lon")
    return None, None


def pick_name(tags):
    return tags.get("name:en") or tags.get("name") or tags.get("name:ar") or ""


def has_latin(s):
    return any("a" <= c.lower() <= "z" for c in s)


def lang_of(name, name_ar, tags):
    if name_ar and (tags.get("name:en") or has_latin(name)):
        return "mixed"
    if name_ar and not name:
        return "ar"
    return "en" if name else "unknown"


def religious_subcat(tags):
    rel = (tags.get("religion") or "").strip().lower()
    if rel in ("muslim", "islam", "مسلم", "الاسلام", "الإسلام"):
        return "mosque"
    if rel in ("christian", "christianity", "مسيحي"):
        return "church"
    return rel or "place_of_worship"


# --- Governorate + neighborhood indexes (shapely STRtree) -------------------------------
def build_gov_index(gov_raw):
    """Return (STRtree, geoms, names) for OSM admin_level=4 governorate polygons."""
    geoms, names = [], []
    for el in gov_raw.get("elements", []):
        if el.get("type") != "relation":
            continue
        segs = [[(p["lon"], p["lat"]) for p in m["geometry"]]
                for m in el.get("members", [])
                if m.get("role") in ("outer", "") and m.get("type") == "way" and m.get("geometry")]
        if not segs:
            continue
        try:
            poly = unary_union(list(polygonize(segs)))
        except Exception:
            continue
        if poly.is_empty:
            continue
        t = el.get("tags", {})
        geoms.append(poly)
        names.append(t.get("name:en") or t.get("name") or "unknown")
    tree = STRtree(geoms) if geoms else None
    return tree, geoms, names


def build_voronoi_index():
    fc = json.loads(VORONOI.read_text(encoding="utf-8"))
    geoms, props = [], []
    for f in fc["features"]:
        try:
            geoms.append(shape(f["geometry"]))
            props.append(f["properties"])
        except Exception:
            continue
    tree = STRtree(geoms) if geoms else None
    return tree, geoms, props, fc["features"]


def locate(pt, tree, geoms):
    """Return index of the polygon containing pt, or None."""
    if tree is None:
        return None
    for idx in tree.query(pt):
        if geoms[idx].contains(pt):
            return int(idx)
    return None


# --- Main -------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="force re-fetch every batch")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Fetch governorate boundaries + build spatial indexes.
    gov_raw = fetch("governorates", q_governorates(), args.refresh)
    time.sleep(SLEEP_BETWEEN)
    gov_tree, gov_geoms, gov_names = build_gov_index(gov_raw)
    print(f"governorates: {len(gov_geoms)} polygons")
    vor_tree, vor_geoms, vor_props, vor_features = build_voronoi_index()
    print(f"voronoi cells: {len(vor_geoms)}")

    # 2) Fetch POIs by category, spatial-join, accumulate rows + per-category features.
    seen: set[str] = set()
    poi_rows: list[dict] = []
    layer_features: dict[str, list] = defaultdict(list)
    # per-voronoi-cell counters keyed by cell index
    cell_counts: dict[int, Counter] = defaultdict(Counter)

    for category, filters in POI_GROUPS:
        raw = fetch(f"poi_{category}", q_pois(filters), args.refresh)
        time.sleep(SLEEP_BETWEEN)
        submap = {(k, v): sub for k, v, sub in filters}
        for el in raw.get("elements", []):
            tags = el.get("tags", {})
            lat, lon = elem_center(el)
            if lat is None or lon is None:
                continue
            key = f"osm_{el['type']}_{el['id']}"
            if key in seen:
                continue
            # resolve subcategory from whichever filter tag this element carries
            sub = None
            for (k, v), s in submap.items():
                if tags.get(k) == v:
                    sub = s
                    break
            if sub is None:
                continue
            if sub == "place_of_worship":
                sub = religious_subcat(tags)
            seen.add(key)

            pt = Point(lon, lat)
            gi = locate(pt, gov_tree, gov_geoms)
            governorate = gov_names[gi] if gi is not None else "unknown"
            vi = locate(pt, vor_tree, vor_geoms)
            neighborhood = vor_props[vi]["neighborhood"] if vi is not None else "other"
            if vi is not None and governorate == "unknown":
                governorate = vor_props[vi].get("governorate") or "unknown"

            name = pick_name(tags)
            name_ar = tags.get("name:ar", "")
            display = name or f"unnamed {sub}"

            poi_rows.append({
                "poi_id": key, "category": category, "subcategory": sub,
                "name": display, "name_ar": name_ar,
                "lat": round(lat, 6), "lng": round(lon, 6),
                "governorate": governorate, "neighborhood": neighborhood,
                "osm_type": el["type"], "osm_id": str(el["id"]),
                "evidence_category": "gis", "language": lang_of(name, name_ar, tags),
                "source_name": "OpenStreetMap",
                "source_url": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
                "capture_date": CAPTURE_DATE, "collected_by": "gis-agent",
                "confidence": "M", "notes": "",
            })
            layer_features[category].append({
                "type": "Feature",
                "properties": {"poi_id": key, "category": category, "subcategory": sub,
                               "name": display, "name_ar": name_ar,
                               "neighborhood": neighborhood, "governorate": governorate},
                "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            })
            if vi is not None:
                counter = cell_counts[vi]
                counter["total_poi_n"] += 1
                col = COUNTER_MAP.get(sub)
                if col:
                    counter[col] += 1

    print(f"POIs collected: {len(poi_rows)}")

    # 3) Geographic feature layers.
    water_raw = fetch("water", q_areas([("waterway", "river"), ("waterway", "stream"),
                                        ("natural", "water"), ("landuse", "reservoir")]), args.refresh)
    time.sleep(SLEEP_BETWEEN)
    green_raw = fetch("green", q_areas([("natural", "wood"), ("landuse", "forest"),
                                        ("leisure", "park"), ("leisure", "garden")]), args.refresh)
    time.sleep(SLEEP_BETWEEN)
    roads_raw = fetch("major_roads", q_lines([("highway", "motorway"), ("highway", "trunk"),
                                              ("highway", "primary")]), args.refresh)

    write_geometry_layer(OUT_DIR / "water.geojson", water_raw,
                         lambda t: t.get("waterway") or t.get("natural") or t.get("landuse") or "water")
    write_geometry_layer(OUT_DIR / "green.geojson", green_raw,
                         lambda t: t.get("natural") or t.get("landuse") or t.get("leisure") or "green")
    road_features = write_geometry_layer(OUT_DIR / "major_roads.geojson", roads_raw,
                                         lambda t: t.get("highway") or "road", want="LineString")

    # 4) Per-category POI GeoJSON layers.
    for category, _ in POI_GROUPS:
        feats = layer_features.get(category, [])
        (OUT_DIR / f"poi_{category}.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
            encoding="utf-8")
        print(f"poi_{category}.geojson: {len(feats)} points")

    # 5) area_amenities: distances to nearest airport + major road per cell.
    airports = [(r["name"], r["lat"], r["lng"]) for r in poi_rows if r["subcategory"] == "airport"]
    road_pts = road_vertices(road_features)
    amen_rows = build_area_amenities(vor_features, cell_counts, airports, road_pts)

    write_poi_csv(OUT_DIR / "poi_extended.csv", poi_rows)
    write_amen_csv(OUT_DIR / "area_amenities.csv", amen_rows)
    write_summary(poi_rows, layer_features, amen_rows, road_features)
    print(f"area_amenities: {len(amen_rows)} neighborhoods summarised")


def write_geometry_layer(path, raw, classify, want=None):
    features = []
    for el in raw.get("elements", []):
        geom = el.get("geometry")
        if not geom:
            continue
        coords = [[round(p["lon"], 5), round(p["lat"], 5)] for p in geom]
        if len(coords) < 2:
            continue
        tags = el.get("tags", {})
        closed = coords[0] == coords[-1] and len(coords) >= 4
        gtype = "Polygon" if (want is None and closed) else "LineString"
        geometry = {"type": "Polygon", "coordinates": [coords]} if gtype == "Polygon" \
            else {"type": "LineString", "coordinates": coords}
        features.append({
            "type": "Feature",
            "properties": {"name": tags.get("name:en") or tags.get("name") or "",
                           "kind": classify(tags), "ref": tags.get("ref", "")},
            "geometry": geometry,
        })
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
                    encoding="utf-8")
    print(f"{path.name}: {len(features)} features")
    return features


def road_vertices(road_features):
    """Downsampled vertex list [(lat, lon)] of all major roads for nearest-road distance."""
    pts = []
    for f in road_features:
        coords = f["geometry"]["coordinates"]
        for i in range(0, len(coords), 3):  # every 3rd vertex — enough for a distance floor
            lon, lat = coords[i]
            pts.append((lat, lon))
    return pts


def build_area_amenities(vor_features, cell_counts, airports, road_pts):
    rows = []
    count_cols = ["schools_n", "universities_n", "hospitals_n", "pharmacies_n", "malls_n",
                  "supermarkets_n", "restaurants_n", "cafes_n", "hotels_n", "parks_n",
                  "playgrounds_n", "stadiums_n", "sports_n", "mosques_n", "churches_n",
                  "banks_n", "atms_n", "fuel_n", "transport_n", "police_n", "negatives_n",
                  "total_poi_n"]
    for idx, f in enumerate(vor_features):
        p = f["properties"]
        clat, clng = p["centroid_lat"], p["centroid_lng"]
        counts = cell_counts.get(idx, Counter())
        near_air, air_km = "unknown", None
        for nm, alat, alng in airports:
            d = haversine_km(clat, clng, alat, alng)
            if air_km is None or d < air_km:
                near_air, air_km = nm, d
        hw_km = None
        for lat, lon in road_pts:
            d = haversine_km(clat, clng, lat, lon)
            if hw_km is None or d < hw_km:
                hw_km = d
        row = {
            "neighborhood": p["neighborhood"], "governorate": p.get("governorate") or "unknown",
            "centroid_lat": round(clat, 6), "centroid_lng": round(clng, 6),
            "is_covered": 1 if p.get("is_covered") else 0,
            "nearest_airport": near_air,
            "km_to_airport": round(air_km, 2) if air_km is not None else "",
            "km_to_highway": round(hw_km, 2) if hw_km is not None else "",
            "source_name": "OpenStreetMap",
            "source_url": "https://www.openstreetmap.org/",
            "capture_date": CAPTURE_DATE, "collected_by": "gis-agent",
            "confidence": "M", "notes": "counts within Voronoi cell; distances centroid-based",
        }
        for c in count_cols:
            row[c] = counts.get(c, 0)
        rows.append(row)
    return rows


def write_poi_csv(path, rows):
    cols = ["poi_id", "category", "subcategory", "name", "name_ar", "lat", "lng",
            "governorate", "neighborhood", "osm_type", "osm_id",
            "evidence_category", "language", "source_name", "source_url",
            "capture_date", "collected_by", "confidence", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


def write_amen_csv(path, rows):
    cols = ["neighborhood", "governorate", "centroid_lat", "centroid_lng", "is_covered",
            "schools_n", "universities_n", "hospitals_n", "pharmacies_n", "malls_n",
            "supermarkets_n", "restaurants_n", "cafes_n", "hotels_n", "parks_n",
            "playgrounds_n", "stadiums_n", "sports_n", "mosques_n", "churches_n",
            "banks_n", "atms_n", "fuel_n", "transport_n", "police_n", "negatives_n",
            "total_poi_n", "nearest_airport", "km_to_airport", "km_to_highway",
            "source_name", "source_url", "capture_date", "collected_by", "confidence", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


def write_summary(poi_rows, layer_features, amen_rows, road_features):
    by_cat = Counter(r["category"] for r in poi_rows)
    by_sub = Counter(r["subcategory"] for r in poi_rows)
    by_gov = Counter(r["governorate"] for r in poi_rows)
    stats = {
        "capture_date": CAPTURE_DATE,
        "poi_total": len(poi_rows),
        "poi_by_category": dict(by_cat),
        "poi_by_subcategory": dict(by_sub.most_common()),
        "poi_by_governorate": dict(by_gov.most_common()),
        "layer_counts": {c: len(f) for c, f in layer_features.items()},
        "major_roads": len(road_features),
        "areas_summarised": len(amen_rows),
    }
    (RAW_DIR / "summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print("summary:", json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
