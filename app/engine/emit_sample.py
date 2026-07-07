"""Emit real Decision-Engine outputs for the frontend.

Runs the full pipeline on the REAL database (db/jordan_re.sqlite) for a representative
apartment in each of the 5 target submarkets and writes:

  * app/engine/outputs/<neighborhood>.json   — one RecommendationResult per submarket
  * app/engine/sample_output.json            — { generated_at, source, neighborhoods: {...} }

Falls back to the synthetic fixtures only if the DB is absent.

    python -m app.engine.emit_sample
"""

from __future__ import annotations

import json
import os
from datetime import date

from .data import load_bundle_from_sqlite
from .fixtures import load_sample_bundle
from .models import Subject
from .pipeline import recommend

_HERE = os.path.dirname(__file__)
_DB = os.path.join(_HERE, "..", "..", "db", "jordan_re.sqlite")
_OUT_DIR = os.path.join(_HERE, "outputs")
AS_OF = date(2026, 7, 7)

# Representative subject per submarket. Attributes are left 'unknown' where the real
# listings currently are (view/parking/finish enrichment pending) — the engine surfaces
# that as a caveat. area/floor are typical premium-apartment values.
NEIGHBORHOODS = ["Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"]


def _subject(nbhd: str) -> Subject:
    # Realistic new premium-apartment launch: luxury finish, covered parking, unfurnished,
    # new build, mid floor. view left unknown (attaches at neighborhood level via R7).
    return Subject(neighborhood=nbhd, property_type="apartment", area_m2=175, bedrooms=3,
                   floor_level=3, view="unknown", parking="covered", building_age_years=0,
                   finish_quality="luxury", furnishing="no", elevator="unknown",
                   location_id=f"demo-{nbhd.lower()}")


def main() -> None:
    if os.path.exists(_DB):
        bundle = load_bundle_from_sqlite(_DB, AS_OF)
        source = f"db/jordan_re.sqlite ({len(bundle.listings)} listings)"
    else:
        bundle = load_sample_bundle(AS_OF)
        source = "synthetic fixtures (DB absent)"

    os.makedirs(_OUT_DIR, exist_ok=True)
    by_nbhd = {}
    for nbhd in NEIGHBORHOODS:
        result = recommend(_subject(nbhd), bundle, AS_OF).to_dict()
        by_nbhd[nbhd] = result
        with open(os.path.join(_OUT_DIR, f"{nbhd.lower()}.json"), "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)

    combined = {"generated_at": AS_OF.isoformat(), "source": source,
                "neighborhoods": by_nbhd}
    with open(os.path.join(_HERE, "sample_output.json"), "w", encoding="utf-8") as fh:
        json.dump(combined, fh, indent=2, ensure_ascii=False)

    print(f"source: {source}")
    for nbhd, r in by_nbhd.items():
        c = r["confidence"]
        print(f"  {nbhd:10} min/rec/prem = {r['min_safe_price_jd_m2']:.0f} / "
              f"{r['recommended_price_jd_m2']:.0f} / {r['premium_price_jd_m2']:.0f} JD/m²  "
              f"conf={c['label']} ({c['numeric']:.2f})  comps={len(r['comparables'])}")


if __name__ == "__main__":
    main()
