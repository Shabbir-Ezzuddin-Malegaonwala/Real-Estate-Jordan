"""P1: DoS quarterly Building Licenses (friend archive) -> construction cost per m2.

Files are DoS 'xls' that are actually HTML tables (Table1 = No. of licenses, Area,
Estimated Cost by issuing authority and license type). Area in 000 M2, Cost in 000 JD,
so Estimated-Cost / Area = JD per m2 directly. Area+cost are reported as authority
totals (all building types blended); counts split Residential/Nonresidential/Fences.

Emits one row per (year, quarter, authority, license_type) with area_m2, estimated_cost_jd
and derived cost_jd_per_m2, plus the residential license share for that block.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
QDIR = ROOT / "data/research-data/frnd/extracted/Data/DOS_Jordan_Building_Licenses/downloads/quarterly"

# col 0 = label, cols 1..3 = New buildings / Extension / Existing buildings
LICENSE_TYPES = {1: "new", 2: "extension", 3: "existing"}
AUTHORITIES = {
    "Kingdom",
    "Greater Amman Municipality",
    "Municipalities",
    "Joint district committees",
    "Regional authorities",
}
BLOCK_ROWS = {"Residential", "Nonresidential", "Fences", "Total number", "Total area", "Estimated costs"}


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (ValueError, TypeError):
        return None


def parse_file(path: Path):
    """Return list of dicts for one quarter file."""
    year, quarter = re.search(r"Quarterly_(\d{4})_Q(\d)", path.name).groups()
    t = pd.read_html(path)[0]
    rows = []
    authority = None
    block = {}  # metric -> {ltype:int -> value}
    order = []  # authorities seen, to flush on change

    def flush():
        if not authority or "Total area" not in block:
            return
        res = block.get("Residential", {})
        nonres = block.get("Nonresidential", {})
        totn = block.get("Total number", {})
        for col, ltype in LICENSE_TYPES.items():
            area_k = block["Total area"].get(col)          # 000 m2
            cost_k = block["Estimated costs"].get(col)      # 000 JD
            if area_k is None or cost_k is None or area_k <= 0:
                continue
            area_m2 = area_k * 1000.0
            cost_jd = cost_k * 1000.0
            res_c = res.get(col) or 0
            nonres_c = nonres.get(col) or 0
            denom = res_c + nonres_c
            res_share = round(res_c / denom, 3) if denom else None
            licenses = totn.get(col)
            rows.append({
                "year": int(year), "quarter": f"Q{quarter}", "authority": authority,
                "license_type": ltype,
                "licenses": int(licenses) if licenses is not None else None,
                "area_m2": round(area_m2, 1), "estimated_cost_jd": round(cost_jd, 1),
                "cost_jd_per_m2": round(cost_jd / area_m2, 2),
                "residential_license_share": res_share,
            })

    for _, r in t.iterrows():
        lbl = str(r.iloc[0]).strip()
        if lbl in AUTHORITIES:
            flush()
            authority = lbl
            block = {}
            order.append(lbl)
            continue
        if lbl in BLOCK_ROWS and authority:
            block[lbl] = {c: _num(r.iloc[c]) for c in LICENSE_TYPES}
    flush()
    return rows


def parse_all():
    all_rows = []
    files = sorted(QDIR.glob("*/*Table1*.xls"))
    for f in files:
        try:
            all_rows.extend(parse_file(f))
        except Exception as e:  # noqa: BLE001 - report and continue per file
            print(f"[warn] {f.name}: {type(e).__name__}: {e}")
    return all_rows, len(files)


if __name__ == "__main__":
    rows, nfiles = parse_all()
    print(f"files={nfiles} rows={len(rows)}")
    king_new = [r for r in rows if r["authority"] == "Kingdom" and r["license_type"] == "new"]
    print("\nKingdom, NEW buildings — cost JD/m2 by quarter:")
    for r in sorted(king_new, key=lambda x: (x["year"], x["quarter"]))[-12:]:
        print(f"  {r['year']}-{r['quarter']}: {r['cost_jd_per_m2']:>7.1f} JD/m2  "
              f"(area {r['area_m2']:,.0f} m2, res_share {r['residential_license_share']})")
    gam_new = [r for r in rows if r["authority"] == "Greater Amman Municipality" and r["license_type"] == "new"]
    print("\nGreater Amman, NEW buildings — cost JD/m2 by quarter (recent):")
    for r in sorted(gam_new, key=lambda x: (x["year"], x["quarter"]))[-8:]:
        print(f"  {r['year']}-{r['quarter']}: {r['cost_jd_per_m2']:>7.1f} JD/m2")
