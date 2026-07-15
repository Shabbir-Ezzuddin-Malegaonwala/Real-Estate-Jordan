"""Precompute engine recommendations for the frontend (national DB).

Writes app/web/public/engine_output.json in the combined shape the React app reads
(offline / precomputed mode): { generated_at, source, neighborhoods: {name: result} }.
Picks a representative national set — the top Amman submarkets by comp depth plus the
main secondary cities — so the demo shows nationwide coverage, not just 5 areas.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

from app.engine import recommend
from app.engine.data import load_bundle_from_sqlite
from app.engine.models import Subject

DB = "db/jordan_re.sqlite"          # canonical DB (Issue #2: one canonical listing set)
LISTINGS_CSV = Path("data/processed/listings_national_20260708.csv")  # legacy source, provenance only
# Pipeline source-of-truth: prepare-data.mjs copies this -> public/engine_output.json.
OUT = Path("app/engine/sample_output.json")
OUTPUTS_DIR = Path("app/engine/outputs")            # per-neighborhood files (C1)
MAP_NAMES = Path("data/processed/map_neighborhoods.txt")
AS_OF = date(2026, 7, 10)   # canonical jordan_re.sqlite vintage

# secondary-city anchors — included to demonstrate national reach in the charts
SECONDARY = ["Irbid", "Zarqa", "Aqaba", "Madaba", "Salt", "Jerash"]
# the five pilot target submarkets — regenerate their per-neighborhood files from
# the NATIONAL db so no stale pilot numbers survive (review C1).
TARGET_FILES = ["Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"]


def _provenance() -> dict:
    """Version-pin: tie every output to the exact snapshot that produced it (review C4)."""
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      text=True).strip()
    except Exception:
        sha = "unknown"
    # Pin to the exact listings snapshot inside the canonical DB (content hash + row
    # count), so a swapped DB is detectable and outputs are reproducible (review C4).
    conn = sqlite3.connect(DB)
    row_count = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    h = hashlib.sha256()
    for row in conn.execute(
            "SELECT listing_id, price_jd, area_m2 FROM listings ORDER BY listing_id"):
        h.update(repr(row).encode())
    conn.close()
    snapshot_hash = h.hexdigest()[:16]
    return {
        "data_source_file": DB,
        "listings_row_count": row_count,
        "listings_snapshot_hash": snapshot_hash,
        "engine_git_sha": sha,
        "generated_at": AS_OF.isoformat(),
    }


def main() -> None:
    bundle = load_bundle_from_sqlite(DB, as_of=AS_OF)
    prov = _provenance()
    cnt = Counter(l.neighborhood for l in bundle.sales() if l.property_type == "apartment")

    # Price EXACTLY the submarkets drawn on the map (map_neighborhoods.txt) so every
    # clickable circle has a recommendation, plus the secondary-city anchors.
    map_names = MAP_NAMES.read_text(encoding="utf-8").splitlines() if MAP_NAMES.exists() else []
    names, seen = [], set()
    for n in [x.strip() for x in map_names if x.strip()] + SECONDARY:
        if n and n not in seen and cnt.get(n, 0) >= 5:
            seen.add(n)
            names.append(n)

    by_nbhd = {}
    for nb in names:
        s = Subject(neighborhood=nb, property_type="apartment", area_m2=175, bedrooms=3,
                    floor_level=4, finish_quality="high", building_age_years=0)
        rec = recommend(s, bundle).to_dict()
        rec["provenance"] = prov
        by_nbhd[nb] = rec

    combined = {
        "generated_at": prov["generated_at"],
        "source": f"{DB} ({len(bundle.listings):,} listings, nationwide)",
        "provenance": prov,
        "neighborhoods": by_nbhd,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")

    # C1: regenerate the per-neighborhood files from NATIONAL data (kill stale pilot files)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for nb in TARGET_FILES:
        if nb in by_nbhd:
            (OUTPUTS_DIR / f"{nb.lower()}.json").write_text(
                json.dumps(by_nbhd[nb], indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {OUT} with {len(by_nbhd)} neighborhoods (source: {prov['data_source_file']}, "
          f"{prov['listings_row_count']:,} rows, hash {prov['listings_snapshot_hash']}, sha {prov['engine_git_sha']})")
    for nb, r in by_nbhd.items():
        print(f"  {nb:<22} {r['min_safe_price_jd_m2']:>5.0f}/{r['recommended_price_jd_m2']:>5.0f}/"
              f"{r['premium_price_jd_m2']:>5.0f}  {r['confidence']['label']}")


if __name__ == "__main__":
    main()
