"""Generic, schema-driven CSV loader for the Jordan Real Estate database.

Ingests any CSV whose header matches a known table and validates every row against the
constraints declared in db/schema.sql. The schema is the single source of truth: enum sets,
required columns, numeric types and NOT-NULL rules are all read back from the live database,
never re-declared here.

Validation rules (documented in docs/db-contract.md):
  * Provenance is the product. source_name / source_url / capture_date must be present and
    must NOT be blank or 'unknown' -> otherwise the row is rejected.
  * Required columns (NOT NULL, no default: e.g. neighborhood, discriminators) blank -> reject.
  * Enum columns: 'unknown' is the ONLY legal null-object. A blank enum value -> reject
    (the collector must write 'unknown', never leave it empty). An out-of-enum value -> reject.
  * Numeric / date columns: 'unknown' or blank -> stored as NULL; a malformed value -> reject.
  * Derived / generated columns (e.g. price_per_m2) present in the CSV are ignored on insert.
  * Duplicate primary keys are skipped and reported (use --replace to upsert instead).

A per-table load report is written to data/processed/load_report_<table>.txt.

Usage:
    python db/load_csv.py path/to/listings_20260708.csv
    python db/load_csv.py path/to/file.csv --table listings
    python db/load_csv.py path/to/file.csv --db db/jordan_re.sqlite --replace
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("load_csv")

DB_DIR = Path(__file__).resolve().parent
DEFAULT_DB = DB_DIR / "jordan_re.sqlite"
REPORT_DIR = DB_DIR.parent / "data" / "processed"

PROVENANCE_STRICT = ("source_name", "source_url", "capture_date")
DATE_COLUMNS = ("capture_date", "listing_date", "published_date", "launch_date", "computed_date")


@dataclass
class ColumnSpec:
    name: str
    type: str
    notnull: bool
    has_default: bool
    is_pk_alias: bool
    insertable: bool  # False for generated/hidden columns
    enum: set[str] | None = None


@dataclass
class TableSpec:
    name: str
    columns: dict[str, ColumnSpec]

    @property
    def required(self) -> set[str]:
        return {
            c.name
            for c in self.columns.values()
            if c.notnull and not c.has_default and not c.is_pk_alias and c.insertable
        }

    @property
    def insertable_names(self) -> set[str]:
        return {c.name for c in self.columns.values() if c.insertable}


@dataclass
class LoadReport:
    table: str
    csv_path: str
    total: int = 0
    inserted: int = 0
    updated: int = 0
    duplicates: int = 0
    rejected: int = 0
    ignored_columns: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            "Jordan RE — CSV load report",
            f"table         : {self.table}",
            f"source csv    : {self.csv_path}",
            f"generated     : {dt.datetime.now().isoformat(timespec='seconds')}",
            "-" * 60,
            f"rows read     : {self.total}",
            f"inserted      : {self.inserted}",
            f"updated       : {self.updated} (upsert: enrichable attrs merged into existing rows)",
            f"duplicates    : {self.duplicates} (existing primary keys, skipped)",
            f"rejected      : {self.rejected}",
        ]
        if self.ignored_columns:
            lines.append(f"ignored cols  : {', '.join(self.ignored_columns)}")
        if self.missing_required:
            lines.append(f"MISSING REQUIRED COLUMNS (file not loaded): {', '.join(self.missing_required)}")
        if self.reasons:
            lines.append("-" * 60)
            lines.append("rejections / notes:")
            lines.extend(f"  {r}" for r in self.reasons)
        return "\n".join(lines) + "\n"


def parse_enums(ddl: str) -> dict[str, set[str]]:
    """Extract {column: {allowed values}} from CHECK(col IN ('a','b',...)) clauses in a table DDL."""
    enums: dict[str, set[str]] = {}
    pattern = re.compile(r'CHECK\s*\(\s*"?(\w+)"?\s+IN\s*\(([^)]*)\)\s*\)', re.IGNORECASE)
    for col, raw in pattern.findall(ddl):
        values = {v.strip().strip("'") for v in raw.split(",") if v.strip()}
        enums[col] = values
    return enums


def load_table_spec(conn: sqlite3.Connection, table: str) -> TableSpec:
    ddl_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not ddl_row:
        raise ValueError(f"unknown table: {table}")
    enums = parse_enums(ddl_row[0])

    columns: dict[str, ColumnSpec] = {}
    for cid, name, ctype, notnull, dflt, pk, hidden in conn.execute(
        f"PRAGMA table_xinfo({table})"
    ).fetchall():
        is_pk_alias = bool(pk) and ctype.upper() == "INTEGER"
        columns[name] = ColumnSpec(
            name=name,
            type=ctype.upper(),
            notnull=bool(notnull),
            has_default=dflt is not None,
            is_pk_alias=is_pk_alias,
            insertable=(hidden == 0),
            enum=enums.get(name),
        )
    return TableSpec(name=table, columns=columns)


def all_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "AND name NOT IN ('schema_meta') ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def detect_table(conn: sqlite3.Connection, header: list[str]) -> str | None:
    """Pick the table whose columns best cover the CSV header and all required columns."""
    header_set = {h.strip() for h in header}
    best: tuple[int, str] | None = None
    for table in all_tables(conn):
        spec = load_table_spec(conn, table)
        cols = spec.insertable_names
        if not spec.required.issubset(header_set):
            continue
        known = header_set & cols
        unknown = header_set - cols
        # Prefer the table that matches the most header columns with the fewest strays.
        score = len(known) - len(unknown)
        if known and (best is None or score > best[0]):
            best = (score, table)
    return best[1] if best else None


def _is_numeric(col: ColumnSpec) -> bool:
    return col.type in ("INTEGER", "REAL") and not col.is_pk_alias


def _canon_enum(value: str, allowed: set[str]) -> str | None:
    if value in allowed:
        return value
    lower = {a.lower(): a for a in allowed}
    return lower.get(value.lower())


def validate_row(
    row: dict[str, str], spec: TableSpec, header_cols: list[str], line_no: int
) -> tuple[dict[str, object] | None, str | None]:
    """Return (values-to-insert, None) if valid, else (None, reason)."""
    out: dict[str, object] = {}
    for col_name in header_cols:
        col = spec.columns.get(col_name)
        if col is None or not col.insertable:
            continue  # unknown or generated column — ignored on insert
        raw = (row.get(col_name) or "").strip()
        low = raw.lower()

        if col_name in PROVENANCE_STRICT:
            if raw == "" or low == "unknown":
                return None, f"line {line_no}: missing provenance '{col_name}' (blank/unknown)"

        if raw == "":
            if col_name in spec.required or col.enum is not None:
                return None, f"line {line_no}: required/enum column '{col_name}' is blank"
            out[col_name] = None
            continue

        if col.enum is not None:
            canon = _canon_enum(raw, col.enum)
            if canon is None:
                return None, (
                    f"line {line_no}: illegal value '{raw}' for '{col_name}' "
                    f"(allowed: {', '.join(sorted(col.enum))})"
                )
            out[col_name] = canon
            continue

        if _is_numeric(col):
            if low == "unknown":
                out[col_name] = None
                continue
            try:
                out[col_name] = int(raw) if col.type == "INTEGER" else float(raw)
            except ValueError:
                return None, f"line {line_no}: non-numeric value '{raw}' for '{col_name}'"
            continue

        if col_name in DATE_COLUMNS:
            if low == "unknown":
                out[col_name] = None
                continue
            try:
                dt.date.fromisoformat(raw)
            except ValueError:
                return None, f"line {line_no}: bad date '{raw}' for '{col_name}' (want YYYY-MM-DD)"
            out[col_name] = raw
            continue

        out[col_name] = raw

    # Guard: every required column must actually be present in the header.
    for req in spec.required:
        if req not in header_cols:
            return None, f"line {line_no}: required column '{req}' absent from CSV header"
    return out, None


# Per-table upsert policy for enrichment reloads (same primary key, improved attribute columns).
# `enrich`      : take the incoming value UNLESS it is 'unknown'/null — never overwrite a real
#                 value with 'unknown', but a real incoming value supersedes (enrichment/correction).
# `fill_if_null`: only fill when the existing value is null — never overwrite a real price/area/coord.
# Everything else (provenance, ids, description) is preserved unchanged on conflict.
UPSERT_POLICY: dict[str, dict[str, object]] = {
    "listings": {
        "conflict": "listing_id",
        # attribute columns a detail-enrichment pass improves; take incoming unless it is an
        # unknown-sentinel (per-column tokens below), never overwriting a real value with unknown.
        "enrich": [
            "view", "parking", "finish_quality", "furnishing",
            "floor_level", "total_floors", "building_age_years", "bathrooms",
            "seller_type", "elevator",
        ],
        # elevator's unknown sentinel is 'u' (plus 'unknown'); all others use 'unknown'.
        "unknown_tokens": {"elevator": ["u", "unknown"]},
        # free-text columns where the richer (longer) text wins — never shrinks existing text.
        "enrich_longest_text": ["description_raw"],
        # fill only when the existing value is null; never overwrite a real price/area/coord.
        "fill_if_null": ["price_jd", "area_m2", "lat", "lng"],
    },
}


def build_upsert_sql(table: str, insert_cols: list[str], spec: TableSpec, policy: dict) -> str:
    col_list = ", ".join(f'"{c}"' for c in insert_cols)
    placeholders = ", ".join("?" for _ in insert_cols)
    tokens_map: dict = policy.get("unknown_tokens", {})
    sets: list[str] = []
    for c in policy["enrich"]:
        if c not in insert_cols:
            continue
        if spec.columns[c].type in ("INTEGER", "REAL"):
            sets.append(f'"{c}" = COALESCE(excluded."{c}", "{table}"."{c}")')
        else:
            tokens = tokens_map.get(c, ["unknown"])
            in_list = ", ".join(f"'{t}'" for t in tokens)
            sets.append(
                f'"{c}" = COALESCE(CASE WHEN excluded."{c}" IN ({in_list}) THEN NULL '
                f'ELSE excluded."{c}" END, "{table}"."{c}")'
            )
    for c in policy.get("enrich_longest_text", []):
        if c in insert_cols:
            sets.append(
                f'"{c}" = CASE WHEN length(COALESCE(excluded."{c}", \'\')) > '
                f'length(COALESCE("{table}"."{c}", \'\')) THEN excluded."{c}" '
                f'ELSE "{table}"."{c}" END'
            )
    for c in policy["fill_if_null"]:
        if c in insert_cols:
            sets.append(f'"{c}" = COALESCE("{table}"."{c}", excluded."{c}")')
    return (
        f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
        f'ON CONFLICT("{policy["conflict"]}") DO UPDATE SET ' + ", ".join(sets)
    )


def load_csv(
    csv_path: Path, db_path: Path, table: str | None, replace: bool, upsert: bool = False
) -> LoadReport:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            header = [h.strip() for h in (reader.fieldnames or [])]
            if not header:
                raise ValueError("CSV has no header row")

            resolved = table or detect_table(conn, header)
            if resolved is None:
                raise ValueError(
                    "could not match CSV header to any known table; pass --table explicitly"
                )
            spec = load_table_spec(conn, resolved)
            report = LoadReport(table=resolved, csv_path=str(csv_path))

            missing = sorted(spec.required - set(header))
            if missing:
                report.missing_required = missing
                log.error("File %s is missing required columns for %s: %s", csv_path, resolved, missing)
                return report

            report.ignored_columns = sorted(set(header) - spec.insertable_names)
            insert_cols = [c for c in header if c in spec.insertable_names]

            if upsert:
                policy = UPSERT_POLICY.get(resolved)
                if policy is None:
                    raise ValueError(f"--upsert is not supported for table '{resolved}'")
                sql = build_upsert_sql(resolved, insert_cols, spec, policy)
            else:
                verb = "INSERT OR REPLACE" if replace else "INSERT"
                placeholders = ", ".join("?" for _ in insert_cols)
                col_list = ", ".join(f'"{c}"' for c in insert_cols)
                sql = f'{verb} INTO "{resolved}" ({col_list}) VALUES ({placeholders})'

            before = conn.execute(f'SELECT count(*) FROM "{resolved}"').fetchone()[0]
            executed = 0
            for line_no, row in enumerate(reader, start=2):  # line 1 is the header
                report.total += 1
                values, reason = validate_row(row, spec, insert_cols, line_no)
                if reason is not None:
                    report.rejected += 1
                    report.reasons.append(reason)
                    continue
                try:
                    conn.execute(sql, [values.get(c) for c in insert_cols])
                    executed += 1
                except sqlite3.IntegrityError as exc:
                    msg = str(exc).lower()
                    if not upsert and ("unique" in msg or "primary key" in msg):
                        report.duplicates += 1
                        report.reasons.append(f"line {line_no}: duplicate key skipped ({exc})")
                    else:
                        report.rejected += 1
                        report.reasons.append(f"line {line_no}: integrity error ({exc})")
            conn.commit()

            after = conn.execute(f'SELECT count(*) FROM "{resolved}"').fetchone()[0]
            report.inserted = after - before
            report.updated = executed - report.inserted if upsert else 0
        return report
    finally:
        conn.close()


def write_report(report: LoadReport) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"load_report_{report.table}.txt"
    out_path.write_text(report.render(), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a CSV into the Jordan Real Estate database.")
    parser.add_argument("csv", type=Path, help="path to the CSV file")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="target sqlite file")
    parser.add_argument("--table", help="target table (auto-detected from header if omitted)")
    parser.add_argument("--replace", action="store_true", help="replace whole rows on duplicate PK")
    parser.add_argument(
        "--upsert", action="store_true",
        help="merge enrichable columns into existing rows on PK conflict (listings only)",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        parser.error(f"CSV not found: {args.csv}")
    if not args.db.exists():
        parser.error(f"database not found: {args.db} (run init_db.py first)")

    report = load_csv(args.csv, args.db, args.table, args.replace, args.upsert)
    out_path = write_report(report)
    log.info(
        "Loaded %s: %d inserted, %d updated, %d duplicates, %d rejected (of %d). Report: %s",
        report.table, report.inserted, report.updated, report.duplicates, report.rejected,
        report.total, out_path,
    )
    if report.missing_required:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
