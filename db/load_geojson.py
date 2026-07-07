"""Load a polygon GeoJSON FeatureCollection into a polygon table (`districts` or `zoning_plots`).

`load_csv.py` handles tabular CSVs; polygons arrive as GeoJSON, so this is the companion loader.
In SpatiaLite-fallback mode (the current state) each feature's geometry is stored verbatim as
GeoJSON text in `<table>.geometry_geojson`, plus a computed shoelace polygon centroid in
`centroid_lat` / `centroid_lng` for cheap mapping and haversine work downstream.

Two targets:
  * `districts`     — neighborhood boundary polygons. Provenance from flags. Feature properties
                      describing how a boundary was derived (the `approximate` circle caveat) are
                      preserved into `notes` so downstream knows neighborhood assignment is fuzzy.
  * `zoning_plots`  — OSM landuse polygons used as a stand-in for regulatory zoning. These are
                      UNOFFICIAL: no zone_class / FAR / max_height. The land-use category is taken
                      from the feature's `type` property; every row's `notes` is stamped
                      "UNOFFICIAL OSM landuse, not GAM regulatory zoning". confidence defaults to L.

Usage:
    python db/load_geojson.py data/processed/neighborhoods.geojson --table districts
    python db/load_geojson.py data/processed/zoning.geojson --table zoning_plots
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("load_geojson")

DB_DIR = Path(__file__).resolve().parent
DEFAULT_DB = DB_DIR / "jordan_re.sqlite"
REPORT_DIR = DB_DIR.parent / "data" / "processed"

ZONING_UNOFFICIAL_NOTE = "UNOFFICIAL OSM landuse, not GAM regulatory zoning"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).strip().lower()).strip("_")


def ring_centroid(ring: list[list[float]]) -> tuple[float, float]:
    """Shoelace centroid of a [[lng, lat], ...] ring; falls back to vertex mean for degenerate rings."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if area == 0:
        n = len(ring)
        return sum(p[1] for p in ring) / n, sum(p[0] for p in ring) / n
    area *= 0.5
    return cy / (6 * area), cx / (6 * area)  # (lat, lng)


def exterior_ring(geometry: dict) -> list[list[float]] | None:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    ring = None
    if gtype == "Polygon" and coords:
        ring = coords[0]
    elif gtype == "MultiPolygon" and coords and coords[0]:
        ring = coords[0][0]
    if not ring or len(ring) < 3:  # need at least a triangle for a centroid
        return None
    return ring


def district_row(feat: dict, geom: dict, lat: float, lng: float, prov: dict):
    props = feat.get("properties", {}) or {}
    name = props.get("neighborhood") or props.get("name")
    if not name:
        return None
    keep = ("source", "approximate", "centered_on", "radius_km", "name_ar")
    notes = "; ".join(f"{k}={props[k]}" for k in keep if props.get(k) not in (None, ""))
    return (
        "districts",
        (
            f"district_{slug(name)}", name, name,
            json.dumps(geom, ensure_ascii=False), round(lat, 6), round(lng, 6),
            prov["evidence_category"], prov["language"], prov["source_name"],
            prov["source_url"], prov["capture_date"], prov["collected_by"],
            prov["confidence"], notes,
        ),
    )


def zoning_row(feat: dict, geom: dict, lat: float, lng: float, prov: dict):
    props = feat.get("properties", {}) or {}
    osm_id = props.get("osm_id") or props.get("FID")
    if osm_id is None:
        return None
    land_use = props.get("type") or props.get("landuse")
    caveat = ZONING_UNOFFICIAL_NOTE
    detail = "; ".join(
        f"{k}={props[k]}" for k in ("type", "name", "osm_id") if props.get(k) not in (None, "")
    )
    notes = f"{caveat}; {detail}" if detail else caveat
    return (
        "zoning_plots",
        (
            f"plot_{osm_id}", land_use, None,  # plot_id, land_use, neighborhood(null)
            json.dumps(geom, ensure_ascii=False), round(lat, 6), round(lng, 6),
            prov["evidence_category"], prov["language"],
            props.get("source_name") or prov["source_name"],
            props.get("source_service") or prov["source_url"],
            props.get("capture_date") or prov["capture_date"],
            props.get("collected_by") or prov["collected_by"],
            prov["confidence"], notes,
        ),
    )


SQL = {
    "districts": (
        "INTO districts (district_id, name, neighborhood, geometry_geojson, centroid_lat, "
        "centroid_lng, evidence_category, language, source_name, source_url, capture_date, "
        "collected_by, confidence, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    ),
    "zoning_plots": (
        "INTO zoning_plots (plot_id, land_use, neighborhood, geometry_geojson, centroid_lat, "
        "centroid_lng, evidence_category, language, source_name, source_url, capture_date, "
        "collected_by, confidence, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    ),
}
BUILDERS = {"districts": district_row, "zoning_plots": zoning_row}


def load(geojson_path: Path, db_path: Path, table: str, prov: dict, replace: bool) -> dict:
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    features = data.get("features", [])
    report = {"read": len(features), "inserted": 0, "skipped": 0, "issues": []}
    build = BUILDERS[table]
    sql = ("INSERT OR REPLACE " if replace else "INSERT OR IGNORE ") + SQL[table]

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        for i, feat in enumerate(features):
            geom = feat.get("geometry") or {}
            ring = exterior_ring(geom)
            if ring is None:
                report["issues"].append(f"feature {i}: unsupported/missing geometry")
                continue
            lat, lng = ring_centroid(ring)
            built = build(feat, geom, lat, lng, prov)
            if built is None:
                report["issues"].append(f"feature {i}: missing id/name property")
                continue
            cur = conn.execute(sql, built[1])
            report["inserted" if cur.rowcount else "skipped"] += 1
        conn.commit()
    finally:
        conn.close()
    return report


def write_report(geojson_path: Path, table: str, report: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"load_report_{table}.txt"
    lines = [
        "Jordan RE — GeoJSON load report",
        f"table         : {table}",
        f"source        : {geojson_path}",
        f"generated     : {dt.datetime.now().isoformat(timespec='seconds')}",
        "-" * 60,
        f"features read : {report['read']}",
        f"inserted      : {report['inserted']}",
        f"skipped (dup) : {report['skipped']}",
    ]
    if report["issues"]:
        lines.append("-" * 60)
        lines.append("issues:")
        lines.extend(f"  {x}" for x in report["issues"][:50])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Load a polygon GeoJSON into a polygon table.")
    p.add_argument("geojson", type=Path)
    p.add_argument("--table", choices=("districts", "zoning_plots"), default="districts")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--replace", action="store_true", help="upsert instead of skipping existing ids")
    p.add_argument("--source-name", default="OpenStreetMap")
    p.add_argument("--source-url", default="https://overpass-api.de/api")
    p.add_argument("--capture-date", default="2026-07-07")
    p.add_argument("--collected-by", default="gis-specialist")
    p.add_argument("--evidence-category", default="gis")
    p.add_argument("--language", default="en")
    p.add_argument("--confidence", default=None, help="defaults: districts=M, zoning_plots=L")
    args = p.parse_args()

    if not args.geojson.exists():
        p.error(f"GeoJSON not found: {args.geojson}")
    if not args.db.exists():
        p.error(f"database not found: {args.db} (run init_db.py first)")

    confidence = args.confidence or ("L" if args.table == "zoning_plots" else "M")
    prov = {
        "source_name": args.source_name,
        "source_url": args.source_url,
        "capture_date": args.capture_date,
        "collected_by": args.collected_by,
        "evidence_category": args.evidence_category,
        "language": args.language,
        "confidence": confidence,
    }
    report = load(args.geojson, args.db, args.table, prov, args.replace)
    out = write_report(args.geojson, args.table, report)
    log.info(
        "%s: %d/%d inserted, %d skipped. Report: %s",
        args.table, report["inserted"], report["read"], report["skipped"], out,
    )


if __name__ == "__main__":
    main()
