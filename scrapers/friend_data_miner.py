"""Mine the underused friend archive into the platform DB with full provenance.

Four priorities, each deduped against what is already loaded:
  P1  DoS quarterly Building Licenses -> dos_building_cost (2004-2026) + fill cost_benchmarks
      basic/standard with the DoS-derived official construction cost floor.
  P2  Aqaba ASEZ official land-use polygons -> zoning_plots (Aqaba submarket).
  P3  DLS English annual reports -> macro_series (annual transaction counts + market size).
  P4  ASEZ regulatory instructions -> evidence_items (foreign-ownership rules).

Never fabricates: every figure traces to a file + source URL; unmatched sources are skipped
and logged. Idempotent: unique keys / PKs mean a re-run inserts nothing new.
"""
from __future__ import annotations

import glob
import json
import re
import sqlite3
from datetime import date
from pathlib import Path
from statistics import mean

import fitz  # PyMuPDF

from friend_building_cost import parse_all as parse_building_cost

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "jordan_re.sqlite"
DATA = ROOT / "data/research-data/frnd/extracted/Data"
CAPTURE = date.today().isoformat()
BY = "friend-data-miner"

ARCGIS_ITEM = "https://www.arcgis.com/home/item.html?id=d7f591c9dff647068e01de91988048fa"
DLS_ANNUAL_PAGE = "https://www.dls.gov.jo/EN/List/Annual_Reports"
DOS_LICENSES_PAGE = "https://dosweb.dos.gov.jo/industry/building-licenses/"


# ---------------------------------------------------------------------------
# P1 — construction cost
# ---------------------------------------------------------------------------

def load_building_cost(conn: sqlite3.Connection) -> dict:
    rows, nfiles = parse_building_cost()
    src = "DoS Building Licenses (quarterly, friend archive)"
    note_base = ("Filed licensed estimated cost / filed area (Area 000 M2, Cost 000 JD). "
                 "Area+cost are authority totals across all building types (~90% residential by "
                 "license count). This is the licensing authority's administrative estimate — a "
                 "conservative floor, not turnkey market build cost.")
    ins = 0
    for r in rows:
        cur = conn.execute(
            """INSERT OR IGNORE INTO dos_building_cost
               (year, quarter, authority, building_type, license_type, licenses,
                residential_license_share, area_m2, estimated_cost_jd, cost_jd_per_m2,
                evidence_category, language, source_name, source_url, capture_date,
                collected_by, confidence, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["year"], r["quarter"], r["authority"], "all", r["license_type"], r["licenses"],
             r["residential_license_share"], r["area_m2"], r["estimated_cost_jd"], r["cost_jd_per_m2"],
             "government", "en", src, DOS_LICENSES_PAGE, CAPTURE, BY, "H",
             f"{note_base} license_type={r['license_type']}"),
        )
        ins += cur.rowcount

    bands = _cost_bands(rows)
    _fill_cost_benchmarks(conn, bands, src)
    return {"files": nfiles, "parsed": len(rows), "inserted": ins, "bands": bands}


def _cost_bands(rows: list[dict]) -> dict:
    """Recent (2023Q2-latest) new-building JD/m2 min-max per authority for the benchmark fill."""
    out = {}
    for auth in ("Kingdom", "Greater Amman Municipality"):
        recent = [x["cost_jd_per_m2"] for x in rows
                  if x["authority"] == auth and x["license_type"] == "new"
                  and (x["year"], x["quarter"]) >= (2023, "Q2")]
        if recent:
            out[auth] = (round(min(recent), 1), round(max(recent), 1), round(mean(recent), 1), len(recent))
    return out


def _fill_cost_benchmarks(conn: sqlite3.Connection, bands: dict, src: str) -> None:
    """Fill the NULL basic/standard construction rows with the DoS official floor."""
    plan = {
        "basic": ("Kingdom",
                  "DoS Kingdom-wide new-building licensed cost, recent 12 quarters. Official "
                  "administrative floor — understates turnkey build cost; use as cost-approach floor."),
        "standard": ("Greater Amman Municipality",
                     "DoS Greater Amman new-building licensed cost, recent 12 quarters (urban, "
                     "higher-spec). Official administrative floor; conservative vs turnkey."),
    }
    for spec, (auth, note) in plan.items():
        if auth not in bands:
            continue
        lo, hi, mn, n = bands[auth]
        conn.execute(
            """UPDATE cost_benchmarks
               SET cost_jd_per_m2_low = ?, cost_jd_per_m2_high = ?, year = 2026,
                   source_name = ?, source_url = ?, capture_date = ?, collected_by = ?,
                   confidence = 'H', evidence_category = 'government',
                   notes = ?
               WHERE spec_class = ? AND cost_jd_per_m2_low IS NULL""",
            (lo, hi, f"DoS Building Licenses ({auth})", DOS_LICENSES_PAGE, CAPTURE, BY,
             f"{note} n={n} quarters, mean {mn} JD/m2.", spec),
        )


# ---------------------------------------------------------------------------
# P2 — Aqaba official zoning
# ---------------------------------------------------------------------------

def _centroid(geom: dict) -> tuple[float | None, float | None]:
    pts = []

    def walk(c):
        if isinstance(c, list) and c and isinstance(c[0], (int, float)):
            pts.append(c)
        elif isinstance(c, list):
            for x in c:
                walk(x)

    walk(geom.get("coordinates"))
    if not pts:
        return None, None
    return round(mean(p[1] for p in pts), 6), round(mean(p[0] for p in pts), 6)


def load_aqaba_zoning(conn: sqlite3.Connection) -> dict:
    layers = [
        ("Iqlim_Landuse.geojson", "aqaba-iqlim", "Landuse"),
        ("GeneralLanduse.geojson", "aqaba-genlu", "CLASSES"),
    ]
    ins = 0
    classes: dict[str, int] = {}
    for fname, prefix, lu_key in layers:
        data = json.loads((DATA / "Aqaba_ASEZ_LandUse" / fname).read_text(encoding="utf-8"))
        for f in data.get("features", []):
            props = f.get("properties", {})
            geom = f.get("geometry")
            if not geom:
                continue
            fid = props.get("FID", props.get("OBJECTID"))
            raw_lu = props.get(lu_key)
            land_use = str(raw_lu).strip() if raw_lu not in (None, "") else "unknown"
            classes[land_use] = classes.get(land_use, 0) + 1
            lat, lng = _centroid(geom)
            cur = conn.execute(
                """INSERT OR IGNORE INTO zoning_plots
                   (plot_id, zone_class, far, max_height_m, land_use, neighborhood, district,
                    geometry_geojson, centroid_lat, centroid_lng, evidence_category, language,
                    source_name, source_url, capture_date, collected_by, confidence, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"{prefix}-{fid}", land_use, None, None, land_use, "Aqaba",
                 props.get("Z_DISTRI_3") or "Aqaba", json.dumps(geom, ensure_ascii=False),
                 lat, lng, "government", "en", "Aqaba ASEZ official", ARCGIS_ITEM, CAPTURE, BY, "H",
                 "ASEZAGIS master-plan land-use snapshot (ArcGIS web map 'Aqaba General LandUse'); "
                 f"layer {fname}."),
            )
            ins += cur.rowcount
    return {"inserted": ins, "classes": classes}


# ---------------------------------------------------------------------------
# P3 — DLS English annual reports
# ---------------------------------------------------------------------------

_WORD_BILLION = {"five": 5000, "six": 6000, "seven": 7000, "eight": 8000, "nine": 9000, "four": 4000}
_P_TOTAL = re.compile(r"total sale transactions? in the [Kk]ingdom.{0,40}?year\s*\(?(\d{4})\)?\s*reached\s*\(?([\d,]{4,})\)?", re.I | re.S)
_P_NONJ = re.compile(r"sale (?:transactions )?for non[- ]?[Jj]ordanians?.{0,20}?(\d{4})\D{0,20}?reached\s*\(?([\d,]{3,})\)?", re.I | re.S)
_P_SIZE = re.compile(r"[Rr]eal estate market size.{0,40}?year\s*\(?(\d{4})\)?\s*reached\s*(\w+)\s*billion", re.I | re.S)


def _macro(conn, indicator, period, value, unit, note):
    cur = conn.execute(
        """INSERT OR IGNORE INTO macro_series
           (indicator, geography, period, value, unit, evidence_category, language,
            source_name, source_url, capture_date, collected_by, confidence, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (indicator, "Jordan", period, value, unit, "government", "en",
         "DLS Annual Report (Dept. of Lands & Survey)", DLS_ANNUAL_PAGE, CAPTURE, BY, "H", note),
    )
    return cur.rowcount


def load_dls_annual(conn: sqlite3.Connection) -> dict:
    files = sorted(glob.glob(str(DATA / "DLS_Jordan_Annual_Reports/downloads/EN/*.pdf")))
    ins = 0
    matched = []
    for f in files:
        d = fitz.open(f)
        txt = re.sub(r"\s+", " ", " ".join(p.get_text() for p in d))
        rep = Path(f).name
        t = _P_TOTAL.search(txt)
        if t:
            yr, val = t.group(1), int(t.group(2).replace(",", ""))
            ins += _macro(conn, "Real estate sale transactions (count)", yr, val, "transactions",
                          f"Kingdom total sale transactions, DLS annual report {rep}.")
        n = _P_NONJ.search(txt)
        if n:
            yr, val = n.group(1), int(n.group(2).replace(",", ""))
            ins += _macro(conn, "Non-Jordanian sale transactions (count)", yr, val, "transactions",
                          f"Property sales to non-Jordanians, DLS annual report {rep}.")
        s = _P_SIZE.search(txt)
        if s and s.group(2).lower() in _WORD_BILLION:
            yr, val = s.group(1), _WORD_BILLION[s.group(2).lower()]
            ins += _macro(conn, "Real estate trading volume", yr, float(val), "million JD",
                          f"Real estate market size, rounded to nearest billion as stated in DLS "
                          f"annual report {rep}.")
        matched.append((rep, bool(t), bool(n), bool(s)))
    return {"files": len(files), "inserted": ins, "matched": matched}


# ---------------------------------------------------------------------------
# P4 — ASEZ regulatory instructions (foreign-ownership rules)
# ---------------------------------------------------------------------------

ASEZ_NONJORD_URL = "https://opendata.gov.jo/dataset/MIGRATED-1640-2022/resource/c35401fc-502f-4f76-96ce-6068aa07eef5/download/-.pdf"
ASEZ_LANDSALE_URL = "https://opendata.gov.jo/dataset/MIGRATED-1420-2022/resource/3b479c65-7104-4c55-9c84-177780de4377/download/-.pdf"

# Rules read directly from ASEZ Instructions No. 132/2007 (Arabic source PDF); cited, not interpreted.
ASEZ_RULES = [
    ("asez-nonjord-resi-land",
     "ASEZ: non-Jordanians may own residential land (up to 6 dunums)",
     "In the Aqaba Special Economic Zone a non-Jordanian natural person may own residential land "
     "up to 3 dunums (Commissioner approval) or 3-6 dunums (Chairman approval), subject to "
     "reciprocity and security clearance (Art. 4, Instructions 132/2007).",
     "Aqaba", ASEZ_NONJORD_URL,
     "Instructions No. 132 of 2007 on selling/leasing immovable property to non-Jordanians in ASEZ, Art. 4."),
    ("asez-nonjord-resi-building",
     "ASEZ: non-Jordanians may own residential buildings (up to 2000 m2)",
     "A non-Jordanian may own residential buildings up to 1000 m2 (Commissioner approval) or "
     "1000-2000 m2 (Chairman approval) in ASEZ, subject to reciprocity and security clearance "
     "(Art. 5, Instructions 132/2007).",
     "Aqaba", ASEZ_NONJORD_URL,
     "Instructions No. 132 of 2007, Art. 5."),
    ("asez-arab-reciprocity-exempt",
     "ASEZ: Arab-nationality buyers exempt from the reciprocity condition",
     "Holders of any Arab nationality are exempt from the reciprocity requirement for owning "
     "immovable property in ASEZ, provided the property is not owned by the Authority or a "
     "registered enterprise (Art. 6, Instructions 132/2007).",
     "Aqaba", ASEZ_NONJORD_URL,
     "Instructions No. 132 of 2007, Art. 6."),
    ("asez-nonjord-resale-lock",
     "ASEZ: non-Jordanian resale lock (3 years residential / 5 years other)",
     "A non-Jordanian owner may not transfer property acquired under these rules before 3 years "
     "(if for residence) or 5 years (any other purpose) from acquisition, except with Chairman "
     "approval; investment/development purchases are exempt (Art. 13, Instructions 132/2007).",
     "Aqaba", ASEZ_NONJORD_URL,
     "Instructions No. 132 of 2007, Art. 13."),
    ("asez-legal-person-land",
     "ASEZ: legal persons may own business land (up to 100 dunums, tiered)",
     "A legal person may own land needed for its business in ASEZ: up to 10 dunums (Commissioner), "
     "10-50 dunums (Chairman), or 50-100 dunums (Council); above 100 dunums needs Council of "
     "Ministers approval (Art. 10, Instructions 132/2007).",
     "Aqaba", ASEZ_NONJORD_URL,
     "Instructions No. 132 of 2007, Art. 10."),
    ("asez-land-sale-lease-system",
     "ASEZ: land sale and lease governed by ASEZ Regulation No. 7/2001",
     "Sale and lease of land in ASEZ is governed by Regulation No. 7 of 2001; land use, plot and "
     "building organisation follow rules set by the ASEZA Board under Art. 43 of the ASEZ Law "
     "(Regulation 7/2001, Art. 4).",
     "Aqaba", ASEZ_LANDSALE_URL,
     "Regulation No. 7 of 2001 on selling/leasing land in ASEZ, Art. 4."),
]


def load_regulatory(conn: sqlite3.Connection) -> dict:
    ins = 0
    for eid, title, summary, impact, url, note in ASEZ_RULES:
        cur = conn.execute(
            """INSERT OR IGNORE INTO evidence_items
               (evidence_id, type, title, summary_2_lines, impact_area, expected_year,
                expected_effect, published_date, evidence_category, language, source_name,
                source_url, capture_date, collected_by, confidence, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, "policy", title, summary, impact, None, "unknown", "2007-09-11",
             "government", "en", "ASEZA (Aqaba Special Economic Zone Authority)", url,
             CAPTURE, BY, "H", note),
        )
        ins += cur.rowcount
    return {"inserted": ins}


# ---------------------------------------------------------------------------

def main() -> None:
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        p1 = load_building_cost(conn)
        p2 = load_aqaba_zoning(conn)
        p3 = load_dls_annual(conn)
        p4 = load_regulatory(conn)
        conn.commit()
    finally:
        conn.close()

    print("=== P1 building cost ===")
    print(f"  files={p1['files']} parsed={p1['parsed']} inserted={p1['inserted']}")
    for auth, (lo, hi, mn, n) in p1["bands"].items():
        print(f"  {auth}: {lo}-{hi} JD/m2 (mean {mn}, n={n}) -> cost_benchmarks")
    print("=== P2 Aqaba zoning ===")
    print(f"  inserted={p2['inserted']}  classes={len(p2['classes'])}")
    print("=== P3 DLS annual ===")
    print(f"  files={p3['files']} macro rows inserted={p3['inserted']}")
    print("=== P4 regulatory ===")
    print(f"  evidence_items inserted={p4['inserted']}")


if __name__ == "__main__":
    main()
