"""Create and initialise the Jordan Real Estate SQLite database.

Runs db/schema.sql against db/jordan_re.sqlite. Idempotent: every DDL statement uses
IF NOT EXISTS, so re-running is safe and never destroys data.

SpatiaLite is optional. If mod_spatialite loads, spatial metadata is initialised and
schema_meta.spatial_enabled is set to 1. If it is unavailable (common on Windows), we log
a clear warning and continue in fallback mode: geometry is kept as GeoJSON text plus
centroid lat/lng, and distance work is done with plain haversine downstream. We never crash.

Usage:
    python db/init_db.py            # create/upgrade db/jordan_re.sqlite
    python db/init_db.py --db PATH  # target a different file
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("init_db")

DB_DIR = Path(__file__).resolve().parent
DEFAULT_DB = DB_DIR / "jordan_re.sqlite"
SCHEMA_FILE = DB_DIR / "schema.sql"

SPATIALITE_CANDIDATES = ("mod_spatialite", "mod_spatialite.dll", "libspatialite", "libspatialite.dll")


def try_load_spatialite(conn: sqlite3.Connection) -> bool:
    """Attempt to load mod_spatialite. Return True on success, False otherwise. Never raises."""
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        log.warning("This Python sqlite3 build has no extension-loading support.")
        return False
    except sqlite3.OperationalError as exc:
        log.warning("Could not enable extension loading: %s", exc)
        return False

    for name in SPATIALITE_CANDIDATES:
        try:
            conn.load_extension(name)
            log.info("SpatiaLite loaded via '%s'.", name)
            return True
        except sqlite3.OperationalError:
            continue
    return False


def init_spatial_metadata(conn: sqlite3.Connection) -> None:
    """Initialise SpatiaLite spatial metadata once (guarded; safe to call repeatedly)."""
    already = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='spatial_ref_sys'"
    ).fetchone()
    if already:
        return
    conn.execute("SELECT InitSpatialMetaData(1)")


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO schema_meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def init_db(db_path: Path) -> None:
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"schema file not found: {SCHEMA_FILE}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")

    conn = sqlite3.connect(db_path)
    try:
        spatial = try_load_spatialite(conn)
        if not spatial:
            log.warning(
                "SpatiaLite unavailable — running in FALLBACK mode. Polygons stored as GeoJSON "
                "text; point tables use plain REAL lat/lng; distances via haversine downstream."
            )

        conn.executescript(schema_sql)

        if spatial:
            try:
                init_spatial_metadata(conn)
            except sqlite3.OperationalError as exc:
                log.warning("Spatial metadata init skipped: %s", exc)
                spatial = False

        set_meta(conn, "schema_version", "1")
        set_meta(conn, "spatial_enabled", "1" if spatial else "0")
        conn.commit()

        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "AND name NOT LIKE 'idx_%' ORDER BY name"
            ).fetchall()
        ]
        log.info("Database ready at %s", db_path)
        log.info("Spatial mode: %s", "SpatiaLite" if spatial else "fallback (GeoJSON + haversine)")
        log.info("Tables (%d): %s", len(tables), ", ".join(tables))
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialise the Jordan Real Estate database.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="target sqlite file path")
    args = parser.parse_args()
    init_db(args.db)


if __name__ == "__main__":
    main()
