"""Inspect candidate ArcGIS feature services for Amman zoning/landuse/parcel polygons."""
import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,*/*"}
SERVICES = [
    ("AMMAN_PLOT", "https://services6.arcgis.com/cpH3GzzxXWyuR151/arcgis/rest/services/AMMAN_PLOT/FeatureServer"),
    ("Amman_2022_WFL1", "https://services3.arcgis.com/0IVKjWoVA5tJIUq8/arcgis/rest/services/Amman_2022_WFL1/FeatureServer"),
    ("Zahran_WFL1", "https://services3.arcgis.com/0IVKjWoVA5tJIUq8/arcgis/rest/services/Zahran_WFL1/FeatureServer"),
    ("Amman_new_WFL1", "https://services3.arcgis.com/0IVKjWoVA5tJIUq8/arcgis/rest/services/Amman_new_WFL1/FeatureServer"),
    ("Amman_generic", "https://services.arcgis.com/lqRTrQp2HrfnJt8U/arcgis/rest/services/Amman/FeatureServer"),
]


def gj(url, params):
    r = requests.get(url, headers=H, params=params, timeout=45, verify=True)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"_text": r.text[:200]}


def main():
    for name, svc in SERVICES:
        print(f"\n===== {name}: {svc}")
        sc, j = gj(svc, {"f": "json"})
        if sc != 200 or "layers" not in j:
            print(f"  HTTP {sc} keys={list(j.keys())[:6]}")
            continue
        for lyr in j.get("layers", []):
            lid = lyr.get("id")
            sc2, lj = gj(f"{svc}/{lid}", {"f": "json"})
            fields = [f.get("name") for f in (lj.get("fields") or [])]
            sc3, cj = gj(f"{svc}/{lid}/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})
            print(f"  layer {lid} '{lyr.get('name')}' geom={lj.get('geometryType')} count={cj.get('count')}")
            print(f"    fields: {fields}")
            # sample one feature attributes
            sc4, fj = gj(f"{svc}/{lid}/query", {"where": "1=1", "outFields": "*", "resultRecordCount": 1, "f": "json"})
            feats = fj.get("features") or []
            if feats:
                print(f"    sample attrs: {feats[0].get('attributes')}")


if __name__ == "__main__":
    main()
