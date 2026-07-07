"""Deterministic generator for the engine's synthetic test fixtures.

Every row is SYNTHETIC (labelled so in `notes`). A known data-generating process bakes
attribute premiums into the prices so the Adjustment Engine has genuine signal to
recover — proving the derivation works without any hardcoded weight. Re-run with:

    python app/engine/fixtures/_generate_fixtures.py

Amman premium-submarket price levels are realistic in magnitude; they are NOT collected
market facts and must never be presented as such.
"""

from __future__ import annotations

import csv
import os
import random

HERE = os.path.dirname(__file__)
random.seed(20260707)

# --- Known DGP premiums (the engine must REDISCOVER these from prices, not read them) ---
VIEW_MULT = {"none": 1.00, "city": 1.08, "panoramic": 1.15, "garden": 1.04}
PARKING_MULT = {"none": 1.00, "open": 1.02, "covered": 1.06}
FINISH_MULT = {"basic": 0.90, "standard": 1.00, "high": 1.08, "luxury": 1.16}
FLOOR_PER = 0.009      # +0.9% per floor
AGE_PER = -0.008       # -0.8% per year
SIZE_PER_M2 = -0.0006  # larger units slightly cheaper per m²

BASE_PPM2 = {"Abdoun": 1150, "Dabouq": 1000, "Sweifieh": 900, "Khalda": 820, "Shmeisani": 760}
NBHD_COORD = {"Abdoun": (31.9478, 35.8920), "Dabouq": (31.9950, 35.8000),
              "Sweifieh": (31.9560, 35.8570), "Khalda": (31.9880, 35.8250),
              "Shmeisani": (31.9660, 35.9020)}

LISTING_HEADER = ["listing_id", "portal", "listing_url", "listing_type", "property_type",
                  "neighborhood", "district", "lat", "lng", "price_jd", "area_m2",
                  "bedrooms", "bathrooms", "floor_level", "total_floors", "view", "parking",
                  "building_age_years", "furnishing", "elevator", "finish_quality",
                  "seller_type", "listing_date", "main_image_url", "description_raw",
                  "evidence_category", "language", "source_name", "source_url",
                  "capture_date", "collected_by", "confidence", "notes"]

CAPTURE = "2026-07-07"
_uid = 0


def _row(nbhd, view, parking, finish, floor, age, area, ldate, ltype="sale", portal="synthetic"):
    global _uid
    _uid += 1
    base = BASE_PPM2[nbhd]
    ppm2 = (base * VIEW_MULT[view] * PARKING_MULT[parking] * FINISH_MULT[finish]
            * (1 + FLOOR_PER * floor) * (1 + AGE_PER * age)
            * (1 + SIZE_PER_M2 * (area - 150)))
    ppm2 *= random.uniform(0.97, 1.03)  # market noise
    if ltype == "rent":
        ppm2 = ppm2 * 0.065 / 12  # ~6.5% gross yield -> monthly rent per m²
    price = round(ppm2 * area, -1 if ltype == "rent" else -2)
    lat, lng = NBHD_COORD[nbhd]
    lid = f"syn-{nbhd[:3].lower()}-{_uid:03d}"
    return {
        "listing_id": lid, "portal": portal,
        "listing_url": f"https://example.invalid/{lid}", "listing_type": ltype,
        "property_type": "apartment", "neighborhood": nbhd, "district": "Amman",
        "lat": round(lat + random.uniform(-0.004, 0.004), 5),
        "lng": round(lng + random.uniform(-0.004, 0.004), 5),
        "price_jd": price, "area_m2": area, "bedrooms": max(1, round(area / 60)),
        "bathrooms": max(1, round(area / 80)), "floor_level": floor, "total_floors": floor + 2,
        "view": view, "parking": parking, "building_age_years": age, "furnishing": "unknown",
        "elevator": "y", "finish_quality": finish, "seller_type": "agent",
        "listing_date": ldate, "main_image_url": "unknown",
        "description_raw": f"{finish} apartment in {nbhd}", "evidence_category": "portal",
        "language": "en", "source_name": "Synthetic Fixture (engine test data)",
        "source_url": f"https://example.invalid/{lid}", "capture_date": CAPTURE,
        "collected_by": "engine-fixture-generator", "confidence": "M",
        "notes": "SYNTHETIC — engine test fixture, not a real listing",
    }


def _spread(specs, ltype="sale"):
    return [_row(*s, ltype=ltype) for s in specs]


def build_listings():
    rows = []
    # Abdoun — rich pool (happy path). Varied attributes, mostly recent, a few stale.
    abdoun = [
        ("Abdoun", "none", "none", "standard", 2, 8, 140, "2026-05-10"),
        ("Abdoun", "none", "covered", "standard", 3, 5, 160, "2026-04-22"),
        ("Abdoun", "none", "covered", "high", 4, 3, 180, "2026-06-01"),
        ("Abdoun", "city", "covered", "high", 5, 2, 175, "2026-06-15"),
        ("Abdoun", "city", "covered", "luxury", 6, 1, 200, "2026-05-28"),
        ("Abdoun", "city", "open", "standard", 3, 6, 150, "2026-03-30"),
        ("Abdoun", "panoramic", "covered", "luxury", 8, 0, 220, "2026-06-20"),
        ("Abdoun", "panoramic", "covered", "high", 7, 2, 190, "2026-05-05"),
        ("Abdoun", "none", "none", "basic", 1, 15, 120, "2026-04-11"),
        ("Abdoun", "city", "covered", "standard", 4, 4, 165, "2026-06-08"),
        ("Abdoun", "none", "open", "high", 2, 7, 155, "2026-05-19"),
        ("Abdoun", "panoramic", "covered", "luxury", 9, 1, 210, "2026-06-25"),
        ("Abdoun", "city", "covered", "high", 5, 3, 170, "2026-04-02"),
        ("Abdoun", "none", "covered", "standard", 3, 9, 145, "2026-05-14"),
        ("Abdoun", "city", "open", "basic", 2, 12, 130, "2026-03-18"),
        # stale-but-selectable comps (13-18 mo) -> exercise the CBJ time-adjustment path
        ("Abdoun", "city", "covered", "high", 5, 3, 172, "2025-02-05"),
        ("Abdoun", "panoramic", "covered", "luxury", 8, 1, 205, "2025-03-20"),
        ("Abdoun", "none", "covered", "standard", 3, 6, 158, "2025-01-15"),
    ]
    sweifieh = [
        ("Sweifieh", "none", "none", "standard", 2, 10, 135, "2026-05-01"),
        ("Sweifieh", "none", "covered", "standard", 3, 6, 150, "2026-04-15"),
        ("Sweifieh", "city", "covered", "high", 4, 3, 160, "2026-06-03"),
        ("Sweifieh", "none", "covered", "high", 3, 5, 155, "2026-05-22"),
        ("Sweifieh", "city", "open", "standard", 2, 8, 140, "2026-03-27"),
        ("Sweifieh", "none", "covered", "luxury", 5, 2, 175, "2026-06-11"),
        ("Sweifieh", "panoramic", "covered", "high", 6, 1, 170, "2026-05-30"),
        ("Sweifieh", "none", "none", "basic", 1, 14, 118, "2026-04-08"),
        ("Sweifieh", "city", "covered", "standard", 4, 4, 148, "2026-06-18"),
        ("Sweifieh", "none", "open", "standard", 2, 9, 138, "2026-05-06"),
    ]
    khalda = [
        ("Khalda", "none", "none", "standard", 2, 9, 130, "2026-05-03"),
        ("Khalda", "none", "covered", "high", 3, 4, 150, "2026-04-19"),
        ("Khalda", "city", "covered", "standard", 4, 5, 145, "2026-06-05"),
        ("Khalda", "none", "covered", "standard", 3, 7, 140, "2026-05-25"),
        ("Khalda", "city", "open", "high", 5, 3, 155, "2026-06-14"),
        ("Khalda", "none", "none", "basic", 1, 13, 115, "2026-04-05"),
        ("Khalda", "panoramic", "covered", "luxury", 6, 1, 165, "2026-06-22"),
        ("Khalda", "none", "covered", "standard", 2, 8, 135, "2026-05-12"),
    ]
    shmeisani = [
        ("Shmeisani", "none", "none", "standard", 2, 12, 128, "2026-05-02"),
        ("Shmeisani", "city", "covered", "high", 5, 6, 145, "2026-04-20"),
        ("Shmeisani", "none", "covered", "standard", 3, 9, 135, "2026-06-04"),
        ("Shmeisani", "none", "open", "standard", 2, 11, 130, "2026-05-24"),
        ("Shmeisani", "city", "covered", "standard", 4, 7, 140, "2026-06-13"),
        ("Shmeisani", "none", "none", "basic", 1, 16, 120, "2026-04-06"),
    ]
    # Dabouq — intentionally THIN (2 comps) to exercise the low-confidence path
    dabouq = [
        ("Dabouq", "panoramic", "covered", "luxury", 3, 2, 260, "2026-05-15"),
        ("Dabouq", "city", "covered", "high", 2, 4, 240, "2026-04-28"),
    ]
    for group in (abdoun, sweifieh, khalda, shmeisani, dabouq):
        rows.extend(_spread(group))

    # rentals for the income-approach ceiling (monthly asking rent per m²)
    rentals = [
        ("Abdoun", "city", "covered", "high", 4, 3, 160, "2026-06-01"),
        ("Abdoun", "none", "covered", "standard", 3, 6, 150, "2026-05-10"),
        ("Abdoun", "panoramic", "covered", "luxury", 7, 1, 200, "2026-06-12"),
        ("Abdoun", "none", "none", "standard", 2, 9, 140, "2026-05-20"),
        ("Sweifieh", "none", "covered", "standard", 3, 6, 150, "2026-05-18"),
        ("Sweifieh", "city", "covered", "high", 4, 3, 160, "2026-06-02"),
        ("Khalda", "none", "covered", "standard", 3, 5, 145, "2026-05-22"),
        ("Khalda", "city", "open", "high", 4, 4, 150, "2026-06-07"),
        ("Shmeisani", "none", "covered", "standard", 3, 9, 135, "2026-05-15"),
    ]
    rows.extend(_spread(rentals, ltype="rent"))
    return rows


def build_cost_benchmarks():
    header = ["spec_class", "cost_jd_per_m2_low", "cost_jd_per_m2_high", "year",
              "evidence_category", "language", "source_name", "source_url",
              "capture_date", "collected_by", "confidence", "notes"]
    data = [
        ("basic", 300, 380, 2026), ("standard", 380, 480, 2026),
        ("high", 480, 620, 2026), ("luxury", 620, 820, 2026),
    ]
    rows = []
    for spec, lo, hi, yr in data:
        rows.append({
            "spec_class": spec, "cost_jd_per_m2_low": lo, "cost_jd_per_m2_high": hi,
            "year": yr, "evidence_category": "derived", "language": "en",
            "source_name": "Synthetic Fixture (cost benchmark)",
            "source_url": "https://example.invalid/cost-benchmarks",
            "capture_date": CAPTURE, "collected_by": "engine-fixture-generator",
            "confidence": "M", "notes": "SYNTHETIC — plausible Amman build cost, not sourced",
        })
    return header, rows


def build_evidence_items():
    header = ["evidence_id", "type", "title", "summary_2_lines", "impact_area",
              "expected_year", "expected_effect", "published_date", "evidence_category",
              "language", "source_name", "source_url", "capture_date", "collected_by",
              "confidence", "notes"]
    data = [
        ("ev-001", "infrastructure", "Amman BRT extension toward western corridor",
         "Bus rapid transit expansion improving access to western Amman submarkets.",
         "citywide", 2027, "unknown", "2026-01-15", "H"),
        ("ev-002", "infrastructure", "New arterial road widening near Abdoun",
         "Road widening scheme easing congestion around the Abdoun circle district.",
         "Abdoun", 2027, "unknown", "2026-03-02", "M"),
        ("ev-003", "market_news", "Premium mall development announced in Sweifieh",
         "Mixed-use retail development planned in the Sweifieh commercial spine.",
         "Sweifieh", 2028, "unknown", "2026-02-20", "M"),
    ]
    rows = []
    for eid, typ, title, summ, area, yr, eff, pub, conf in data:
        rows.append({
            "evidence_id": eid, "type": typ, "title": title, "summary_2_lines": summ,
            "impact_area": area, "expected_year": yr, "expected_effect": eff,
            "published_date": pub, "evidence_category": "infrastructure" if typ == "infrastructure" else "news",
            "language": "en", "source_name": "Synthetic Fixture (future signal)",
            "source_url": f"https://example.invalid/{eid}", "capture_date": CAPTURE,
            "collected_by": "engine-fixture-generator", "confidence": conf,
            "notes": "SYNTHETIC — illustrative future signal, not a verified announcement",
        })
    return header, rows


def build_projects():
    header = ["project_id", "name", "developer", "builder_tier", "neighborhood", "lat", "lng",
              "status", "unit_types", "launch_price_jd_m2", "payment_plan", "launch_date",
              "units_total", "evidence_category", "language", "source_name", "source_url",
              "capture_date", "collected_by", "confidence", "notes"]
    data = [
        ("pr-001", "Abdoun Heights", "premium", "Abdoun", "selling", 1250, 2026),
        ("pr-002", "Diplomatic Residences", "luxury", "Abdoun", "construction", 1400, 2027),
        ("pr-003", "Sweifieh Square Living", "premium", "Sweifieh", "selling", 980, 2026),
        ("pr-004", "Dabouq Villas Collection", "luxury", "Dabouq", "planned", 1500, 2027),
    ]
    rows = []
    for pid, name, tier, nbhd, status, ppm2, yr in data:
        lat, lng = NBHD_COORD[nbhd]
        rows.append({
            "project_id": pid, "name": name, "developer": f"{name} Developments",
            "builder_tier": tier, "neighborhood": nbhd, "lat": lat, "lng": lng,
            "status": status, "unit_types": "2-4 bed apartments", "launch_price_jd_m2": ppm2,
            "payment_plan": "20% down, 3yr installments", "launch_date": f"{yr}-01-01",
            "units_total": 60, "evidence_category": "builder", "language": "en",
            "source_name": "Synthetic Fixture (competitor project)",
            "source_url": f"https://example.invalid/{pid}", "capture_date": CAPTURE,
            "collected_by": "engine-fixture-generator", "confidence": "M",
            "notes": "SYNTHETIC — illustrative competitor, not a real project",
        })
    return header, rows


def build_index():
    """CBJ apartment index: real values through 2021-Q3, then synthetically extended."""
    header = ["indicator", "geography", "period", "value", "unit", "source_name",
              "source_url", "capture_date", "confidence", "notes"]
    real = {  # subset of the real CBJ series (see data/processed/_cbj_rows.csv)
        "2021-Q3": 104.5, "2021-Q2": 105.665, "2021-Q1": 105.951, "2020-Q4": 106.659,
    }
    rows = []
    src = ("Central Bank of Jordan (Real Estate Price Index)",
           "https://www.cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index")
    for period, val in sorted(real.items()):
        rows.append(_index_row(header, period, val, src, "H",
                               "Real CBJ apartment index value (base 2012=100)"))
    # Synthetic extension 2021-Q4 .. 2026-Q2 with a mild recovery trend.
    val = 104.5
    quarters = [f"{y}-Q{q}" for y in range(2021, 2027) for q in range(1, 5)]
    quarters = [q for q in quarters if q > "2021-Q3" and q <= "2026-Q2"]
    for period in quarters:
        val *= 1.012 * random.uniform(0.998, 1.006)
        rows.append(_index_row(header, period, round(val, 3), src, "M",
                               "SYNTHETIC extension of CBJ apartment index for engine testing"))
    return header, rows


def _index_row(header, period, val, src, conf, note):
    return {"indicator": "cbj_repi_apartment", "geography": "Jordan", "period": period,
            "value": val, "unit": "index_2012=100", "source_name": src[0],
            "source_url": src[1], "capture_date": CAPTURE, "confidence": conf, "notes": note}


def _write(name, header, rows):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows):>3} rows -> {name}")


def main():
    _write("sample_listings.csv", LISTING_HEADER, build_listings())
    _write("sample_cost_benchmarks.csv", *build_cost_benchmarks())
    _write("sample_evidence.csv", *build_evidence_items())
    _write("sample_projects.csv", *build_projects())
    _write("sample_index.csv", *build_index())


if __name__ == "__main__":
    main()
