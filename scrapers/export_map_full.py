"""Regenerate ALL frontend map layers from the CANONICAL database at full resolution.

Fixes the "map only shows Amman / 5 areas" gap: the old gen_map_layers.py clipped
POIs to an Amman bounding box (~12k of 86k) and priced only 5 submarkets. This
exports EVERYTHING we collected, nationwide:

  poi_<category>.geojson   all ~69k categorised POIs across all 12 governorates
  listings.geojson         every geocoded listing (~24k) as a point, with JD/m2
  area_prices.geojson      median asking JD/m2 for every neighbourhood with >=5
                           priced listings (~400), as a centroid point

Writes to data/processed/ (source of truth) AND app/web/public/data/ (served).
Reads the canonical DB the auto-update pipeline keeps fresh (see docs/LIVE-DATA.md).
"""
from __future__ import annotations
import json
import sqlite3
import statistics as st
from collections import defaultdict
from pathlib import Path

from poi_taxonomy import classify, types_manifest, TYPE_INFO

DB = "C:/Rubicon/Real-Estate-Jordan/db/jordan_re.sqlite"
SRC = Path("data/processed")
PUB = Path("app/web/public/data")

JORDAN = (29.0, 33.6, 34.8, 39.4)  # lat_min, lat_max, lng_min, lng_max


def _fc(features: list) -> dict:
    return {"type": "FeatureCollection", "features": features}


def _write(name: str, fc: dict) -> None:
    text = json.dumps(fc, ensure_ascii=False)
    for d in (SRC, PUB):
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text, encoding="utf-8")


def _in_jordan(lat: float, lng: float) -> bool:
    return JORDAN[0] < lat < JORDAN[1] and JORDAN[2] < lng < JORDAN[3]


def export_pois(c: sqlite3.Connection) -> dict:
    """Classify every POI into a curated type (poi_taxonomy) and bucket by GROUP.
    Noise (no matching type) is dropped. Each feature carries type/emoji/group so
    the map can draw a per-type emoji. Also builds area_poi_counts.json."""
    groups: dict[str, list] = defaultdict(list)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    kept = 0
    dropped = 0
    per_type: dict[str, int] = defaultdict(int)
    for cat, sub, name, name_ar, lat, lng, nb in c.execute(
        "SELECT category, subcategory, name, name_ar, lat, lng, neighborhood "
        "FROM poi_extended WHERE lat IS NOT NULL AND lng IS NOT NULL"
    ):
        if not _in_jordan(lat, lng):
            continue
        t = classify(sub, name, cat)
        if t is None:
            dropped += 1
            continue
        info = TYPE_INFO[t]
        grp = info["group"]
        groups[grp].append({
            "type": "Feature",
            "properties": {"type": t, "emoji": info["emoji"], "group": grp,
                           "name": name or "", "name_ar": name_ar or "",
                           "neighborhood": nb or "", "subcategory": sub or ""},
            "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
        })
        kept += 1
        per_type[t] += 1
        if nb:
            counts[nb][t] += 1

    for grp, feats in groups.items():
        _write(f"poi_{grp}.geojson", _fc(feats))
    _write("poi_types.json", types_manifest())
    _write("area_poi_counts.json", {k: dict(v) for k, v in counts.items()})
    print(f"POIs kept={kept} dropped(noise)={dropped} across {len(groups)} groups; "
          f"areas with counts={len(counts)}")
    return {"per_group": {g: len(f) for g, f in sorted(groups.items(), key=lambda kv: -len(kv[1]))},
            "top_types": dict(sorted(per_type.items(), key=lambda kv: -kv[1])[:12])}


def export_listings(c: sqlite3.Connection) -> int:
    feats = []
    for nb, pt, price, area, lat, lng in c.execute(
        "SELECT neighborhood, property_type, price_jd, area_m2, lat, lng FROM listings "
        "WHERE lat IS NOT NULL AND lng IS NOT NULL AND price_jd > 0"
    ):
        if not _in_jordan(lat, lng):
            continue
        ppm2 = round(price / area) if area and area > 0 else None
        feats.append({
            "type": "Feature",
            "properties": {"nb": nb or "", "pt": pt or "", "price": round(price), "ppm2": ppm2},
            "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
        })
    _write("listings.geojson", _fc(feats))
    return len(feats)


def export_area_prices(c: sqlite3.Connection) -> int:
    ppm2s: dict[str, list] = defaultdict(list)
    coords: dict[str, list] = defaultdict(list)
    for nb, price, area, lat, lng in c.execute(
        "SELECT neighborhood, price_jd, area_m2, lat, lng FROM listings "
        "WHERE neighborhood IS NOT NULL AND price_jd > 0 AND area_m2 > 0"
    ):
        ppm2s[nb].append(price / area)
        if lat and lng and _in_jordan(lat, lng):
            coords[nb].append((lat, lng))
    amen = {r[0]: (r[1], r[2]) for r in c.execute(
        "SELECT neighborhood, centroid_lat, centroid_lng FROM area_amenities "
        "WHERE centroid_lat IS NOT NULL")}
    feats = []
    for nb, vals in ppm2s.items():
        if len(vals) < 5:
            continue
        if coords[nb]:
            lat = st.median([p[0] for p in coords[nb]])
            lng = st.median([p[1] for p in coords[nb]])
        elif nb in amen and amen[nb][0]:
            lat, lng = float(amen[nb][0]), float(amen[nb][1])
        else:
            continue
        feats.append({
            "type": "Feature",
            "properties": {"neighborhood": nb, "ppm2": round(st.median(vals)), "n": len(vals)},
            "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
        })
    feats.sort(key=lambda f: -f["properties"]["ppm2"])
    _write("area_prices.geojson", _fc(feats))
    return len(feats)


def main() -> None:
    c = sqlite3.connect(DB)
    pois = export_pois(c)
    listings = export_listings(c)
    areas = export_area_prices(c)
    c.close()
    print("POIs per group:", pois["per_group"])
    print("top types:", pois["top_types"])
    print("listing points:", listings)
    print("area price points:", areas)


if __name__ == "__main__":
    main()
