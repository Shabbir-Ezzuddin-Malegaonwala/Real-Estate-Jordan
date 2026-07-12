"""Rebuild the `districts` registry from the national listings corpus.

WHY: the app flags an area as "covered / with structured data" only if its name is
present in the `districts` table. A fresh national build populates `listings` but leaves
`districts` empty -> every area reads as "0 with structured data" even though the listings
are all there. This script regenerates `districts` deterministically FROM the data itself.

RULE (product decision, 2026-07): every unique neighborhood we hold ANY listing for is a
first-class area -- no minimum-listing threshold. Coverage is not gated on depth; thin areas
simply price with wider (honest) confidence bands, or degrade to "no data yet" until more
data arrives. As more data is scraped, re-run this script and the registry grows with it.

CENTROID (map location) is derived, in priority order:
  1. median lat/lng of that neighborhood's own listings (exact, data-derived), else
  2. the matching centroid from neighborhoods_voronoi.geojson (290 pre-computed centroids), else
  3. NULL -- the area still lists in search; it just can't fly the map until coords arrive.

Everything is derived from national data. Nothing is copied from the old jordan_re.sqlite
sample DB (we only reuse its column shape, which is already the schema here).

Idempotent: clears and rewrites every row. Safe to run after each data refresh.

Usage:  python db/build_districts.py [--db db/jordan_national.sqlite]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB = _REPO_ROOT / "db" / "jordan_national.sqlite"
_VORONOI = _REPO_ROOT / "app" / "web" / "public" / "data" / "neighborhoods_voronoi.geojson"

_ARABIC = re.compile(r"[؀-ۿ]")
_ASCII_LETTER = re.compile(r"[A-Za-z]")


def _lang(name: str) -> str:
    has_ar = bool(_ARABIC.search(name))
    has_en = bool(_ASCII_LETTER.search(name))
    if has_ar and has_en:
        return "mixed"
    if has_ar:
        return "ar"
    if has_en:
        return "en"
    return "unknown"


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "area"


def _voronoi_centroids() -> dict[str, tuple[float, float]]:
    """lower-cased neighborhood -> (lat, lng) from the baked voronoi geojson, if present."""
    out: dict[str, tuple[float, float]] = {}
    if not _VORONOI.exists():
        return out
    data = json.loads(_VORONOI.read_text(encoding="utf-8"))
    for ft in data.get("features", []):
        p = ft.get("properties") or {}
        name = str(p.get("neighborhood") or "").strip()
        lat, lng = p.get("centroid_lat"), p.get("centroid_lng")
        if name and isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            out.setdefault(name.lower(), (float(lat), float(lng)))
    return out


def build(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT neighborhood AS n, lat, lng, listing_type
               FROM listings
               WHERE neighborhood IS NOT NULL AND TRIM(neighborhood) != ''
                     AND LOWER(neighborhood) != 'unknown'"""
        ).fetchall()

        # Aggregate per unique neighborhood (using the exact listing spelling as the key).
        agg: dict[str, dict] = {}
        for r in rows:
            name = r["n"].strip()
            a = agg.setdefault(name, {"name": name, "lats": [], "lngs": [],
                                      "n_listings": 0, "n_sale": 0})
            a["n_listings"] += 1
            if r["listing_type"] == "sale":
                a["n_sale"] += 1
            if r["lat"] is not None and r["lng"] is not None:
                a["lats"].append(float(r["lat"]))
                a["lngs"].append(float(r["lng"]))

        voronoi = _voronoi_centroids()
        today = date.today().isoformat()

        conn.execute("DELETE FROM districts")
        used_ids: set[str] = set()
        stats = {"total": 0, "centroid_from_listings": 0,
                 "centroid_from_voronoi": 0, "centroid_missing": 0, "with_sale": 0}

        for name, a in sorted(agg.items()):
            # 1) centroid from the area's own listing coordinates (robust median), else
            # 2) voronoi geojson centroid, else 3) NULL.
            if a["lats"]:
                lat = round(statistics.median(a["lats"]), 6)
                lng = round(statistics.median(a["lngs"]), 6)
                src, conf = "listings (median coords)", "H"
                stats["centroid_from_listings"] += 1
            elif name.lower() in voronoi:
                lat, lng = voronoi[name.lower()]
                src, conf = "neighborhoods_voronoi.geojson", "M"
                stats["centroid_from_voronoi"] += 1
            else:
                lat = lng = None
                src, conf = "no coordinates available yet", "L"
                stats["centroid_missing"] += 1

            # unique, stable district_id
            base = _slug(name)
            did, i = base, 2
            while did in used_ids:
                did, i = f"{base}-{i}", i + 1
            used_ids.add(did)

            if a["n_sale"] > 0:
                stats["with_sale"] += 1
            stats["total"] += 1

            conn.execute(
                """INSERT INTO districts
                   (district_id, name, neighborhood, centroid_lat, centroid_lng,
                    evidence_category, language, source_name, source_url, capture_date,
                    collected_by, confidence, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (did, name, name, lat, lng,
                 "derived", _lang(name),
                 f"Jordan national listings build ({src})",
                 "internal://jordan_national.sqlite", today,
                 "db/build_districts.py",
                 conf,
                 f"n_listings={a['n_listings']}, n_sale={a['n_sale']}, centroid_source={src}"),
            )

        conn.commit()
        return stats
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(_DEFAULT_DB), help="path to the SQLite DB")
    args = ap.parse_args()

    s = build(Path(args.db))
    print(f"districts rebuilt in {args.db}")
    print(f"  total areas ............. {s['total']}")
    print(f"  with >=1 sale listing ... {s['with_sale']}  (these become 'covered / with structured data')")
    print(f"  centroid from listings .. {s['centroid_from_listings']}")
    print(f"  centroid from voronoi ... {s['centroid_from_voronoi']}")
    print(f"  centroid missing (NULL) . {s['centroid_missing']}")


if __name__ == "__main__":
    main()
