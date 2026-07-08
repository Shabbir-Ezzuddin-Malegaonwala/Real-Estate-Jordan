"""Parse DOS building-licence tables -> construction cost/m² -> cost_benchmarks + macro_series.

The DOS files are Microsoft-HTML tables (.xls extension) nested by issuing authority
(Kingdom -> Greater Amman Municipality -> other municipalities). Each authority block has
Residential/Non-residential/Fences count rows, then 'Total area' (000 m²) and
'Estimated costs' (000 JD) rows across [New | Extension | Existing] columns.

National new-building construction cost/m² = Estimated costs[New] / Total area[New]
(both in thousands -> the ratio is JD/m²). We read the last few YEARLY Table1 files,
emit a per-year national cost series (macro_series) and one cost_benchmarks 'standard'
row whose low/high span the recent range.

NB: DOS 'estimated cost' is the licence-declared build cost — official and defensible,
but typically conservative (a floor), which is exactly the role it plays here.

Usage:
    python scrapers/dos_costs.py
"""

from __future__ import annotations

import csv
import glob
import re
from pathlib import Path

from bs4 import BeautifulSoup

SRC = Path("D:/Rubikon Labs/Project on Jordan/Data/DOS_Jordan_Building_Licenses/downloads")
OUT = Path("data/processed")
CAPTURE = "2026-07-03"
SRC_URL = "http://dosweb.dos.gov.jo/industry/building-licenses/"

AUTHORITIES = {"kingdom", "greater amman municipality"}


def _cells(tr) -> list[str]:
    return [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]


def _num(s: str):
    s = (s or "").replace(",", "").strip()
    m = re.match(r"^-?\d+(\.\d+)?$", s)
    return float(s) if m else None


def parse_year_file(path: Path) -> dict[str, float]:
    """Return {authority: cost_per_m2_new} for a yearly Table1 file."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    current = None
    area_new: dict[str, float] = {}
    cost_new: dict[str, float] = {}
    for tr in soup.find_all("tr"):
        cells = _cells(tr)
        if not cells:
            continue
        head = cells[0].strip().lower()
        rest_blank = all(not c.strip() for c in cells[1:])
        if head in AUTHORITIES and rest_blank:
            current = head
            continue
        if current is None:
            continue
        if head == "total area":
            v = _num(cells[1]) if len(cells) > 1 else None
            if v:
                area_new[current] = v
        elif head == "estimated costs":
            v = _num(cells[1]) if len(cells) > 1 else None
            if v:
                cost_new[current] = v
    out = {}
    for auth in area_new:
        a, c = area_new.get(auth), cost_new.get(auth)
        if a and c and a > 0:
            out[auth] = round(c / a, 1)      # (000 JD)/(000 m²) = JD/m²
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(str(SRC / "yearly" / "*" / "*Table1*.xls")))
    per_year: dict[int, dict[str, float]] = {}
    for f in files:
        m = re.search(r"Yearly_(\d{4})_", Path(f).name)
        if not m:
            continue
        year = int(m.group(1))
        costs = parse_year_file(Path(f))
        if costs:
            per_year[year] = costs

    years = sorted(per_year)
    print(f"parsed {len(years)} yearly files: {years[0]}–{years[-1]}")
    for y in years[-6:]:
        k = per_year[y].get("kingdom")
        a = per_year[y].get("greater amman municipality")
        print(f"  {y}: Kingdom {k} JD/m² | Greater Amman {a} JD/m²")

    # macro_series — national construction cost/m² per year
    macro_path = OUT / "macro_construction_cost_dos.csv"
    with macro_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["indicator", "geography", "period", "value", "unit",
                    "evidence_category", "language", "source_name", "source_url",
                    "capture_date", "collected_by", "confidence", "notes"])
        for y in years:
            k = per_year[y].get("kingdom")
            if k:
                w.writerow(["dos_construction_cost_jd_m2", "Jordan", str(y), k, "JD/m2",
                            "government", "en", "DOS Building Licenses", SRC_URL,
                            CAPTURE, "scraper", "H",
                            "declared licence build cost (new buildings), Kingdom"])

    # cost_benchmarks — one 'standard' row spanning the recent Kingdom range
    recent = [per_year[y]["kingdom"] for y in years[-3:] if per_year[y].get("kingdom")]
    low, high = min(recent), max(recent)
    latest = years[-1]
    bench_path = OUT / "cost_benchmarks_dos_20260708.csv"
    with bench_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["spec_class", "cost_jd_per_m2_low", "cost_jd_per_m2_high", "year",
                    "evidence_category", "language", "source_name", "source_url",
                    "capture_date", "collected_by", "confidence", "notes"])
        w.writerow(["standard", low, high, latest, "government", "en",
                    "DOS Building Licenses", SRC_URL, CAPTURE, "scraper", "H",
                    f"national declared build cost/m2, {years[-3]}–{latest} range; "
                    f"construction only (excl. land); conservative licence valuation"])
    print(f"\ncost_benchmarks 'standard': low={low} high={high} JD/m² (year {latest})")
    print(f"written -> {macro_path}\nwritten -> {bench_path}")


if __name__ == "__main__":
    main()
