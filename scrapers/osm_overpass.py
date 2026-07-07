"""OSM/Overpass extraction for Amman POIs, neighbourhood boundaries and roads.

Fetches raw Overpass JSON (cached under data/raw/osm/) then builds the map-ready
GeoJSON + CSV layers under data/processed/. Re-runnable: pass --refresh to force
re-fetch, otherwise cached raw JSON is reused.

Primary endpoint is Overpass with polite rate-limiting and mirror fallback.
Geometry (point-in-polygon, haversine) is pure-Python — no geospatial deps.
"""

import argparse
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "osm"
OUT_DIR = ROOT / "data" / "processed"

# Amman bounding box (south, west, north, east) — lat/lon, EPSG:4326.
# lon 35.75–36.05 E, lat 31.85–32.05 N (per task brief).
BBOX = (31.85, 35.75, 32.05, 36.05)

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

HEADERS = {"User-Agent": "RubiconRealEstate-GIS/1.0 (husain.bhattiwala@rubikonlabs.com)"}

CAPTURE_DATE = date.today().isoformat()

# Target neighbourhoods: English + Arabic names, fallback centre (lat, lon) used
# only if OSM has no place node. Radius (km) for the approximate-circle boundary.
TARGETS = [
    {"key": "Abdoun", "en": "Abdoun", "ar": "عبدون", "alt": ["abdun"], "center": (31.9488, 35.8927), "radius_km": 1.2},
    {"key": "Dabouq", "en": "Dabouq", "ar": "دابوق", "alt": ["dabuq"], "center": (31.9881, 35.8113), "radius_km": 1.5},
    {"key": "Sweifieh", "en": "Sweifieh", "ar": "الصويفية", "alt": ["swefieh", "sweifiyeh"], "center": (31.9584, 35.8639), "radius_km": 1.2},
    {"key": "Khalda", "en": "Khalda", "ar": "خلدا", "alt": ["khaldah"], "center": (31.9901, 35.8448), "radius_km": 1.5},
    {"key": "Shmeisani", "en": "Shmeisani", "ar": "الشميساني", "alt": ["shmesani", "al shmeisani"], "center": (31.9735, 35.8969), "radius_km": 1.2},
]


def bbox_clause():
    s, w, n, e = BBOX
    return f"({s},{w},{n},{e})"


# --- Overpass fetch with caching + mirror fallback --------------------------

def fetch(name, query, refresh=False, max_retries=4):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_DIR / f"{name}.json"
    if cache.exists() and not refresh:
        print(f"[cache] {name} -> {cache.name}")
        return json.loads(cache.read_text(encoding="utf-8"))

    last_err = None
    for endpoint in ENDPOINTS:
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.post(endpoint, data={"data": query}, headers=HEADERS, timeout=180)
                if r.status_code == 200:
                    data = r.json()
                    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                    print(f"[ok]  {name}: {len(data.get('elements', []))} elements via {endpoint.split('/')[2]}")
                    return data
                if r.status_code in (429, 504, 502, 503):
                    wait = min(60, 5 * attempt * attempt)
                    print(f"[wait] {name}: HTTP {r.status_code} on {endpoint.split('/')[2]}, retry in {wait}s")
                    time.sleep(wait)
                    continue
                print(f"[err] {name}: HTTP {r.status_code} on {endpoint.split('/')[2]}: {r.text[:120]}")
                break  # non-retryable -> next endpoint
            except requests.RequestException as ex:
                last_err = ex
                wait = min(60, 5 * attempt * attempt)
                print(f"[wait] {name}: {type(ex).__name__} on {endpoint.split('/')[2]}, retry in {wait}s")
                time.sleep(wait)
        print(f"[fail] {name}: giving up on {endpoint.split('/')[2]}, trying next mirror")
    raise RuntimeError(f"All Overpass endpoints failed for {name}: {last_err}")


# --- Query builders ---------------------------------------------------------

def q_pois():
    b = bbox_clause()
    filters = [
        "amenity=school", "amenity=university", "amenity=college",
        "amenity=hospital", "amenity=clinic",
        "amenity=place_of_worship", "amenity=marketplace",
        "shop=mall", "leisure=park",
        "public_transport=station", "railway=station",
    ]
    parts = "".join(f"  nwr[{k}={v}]{b};\n" for k, v in (f.split("=") for f in filters))
    return f"[out:json][timeout:180];\n(\n{parts});\nout center tags;"


def q_boundaries():
    b = bbox_clause()
    parts = "".join(
        f"  relation[boundary=administrative][admin_level={lvl}]{b};\n" for lvl in (8, 9, 10, 11)
    )
    return f"[out:json][timeout:180];\n(\n{parts});\nout geom;"


def q_places():
    b = bbox_clause()
    parts = "".join(
        f"  node[place={p}]{b};\n" for p in ("suburb", "neighbourhood", "quarter", "town", "city")
    )
    return f"[out:json][timeout:120];\n(\n{parts});\nout;"


def q_roads():
    b = bbox_clause()
    parts = "".join(
        f"  way[highway={h}]{b};\n" for h in ("motorway", "trunk", "primary", "secondary")
    )
    return f"[out:json][timeout:180];\n(\n{parts});\nout geom;"


# --- Geometry helpers (pure python) -----------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def point_in_ring(lat, lon, ring):
    """Ray-casting on a ring of [lon, lat] pairs (GeoJSON order)."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon(lat, lon, geometry):
    """geometry is a GeoJSON Polygon coordinates list [ [outer], [hole]... ]."""
    if not point_in_ring(lat, lon, geometry[0]):
        return False
    for hole in geometry[1:]:
        if point_in_ring(lat, lon, hole):
            return False
    return True


def circle_polygon(lat, lon, radius_km, steps=48):
    coords = []
    for i in range(steps + 1):
        ang = 2 * math.pi * i / steps
        dlat = (radius_km / 111.32) * math.cos(ang)
        dlon = (radius_km / (111.32 * math.cos(math.radians(lat)))) * math.sin(ang)
        coords.append([round(lon + dlon, 6), round(lat + dlat, 6)])
    return [coords]


# --- Element helpers --------------------------------------------------------

def elem_center(el):
    if el["type"] == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center")
    if c:
        return c.get("lat"), c.get("lon")
    return None, None


def category_for(tags):
    if tags.get("amenity") == "school":
        return "school"
    if tags.get("amenity") in ("university", "college"):
        return "university"
    if tags.get("amenity") in ("hospital", "clinic"):
        return "hospital"
    if tags.get("amenity") == "place_of_worship":
        return "mosque"
    if tags.get("shop") == "mall":
        return "mall"
    if tags.get("amenity") == "marketplace":
        return "mall"
    if tags.get("leisure") == "park":
        return "park"
    if tags.get("public_transport") == "station" or tags.get("railway") == "station":
        return "transport"
    return None


def build_neighborhoods(bnd_raw, place_raw):
    """Return (features, name->polygon-geometry map). Prefer real OSM boundary
    polygons whose name matches a target; else circle around the place node;
    else circle around the hardcoded fallback centre."""
    places = [el for el in place_raw.get("elements", []) if el.get("lat") is not None]

    def match_place(tgt):
        """Nearest place node whose name matches the target (en/ar/alt),
        tie-broken by distance to the fallback centre. Returns (lat, lon) or None."""
        terms = [tgt["en"].lower(), tgt["ar"]] + [a.lower() for a in tgt.get("alt", [])]
        best, best_d = None, 1e9
        for el in places:
            t = el.get("tags", {})
            names = " ".join(t.get(k, "") for k in ("name:en", "name", "name:ar")).lower()
            if not any(term and (term in names or names.split() and term in names.split()) for term in terms):
                continue
            d = haversine_km(el["lat"], el["lon"], tgt["center"][0], tgt["center"][1])
            if d < best_d:
                best, best_d = (el["lat"], el["lon"]), d
        return best

    # index boundary relations by name, converting outer ways to a ring
    boundary_polys = {}
    for el in bnd_raw.get("elements", []):
        if el.get("type") != "relation":
            continue
        t = el.get("tags", {})
        names = {t.get(k, "").strip().lower() for k in ("name:en", "name", "name:ar") if t.get(k)}
        ring = relation_outer_ring(el)
        if not ring:
            continue
        for nm in names:
            boundary_polys[nm] = [ring]

    features = []
    poly_map = {}
    for tgt in TARGETS:
        cands = {tgt["en"].lower(), tgt["ar"].lower(),
                 f"{tgt['en'].lower()} district".lower()}
        matched = next((boundary_polys[n] for n in cands if n in boundary_polys), None)
        if matched:
            geom = matched
            source, approx = "osm_boundary", False
            centered_on = "osm_boundary_relation"
        else:
            node = match_place(tgt)
            center = node or tgt["center"]
            centered_on = "osm_place_node" if node else "manual_fallback_center"
            geom = circle_polygon(center[0], center[1], tgt["radius_km"])
            source, approx = "approximate_circle", True

        poly_map[tgt["key"]] = geom
        features.append({
            "type": "Feature",
            "properties": {
                "neighborhood": tgt["key"],
                "name_ar": tgt["ar"],
                "source": source,
                "approximate": approx,
                "centered_on": centered_on,
                "radius_km": tgt["radius_km"] if approx else None,
            },
            "geometry": {"type": "Polygon", "coordinates": geom},
        })
    return features, poly_map


def relation_outer_ring(rel):
    """Stitch outer member ways (with out geom) into a single closed ring.
    Returns list of [lon,lat] or None. Simple stitching — good enough for the
    coarse admin polygons we consume."""
    segs = []
    for m in rel.get("members", []):
        if m.get("role") in ("outer", "") and m.get("type") == "way" and m.get("geometry"):
            segs.append([[p["lon"], p["lat"]] for p in m["geometry"]])
    if not segs:
        return None
    ring = list(segs.pop(0))
    changed = True
    while segs and changed:
        changed = False
        for i, seg in enumerate(segs):
            if ring[-1] == seg[0]:
                ring.extend(seg[1:]); segs.pop(i); changed = True; break
            if ring[-1] == seg[-1]:
                ring.extend(list(reversed(seg))[1:]); segs.pop(i); changed = True; break
            if ring[0] == seg[-1]:
                ring = seg[:-1] + ring; segs.pop(i); changed = True; break
            if ring[0] == seg[0]:
                ring = list(reversed(seg))[:-1] + ring; segs.pop(i); changed = True; break
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    if len(ring) < 4:
        return None
    return ring


def assign_neighborhood(lat, lon, poly_map):
    for name, geom in poly_map.items():
        if point_in_polygon(lat, lon, geom):
            return name
    # nearest target centroid within 2km
    best, best_d = None, 2.0
    for tgt in TARGETS:
        c = tgt["center"]
        d = haversine_km(lat, lon, c[0], c[1])
        if d < best_d:
            best, best_d = tgt["key"], d
    return best or "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="force re-fetch from Overpass")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    poi_raw = fetch("pois", q_pois(), args.refresh); time.sleep(2)
    bnd_raw = fetch("boundaries", q_boundaries(), args.refresh); time.sleep(2)
    place_raw = fetch("places", q_places(), args.refresh); time.sleep(2)
    road_raw = fetch("roads", q_roads(), args.refresh)

    # neighbourhoods first (POIs need the polygons)
    nb_features, poly_map = build_neighborhoods(bnd_raw, place_raw)
    (OUT_DIR / "neighborhoods.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": nb_features}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"neighborhoods.geojson: {len(nb_features)} polygons "
          f"({sum(1 for f in nb_features if not f['properties']['approximate'])} real OSM)")

    # POIs
    poi_features, poi_rows, seen = [], [], set()
    for el in poi_raw.get("elements", []):
        tags = el.get("tags", {})
        cat = category_for(tags)
        if not cat:
            continue
        lat, lon = elem_center(el)
        if lat is None or lon is None:
            continue
        key = (el["type"], el["id"])
        if key in seen:
            continue
        seen.add(key)
        name = tags.get("name:en") or tags.get("name") or tags.get("name:ar") or ""
        name_ar = tags.get("name:ar", "")
        neigh = assign_neighborhood(lat, lon, poly_map)
        poi_id = f"osm_{el['type']}_{el['id']}"
        osm_url = f"https://www.openstreetmap.org/{el['type']}/{el['id']}"
        note = []
        if tags.get("amenity") == "marketplace":
            note.append("osm marketplace mapped to mall")
        if tags.get("amenity") == "clinic":
            note.append("osm clinic mapped to hospital")
        if cat == "mosque" and tags.get("religion") and tags.get("religion") != "muslim":
            note.append(f"place_of_worship religion={tags.get('religion')}")
        lang = "mixed" if name_ar and (tags.get("name:en") or _has_latin(name)) else ("ar" if name_ar and not name else "en")

        poi_features.append({
            "type": "Feature",
            "properties": {
                "poi_id": poi_id, "category": cat,
                "name": name, "name_ar": name_ar, "neighborhood": neigh,
            },
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        })
        poi_rows.append({
            "poi_id": poi_id, "category": cat, "name": name or "unknown",
            "lat": round(lat, 6), "lng": round(lon, 6), "neighborhood": neigh,
            "exists": "yes", "evidence_category": "gis", "language": lang,
            "source_name": "OpenStreetMap", "source_url": osm_url,
            "capture_date": CAPTURE_DATE, "collected_by": "gis-agent",
            "confidence": "M", "notes": "; ".join(note),
        })

    (OUT_DIR / "poi.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": poi_features}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    write_poi_csv(OUT_DIR / "poi.csv", poi_rows)
    print(f"poi.geojson / poi.csv: {len(poi_rows)} POIs")

    # Roads
    road_features = []
    for el in road_raw.get("elements", []):
        if el.get("type") != "way" or not el.get("geometry"):
            continue
        tags = el.get("tags", {})
        coords = [[round(p["lon"], 6), round(p["lat"], 6)] for p in el["geometry"]]
        if len(coords) < 2:
            continue
        road_features.append({
            "type": "Feature",
            "properties": {
                "name": tags.get("name:en") or tags.get("name") or "",
                "name_ar": tags.get("name:ar", ""),
                "highway": tags.get("highway", ""),
                "ref": tags.get("ref", ""),
            },
            "geometry": {"type": "LineString", "coordinates": coords},
        })
    (OUT_DIR / "roads.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": road_features}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"roads.geojson: {len(road_features)} roads")

    write_summary(poi_rows, nb_features, road_features)


def _has_latin(s):
    return any("a" <= c.lower() <= "z" for c in s)


def write_poi_csv(path, rows):
    import csv
    cols = ["poi_id", "category", "name", "lat", "lng", "neighborhood", "exists",
            "evidence_category", "language", "source_name", "source_url",
            "capture_date", "collected_by", "confidence", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_summary(poi_rows, nb_features, road_features):
    from collections import Counter
    by_cat = Counter(r["category"] for r in poi_rows)
    by_neigh = Counter(r["neighborhood"] for r in poi_rows)
    by_road = Counter(f["properties"]["highway"] for f in road_features)
    stats = {
        "capture_date": CAPTURE_DATE,
        "poi_total": len(poi_rows),
        "poi_by_category": dict(by_cat),
        "poi_by_neighborhood": dict(by_neigh),
        "roads_total": len(road_features),
        "roads_by_class": dict(by_road),
        "neighborhoods": [
            {"neighborhood": f["properties"]["neighborhood"],
             "source": f["properties"]["source"],
             "approximate": f["properties"]["approximate"]} for f in nb_features
        ],
    }
    (RAW_DIR / "summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print("summary:", json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
