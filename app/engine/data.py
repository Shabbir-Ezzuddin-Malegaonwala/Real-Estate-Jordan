"""DataBundle — the engine's read model over collected CSVs (fixtures or a DB export).

The engine never touches the database directly. A caller (API/service) loads the
relevant rows into a DataBundle and hands it to `pipeline.recommend`. This keeps
business logic in the engine and I/O at the edge.
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .models import Listing, _num, _int

# CBJ publishes many series under long human-readable names; the engine only needs the
# apartment (and residential fallback) buildings index, mapped to a canonical key.
_CBJ_APARTMENT = "Real estate price index - Buildings - Apartment"
_CBJ_RESIDENTIAL = "Real estate price index - Buildings - Residential"
_CANONICAL_INDEX = "cbj_repi_apartment"


@dataclass
class PriceIndex:
    """CBJ-style quarterly index, keyed by indicator then 'YYYY-QN'."""

    series: dict[str, dict[str, float]] = field(default_factory=dict)
    source: dict[str, str] = field(default_factory=dict)

    def value_at(self, quarter: str, indicator: str = "cbj_repi_apartment") -> Optional[float]:
        return self.series.get(indicator, {}).get(quarter)

    def latest(self, indicator: str = "cbj_repi_apartment") -> Optional[tuple[str, float]]:
        s = self.series.get(indicator, {})
        if not s:
            return None
        q = max(s)
        return q, s[q]

    def has(self, indicator: str = "cbj_repi_apartment") -> bool:
        return bool(self.series.get(indicator))


@dataclass
class CostBenchmark:
    spec_class: str
    low: Optional[float]
    high: Optional[float]
    year: Optional[int]
    source_name: str
    source_url: str
    capture_date: Optional[str]
    confidence: str

    @property
    def midpoint(self) -> Optional[float]:
        if self.low is not None and self.high is not None:
            return (self.low + self.high) / 2
        return self.low if self.low is not None else self.high


@dataclass
class ConstructionCost:
    """Official DoS building-licence construction cost (JD/m2), recent-quarter mean by authority.

    This is the licensing authority's FILED administrative estimate — a conservative construction
    FLOOR that understates full turnkey market build. A residual land value derived from it is
    therefore an UPPER bound (real build cost is higher -> real land ceiling is lower)."""

    amman_jd_m2: Optional[float]      # Greater Amman Municipality recent-12 new-build mean
    kingdom_jd_m2: Optional[float]    # Kingdom-wide recent-12 new-build mean
    quarters: int
    latest_period: Optional[str]
    source_name: str
    source_url: str
    capture_date: Optional[str]
    caveat: str

    def for_area(self, is_amman: bool) -> Optional[float]:
        v = self.amman_jd_m2 if is_amman else self.kingdom_jd_m2
        return v if v is not None else (self.kingdom_jd_m2 or self.amman_jd_m2)

    def source(self) -> dict:
        return {"name": self.source_name, "url": self.source_url,
                "capture_date": self.capture_date or "unknown"}


@dataclass
class EvidenceItem:
    """Future-signal row (infrastructure / policy / market news)."""

    evidence_id: str
    type: str
    title: str
    summary: str
    impact_area: str
    expected_year: Optional[int]
    expected_effect: str
    published_date: Optional[str]
    source_name: str
    source_url: str
    capture_date: Optional[str]
    confidence: str


@dataclass
class NeighborhoodGeoContext:
    """Median terrain/density/night-light summary for one submarket (friend-sourced).

    NON-PRICED context: elevation does not correlate with price (MASTER-PLAN decision).
    Used only to build the "Neighborhood spatial context" evidence chip.
    """

    neighborhood: str
    median_elevation_m: Optional[float]
    elevation_rank: Optional[int]
    median_population_density: Optional[float]
    median_nightlight: Optional[float]
    dominant_aspect: str
    context: str
    source_name: str
    source_url: str
    capture_date: Optional[str]
    confidence: str


@dataclass
class Project:
    project_id: str
    name: str
    builder_tier: str
    neighborhood: str
    status: str
    launch_price_jd_m2: Optional[float]
    lat: Optional[float]
    lng: Optional[float]
    source_name: str
    source_url: str
    capture_date: Optional[str]
    confidence: str


@dataclass
class DataBundle:
    listings: list[Listing] = field(default_factory=list)
    cost_benchmarks: list[CostBenchmark] = field(default_factory=list)
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    price_index: PriceIndex = field(default_factory=PriceIndex)
    geocontext: list[NeighborhoodGeoContext] = field(default_factory=list)
    construction_cost: Optional["ConstructionCost"] = None
    as_of: date = field(default_factory=date.today)

    def geocontext_for(self, neighborhood: str) -> Optional[NeighborhoodGeoContext]:
        n = (neighborhood or "").strip().lower()
        return next((g for g in self.geocontext if g.neighborhood.strip().lower() == n), None)

    def sales(self) -> list[Listing]:
        return [l for l in self.listings if l.listing_type == "sale" and l.price_per_m2]

    def rentals(self) -> list[Listing]:
        return [l for l in self.listings if l.listing_type == "rent" and l.price_per_m2]

    def cost_for(self, spec_class: str) -> Optional[CostBenchmark]:
        want = (spec_class or "").lower()
        exact = [c for c in self.cost_benchmarks if c.spec_class == want]
        if exact:
            return exact[0]
        for fallback in ("standard", "high", "basic"):
            hit = [c for c in self.cost_benchmarks if c.spec_class == fallback]
            if hit:
                return hit[0]
        return self.cost_benchmarks[0] if self.cost_benchmarks else None


def _read(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_listings(path: str) -> list[Listing]:
    return [Listing.from_row(r) for r in _read(path)]


def load_cost_benchmarks(path: str) -> list[CostBenchmark]:
    out = []
    for r in _read(path):
        out.append(CostBenchmark(
            spec_class=(r.get("spec_class") or "unknown").strip().lower(),
            low=_num(r.get("cost_jd_per_m2_low")),
            high=_num(r.get("cost_jd_per_m2_high")),
            year=_int(r.get("year")),
            source_name=r.get("source_name", "unknown"),
            source_url=r.get("source_url", "unknown"),
            capture_date=(r.get("capture_date") or "").strip() or None,
            confidence=(r.get("confidence") or "unknown").strip(),
        ))
    return out


def load_evidence_items(path: str) -> list[EvidenceItem]:
    out = []
    for r in _read(path):
        out.append(EvidenceItem(
            evidence_id=r.get("evidence_id", ""),
            type=(r.get("type") or "unknown").strip().lower(),
            title=r.get("title", ""),
            summary=r.get("summary_2_lines", ""),
            impact_area=(r.get("impact_area") or "").strip(),
            expected_year=_int(r.get("expected_year")),
            expected_effect=(r.get("expected_effect") or "unknown").strip(),
            published_date=(r.get("published_date") or "").strip() or None,
            source_name=r.get("source_name", "unknown"),
            source_url=r.get("source_url", "unknown"),
            capture_date=(r.get("capture_date") or "").strip() or None,
            confidence=(r.get("confidence") or "unknown").strip(),
        ))
    return out


def load_projects(path: str) -> list[Project]:
    out = []
    for r in _read(path):
        out.append(Project(
            project_id=r.get("project_id", ""),
            name=r.get("name", ""),
            builder_tier=(r.get("builder_tier") or "unknown").strip().lower(),
            neighborhood=(r.get("neighborhood") or "").strip(),
            status=(r.get("status") or "unknown").strip().lower(),
            launch_price_jd_m2=_num(r.get("launch_price_jd_m2")),
            lat=_num(r.get("lat")),
            lng=_num(r.get("lng")),
            source_name=r.get("source_name", "unknown"),
            source_url=r.get("source_url", "unknown"),
            capture_date=(r.get("capture_date") or "").strip() or None,
            confidence=(r.get("confidence") or "unknown").strip(),
        ))
    return out


def load_bundle_from_sqlite(db_path: str, as_of: Optional[date] = None) -> DataBundle:
    """Build a DataBundle from the live SQLite DB (docs/db-contract.md tables).

    Missing/empty tables (cost_benchmarks, projects, evidence_items still being collected)
    degrade to empty lists — the engine handles their absence and surfaces it as a caveat.

    Retained for the pilot/reference DB (db/jordan_re.sqlite) used by emit_sample.py and the
    pipeline tests. Production (the API) reads Postgres via load_bundle_from_postgres().
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        listings = [Listing.from_row(dict(r)) for r in _table(conn, "listings")]
        bundle = DataBundle(
            listings=listings,
            cost_benchmarks=[_cost_from(dict(r)) for r in _table(conn, "cost_benchmarks")],
            evidence_items=[_evidence_from(dict(r)) for r in _table(conn, "evidence_items")],
            projects=[_project_from(dict(r)) for r in _table(conn, "projects")],
            price_index=_build_index([dict(r) for r in _table(conn, "macro_series")]),
            geocontext=[_geocontext_from(dict(r))
                        for r in _table(conn, "neighborhood_geocontext")],
            construction_cost=_construction_cost_from_sqlite(conn),
            as_of=as_of or date.today(),
        )
        return bundle
    finally:
        conn.close()


def load_bundle_from_postgres(dsn: str, as_of: Optional[date] = None) -> DataBundle:
    """Build a DataBundle from the live Postgres DB (Neon). Same table contract as the
    SQLite loader; the whole read model is pulled into memory once at API startup.

    Missing/empty tables degrade to empty lists — the engine surfaces their absence as a caveat.
    """
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        listings = [Listing.from_row(r) for r in _pg_table(conn, "listings")]
        return DataBundle(
            listings=listings,
            cost_benchmarks=[_cost_from(r) for r in _pg_table(conn, "cost_benchmarks")],
            evidence_items=[_evidence_from(r) for r in _pg_table(conn, "evidence_items")],
            projects=[_project_from(r) for r in _pg_table(conn, "projects")],
            price_index=_build_index(_pg_table(conn, "macro_series")),
            geocontext=[_geocontext_from(r)
                        for r in _pg_table(conn, "neighborhood_geocontext")],
            construction_cost=_construction_cost_from_postgres(conn),
            as_of=as_of or date.today(),
        )


def _pg_table(conn, name: str) -> list[dict]:
    """All rows of a Postgres table as dicts, or [] if the table does not exist."""
    reg = conn.execute("SELECT to_regclass(%s) AS r", (f"public.{name}",)).fetchone()
    if not reg or reg["r"] is None:
        return []
    return conn.execute(f'SELECT * FROM "{name}"').fetchall()


def _construction_cost_from_postgres(conn) -> Optional[ConstructionCost]:
    """Recent-12-quarter mean of DoS new-build filed cost/m2, by licensing authority (Postgres)."""
    reg = conn.execute("SELECT to_regclass('public.dos_building_cost') AS r").fetchone()
    if not reg or reg["r"] is None:
        return None

    def recent_mean(authority: str):
        rows = conn.execute(
            "SELECT year, quarter, cost_jd_per_m2, source_name, source_url, capture_date "
            "FROM dos_building_cost WHERE authority=%s AND license_type='new' "
            "AND building_type='all' AND cost_jd_per_m2 IS NOT NULL "
            "ORDER BY year DESC, quarter DESC LIMIT 12", (authority,)).fetchall()
        vals = [r["cost_jd_per_m2"] for r in rows]
        if not vals:
            return None, None, None
        return sum(vals) / len(vals), f"{rows[0]['year']}-{rows[0]['quarter']}", rows[0]

    amman, amman_period, a_row = recent_mean("Greater Amman Municipality")
    kingdom, kingdom_period, k_row = recent_mean("Kingdom")
    if amman is None and kingdom is None:
        return None
    ref = a_row or k_row
    return ConstructionCost(
        amman_jd_m2=round(amman, 1) if amman is not None else None,
        kingdom_jd_m2=round(kingdom, 1) if kingdom is not None else None,
        quarters=12, latest_period=amman_period or kingdom_period,
        source_name=ref["source_name"], source_url=ref["source_url"],
        capture_date=ref["capture_date"],
        caveat="DoS filed-licence administrative estimate - a conservative construction-cost FLOOR "
               "that understates full turnkey build; residual land value derived from it is an "
               "UPPER bound.")


def _construction_cost_from_sqlite(conn: sqlite3.Connection) -> Optional[ConstructionCost]:
    """Recent-12-quarter mean of DoS new-build filed cost/m2, by licensing authority."""
    if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dos_building_cost'"
    ).fetchone():
        return None

    def recent_mean(authority: str):
        rows = conn.execute(
            "SELECT year, quarter, cost_jd_per_m2, source_name, source_url, capture_date "
            "FROM dos_building_cost WHERE authority=? AND license_type='new' "
            "AND building_type='all' AND cost_jd_per_m2 IS NOT NULL "
            "ORDER BY year DESC, quarter DESC LIMIT 12", (authority,)).fetchall()
        vals = [r["cost_jd_per_m2"] for r in rows]
        if not vals:
            return None, None, None
        return sum(vals) / len(vals), f"{rows[0]['year']}-{rows[0]['quarter']}", rows[0]

    amman, amman_period, a_row = recent_mean("Greater Amman Municipality")
    kingdom, kingdom_period, k_row = recent_mean("Kingdom")
    if amman is None and kingdom is None:
        return None
    ref = a_row or k_row
    return ConstructionCost(
        amman_jd_m2=round(amman, 1) if amman is not None else None,
        kingdom_jd_m2=round(kingdom, 1) if kingdom is not None else None,
        quarters=12, latest_period=amman_period or kingdom_period,
        source_name=ref["source_name"], source_url=ref["source_url"],
        capture_date=ref["capture_date"],
        caveat="DoS filed-licence administrative estimate - a conservative construction-cost FLOOR "
               "that understates full turnkey build; residual land value derived from it is an "
               "UPPER bound.")


def _table(conn: sqlite3.Connection, name: str) -> list[sqlite3.Row]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    if not exists:
        return []
    return conn.execute(f"SELECT * FROM {name}").fetchall()


def _build_index(rows: list[dict]) -> PriceIndex:
    """Build the CBJ price index from macro_series rows (dicts). Driver-agnostic:
    works for both the SQLite and Postgres loaders."""
    idx = PriceIndex()
    for indicator, canonical in ((_CBJ_APARTMENT, _CANONICAL_INDEX),
                                 (_CBJ_RESIDENTIAL, _CANONICAL_INDEX)):
        series = {str(r["period"]).strip(): _num(r["value"])
                  for r in rows if r["indicator"] == indicator and _num(r["value"]) is not None}
        if series and canonical not in idx.series:
            idx.series[canonical] = series
            sample = next(r for r in rows if r["indicator"] == indicator)
            idx.source = {"name": sample["source_name"], "url": sample["source_url"],
                          "capture_date": (sample["capture_date"] or "unknown")}
    return idx


def _cost_from(r: dict) -> "CostBenchmark":
    return CostBenchmark(
        spec_class=(r.get("spec_class") or "unknown").strip().lower(),
        low=_num(r.get("cost_jd_per_m2_low")), high=_num(r.get("cost_jd_per_m2_high")),
        year=_int(r.get("year")), source_name=r.get("source_name", "unknown"),
        source_url=r.get("source_url", "unknown"),
        capture_date=(r.get("capture_date") or None), confidence=(r.get("confidence") or "unknown"))


def _evidence_from(r: dict) -> "EvidenceItem":
    return EvidenceItem(
        evidence_id=r.get("evidence_id", ""), type=(r.get("type") or "unknown").strip().lower(),
        title=r.get("title", ""), summary=r.get("summary_2_lines", ""),
        impact_area=(r.get("impact_area") or "").strip(), expected_year=_int(r.get("expected_year")),
        expected_effect=(r.get("expected_effect") or "unknown").strip(),
        published_date=(r.get("published_date") or None), source_name=r.get("source_name", "unknown"),
        source_url=r.get("source_url", "unknown"), capture_date=(r.get("capture_date") or None),
        confidence=(r.get("confidence") or "unknown"))


def _project_from(r: dict) -> "Project":
    return Project(
        project_id=r.get("project_id", ""), name=r.get("name", ""),
        builder_tier=(r.get("builder_tier") or "unknown").strip().lower(),
        neighborhood=(r.get("neighborhood") or "").strip(),
        status=(r.get("status") or "unknown").strip().lower(),
        launch_price_jd_m2=_num(r.get("launch_price_jd_m2")), lat=_num(r.get("lat")),
        lng=_num(r.get("lng")), source_name=r.get("source_name", "unknown"),
        source_url=r.get("source_url", "unknown"), capture_date=(r.get("capture_date") or None),
        confidence=(r.get("confidence") or "unknown"))


def _geocontext_from(r: dict) -> "NeighborhoodGeoContext":
    return NeighborhoodGeoContext(
        neighborhood=(r.get("neighborhood") or "").strip(),
        median_elevation_m=_num(r.get("median_elevation_m")),
        elevation_rank=_int(r.get("elevation_rank")),
        median_population_density=_num(r.get("median_population_density")),
        median_nightlight=_num(r.get("median_nightlight")),
        dominant_aspect=(r.get("dominant_aspect") or "unknown").strip(),
        context=(r.get("context") or "").strip(),
        source_name=r.get("source_name", "unknown"),
        source_url=r.get("source_url", "unknown"),
        capture_date=(r.get("capture_date") or None),
        confidence=(r.get("confidence") or "unknown"))


def load_price_index(path: str) -> PriceIndex:
    idx = PriceIndex()
    for r in _read(path):
        ind = (r.get("indicator") or "").strip()
        period = (r.get("period") or "").strip()
        val = _num(r.get("value"))
        if not ind or not period or val is None:
            continue
        idx.series.setdefault(ind, {})[period] = val
        if not idx.source:
            idx.source = {
                "name": r.get("source_name", "Central Bank of Jordan"),
                "url": r.get("source_url", "unknown"),
                "capture_date": (r.get("capture_date") or "").strip() or "unknown",
            }
    return idx
