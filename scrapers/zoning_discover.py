"""Task D: Amman zoning fallback via public ArcGIS Online mirrors.
Resolves item -> feature service URL, inspects layers, checks for landuse/zoning polygons.
"""
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json,*/*",
}
ITEMS = [
    ("Amman_2022_WFL1", "4909a23609c441408ba48660bdecbdd0"),
    ("AMMAN_PLOT", "f4e390d55fe94a5b9f3df0687d918321"),
]


def get_json(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=40, verify=True)
    ct = r.headers.get("content-type", "")
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"_raw_len": len(r.content), "_ctype": ct, "_text": r.text[:300]}


def item_service(item_id):
    url = f"https://www.arcgis.com/sharing/rest/content/items/{item_id}"
    sc, j = get_json(url, {"f": "json"})
    print(f"  item meta HTTP {sc}: type={j.get('type')} title={j.get('title')} url={j.get('url')}")
    return j.get("url"), j


def inspect_service(svc):
    sc, j = get_json(svc, {"f": "json"})
    print(f"  service HTTP {sc}")
    layers = j.get("layers", []) or []
    tables = j.get("tables", []) or []
    for lyr in layers:
        print(f"    layer {lyr.get('id')}: {lyr.get('name')} geom={lyr.get('geometryType')}")
    # inspect each layer fields + count
    for lyr in layers:
        lid = lyr.get("id")
        sc2, lj = get_json(f"{svc}/{lid}", {"f": "json"})
        fields = [f.get("name") for f in (lj.get("fields") or [])]
        print(f"    -> layer {lid} '{lj.get('name')}' geom={lj.get('geometryType')} fields={fields}")
        sc3, cj = get_json(f"{svc}/{lid}/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})
        print(f"       count={cj.get('count')}")


def search():
    url = "https://www.arcgis.com/sharing/rest/search"
    sc, j = get_json(url, {"q": "Amman landuse OR zoning OR GAM", "f": "json", "num": 20})
    print(f"\n===== SEARCH HTTP {sc} total={j.get('total')}")
    for res in j.get("results", []):
        print(f"  {res.get('id')} | {res.get('type')} | {res.get('title')} | owner={res.get('owner')}")


def main():
    for name, iid in ITEMS:
        print(f"\n===== ITEM {name} ({iid})")
        try:
            svc, meta = item_service(iid)
            if svc:
                inspect_service(svc)
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
    try:
        search()
    except Exception as e:
        print(f"SEARCH ERROR: {e}")


if __name__ == "__main__":
    main()
