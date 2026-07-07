"""Extract CBJ Real Estate Price Index quarterly series into macro_series rows.
Sheet 1 = by property type (national/Jordan). Sheet 2 = by governorate.
Base 2012=100. Emits partial CSV consumed by build_macro_series.py.
"""
import csv
import re
import xlrd

SRC = r"C:\Rubicon\Real-Estate-Jordan\data\raw\cbj\real_estate_en.xls"
OUT = r"C:\Rubicon\Real-Estate-Jordan\data\processed\_cbj_rows.csv"
SOURCE_URL = "https://www.cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index"
CAPTURE = "2026-07-07"


def slug(s):
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def quarter_map(sh, year_row, q_row):
    """Return {col_index: (year, quarter)} for quarterly columns only."""
    cmap = {}
    cur_year = None
    for c in range(sh.ncols):
        yv = sh.cell_value(year_row, c)
        qv = str(sh.cell_value(q_row, c)).strip()
        if isinstance(yv, float) and yv == int(yv) and 2000 <= int(yv) <= 2035:
            cur_year = int(yv)
        elif isinstance(yv, str) and re.fullmatch(r"20\d\d", yv.strip()):
            cur_year = int(yv.strip())
        if qv in ("Q1", "Q2", "Q3", "Q4") and cur_year:
            cmap[c] = (cur_year, qv)
    return cmap


def eng_label(sh, r):
    """Last non-empty cell in row = English series name."""
    for c in range(sh.ncols - 1, -1, -1):
        v = sh.cell_value(r, c)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def extract_sheet(sh, geography_mode, year_row, q_row, data_rows):
    cmap = quarter_map(sh, year_row, q_row)
    rows = []
    seen = {}
    for r in data_rows:
        label = eng_label(sh, r)
        if not label or label.lower() in ("period", "source: department of lands and survey & central bank of  jordan.", "*: preliminary."):
            continue
        if geography_mode == "type":
            base = slug(label)
            n = seen.get(base, 0)
            seen[base] = n + 1
            key = base if n == 0 else "land_" + base
            key = key.replace("non_regulaetd", "non_regulated")
            indicator = "cbj_repi_" + key
            geography = "Jordan"
        else:
            indicator = "cbj_repi_general_index"
            geography = label  # governorate English name
        for c, (year, q) in sorted(cmap.items()):
            v = sh.cell_value(r, c)
            if not isinstance(v, (int, float)):
                continue
            if v == "" or v is None:
                continue
            period = f"{year}-{q}"
            rows.append({
                "indicator": indicator,
                "geography": geography,
                "period": period,
                "value": round(float(v), 3),
                "unit": "index_2012=100",
                "source_name": "Central Bank of Jordan (Real Estate Price Index)",
                "source_url": SOURCE_URL,
                "notes": f"Base 2012=100. Series: {label}. Latest quarters preliminary. Extracted from real_estate.xls.",
            })
    return rows


def main():
    wb = xlrd.open_workbook(SRC)
    sh1 = wb.sheet_by_index(0)  # by property type
    sh2 = wb.sheet_by_index(1)  # by governorate
    # sheet1: year header row 7, quarter row 8, data rows 9..22
    rows = extract_sheet(sh1, "type", 7, 8, range(9, 23))
    # sheet2: year header row 5, quarter row 6, data rows 8..19 (12 governorates; row 20 = national General Index, already in sheet1)
    rows += extract_sheet(sh2, "gov", 5, 6, range(8, 20))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    inds = sorted(set(r["indicator"] for r in rows))
    geos = sorted(set(r["geography"] for r in rows))
    periods = sorted(set(r["period"] for r in rows))
    print(f"rows={len(rows)} indicators={len(inds)} geos={len(geos)}")
    print("indicators:", inds)
    print("geos:", geos)
    print("period range:", periods[0], "->", periods[-1], f"({len(periods)} quarters)")


if __name__ == "__main__":
    main()
