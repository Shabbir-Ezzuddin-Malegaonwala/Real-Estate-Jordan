"""Derive per-submarket observed gross rental yield from the listings table.

For each (neighborhood, property_type) it takes the robust median rent/m² and sale/m²
(same plausibility floors + log-MAD trim the engine uses) and computes the observed gross
yield = annual rent/m² ÷ sale/m². Output feeds the `area_yields` table, which powers the
"Gross yield %" map layer and the left-panel income line.

This is the DESCRIPTIVE observed yield. The engine's income ceiling keeps a citywide market
benchmark as the *required* yield on purpose — an area's own realised yield would collapse the
ceiling back onto that area's sale price.

Usage:
    python scrapers/build_area_yields.py                 # writes data/processed/area_yields.csv
    python scrapers/build_area_yields.py --db db/jordan_re.sqlite
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from app.engine.config import (  # noqa: E402  (import after sys.path bootstrap)
    MIN_PLAUSIBLE_RENT_PPM2, MIN_PLAUSIBLE_SALE_PPM2, RENT_MONTHLY_MAX_PPM2)
from app.engine.stats import median, robust_keep, to_monthly_rent  # noqa: E402

MIN_PUBLISH = 3          # need >=3 usable rows on a side before publishing its median
SOURCE_NAME = "Derived — portal rent vs sale medians (Bayut/OpenSooq)"
SOURCE_URL = "internal://engine/build_area_yields"
COLLECTED_BY = "data-pipeline-agent"

COLUMNS = [
    "neighborhood", "property_type", "median_rent_jd_m2", "annual_rent_jd_m2",
    "median_sale_jd_m2", "gross_yield_pct", "n_rent", "n_sale",
    "evidence_category", "language", "source_name", "source_url", "capture_date",
    "collected_by", "confidence", "notes",
]


def _kept(values: list[float], floor: float) -> list[float]:
    keep = robust_keep(values, floor)
    return [v for v, k in zip(values, keep) if k]


def _confidence(n_rent: int, n_sale: int) -> str:
    strength = min(n_rent, n_sale) if n_sale else n_rent
    if strength >= 30:
        return "H"
    if strength >= 10:
        return "M"
    return "L"


def build_rows(conn: sqlite3.Connection, as_of: str) -> list[dict]:
    conn.row_factory = sqlite3.Row
    raw = conn.execute(
        "SELECT neighborhood, property_type, listing_type, price_per_m2 FROM listings "
        "WHERE price_per_m2 IS NOT NULL AND listing_type IN ('sale','rent') "
        "AND property_type IN ('apartment','villa') AND neighborhood <> ''"
    ).fetchall()

    buckets: dict[tuple[str, str], dict[str, list[float]]] = {}
    for r in raw:
        key = (r["neighborhood"], r["property_type"])
        bucket = buckets.setdefault(key, {"rent": [], "sale": []})
        if r["listing_type"] == "rent":
            monthly = to_monthly_rent(r["price_per_m2"], RENT_MONTHLY_MAX_PPM2)
            if monthly is not None:
                bucket["rent"].append(monthly)
        else:
            bucket["sale"].append(r["price_per_m2"])

    rows: list[dict] = []
    for (nbhd, ptype), sides in sorted(buckets.items()):
        rent = _kept(sides["rent"], MIN_PLAUSIBLE_RENT_PPM2)
        sale = _kept(sides["sale"], MIN_PLAUSIBLE_SALE_PPM2)
        n_rent, n_sale = len(rent), len(sale)
        if n_rent < MIN_PUBLISH:
            continue  # the rent side is the new capability; skip areas with no usable rent

        med_rent = round(median(rent), 2)
        annual_rent = round(med_rent * 12, 2)
        med_sale = round(median(sale), 2) if n_sale >= MIN_PUBLISH else None
        yield_pct = round(annual_rent / med_sale * 100, 2) if med_sale else None

        rows.append({
            "neighborhood": nbhd,
            "property_type": ptype,
            "median_rent_jd_m2": med_rent,
            "annual_rent_jd_m2": annual_rent,
            "median_sale_jd_m2": med_sale if med_sale is not None else "unknown",
            "gross_yield_pct": yield_pct if yield_pct is not None else "unknown",
            "n_rent": n_rent,
            "n_sale": n_sale,
            "evidence_category": "derived",
            "language": "en",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "capture_date": as_of,
            "collected_by": COLLECTED_BY,
            "confidence": _confidence(n_rent, n_sale),
            "notes": (f"rent normalised to monthly (annual quotes >{RENT_MONTHLY_MAX_PPM2:g} "
                      f"JD/m² ÷12); robust median (log-MAD trimmed); yield = annual rent ÷ sale; "
                      f"observed asking-based, not the engine's required-yield"),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build per-area observed rental yields.")
    parser.add_argument("--db", type=Path, default=_ROOT / "db" / "jordan_re.sqlite")
    parser.add_argument("--out", type=Path, default=_ROOT / "data" / "processed" / "area_yields.csv")
    args = parser.parse_args()

    as_of = date.today().isoformat()
    conn = sqlite3.connect(args.db)
    try:
        rows = build_rows(conn, as_of)
    finally:
        conn.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    priced = [r for r in rows if r["gross_yield_pct"] != "unknown"]
    print(f"area_yields: {len(rows)} submarket rows written to {args.out} (as_of {as_of})")
    print(f"  with a computable gross yield: {len(priced)}")
    top = sorted(priced, key=lambda r: r["n_rent"], reverse=True)[:12]
    for r in top:
        print(f"  {r['neighborhood']:<16} {r['property_type']:<9} "
              f"rent {r['median_rent_jd_m2']:>6.1f}  sale {r['median_sale_jd_m2']:>7.1f}  "
              f"yield {r['gross_yield_pct']:>4}%  (rent n={r['n_rent']}, sale n={r['n_sale']}, {r['confidence']})")


if __name__ == "__main__":
    main()
