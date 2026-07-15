"""In-process bridge to the existing pricing engine (app.engine).

Design decision (documented in README): we reuse the engine by IMPORTING it,
not by calling the recommendation API over HTTP. Two reasons:

  1. Speed — no second server, no network hop; the DataBundle loads once here.
  2. Coverage — the recommendation API gates /recommend to the 5 districts in
     the `districts` table (its product's supported submarkets). The engine
     itself has no such gate: recommend(subject, bundle) prices ANY neighborhood
     that has enough comparable sales in the corpus. The corpus spans dozens of
     Jordan submarkets (Shafa Badran, Marj Al Hamam, Aqaba, ...), so importing
     the engine lets the assistant serve all of Jordan while the engine reports
     confidence honestly for thin submarkets.

All pricing MATH stays in app.engine — this module only resolves a free-text
neighborhood to a canonical corpus name, builds the Subject, and calls recommend.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from statistics import median
from typing import Optional

from .config import DB_DSN, DB_PATH, RECO_REPO

# Make `app.engine` importable. This app is standalone; the pricing engine lives
# in the sibling recommendation repo (RECO_REPO), which we add to sys.path so we
# can import and CALL the engine in-process (never re-implementing its math).
if not (RECO_REPO / "app" / "engine").exists():
    raise RuntimeError(
        f"Recommendation engine not found at {RECO_REPO}. The assistant reuses the "
        "pricing engine + canonical DB from the recommendation repo. Set RECO_REPO "
        "to its path (the folder containing app/engine and db/jordan_re.sqlite)."
    )
if str(RECO_REPO) not in sys.path:
    sys.path.insert(0, str(RECO_REPO))

from app.engine import recommend as _engine_recommend  # noqa: E402
from app.engine.config import MIN_PLAUSIBLE_SALE_PPM2  # noqa: E402
from app.engine.data import (  # noqa: E402
    DataBundle,
    load_bundle_from_postgres,
    load_bundle_from_sqlite,
)
from app.engine.models import Subject  # noqa: E402


@dataclass
class AreaProfile:
    """A priceable submarket derived from the listings corpus."""

    name: str            # canonical display name (as it appears in listings)
    key: str             # lower-cased match key
    centroid_lat: Optional[float]
    centroid_lng: Optional[float]
    sale_count: int
    median_price_per_m2: Optional[float]


# Below this many clean sale comps we flag the area as thin-data so the agent
# (and UI) can surface low confidence honestly instead of over-claiming.
THIN_DATA_SALE_COUNT = 8


class Engine:
    """Loads the DataBundle once and answers pricing / catalog / geo queries."""

    def __init__(self, bundle: Optional[DataBundle] = None) -> None:
        # Prefer a bundle handed in by the main API (the shared Postgres bundle —
        # one load, one DB, no sqlite). Standalone: load from Postgres if
        # DATABASE_URL is set, else fall back to the local sqlite file.
        if bundle is not None:
            self.db_path = "shared-bundle (postgres)"
            self.bundle = bundle
        elif DB_DSN:
            self.db_path = "postgres"
            self.bundle = load_bundle_from_postgres(DB_DSN)
        else:
            self.db_path = DB_PATH
            self.bundle = load_bundle_from_sqlite(DB_PATH)
        self._areas: dict[str, AreaProfile] = self._build_area_catalog()

    # -- catalog -------------------------------------------------------------
    def _build_area_catalog(self) -> dict[str, AreaProfile]:
        by_key: dict[str, list] = {}
        for l in self.bundle.sales():
            n = (l.neighborhood or "").strip()
            if not n or n.lower() == "unknown":
                continue
            if not l.price_per_m2 or l.price_per_m2 < MIN_PLAUSIBLE_SALE_PPM2:
                continue
            by_key.setdefault(n.lower(), []).append(l)

        out: dict[str, AreaProfile] = {}
        for key, rows in by_key.items():
            lats = [r.lat for r in rows if r.lat is not None]
            lngs = [r.lng for r in rows if r.lng is not None]
            ppm2 = [r.price_per_m2 for r in rows]
            out[key] = AreaProfile(
                name=rows[0].neighborhood.strip(),
                key=key,
                centroid_lat=round(sum(lats) / len(lats), 6) if lats else None,
                centroid_lng=round(sum(lngs) / len(lngs), 6) if lngs else None,
                sale_count=len(rows),
                median_price_per_m2=round(median(ppm2), 1) if ppm2 else None,
            )
        return out

    def areas(self, min_sales: int = 1) -> list[AreaProfile]:
        return sorted(
            (a for a in self._areas.values() if a.sale_count >= min_sales),
            key=lambda a: a.sale_count,
            reverse=True,
        )

    # -- resolution ----------------------------------------------------------
    def resolve(self, raw: str) -> Optional[AreaProfile]:
        """Free-text neighborhood -> canonical AreaProfile.

        Exact (case-insensitive) first, then a conservative substring match
        (longest sale_count wins) so 'jubaiha' finds 'Al Jubaiha'. Returns None
        when nothing plausible matches — the caller then says "I don't know".
        """
        key = (raw or "").strip().lower()
        if len(key) < 3:  # empty/whitespace or too short to disambiguate
            return None
        if key in self._areas:
            return self._areas[key]
        # Substring match in either direction (so "jubaiha" -> "Al Jubaiha" and
        # "downtown amman" -> "Amman"). Require a >=3-char overlap to avoid noise.
        # Deliberately NO generic token-overlap fallback: matching on a shared
        # generic word ("city", "al") produced false positives (e.g. a fake
        # "Gotham City" resolving to "Sports City"). Prefer the most-sampled hit.
        cands = [
            a for a in self._areas.values()
            if (key in a.key and len(key) >= 3) or (a.key in key and len(a.key) >= 3)
        ]
        if not cands:
            return None
        return max(cands, key=lambda a: a.sale_count)

    def nearest(self, lat: float, lng: float, min_sales: int = 20) -> Optional[AreaProfile]:
        """Nearest priceable submarket centroid to a point (for geocoding).

        Restricted to reasonably-sampled areas (>= min_sales) so a single stray
        listing can't become the 'nearest neighbourhood'. Great-circle-ish via a
        cheap equirectangular approximation (fine at city scale)."""
        best: Optional[AreaProfile] = None
        best_d = math.inf
        for a in self._areas.values():
            if a.sale_count < min_sales or a.centroid_lat is None or a.centroid_lng is None:
                continue
            dlat = math.radians(a.centroid_lat - lat)
            dlng = math.radians(a.centroid_lng - lng) * math.cos(math.radians(lat))
            d = dlat * dlat + dlng * dlng
            if d < best_d:
                best_d, best = d, a
        return best

    # -- pricing -------------------------------------------------------------
    def price(self, neighborhood: str, *, property_type: str = "apartment",
              area_m2: float = 175.0, bedrooms: Optional[int] = None,
              floor_level: Optional[int] = None, finish_quality: Optional[str] = None,
              building_age_years: Optional[int] = None, view: Optional[str] = None,
              parking: Optional[str] = None) -> dict:
        """Resolve the area, run the engine, return its result dict verbatim plus
        a small `resolution` + `coverage` honesty block. Never invents numbers."""
        area = self.resolve(neighborhood)
        if area is None:
            return {
                "error": "neighborhood_not_found",
                "message": (f"'{neighborhood}' does not match any priceable submarket in the "
                            "corpus. Ask the user to name a Jordan neighbourhood, or geocode a "
                            "specific address first."),
                "did_you_mean": [a.name for a in self.areas(min_sales=50)[:12]],
            }
        subject = Subject(
            neighborhood=area.name,
            property_type=property_type,
            area_m2=area_m2,
            bedrooms=bedrooms,
            floor_level=floor_level,
            finish_quality=(finish_quality or "unknown"),
            building_age_years=(building_age_years if building_age_years is not None else 0),
            view=(view or "unknown"),
            parking=(parking or "unknown"),
        )
        result = _engine_recommend(subject, self.bundle)
        return self._compact(result.to_dict(), neighborhood, area)

    @staticmethod
    def _compact(full: dict, requested: str, area: "AreaProfile") -> dict:
        """Trim the engine's (large) result to what the model needs to reason and
        the UI card needs to render — a few hundred tokens instead of several
        thousand. Free-tier Groq models cap per-request tokens (~6-8k TPM), and
        the full result (all comps + evidence + narrative + method_values) fed
        back into the next model call blows that budget. The full numbers are
        preserved; only bulky trails (per-comp adjustment ladders, method_values,
        alternative_scenarios) are dropped."""
        conf = full.get("confidence", {})
        # Keep only 'not_derivable' evidence (what honesty requires surfacing).
        not_deriv = [
            {"factor": e.get("factor"), "adjustment": e.get("adjustment")}
            for e in full.get("evidence_objects", [])
            if "not_derivable" in str(e.get("adjustment", "")).lower()
        ]
        comps = [
            {
                "price_per_m2": c.get("price_per_m2") or c.get("original_ppm2"),
                "area_m2": c.get("area_m2"),
                "bedrooms": c.get("bedrooms"),
                "view": c.get("view"),
                "lat": c.get("lat"),
                "lng": c.get("lng"),
                "source": {"url": (c.get("source") or {}).get("url")},
            }
            for c in full.get("comparables", [])[:5]
        ]
        narrative = (full.get("narrative") or "").strip()
        return {
            "neighborhood": full.get("neighborhood"),
            "property_type": full.get("property_type"),
            "min_safe_price_jd_m2": full.get("min_safe_price_jd_m2"),
            "recommended_price_jd_m2": full.get("recommended_price_jd_m2"),
            "premium_price_jd_m2": full.get("premium_price_jd_m2"),
            "confidence": {
                "label": conf.get("label"),
                "numeric": conf.get("numeric"),
                "interval_jd_m2": conf.get("interval_jd_m2"),
            },
            # Card reads evidence_objects filtered for not_derivable; keep that shape.
            "evidence_objects": not_deriv,
            "comparables": comps,
            "narrative_short": (narrative[:280] + "…") if len(narrative) > 280 else narrative,
            "resolution": {
                "requested": requested,
                "resolved_to": area.name,
                "centroid": ([area.centroid_lng, area.centroid_lat]
                             if area.centroid_lat is not None else None),
                "sale_comps_in_area": area.sale_count,
            },
            "coverage": {
                "thin_data": area.sale_count < THIN_DATA_SALE_COUNT,
                "note": ("Thin comp coverage — treat the band as indicative."
                         if area.sale_count < THIN_DATA_SALE_COUNT else
                         "Comp coverage is adequate."),
            },
            "source": {"name": "Jordan RE Decision Engine (in-process)",
                       "endpoint": "app.engine.recommend", "db": "db/jordan_re.sqlite"},
        }


_ENGINE: Optional["Engine"] = None


def init_engine_from_bundle(bundle: DataBundle) -> "Engine":
    """Wire the assistant to REUSE an already-loaded bundle (the main API's shared
    Postgres bundle). Call once at startup so there's a single in-memory bundle and
    no second DB load / no sqlite."""
    global _ENGINE
    _ENGINE = Engine(bundle=bundle)
    return _ENGINE


def get_engine() -> Engine:
    """Process-wide singleton. Uses the shared bundle if one was injected; else
    builds its own (Postgres if DATABASE_URL is set, sqlite otherwise)."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = Engine()
    return _ENGINE
