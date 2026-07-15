"""FastAPI app exposing the Decision Engine for on-demand launch-price recommendations.

Startup loads the SQLite bundle once into memory; each /recommend builds an engine
Subject from the request and returns engine.recommend(...) verbatim. All pricing math
stays in app.engine — this module only validates input and serialises output.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from statistics import median
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.engine import builder, monitoring, opportunity, recommend, scenario
from app.engine.config import MIN_PLAUSIBLE_SALE_PPM2
from app.engine.data import DataBundle, load_bundle_from_sqlite
from app.engine.models import Subject
from app.engine.opportunity import OPPORTUNITY_WEIGHTS, READINESS_WEIGHTS

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Production DB is the consolidated ENRICHED build (jordan_re_new.sqlite): ~52.6k listings PLUS
# real cost benchmarks + DoS building cost (cost-approach floor), competing projects, evidence
# items (future signals), a price index, area yields, land prices and market intelligence — all
# empty in the old national build. Override with JORDAN_RE_DB.
_DB_PATH = os.environ.get("JORDAN_RE_DB", str(_REPO_ROOT / "db" / "jordan_re_new.sqlite"))

# The engine's human text uses typographic/math symbols (JD/m², →, ×, ≤, ≈, en/em-dash). Those are
# valid UTF-8 on the wire, but a consumer that decodes the body as latin-1 (no charset was declared)
# turns them into mojibake (Â², Ã—, â†'). Normalising to plain ASCII at the serialisation boundary
# makes every response byte < 128 — immune to any transport/decoder — and reads cleaner for an API.
# Applied once here (default_response_class) so it covers every endpoint, incl. the recommend
# narrative/evidence, without touching the engine's text.
_ASCII_MAP = str.maketrans({
    "²": "2", "³": "3", "×": "x", "÷": "/", "−": "-", "–": "-", "—": "-",
    "→": "->", "←": "<-", "↑": "^", "↓": "v", "≤": "<=", "≥": ">=", "≈": "~",
    "±": "+/-", "°": " deg", "Σ": "Sigma", "λ": "lambda", "§": "sec",
    "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...", " ": " ",
})


def _asciify(obj: Any) -> Any:
    if isinstance(obj, str):
        return obj.translate(_ASCII_MAP)
    if isinstance(obj, dict):
        return {k: _asciify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_asciify(v) for v in obj]
    return obj


class AsciiJSONResponse(JSONResponse):
    """JSON with a pure-ASCII body: known symbols mapped to readable ASCII, anything else escaped
    (`ensure_ascii=True`) so no raw byte > 127 ever reaches a mis-configured decoder."""

    media_type = "application/json; charset=utf-8"

    def render(self, content: Any) -> bytes:
        return json.dumps(_asciify(content), ensure_ascii=True, allow_nan=False,
                          separators=(",", ":")).encode("utf-8")

_ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:4173",
                    "http://127.0.0.1:5173", "http://127.0.0.1:4173"]


class Coverage:
    """Runtime view of the covered submarkets, derived from the loaded bundle."""

    def __init__(self, bundle: DataBundle) -> None:
        self.bundle = bundle
        districts = _load_districts()
        self.centroids = {name.strip().lower(): (lat, lng)
                          for name, lat, lng in districts}
        self.canonical: dict[str, str] = {}
        self.stats: list[dict] = []
        # Coverage is the set of TARGET submarkets defined by the districts table
        # (the product's supported neighbourhoods), restricted to those that
        # actually have sale listings. Listings outside these targets are loaded
        # for comp density / future expansion but are NOT exposed as coverage.
        sales_keys = {l.neighborhood.strip().lower()
                      for l in bundle.sales() if l.neighborhood}
        for name, _lat, _lng in districts:
            key = name.strip().lower()
            if key in sales_keys:
                self.canonical[key] = name
                self.stats.append(self._profile(name))
        # Every neighborhood present in the corpus (for area-intelligence endpoints that also
        # serve non-covered submarkets like Aqaba), lower-cased key -> display name.
        self.all_names: dict[str, str] = {}
        for l in bundle.listings:
            n = (l.neighborhood or "").strip()
            if n and n.lower() != "unknown":
                self.all_names.setdefault(n.lower(), n)

    def _profile(self, name: str) -> dict:
        key = name.strip().lower()
        sales = [l.price_per_m2 for l in self.bundle.sales()
                 if l.neighborhood.strip().lower() == key
                 and l.price_per_m2 and l.price_per_m2 >= MIN_PLAUSIBLE_SALE_PPM2]
        lat, lng = self.centroids.get(key, (None, None))
        return {
            "name": name,
            "centroid_lat": lat,
            "centroid_lng": lng,
            "listing_count": sum(1 for l in self.bundle.listings
                                 if l.neighborhood.strip().lower() == key),
            "sale_listing_count": len(sales),
            "median_price_per_m2": round(median(sales), 1) if sales else None,
        }

    def names(self) -> list[str]:
        return [s["name"] for s in self.stats]

    def resolve(self, raw: str) -> Optional[str]:
        return self.canonical.get((raw or "").strip().lower())

    def resolve_any(self, raw: str) -> Optional[str]:
        """Covered submarket first, then any neighborhood in the corpus (e.g. Aqaba)."""
        key = (raw or "").strip().lower()
        return self.canonical.get(key) or self.all_names.get(key)


def _is_amman(cov: "Coverage", canonical: str) -> bool:
    """Covered submarkets are all Greater Amman; anything else (e.g. Aqaba) is Kingdom-wide."""
    return canonical.strip().lower() in {n.strip().lower() for n in cov.names()}


def _load_districts() -> list[tuple[str, Optional[float], Optional[float]]]:
    import sqlite3

    conn = sqlite3.connect(_DB_PATH)
    try:
        rows = conn.execute(
            "SELECT name, centroid_lat, centroid_lng FROM districts").fetchall()
    finally:
        conn.close()
    return [(r[0], r[1], r[2]) for r in rows]


def _zoning_meta() -> dict:
    """Zoning plot counts + source by kind: official ASEZ (Aqaba) vs OSM land-use proxy (rest)."""
    import sqlite3

    conn = sqlite3.connect(_DB_PATH)
    try:
        if not conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='zoning_plots'"
        ).fetchone():
            return {}

        def by_kind(like: str, official: bool):
            op = "LIKE" if official else "NOT LIKE"
            rows = conn.execute(
                f"SELECT count(*) n, min(source_name) sn, min(source_url) su, "
                f"min(capture_date) cd FROM zoning_plots WHERE source_name {op} ?",
                (like,)).fetchone()
            if not rows or not rows[0]:
                return None
            return {"plot_count": rows[0], "kind": "asez" if official else "osm",
                    "source": {"name": rows[1], "url": rows[2],
                               "capture_date": rows[3] or "unknown"}}

        return {"asez": by_kind("%ASEZ%", True), "osm": by_kind("%ASEZ%", False)}
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = load_bundle_from_sqlite(_DB_PATH)
    app.state.bundle = bundle
    app.state.coverage = Coverage(bundle)
    app.state.zoning = _zoning_meta()
    yield


app = FastAPI(title="Jordan Real Estate Intelligence API", version="1.0", lifespan=lifespan,
              default_response_class=AsciiJSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    neighborhood: str = Field(..., min_length=1)
    property_type: Literal["apartment", "villa", "land", "commercial"] = "apartment"
    area_m2: float = Field(175, gt=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor_level: Optional[int] = Field(None, ge=0)
    total_floors: Optional[int] = Field(None, ge=1)
    building_age_years: Optional[int] = Field(None, ge=0)
    view: Optional[Literal["none", "sea", "city", "garden",
                           "mountain", "panoramic", "unknown"]] = None
    parking: Optional[Literal["none", "open", "covered", "unknown"]] = None
    furnishing: Optional[Literal["no", "semi", "full", "unknown"]] = None
    finish_quality: Optional[Literal["basic", "standard", "high",
                                     "luxury", "unknown"]] = None
    elevator: Optional[Literal["y", "n", "u", "unknown"]] = None
    apply_height_view_premium: bool = False


# Fields on RecommendRequest that are NOT engine Subject attributes.
_NON_SUBJECT_FIELDS = {"neighborhood", "property_type", "area_m2", "bathrooms",
                       "total_floors", "apply_height_view_premium", "overrides", "scenarios"}


def _subject_from(req: RecommendRequest, neighborhood: str) -> Subject:
    supplied = req.model_dump(exclude_none=True, exclude=_NON_SUBJECT_FIELDS)
    return Subject(neighborhood=neighborhood, property_type=req.property_type,
                   area_m2=req.area_m2, **supplied)


@app.get("/health")
def health():
    cov: Coverage = app.state.coverage
    return {"status": "ok", "listings": len(app.state.bundle.listings),
            "neighborhoods": cov.names(), "db_path": _DB_PATH}


@app.get("/neighborhoods")
def neighborhoods():
    return app.state.coverage.stats


@app.post("/recommend")
def post_recommend(req: RecommendRequest):
    cov: Coverage = app.state.coverage
    canonical = cov.resolve(req.neighborhood)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail=f"No data for {req.neighborhood}; covered: {cov.names()}")
    result = recommend(_subject_from(req, canonical), app.state.bundle)
    if req.apply_height_view_premium:
        result = builder.apply_height_view_premium(result, req.floor_level, req.total_floors)
    return result.to_dict()


@app.get("/comparables")
def comparables(neighborhood: str = Query(...), limit: int = Query(20, ge=1, le=100)):
    cov: Coverage = app.state.coverage
    canonical = cov.resolve(neighborhood)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail=f"No data for {neighborhood}; covered: {cov.names()}")
    key = canonical.strip().lower()
    rows = [l for l in app.state.bundle.sales()
            if l.neighborhood.strip().lower() == key
            and l.price_per_m2 and l.price_per_m2 >= MIN_PLAUSIBLE_SALE_PPM2]
    rows.sort(key=lambda l: str(l.listing_date or ""), reverse=True)
    return {"neighborhood": canonical, "count": len(rows),
            "comparables": [_comparable_view(l) for l in rows[:limit]]}


def _comparable_view(l) -> dict:
    return {
        "listing_id": l.listing_id,
        "neighborhood": l.neighborhood,
        "property_type": l.property_type,
        "price_jd": l.price_jd,
        "area_m2": l.area_m2,
        "price_per_m2": round(l.price_per_m2, 1) if l.price_per_m2 else None,
        "bedrooms": l.bedrooms,
        "bathrooms": l.bathrooms,
        "floor_level": l.floor_level,
        "view": l.view,
        "parking": l.parking,
        "finish_quality": l.finish_quality,
        "listing_date": l.listing_date.isoformat() if l.listing_date else None,
        "source": {"name": l.source_name, "url": l.listing_url},
    }


# ---------------------------------------------------------------------------
# Intelligence-platform endpoints (decision layer over the pricing engine)
# ---------------------------------------------------------------------------


class ScenarioOverrides(BaseModel):
    """What-if levers. Engine-native ones re-run the Subject; the rest transform the evidence
    (cost floor, future-signal timeline, evidence age) in documented ways — never a manual price."""

    target_floor: Optional[int] = Field(None, ge=0)
    floors: Optional[int] = Field(None, ge=1)
    finish_quality: Optional[Literal["basic", "standard", "high", "luxury", "unknown"]] = None
    parking: Optional[Literal["none", "open", "covered", "unknown"]] = None
    view: Optional[Literal["none", "sea", "city", "garden",
                           "mountain", "panoramic", "unknown"]] = None
    bedrooms: Optional[int] = Field(None, ge=0)
    building_age_years: Optional[int] = Field(None, ge=0)
    construction_cost_delta_pct: Optional[float] = Field(None, ge=-90, le=300)
    metro_delay_years: Optional[int] = Field(None, ge=0, le=30)
    launch_delay_months: Optional[int] = Field(None, ge=0, le=120)
    apply_height_view_premium: bool = False


class ScenarioRequest(RecommendRequest):
    overrides: ScenarioOverrides = Field(default_factory=ScenarioOverrides)


@app.post("/scenario")
def post_scenario(req: ScenarioRequest):
    cov: Coverage = app.state.coverage
    canonical = cov.resolve(req.neighborhood)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail=f"No data for {req.neighborhood}; covered: {cov.names()}")
    base_subject = _subject_from(req, canonical)
    overrides = req.overrides.model_dump(exclude_none=True)
    return scenario.simulate(base_subject, app.state.bundle, overrides,
                             as_of=app.state.bundle.as_of, base_total_floors=req.total_floors)


class ScenarioCompareItem(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)
    overrides: ScenarioOverrides = Field(default_factory=ScenarioOverrides)


class ScenarioCompareRequest(RecommendRequest):
    scenarios: list[ScenarioCompareItem] = Field(..., min_length=2, max_length=4)


@app.post("/scenario/compare")
def post_scenario_compare(req: ScenarioCompareRequest):
    cov: Coverage = app.state.coverage
    canonical = cov.resolve(req.neighborhood)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail=f"No data for {req.neighborhood}; covered: {cov.names()}")
    base_subject = _subject_from(req, canonical)
    scenarios = [{"label": s.label, "overrides": s.overrides.model_dump(exclude_none=True)}
                 for s in req.scenarios]
    return scenario.compare(base_subject, app.state.bundle, scenarios,
                            as_of=app.state.bundle.as_of, base_total_floors=req.total_floors)


class ResidualRequest(BaseModel):
    neighborhood: str = Field(..., min_length=1)
    buildable_area_m2: float = Field(..., gt=0)
    property_type: Literal["apartment", "villa", "land", "commercial"] = "apartment"
    finish_quality: Optional[Literal["basic", "standard", "high",
                                     "luxury", "unknown"]] = None
    gdv_per_m2: Optional[float] = Field(None, gt=0)
    construction_cost_per_m2: Optional[float] = Field(None, gt=0)
    finance_pct: float = Field(builder.FINANCE_PCT_DEFAULT, ge=0, le=1)
    professional_fees_pct: float = Field(builder.PROFESSIONAL_FEES_PCT_DEFAULT, ge=0, le=1)
    developer_profit_pct: float = Field(builder.DEVELOPER_PROFIT_PCT_DEFAULT, ge=0, le=1)


@app.post("/residual-land-value")
def post_residual_land_value(req: ResidualRequest):
    cov: Coverage = app.state.coverage
    bundle: DataBundle = app.state.bundle
    canonical = cov.resolve(req.neighborhood)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail=f"No data for {req.neighborhood}; covered: {cov.names()}")

    gdv = req.gdv_per_m2
    gdv_source = None
    gdv_defaulted = gdv is None
    if gdv_defaulted:
        subj = Subject(neighborhood=canonical, property_type=req.property_type, area_m2=175,
                       finish_quality=req.finish_quality or "unknown")
        rec = recommend(subj, bundle)
        if rec.recommended_price_jd_m2 <= 0:
            raise HTTPException(
                status_code=422,
                detail=("gdv_per_m2 not supplied and the engine cannot price "
                        f"{canonical} — provide gdv_per_m2 explicitly"))
        gdv = rec.recommended_price_jd_m2
        gdv_source = {"name": "Decision Engine recommended price/m²",
                      "url": "internal://engine/recommend", "capture_date": rec.computed_date}

    cost = req.construction_cost_per_m2
    cost_source = None
    caveat = None
    cost_defaulted = cost is None
    if cost_defaulted:
        cc = bundle.construction_cost
        default_cost = cc.for_area(_is_amman(cov, canonical)) if cc else None
        if not default_cost:
            raise HTTPException(
                status_code=422,
                detail=("construction_cost_per_m2 not supplied and no official DoS building-cost "
                        "series is available - provide construction_cost_per_m2 explicitly"))
        cost = default_cost
        authority = "Greater Amman" if _is_amman(cov, canonical) else "Kingdom"
        caveat = cc.caveat
        cost_source = {"name": f"DoS building-licence filed cost ({authority}, "
                               f"recent {cc.quarters}q mean to {cc.latest_period})",
                       "url": cc.source_url, "capture_date": cc.capture_date or "unknown"}

    result = builder.residual_land_value(
        buildable_area_m2=req.buildable_area_m2, gdv_per_m2=gdv, construction_cost_per_m2=cost,
        finance_pct=req.finance_pct, professional_fees_pct=req.professional_fees_pct,
        developer_profit_pct=req.developer_profit_pct, gdv_source=gdv_source,
        cost_source=cost_source, gdv_defaulted=gdv_defaulted, cost_defaulted=cost_defaulted,
        construction_caveat=caveat)
    return {"neighborhood": canonical, **result}


@app.get("/opportunity")
def get_opportunity():
    cov: Coverage = app.state.coverage
    bundle: DataBundle = app.state.bundle
    areas = cov.names()
    scores = opportunity.opportunity_scores(bundle, areas, bundle.as_of, cov.centroids)
    return {
        "version": "v1-heuristic",
        "note": ("Composite = documented, tunable weights over five derived components. "
                 "A null component is dropped and its weight redistributed. Scores are "
                 "relative to the covered set (min-max), for a map heatmap. Each area also "
                 "carries a builder Decision-Readiness block (8 dimensions + overall)."),
        "weights": OPPORTUNITY_WEIGHTS,
        "readiness_weights": READINESS_WEIGHTS,
        "as_of": bundle.as_of.isoformat(),
        "areas": scores,
    }


@app.get("/feasibility")
def get_feasibility(neighborhood: str = Query(..., min_length=1)):
    cov: Coverage = app.state.coverage
    bundle: DataBundle = app.state.bundle
    canonical = cov.resolve_any(neighborhood)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail=f"No data for {neighborhood}; covered: {cov.names()} (or any corpus neighborhood)")
    z = app.state.zoning or {}
    is_aqaba = bool(opportunity.asez_rules_for(bundle, canonical.strip().lower()))
    zoning = z.get("asez") if is_aqaba else z.get("osm")
    construction = None
    cc = bundle.construction_cost
    if cc:
        is_amman = _is_amman(cov, canonical)
        construction = {"value": cc.for_area(is_amman),
                        "authority": "Greater Amman" if is_amman else "Kingdom",
                        "source": cc.source()}
    return opportunity.feasibility_for(bundle, canonical, zoning=zoning, construction=construction)


@app.get("/areas")
def get_areas():
    cov: Coverage = app.state.coverage
    bundle: DataBundle = app.state.bundle
    catalog = opportunity.area_catalog(bundle, set(cov.names()), cov.centroids)
    return {"covered_count": sum(1 for a in catalog if a["covered"]),
            "total_count": len(catalog), "areas": catalog}


@app.get("/area-monitoring")
def get_area_monitoring(neighborhood: str = Query(..., min_length=1)):
    """All Monitoring-dashboard graph data for one area, computed server-side (frontend renders
    only). Resolves to any corpus neighborhood, not just covered submarkets."""
    cov: Coverage = app.state.coverage
    bundle: DataBundle = app.state.bundle
    canonical = cov.resolve_any(neighborhood)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail=f"No data for {neighborhood}; covered: {cov.names()} (or any corpus neighborhood)")
    data = monitoring.area_monitoring(bundle, canonical, bundle.as_of)
    opp = opportunity.opportunity_scores(bundle, cov.names(), bundle.as_of, cov.centroids)
    data["peers"] = monitoring.peer_comparison(bundle, opp, canonical.strip().lower())
    return data
