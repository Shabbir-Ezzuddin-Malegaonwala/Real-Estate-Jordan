"""FastAPI app exposing the Decision Engine for on-demand launch-price recommendations.

Startup loads the SQLite bundle once into memory; each /recommend builds an engine
Subject from the request and returns engine.recommend(...) verbatim. All pricing math
stays in app.engine — this module only validates input and serialises output.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from statistics import median
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.engine import recommend
from app.engine.config import MIN_PLAUSIBLE_SALE_PPM2
from app.engine.data import DataBundle, load_bundle_from_sqlite
from app.engine.models import Subject

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DB_PATH = os.environ.get("JORDAN_RE_DB", str(_REPO_ROOT / "db" / "jordan_re.sqlite"))

_ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:4173",
                    "http://127.0.0.1:5173", "http://127.0.0.1:4173"]


class Coverage:
    """Runtime view of the covered submarkets, derived from the loaded bundle."""

    def __init__(self, bundle: DataBundle) -> None:
        self.bundle = bundle
        self.centroids = {name.strip().lower(): (lat, lng)
                          for name, lat, lng in _load_districts()}
        self.canonical: dict[str, str] = {}
        self.stats: list[dict] = []
        for name in _neighborhoods_with_sales(bundle):
            self.canonical[name.strip().lower()] = name
            self.stats.append(self._profile(name))

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


def _load_districts() -> list[tuple[str, Optional[float], Optional[float]]]:
    import sqlite3

    conn = sqlite3.connect(_DB_PATH)
    try:
        rows = conn.execute(
            "SELECT name, centroid_lat, centroid_lng FROM districts").fetchall()
    finally:
        conn.close()
    return [(r[0], r[1], r[2]) for r in rows]


def _neighborhoods_with_sales(bundle: DataBundle) -> list[str]:
    seen: dict[str, str] = {}
    for l in bundle.sales():
        key = l.neighborhood.strip().lower()
        if key and key not in seen:
            seen[key] = l.neighborhood.strip()
    return sorted(seen.values())


@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = load_bundle_from_sqlite(_DB_PATH)
    app.state.bundle = bundle
    app.state.coverage = Coverage(bundle)
    yield


app = FastAPI(title="Jordan Real Estate Intelligence API", version="1.0", lifespan=lifespan)
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


def _subject_from(req: RecommendRequest, neighborhood: str) -> Subject:
    supplied = req.model_dump(exclude_none=True,
                              exclude={"neighborhood", "property_type", "area_m2",
                                       "bathrooms", "total_floors"})
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
    rows.sort(key=lambda l: l.listing_date or "", reverse=True)
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
