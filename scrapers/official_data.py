"""Official / macro data extraction for the Jordan real-estate platform.

Sources (no APIs — direct file downloads, mostly Arabic Excel/PDF):
  1. CBJ Real Estate Price Index (quarterly + annual, by type & governorate)  -> macro_cbj_price_index.csv
  2. DoS building permits (supply pipeline)                                     -> macro_dos_permits.csv
  3. DLS monthly trading report (Arabic PDF)                                    -> macro_dls_transactions.csv
  4. GAM ArcGIS zoning retry + community mirrors                                -> zoning_*.geojson

Real data only — never fabricate. Unreachable/unparseable sources are logged,
whatever raw file was retrieved is saved under data/raw/official/, and the
required manual step is recorded in docs/official-data-report.md.

Re-runnable: raw downloads are cached; pass --refresh to force re-download.
"""

import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "official"
OUT = ROOT / "data" / "processed"
CAPTURE_DATE = date.today().isoformat()

MACRO_COLS = ["indicator", "geography", "period", "value", "unit",
              "evidence_category", "language",
              "source_name", "source_url", "capture_date", "collected_by",
              "confidence", "notes"]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RubiconRealEstate-GIS/1.0"


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=4, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])))
    return s


def download(url, dest, refresh=False, referer=None, attempts=3):
    """Download url to dest (cached). Returns dest Path or None on failure."""
    RAW.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not refresh:
        print(f"[cache] {dest.name}")
        return dest
    s = session()
    if referer:
        s.headers["Referer"] = referer
    for i in range(attempts):
        try:
            r = s.get(url, timeout=(15, 120))
            if r.status_code == 200 and r.content:
                dest.write_bytes(r.content)
                print(f"[ok] {dest.name}: {len(r.content)} bytes ({r.headers.get('content-type','?')})")
                return dest
            print(f"[warn] {dest.name}: HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"[warn] {dest.name}: {type(e).__name__} {str(e)[:80]}")
        time.sleep(4)
    print(f"[fail] {dest.name}: unreachable after {attempts} attempts")
    return None


def write_macro_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MACRO_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[write] {path.name}: {len(rows)} rows")


# =========================================================================
# 1. CBJ Real Estate Price Index
# =========================================================================

CBJ_URL = "https://www.cbj.gov.jo/ebv4.0/root_storage/en/eb_list_page/real_estate.xls"
CBJ_PAGE = "https://www.cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index"

CBJ_TYPE_MAP = {
    "سكني": "Residential", "فيلا": "Villa", "منزل": "House", "شقة": "Apartment",
    "غير سكني": "Non-residential", "تجاري": "Commercial", "صناعي": "Industrial",
    "اخرى": "Other", "أراضي": "Land", "خارج التنظيم": "Outside-regulation",
    "الرقم القياسي العام": "General",
}
CBJ_GOV_MAP = {
    "عمان": "Amman", "إربد": "Irbid", "الزرقاء": "Zarqa", "البلقاء": "Balqa",
    "المفرق": "Mafraq", "الكرك": "Karak", "الطفيلة": "Tafilah", "معان": "Ma'an",
    "مادبا": "Madaba", "جرش": "Jerash", "عجلون": "Ajloun", "العقبة": "Aqaba",
    "الرقم القياسي العام": "Kingdom",
}


def col_periods(sheet, hdr_row, sub_row):
    """Map data column -> period string. Annual cols (before first quarter col)
    become 'YYYY'; quarterly cols become 'YYYY-Qn' with the year forward-filled
    across each 4-column group."""
    def year_at(c):
        v = str(sheet.cell_value(hdr_row, c)).strip()
        try:
            y = int(float(v))
            return y if 1990 <= y <= 2100 else None
        except ValueError:
            return None

    quarters = {}
    qcols = []
    for c in range(sheet.ncols):
        q = str(sheet.cell_value(sub_row, c)).strip().upper()
        if q in ("Q1", "Q2", "Q3", "Q4"):
            quarters[c] = q
            qcols.append(c)
    qstart = min(qcols) if qcols else sheet.ncols

    periods = {}
    for c in range(sheet.ncols):
        if c < qstart:
            y = year_at(c)
            if y:
                periods[c] = str(y)
    cur_year = None
    for c in range(qstart, sheet.ncols):
        y = year_at(c)
        if y:
            cur_year = y
        if c in quarters and cur_year:
            periods[c] = f"{cur_year}-{quarters[c]}"
    return periods


def _find_header(sheet):
    for r in range(sheet.nrows):
        if any("الفترة" in str(sheet.cell_value(r, c)) for c in range(sheet.ncols)):
            return r
    raise RuntimeError("CBJ header row not found")


def parse_cbj(path, log):
    import xlrd
    b = xlrd.open_workbook(path)
    rows = []

    def emit_sheet(sheet, dim_map, dim_role):
        hdr = _find_header(sheet)
        periods = col_periods(sheet, hdr, hdr + 1)
        section = "Buildings" if dim_role == "type" else None
        for r in range(hdr + 1, sheet.nrows):
            label = str(sheet.cell_value(r, 1)).strip()
            if not label or label.startswith("المصدر") or "اولية" in label:
                continue
            if dim_role == "type" and label == "أراضي":
                section = "Lands"
            en = dim_map.get(label)
            if en is None:
                continue
            weight = str(sheet.cell_value(r, 2)).strip()
            wnote = ""
            try:
                wnote = f"relative weight {float(weight):.4f}"
            except ValueError:
                pass
            for c, period in periods.items():
                raw = sheet.cell_value(r, c)
                try:
                    val = float(raw)
                except (ValueError, TypeError):
                    continue
                if val == 0:
                    continue
                if dim_role == "type":
                    prefix = f"{section} - " if en not in ("General",) else ""
                    indicator = f"Real estate price index - {prefix}{en}"
                    geography = "Jordan (Kingdom)"
                else:
                    indicator = "Real estate price index - General"
                    geography = en
                rows.append({
                    "indicator": indicator, "geography": geography,
                    "period": period, "value": round(val, 2),
                    "unit": "index (base 2012=100)",
                    "evidence_category": "government", "language": "en",
                    "source_name": "CBJ",
                    "source_url": CBJ_PAGE, "capture_date": CAPTURE_DATE,
                    "collected_by": "gis-specialist", "confidence": "H",
                    "notes": wnote,
                })

    emit_sheet(b.sheet_by_index(0), CBJ_TYPE_MAP, "type")
    emit_sheet(b.sheet_by_index(1), CBJ_GOV_MAP, "gov")
    log.append(f"CBJ: parsed {len(rows)} rows from {path.name} "
               f"(base 2012=100; annual 2005+ and quarterly 2013+).")
    return rows


def run_cbj(refresh, log):
    path = download(CBJ_URL, RAW / "cbj_real_estate.xls", refresh, referer=CBJ_PAGE)
    if not path:
        log.append("CBJ: DOWNLOAD FAILED — manual step: open "
                   f"{CBJ_PAGE} and download real_estate.xls into {RAW}.")
        return
    rows = parse_cbj(path, log)
    write_macro_csv(OUT / "macro_cbj_price_index.csv", rows)


# =========================================================================
# 2. DoS building permits (supply pipeline)
# =========================================================================

DOS_HOST = "http://www.dos.gov.jo"  # HTTPS is refused from outside JO; HTTP works
DOS_YEAR_TABLE = DOS_HOST + "/owa-user/owa/builds_YEAR.show_tables1_build?lang=E&year1={year}&t_no=1"
DOS_PAGE = "https://dosweb.dos.gov.jo/industry/building-licenses/"
DOS_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

DOS_COUNT_METRICS = {"Residential", "Nonresidential", "Fences", "Total number"}
DOS_LICENSE_TYPES = {1: "New buildings", 2: "Extension to existing buildings", 3: "Existing buildings"}


def _num(v):
    try:
        f = float(v)
        return f if f == f else None  # drop NaN
    except (ValueError, TypeError):
        return None


def parse_dos_year(html, year, log):
    import pandas as pd
    from io import StringIO
    t = pd.read_html(StringIO(html))[0]
    metrics = DOS_COUNT_METRICS | {"Total area", "Estimated costs"}
    rows = []
    authority = None
    for _, row in t.iterrows():
        lbl = str(row[0]).strip()
        if not lbl or lbl == "nan" or lbl == "New buildings":
            continue
        is_group = pd.isna(row[1]) and pd.isna(row[2])
        if is_group and lbl not in metrics:
            authority = lbl
            continue
        if lbl not in metrics or authority is None:
            continue
        if lbl in DOS_COUNT_METRICS:
            unit = "licenses (count)"
        elif lbl == "Total area":
            unit = "1000 m2"
        else:
            unit = "1000 JD"
        for col, ltype in DOS_LICENSE_TYPES.items():
            val = _num(row[col])
            if val is None:
                continue
            rows.append({
                "indicator": f"Building licenses: {lbl} ({ltype})",
                "geography": authority, "period": str(year),
                "value": round(val, 2), "unit": unit,
                "evidence_category": "government", "language": "en",
                "source_name": "DoS",
                "source_url": DOS_PAGE, "capture_date": CAPTURE_DATE,
                "collected_by": "gis-specialist", "confidence": "H",
                "notes": "issuing-authority breakdown; area in 000 m2, cost in 000 JD",
            })
    return rows


def run_dos(refresh, log):
    all_rows = []
    for year in DOS_YEARS:
        dest = RAW / f"dos_licenses_{year}.html"
        url = DOS_YEAR_TABLE.format(year=year)
        path = download(url, dest, refresh, referer=DOS_PAGE)
        if not path:
            log.append(f"DoS {year}: download failed")
            continue
        html = path.read_bytes().decode("windows-1256", "replace")
        try:
            rows = parse_dos_year(html, year, log)
            all_rows.extend(rows)
        except Exception as e:
            log.append(f"DoS {year}: parse error {type(e).__name__}: {e}")
        time.sleep(2)
    if all_rows:
        write_macro_csv(OUT / "macro_dos_permits.csv", all_rows)
        years = sorted({r["period"] for r in all_rows})
        log.append(f"DoS: {len(all_rows)} rows across years {years[0]}-{years[-1]} "
                   f"(authorities incl. Greater Amman Municipality; via HTTP owa endpoint, "
                   f"HTTPS refused from outside Jordan).")
    else:
        log.append("DoS: NO ROWS — manual step: browse " + DOS_PAGE +
                    " or the owa year table over HTTP from a Jordan IP.")


# =========================================================================
# 3. DLS monthly trading report
# =========================================================================
# DLS primary site (dls.gov.jo) is UNREACHABLE from our location — connection
# times out on both HTTP/HTTPS (same 193.188.x gov block that geo-blocks GAM).
# The structured monthly report (by governorate / property type / nationality)
# lives only in the DLS Arabic PDF and cannot be retrieved here.
#
# Fallback (per the plan's source-resilience map: "news summaries of DLS data"):
# national aggregates transcribed from two reputable, dated articles that cite
# the DLS report directly. National-level only, confidence=L. Each figure keeps
# its own source URL. This is real DLS-origin data via secondary sources — NOT
# fabricated — and is clearly marked as such.

DLS_HOSTS = ["http://www.dls.gov.jo/", "https://dls.gov.jo/"]

DLS_ZAWYA = "https://www.zawya.com/en/economy/levant/jordan-real-estate-trading-volume-rises-3-in-first-eight-months-of-2025-yqqnnwmw"
DLS_JNEWS = "https://www.jordannews.jo/Section-33/Trade-Industry/Real-Estate-Trading-Volume-Reaches-JD-7-1-Billion-in-2025-48007"

# (indicator, period, value_million_jd, unit, source_name, source_url, note)
DLS_NEWS_ROWS = [
    ("Real estate trading volume", "2025-YTD-08", 4565.0, "million JD", "Zawya (DLS report via news)", DLS_ZAWYA, "cumulative Jan-Aug 2025, +3% YoY; article dated 2025-09-10"),
    ("Real estate trading volume", "2025-08", 686.7, "million JD", "Zawya (DLS report via news)", DLS_ZAWYA, "August 2025 single month, -3% YoY"),
    ("Real estate transaction revenues", "2025-YTD-08", 174.6, "million JD", "Zawya (DLS report via news)", DLS_ZAWYA, "cumulative Jan-Aug 2025, +4% YoY"),
    ("Real estate transaction revenues", "2025-08", 25.2, "million JD", "Zawya (DLS report via news)", DLS_ZAWYA, "August 2025 single month"),
    ("Foreign-ownership transaction value", "2025-YTD-08", 123.4, "million JD", "Zawya (DLS report via news)", DLS_ZAWYA, "cumulative Jan-Aug 2025 non-Jordanian ownership, -9% YoY"),
    ("Foreign-ownership transaction value", "2025-08", 16.2, "million JD", "Zawya (DLS report via news)", DLS_ZAWYA, "August 2025 non-Jordanian ownership"),
    ("Real estate trading volume", "2025", 7179.0, "million JD", "Jordan News (DLS report via news)", DLS_JNEWS, "full-year 2025, +7% YoY; article dated 2026-01-11"),
    ("Real estate trading volume", "2025-12", 724.7, "million JD", "Jordan News (DLS report via news)", DLS_JNEWS, "December 2025 single month, +58% YoY"),
    ("Real estate transaction revenues", "2025", 275.0, "million JD", "Jordan News (DLS report via news)", DLS_JNEWS, "full-year 2025, +5% YoY"),
    ("Real estate transaction revenues", "2025-12", 28.0, "million JD", "Jordan News (DLS report via news)", DLS_JNEWS, "December 2025 single month"),
]


def dls_primary_reachable():
    for host in DLS_HOSTS:
        try:
            r = requests.get(host, headers={"User-Agent": UA}, timeout=15)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
    return False


def run_dls(log):
    reachable = dls_primary_reachable()
    if reachable:
        log.append("DLS: primary dls.gov.jo is now REACHABLE — manual step: download the "
                   "latest monthly تداولات PDF and parse governorate/type/nationality breakdown "
                   "(this run still emits only the news-derived national aggregates).")
    else:
        log.append("DLS: primary dls.gov.jo UNREACHABLE (connection timeout, HTTP+HTTPS). "
                   "Structured monthly breakdown (governorate/type/nationality) NOT obtainable here. "
                   "MANUAL STEP: access DLS from a Jordan IP / VPN and download the latest monthly PDF.")
    rows = []
    for ind, period, val, unit, sname, surl, note in DLS_NEWS_ROWS:
        rows.append({
            "indicator": ind, "geography": "Jordan", "period": period,
            "value": val, "unit": unit,
            "evidence_category": "news", "language": "en",
            "source_name": sname, "source_url": surl, "capture_date": CAPTURE_DATE,
            "collected_by": "gis-specialist", "confidence": "L",
            "notes": "DLS figure via news (primary site unreachable); national only; " + note,
        })
    write_macro_csv(OUT / "macro_dls_transactions.csv", rows)
    log.append(f"DLS: wrote {len(rows)} news-derived national aggregate rows (confidence L).")


# =========================================================================
# 4. Zoning — GAM ArcGIS retry, community mirrors, OSM landuse fallback
# =========================================================================

GAM_REST = "https://www.ammancitygis.gov.jo/arcgis/rest/services?f=json"
MIRROR_ITEMS = ["4909a23609c441408ba48660bdecbdd0", "f4e390d55fe94a5b9f3df0687d918321"]
OVERPASS = "https://overpass-api.de/api/interpreter"
AMMAN_BBOX = "(31.85,35.75,32.05,36.05)"
OSM_UA = "RubiconRealEstate-GIS/1.0 (husain.bhattiwala@rubikonlabs.com)"


def gam_reachable(log):
    for u in (GAM_REST, GAM_REST.replace("https://", "http://")):
        try:
            r = requests.get(u, headers={"User-Agent": UA}, timeout=15)
            if r.status_code == 200 and "error" not in r.text[:60].lower():
                log.append(f"GAM ArcGIS: REACHABLE at {u} — pull official zoning directly.")
                return True
        except requests.RequestException:
            pass
    log.append("GAM ArcGIS (ammancitygis.gov.jo): UNREACHABLE (connection timeout) — geo-blocked to Jordan.")
    return False


def mirrors_reachable(log):
    ok = False
    for iid in MIRROR_ITEMS:
        try:
            j = requests.get(f"https://www.arcgis.com/sharing/rest/content/items/{iid}?f=json",
                             headers={"User-Agent": UA}, timeout=30).json()
            if "error" in j:
                log.append(f"GAM mirror {iid}: NOT accessible ({j['error'].get('message','')[:60]}).")
            else:
                log.append(f"GAM mirror {iid}: accessible — title={j.get('title')} url={j.get('url')}.")
                ok = True
        except requests.RequestException as e:
            log.append(f"GAM mirror {iid}: request error {type(e).__name__}.")
    return ok


def run_zoning(refresh, log):
    gam_reachable(log)
    mirrors_reachable(log)

    # Fallback: OSM landuse polygons (the plan's verified zoning fallback).
    dest = RAW / "osm_landuse.json"
    if dest.exists() and not refresh:
        print(f"[cache] {dest.name}")
        data = json.loads(dest.read_text(encoding="utf-8"))
    else:
        cls = "residential|commercial|industrial|retail|construction"
        q = (f"[out:json][timeout:180];("
             f'way[landuse~"^({cls})$"]{AMMAN_BBOX};'
             f'relation[landuse~"^({cls})$"]{AMMAN_BBOX};);out geom;')
        try:
            r = requests.post(OVERPASS, data={"data": q},
                              headers={"User-Agent": OSM_UA}, timeout=180)
            if r.status_code != 200:
                log.append(f"Zoning OSM landuse: Overpass HTTP {r.status_code} — no fallback layer written.")
                return
            data = r.json()
            dest.write_bytes(r.content)
        except requests.RequestException as e:
            log.append(f"Zoning OSM landuse: Overpass error {type(e).__name__} — no fallback layer written.")
            return

    features = []
    for el in data.get("elements", []):
        lu = el.get("tags", {}).get("landuse", "")
        name = el.get("tags", {}).get("name:en") or el.get("tags", {}).get("name", "")
        if el.get("type") == "way" and el.get("geometry"):
            ring = [[round(p["lon"], 6), round(p["lat"], 6)] for p in el["geometry"]]
            if len(ring) < 4:
                continue
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            features.append(_zoning_feature(ring, lu, name, el["type"], el["id"]))
        elif el.get("type") == "relation":
            for m in el.get("members", []):
                if m.get("role") == "outer" and m.get("geometry"):
                    ring = [[round(p["lon"], 6), round(p["lat"], 6)] for p in m["geometry"]]
                    if len(ring) < 4:
                        continue
                    if ring[0] != ring[-1]:
                        ring.append(ring[0])
                    features.append(_zoning_feature(ring, lu, name, el["type"], el["id"]))

    fc = {"type": "FeatureCollection", "features": features}
    (OUT / "zoning_osm_landuse.geojson").write_text(
        json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    by = Counter(f["properties"]["landuse"] for f in features)
    log.append(f"Zoning: official GAM zone classes unavailable; wrote OSM landuse FALLBACK "
               f"zoning_osm_landuse.geojson with {len(features)} polygons {dict(by)} "
               f"(community landuse, NOT official Res-A/B/C/D classes).")
    print(f"[write] zoning_osm_landuse.geojson: {len(features)} polygons {dict(by)}")


def _zoning_feature(ring, landuse, name, otype, oid):
    return {
        "type": "Feature",
        "properties": {
            "landuse": landuse, "name": name,
            "source": "osm_landuse", "official": False,
            "osm_id": f"{otype}/{oid}",
            "note": "OSM community landuse proxy; not official GAM zoning class",
        },
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--only", help="comma list: cbj,dos,dls,zoning")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(",")) if args.only else {"cbj", "dos", "dls", "zoning"}
    log = []

    if "cbj" in only:
        run_cbj(args.refresh, log)
    if "dos" in only:
        run_dos(args.refresh, log)
    if "dls" in only:
        run_dls(log)
    if "zoning" in only:
        run_zoning(args.refresh, log)

    print("\n=== LOG ===")
    for line in log:
        print(" -", line)
    (RAW / "run_log.txt").write_text("\n".join(log), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
