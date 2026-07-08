"""Precompute engine recommendations for the frontend (national DB).

Writes app/web/public/engine_output.json in the combined shape the React app reads
(offline / precomputed mode): { generated_at, source, neighborhoods: {name: result} }.
Picks a representative national set — the top Amman submarkets by comp depth plus the
main secondary cities — so the demo shows nationwide coverage, not just 5 areas.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from app.engine import recommend
from app.engine.data import load_bundle_from_sqlite
from app.engine.models import Subject

DB = "db/jordan_national.sqlite"
OUT = Path("app/web/public/engine_output.json")
AS_OF = date(2026, 7, 8)

# secondary-city anchors we always include (if present) to show national reach
SECONDARY = ["Irbid", "Zarqa", "Aqaba", "Madaba", "Salt", "Jerash"]


def main() -> None:
    bundle = load_bundle_from_sqlite(DB, as_of=AS_OF)
    cnt = Counter(l.neighborhood for l in bundle.sales() if l.property_type == "apartment")
    top_amman = [n for n, _ in cnt.most_common(14)]
    names, seen = [], set()
    for n in top_amman + SECONDARY:
        if n and n not in seen and cnt.get(n, 0) >= 8:
            seen.add(n)
            names.append(n)

    by_nbhd = {}
    for nb in names:
        s = Subject(neighborhood=nb, property_type="apartment", area_m2=175, bedrooms=3,
                    floor_level=4, finish_quality="high", building_age_years=0)
        by_nbhd[nb] = recommend(s, bundle).to_dict()

    combined = {
        "generated_at": AS_OF.isoformat(),
        "source": f"{DB} ({len(bundle.listings):,} listings, nationwide)",
        "neighborhoods": by_nbhd,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} with {len(by_nbhd)} neighborhoods:")
    for nb, r in by_nbhd.items():
        print(f"  {nb:<22} {r['min_safe_price_jd_m2']:>5.0f}/{r['recommended_price_jd_m2']:>5.0f}/"
              f"{r['premium_price_jd_m2']:>5.0f}  {r['confidence']['label']}")


if __name__ == "__main__":
    main()
