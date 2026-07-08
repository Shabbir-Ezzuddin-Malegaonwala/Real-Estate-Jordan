"""Cross-portal / relisting de-duplication (review M4).

The same unit is often relisted across Bayut/OpenSooq/others and across months,
inflating apparent comp density and biasing medians toward repeatedly-pushed listings.
This collapses rows that share the same (listing_type, property_type, neighborhood,
price, area, bedrooms) — a conservative exact-signature match that catches genuine
relistings without merging distinct units. The richest row (most populated attributes,
coordinates preferred) is kept; the rest are dropped.

Runs after ingest, before enrichment. Rewrites the national listings CSV in place.

Usage:  python scrapers/dedup_listings.py
"""

from __future__ import annotations

import csv
from pathlib import Path

CSV = Path("data/processed/listings_national_20260708.csv")

# attribute columns whose fill-count decides which duplicate is "richest"
RICH_COLS = ["lat", "lng", "floor_level", "building_age_years", "view", "parking",
             "finish_quality", "furnishing", "bathrooms", "description_raw"]
BLANK = ("", "unknown", "u")


def signature(r: dict):
    price = (r.get("price_jd") or "").strip()
    area = (r.get("area_m2") or "").strip()
    beds = (r.get("bedrooms") or "").strip()
    # only dedup rows that actually have a price+area+beds signature to match on
    if not (price and area and beds):
        return None
    try:
        pk = round(float(price))
        ak = round(float(area), 1)
    except ValueError:
        return None
    return (r.get("listing_type"), r.get("property_type"), r.get("neighborhood"), pk, ak, beds)


def richness(r: dict) -> int:
    return sum(1 for c in RICH_COLS if (r.get(c) or "").strip().lower() not in BLANK)


def main() -> None:
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    hdr = list(rows[0].keys())

    best: dict = {}          # signature -> chosen row
    singletons = []          # rows with no dedup signature (kept as-is)
    removed = 0
    for r in rows:
        sig = signature(r)
        if sig is None:
            singletons.append(r)
            continue
        if sig not in best:
            best[sig] = r
        else:
            removed += 1
            # keep the richer row (ties: keep the incumbent)
            if richness(r) > richness(best[sig]):
                best[sig] = r

    kept = list(best.values()) + singletons
    with CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader()
        w.writerows(kept)

    print(f"dedup: {len(rows):,} -> {len(kept):,} rows  (removed {removed:,} relistings; "
          f"{len(singletons):,} kept without a price+area+beds signature)")


if __name__ == "__main__":
    main()
