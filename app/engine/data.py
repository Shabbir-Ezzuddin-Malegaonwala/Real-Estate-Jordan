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
            price_index=_index_from_sqlite(conn),
            geocontext=[_geocontext_from(dict(r))
                        for r in _table(conn, "neighborhood_geocontext")],
            as_of=as_of or date.today(),
        )
        return bundle
    finally:
        conn.close()


def _table(conn: sqlite3.Connection, name: str) -> list[sqlite3.Row]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    if not exists:
        return []
    return conn.execute(f"SELECT * FROM {name}").fetchall()


def _index_from_sqlite(conn: sqlite3.Connection) -> PriceIndex:
    idx = PriceIndex()
    rows = _table(conn, "macro_series")
    for indicator, canonical in ((_CBJ_APARTMENT, _CANONICAL_INDEX),
                                 (_CBJ_RESIDENTIAL, _CANONICAL_INDEX)):
        series = {r["period"].strip(): _num(r["value"])
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
