"""Task D deliverable: export Amman landuse polygons -> data/processed/zoning.geojson.
Source: public ArcGIS Online mirror (OSM-derived landuse). UNOFFICIAL fallback —
NOT GAM regulatory zoning (Res A/B/C/D). Verify before client use.
"""
import json
import time
import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,*/*"}
BASE = "https://services.arcgis.com/lqRTrQp2HrfnJt8U/arcgis/rest/services/Amman/FeatureServer/5/query"
OUT = r"C:\Rubicon\Real-Estate-Jordan\data\processed\zoning.geojson"
PAGE = 1000


def fetch_page(offset):
    params = {
        "where": "1=1",
        "outFields": "FID,osm_id,name,type,Shape__Area,Shape__Length",
        "outSR": 4326,
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": PAGE,
    }
    r = requests.get(BASE, headers=H, params=params, timeout=90, verify=True)
    return r.json()


def main():
    feats = []
    offset = 0
    while True:
        j = fetch_page(offset)
        page = j.get("features", [])
        feats.extend(page)
        print(f"offset={offset} got={len(page)} total={len(feats)}")
        if len(page) < PAGE:
            break
        offset += PAGE
        time.sleep(0.4)

    # inject provenance into each feature
    for f in feats:
        p = f.setdefault("properties", {})
        p["source_name"] = "ArcGIS Online public mirror (OSM-derived Amman landuse)"
        p["source_service"] = "services.arcgis.com/lqRTrQp2HrfnJt8U/.../Amman/FeatureServer/5"
        p["evidence_category"] = "gis"
        p["authenticity"] = "UNOFFICIAL_MIRROR — OSM landuse, NOT GAM regulatory zoning; verify before client use"
        p["capture_date"] = "2026-07-07"
        p["collected_by"] = "official-data-agent"

    fc = {
        "type": "FeatureCollection",
        "name": "amman_landuse_fallback",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "_provenance": {
            "source": "Public ArcGIS Online mirror of OSM landuse for Amman",
            "service_url": "https://services.arcgis.com/lqRTrQp2HrfnJt8U/arcgis/rest/services/Amman/FeatureServer/5",
            "authenticity": "UNOFFICIAL — OSM landuse polygons used as fallback because GAM ArcGIS zoning is geo-blocked and named mirror items require a token",
            "not_a_substitute_for": "GAM regulatory zoning (Res A/B/C/D, FAR, max_height) — access pending",
            "capture_date": "2026-07-07",
            "feature_count": len(feats),
        },
        "features": feats,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False)
    # summarise types
    from collections import Counter
    types = Counter(f["properties"].get("type") for f in feats)
    print(f"\nwrote {len(feats)} features -> {OUT}")
    print("top types:", types.most_common(12))


if __name__ == "__main__":
    main()
