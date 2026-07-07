"""Adversarial edge-case tests for the Decision Engine (app.engine).

These go beyond app/engine/test_pipeline.py (happy-path + 6 named scenarios). They build
synthetic DataBundles directly to stress the sub-engines at their boundaries, and they
re-assert the two hard invariants of the whole project on the rich sample bundle:

  * NO hardcoded pricing-weight constants exist anywhere in the engine source.
  * Every APPLIED comp adjustment carries a structured evidence object with a real source_url.

Edge cases (each maps to the QA brief):
  thin market (few / zero / single comp) · all-attributes-unknown · extreme area
  (1 m², 100000 m²) · negative / zero area · outlier-heavy pool (0-price, whole-building,
  extreme high) · stale CBJ index ending 2021-Q3 · empty cost/projects/evidence tables ·
  confidence must widen as the market thins.

Run:  python -m pytest tests/test_engine_edge_cases.py -v      (from repo root)
"""

from __future__ import annotations

import json
import math
import os
import re
import unittest
from datetime import date

from app.engine.comparable_analysis import collapse_near_duplicates
from app.engine.data import (CostBenchmark, DataBundle, EvidenceItem,
                             NeighborhoodGeoContext, PriceIndex, Project)
from app.engine.fixtures import load_sample_bundle
from app.engine.models import Listing, Subject
from app.engine.pipeline import recommend

AS_OF = date(2026, 7, 7)
_ENGINE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "app", "engine")
_CONTEXT_FACTORS = {"Time (market movement)", "Net adjustment cap"}

# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------

_SEQ = [0]


def make_listing(neighborhood="Abdoun", price_jd=180000.0, area_m2=180.0,
                 listing_type="sale", property_type="apartment",
                 listing_date="2026-05-01", **over) -> Listing:
    _SEQ[0] += 1
    lid = over.pop("listing_id", f"syn-{_SEQ[0]:04d}")
    row = dict(
        listing_id=lid, portal="synthetic",
        listing_url=f"https://example.invalid/{lid}",
        listing_type=listing_type, property_type=property_type,
        neighborhood=neighborhood, price_jd=str(price_jd), area_m2=str(area_m2),
        listing_date=listing_date, source_name="Synthetic Fixture",
        source_url=f"https://example.invalid/{lid}", capture_date="2026-07-07",
        confidence="M",
    )
    row.update({k: (str(v) if v is not None else "") for k, v in over.items()})
    return Listing.from_row(row)


def pool_around(n, neighborhood="Abdoun", base_ppm2=1000.0, area_m2=180.0,
                spread=0.05, **over) -> list[Listing]:
    """n plausible same-submarket sale comps clustered around base_ppm2."""
    out = []
    for i in range(n):
        ppm2 = base_ppm2 * (1 + spread * ((i % 5) - 2) / 2)
        out.append(make_listing(neighborhood=neighborhood, area_m2=area_m2,
                                 price_jd=round(ppm2 * area_m2, 1), **over))
    return out


def bundle_of(listings, *, costs=None, projects=None, evidence=None,
              index=None, as_of=AS_OF) -> DataBundle:
    return DataBundle(
        listings=listings,
        cost_benchmarks=costs if costs is not None else [_std_cost()],
        evidence_items=evidence if evidence is not None else [],
        projects=projects if projects is not None else [],
        price_index=index if index is not None else _current_index(),
        as_of=as_of,
    )


def _std_cost() -> CostBenchmark:
    return CostBenchmark(spec_class="high", low=520.0, high=680.0, year=2026,
                         source_name="Cost Bench", source_url="https://example.invalid/cost",
                         capture_date="2026-06-01", confidence="M")


def _current_index() -> PriceIndex:
    """Quarterly index growing to a quarter close to AS_OF (so it is 'current')."""
    idx = PriceIndex()
    series = {}
    quarters = [(y, q) for y in range(2023, 2027) for q in (1, 2, 3, 4)]
    quarters = [q for q in quarters if not (q[0] == 2026 and q[1] > 2)]  # through 2026-Q2
    val = 100.0
    for y, q in quarters:
        series[f"{y}-Q{q}"] = round(val, 1)
        val *= 1.02
    idx.series["cbj_repi_apartment"] = series
    idx.source = {"name": "Central Bank of Jordan", "url": "https://www.cbj.gov.jo/idx",
                  "capture_date": "2026-07-01"}
    return idx


def _stale_index_2021q3() -> PriceIndex:
    idx = PriceIndex()
    series = {}
    val = 90.0
    for y in (2019, 2020, 2021):
        for q in (1, 2, 3, 4):
            if y == 2021 and q > 3:
                continue
            series[f"{y}-Q{q}"] = round(val, 1)
            val *= 1.015
    idx.series["cbj_repi_apartment"] = series
    idx.source = {"name": "Central Bank of Jordan", "url": "https://www.cbj.gov.jo/idx",
                  "capture_date": "2021-10-01"}
    return idx


def subj(**over) -> Subject:
    base = dict(neighborhood="Abdoun", property_type="apartment", area_m2=180.0)
    base.update(over)
    return Subject(**base)


def _ordered(r) -> bool:
    return r.min_safe_price_jd_m2 <= r.recommended_price_jd_m2 <= r.premium_price_jd_m2


def _finite_nonneg(r) -> bool:
    vals = [r.min_safe_price_jd_m2, r.recommended_price_jd_m2, r.premium_price_jd_m2]
    return all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in vals)


# ---------------------------------------------------------------------------
# thin market / comp count
# ---------------------------------------------------------------------------

class ThinAndEmptyMarket(unittest.TestCase):
    def test_zero_comps_returns_safe_empty_not_crash(self):
        r = recommend(subj(neighborhood="Abdoun"), bundle_of([]), AS_OF)
        self.assertEqual(r.recommended_price_jd_m2, 0.0)
        self.assertEqual(r.premium_price_jd_m2, 0.0)
        self.assertEqual(r.confidence_label, "L")
        self.assertTrue(r.risk_factors)
        json.dumps(r.to_dict())

    def test_zero_comps_in_target_but_data_elsewhere(self):
        # data exists, but none in the requested submarket -> unpriceable, not a leak
        other = pool_around(8, neighborhood="Khalda", base_ppm2=1000.0)
        r = recommend(subj(neighborhood="Abdoun"), bundle_of(other), AS_OF)
        self.assertEqual(r.recommended_price_jd_m2, 0.0)

    def test_single_comparable_prices_but_flags_thin(self):
        r = recommend(subj(), bundle_of(pool_around(1, base_ppm2=1000.0)), AS_OF)
        self.assertGreater(r.recommended_price_jd_m2, 0)
        self.assertTrue(_ordered(r) and _finite_nonneg(r))
        self.assertTrue(any("thin" in rk["factor"].lower() for rk in r.risk_factors))
        lo, hi = r.confidence_interval_jd_m2
        self.assertLess(lo, r.recommended_price_jd_m2)
        self.assertLess(r.recommended_price_jd_m2, hi)

    def test_two_comparables_still_thin(self):
        r = recommend(subj(), bundle_of(pool_around(2, base_ppm2=1000.0)), AS_OF)
        self.assertTrue(any("thin" in rk["factor"].lower() for rk in r.risk_factors))

    def test_confidence_interval_widens_as_market_thins(self):
        def width(n):
            r = recommend(subj(), bundle_of(pool_around(n, base_ppm2=1000.0, spread=0.05)),
                          AS_OF)
            return (r.premium_price_jd_m2 - r.min_safe_price_jd_m2) / r.recommended_price_jd_m2
        thin, rich = width(2), width(12)
        self.assertGreater(thin, rich,
                           f"thin band ({thin:.3f}) should be wider than rich ({rich:.3f})")

    def test_thin_market_confidence_not_higher_than_rich(self):
        thin = recommend(subj(), bundle_of(pool_around(2, base_ppm2=1000.0)), AS_OF)
        rich = recommend(subj(), bundle_of(pool_around(12, base_ppm2=1000.0)), AS_OF)
        self.assertLessEqual(thin.confidence_numeric, rich.confidence_numeric)


# ---------------------------------------------------------------------------
# area boundaries
# ---------------------------------------------------------------------------

class AreaBoundaries(unittest.TestCase):
    def setUp(self):
        self.b = bundle_of(pool_around(10, base_ppm2=1000.0, area_m2=180.0))

    def test_zero_area_degrades_not_crashes(self):
        # BUG-1 (was xfail): area_m2 in {0, negative, inf, nan} used to divide by zero /
        # be silently priced (OBS-1/OBS-2). The engine now refuses to emit a confident band
        # from a corrupt area and returns an honest cannot-price result (rec=0) with an
        # explanatory risk factor. None stays valid (size unknown) — see test_none_area.
        for bad in (0, -50, float("inf"), float("nan")):
            r = recommend(subj(area_m2=bad), self.b, AS_OF)
            self.assertTrue(_finite_nonneg(r), f"area_m2={bad} produced a non-finite band")
            self.assertEqual(r.recommended_price_jd_m2, 0.0, f"area_m2={bad} should not price")
            self.assertTrue(any("area" in (rk["factor"] + rk["detail"]).lower()
                                for rk in r.risk_factors),
                            f"area_m2={bad} lacks an explanatory area risk factor")
            json.dumps(r.to_dict())

    def test_tiny_area_1m2(self):
        r = recommend(subj(area_m2=1), self.b, AS_OF)
        self.assertTrue(_ordered(r) and _finite_nonneg(r))
        self.assertGreater(r.recommended_price_jd_m2, 0)

    def test_huge_area_100000m2(self):
        r = recommend(subj(area_m2=100000), self.b, AS_OF)
        self.assertTrue(_ordered(r) and _finite_nonneg(r))

    def test_none_area(self):
        r = recommend(subj(area_m2=None), self.b, AS_OF)
        self.assertTrue(_ordered(r) and _finite_nonneg(r))

    def test_negative_area_does_not_crash(self):
        # Physically impossible; API blocks it (gt=0). Engine currently PRICES it silently.
        # Minimum bar: it must not crash and must stay finite. Silent acceptance is logged
        # as an observation in the QA report (validation gap), not asserted here.
        r = recommend(subj(area_m2=-50), self.b, AS_OF)
        self.assertTrue(_finite_nonneg(r))

    def test_nonfinite_area_does_not_crash(self):
        for bad in (float("inf"), float("nan")):
            r = recommend(subj(area_m2=bad), self.b, AS_OF)
            self.assertTrue(_finite_nonneg(r),
                            f"non-finite subject area {bad} produced a non-finite price band")


# ---------------------------------------------------------------------------
# unknown attributes
# ---------------------------------------------------------------------------

class UnknownAttributes(unittest.TestCase):
    def test_all_attributes_unknown_prices_and_flags(self):
        b = bundle_of(pool_around(10, base_ppm2=1000.0))
        r = recommend(subj(view="unknown", parking="unknown", finish_quality="unknown",
                           furnishing="unknown", elevator="unknown", floor_level=None,
                           building_age_years=None), b, AS_OF)
        self.assertGreater(r.recommended_price_jd_m2, 0)
        self.assertTrue(_ordered(r) and _finite_nonneg(r))
        # no categorical/continuous adjustment can be applied when subject side is unknown
        for c in r.comparables:
            applied = c["adjustments_applied"]
            self.assertNotIn("View", applied)
            self.assertNotIn("Finish quality", applied)

    def test_unknown_finish_surfaces_risk(self):
        b = bundle_of(pool_around(10, base_ppm2=1000.0))
        r = recommend(subj(finish_quality="unknown", furnishing="unknown"), b, AS_OF)
        blob = " ".join((rk["factor"] + rk["detail"]).lower() for rk in r.risk_factors)
        self.assertIn("unknown", blob)


# ---------------------------------------------------------------------------
# outlier-heavy pool
# ---------------------------------------------------------------------------

class OutlierRobustness(unittest.TestCase):
    def test_zero_price_and_whole_building_placeholders_are_ignored(self):
        good = pool_around(10, base_ppm2=1000.0, area_m2=180.0)
        junk = [
            make_listing(price_jd=0.0, area_m2=180.0),              # 0-price -> ppm2 0
            make_listing(price_jd=1.0, area_m2=180.0),              # ~0 ppm2
            make_listing(price_jd=400000.0, area_m2=3000.0),        # whole building ~133 ppm2
        ]
        r = recommend(subj(), bundle_of(good + junk), AS_OF)
        # anchored on ~1000; the sub-250 placeholders must be filtered out
        self.assertGreater(r.recommended_price_jd_m2, 500)
        self.assertLess(r.recommended_price_jd_m2, 1500)

    def test_extreme_high_outlier_does_not_dominate(self):
        good = pool_around(10, base_ppm2=1000.0)
        r_clean = recommend(subj(), bundle_of(good), AS_OF)
        spiked = good + [make_listing(price_jd=9000.0 * 180, area_m2=180.0)]  # ~9000 ppm2
        r_spiked = recommend(subj(), bundle_of(spiked), AS_OF)
        drift = abs(r_spiked.recommended_price_jd_m2 - r_clean.recommended_price_jd_m2)
        self.assertLess(drift / r_clean.recommended_price_jd_m2, 0.20,
                        "one extreme outlier moved the recommendation more than 20%")

    def test_negative_price_rows_are_filtered(self):
        good = pool_around(8, base_ppm2=1000.0)
        r = recommend(subj(), bundle_of(good + [make_listing(price_jd=-50000.0)]), AS_OF)
        self.assertGreater(r.recommended_price_jd_m2, 400)


# ---------------------------------------------------------------------------
# time adjustment / stale index
# ---------------------------------------------------------------------------

class TimeAdjustment(unittest.TestCase):
    def test_stale_index_2021q3_disables_time_adjustment(self):
        # Index ends 2021-Q3, run date 2026 -> engine must NOT extrapolate backward.
        old = pool_around(8, base_ppm2=1000.0, listing_date="2023-02-01")
        r = recommend(subj(), bundle_of(old, index=_stale_index_2021q3()), AS_OF)
        for c in r.comparables:
            self.assertFalse(any(a["factor"] == "Time (market movement)"
                                 for a in c["adjustments"]),
                             "stale index must not drive a time adjustment")
        self.assertFalse(any(e["factor"] == "Time (market movement)"
                             for e in r.evidence_objects))
        blob = " ".join(rk["factor"].lower() for rk in r.risk_factors)
        self.assertIn("index not current", blob)

    def test_current_index_time_adjusts_stale_comps_and_evidences_it(self):
        old = pool_around(8, base_ppm2=1000.0, listing_date="2024-01-15")  # >12 mo old
        r = recommend(subj(), bundle_of(old, index=_current_index()), AS_OF)
        timed = [c for c in r.comparables
                 if any(a["factor"] == "Time (market movement)" for a in c["adjustments"])]
        self.assertTrue(timed, "old comps under a current index must be time-adjusted")
        for c in timed:
            self.assertNotAlmostEqual(c["original_ppm2"], c["time_adjusted_ppm2"], places=1)
        te = [e for e in r.evidence_objects if e["factor"] == "Time (market movement)"]
        self.assertTrue(te and "CBJ" in te[0]["method"])
        self.assertEqual(te[0]["datasets"], ["macro_series (CBJ index)"])

    def test_recent_comps_are_not_time_adjusted(self):
        recent = pool_around(8, base_ppm2=1000.0, listing_date="2026-05-01")
        r = recommend(subj(), bundle_of(recent, index=_current_index()), AS_OF)
        for c in r.comparables:
            self.assertFalse(any(a["factor"] == "Time (market movement)"
                                 for a in c["adjustments"]))


# ---------------------------------------------------------------------------
# empty auxiliary tables must degrade, not crash
# ---------------------------------------------------------------------------

class EmptyAuxTables(unittest.TestCase):
    def _priced(self, **kw):
        listings = pool_around(10, base_ppm2=1000.0)
        return recommend(subj(finish_quality="high"),
                         bundle_of(listings, **kw), AS_OF)

    def test_empty_cost_benchmarks(self):
        r = self._priced(costs=[])
        self.assertGreater(r.recommended_price_jd_m2, 0)
        self.assertTrue(any("cost-approach floor" in rk["detail"].lower()
                            or "cost" in rk["factor"].lower() for rk in r.risk_factors))

    def test_empty_projects(self):
        r = self._priced(projects=[])
        self.assertFalse(any(e["factor"] == "Competitive positioning"
                             for e in r.evidence_objects))
        self.assertGreater(r.recommended_price_jd_m2, 0)

    def test_empty_evidence_items(self):
        r = self._priced(evidence=[])
        self.assertFalse(any(e["category"] == "future_signal"
                             for e in r.evidence_objects))
        self.assertTrue(any("future" in rk["factor"].lower() for rk in r.risk_factors))

    def test_all_aux_empty_and_no_index(self):
        listings = pool_around(10, base_ppm2=1000.0)
        r = recommend(subj(), bundle_of(listings, costs=[], projects=[], evidence=[],
                                        index=PriceIndex()), AS_OF)
        self.assertGreater(r.recommended_price_jd_m2, 0)
        self.assertTrue(_ordered(r) and _finite_nonneg(r))
        json.dumps(r.to_dict())

    def test_completely_empty_bundle(self):
        r = recommend(subj(), DataBundle(as_of=AS_OF), AS_OF)
        self.assertEqual(r.recommended_price_jd_m2, 0.0)
        json.dumps(r.to_dict())


# ---------------------------------------------------------------------------
# arms-length / comp-hygiene (research: exclude non-comparable transactions)
# ---------------------------------------------------------------------------

class CompHygiene(unittest.TestCase):
    def test_rentals_are_not_used_as_sale_comps(self):
        sales = pool_around(6, base_ppm2=1000.0)
        rents = pool_around(6, base_ppm2=6.0, listing_type="rent")  # monthly rent ppm2
        r = recommend(subj(), bundle_of(sales + rents), AS_OF)
        self.assertGreater(r.recommended_price_jd_m2, 400)  # not dragged toward rent ppm2

    def test_other_property_types_are_not_mixed_in(self):
        apts = pool_around(6, base_ppm2=1000.0, property_type="apartment")
        villas = pool_around(6, base_ppm2=3000.0, property_type="villa")
        r = recommend(subj(property_type="apartment"), bundle_of(apts + villas), AS_OF)
        # villa comps (3000) must not inflate an apartment recommendation
        self.assertLess(r.recommended_price_jd_m2, 1600)

    def test_wrong_neighborhood_not_mixed_in(self):
        here = pool_around(6, neighborhood="Abdoun", base_ppm2=1000.0)
        there = pool_around(6, neighborhood="Khalda", base_ppm2=2500.0)
        r = recommend(subj(neighborhood="Abdoun"), bundle_of(here + there), AS_OF)
        self.assertLess(r.recommended_price_jd_m2, 1500)


# ---------------------------------------------------------------------------
# near-duplicate collapse (OBS-3: same unit cross-posted across portals)
# ---------------------------------------------------------------------------

class NearDuplicateCollapse(unittest.TestCase):
    def _unit(self, lid, ppm2=1000.0, area=180.0, beds=3, portal="bayut", **over):
        return make_listing(listing_id=lid, area_m2=area, price_jd=round(ppm2 * area, 1),
                            bedrooms=beds, portal=portal, **over)

    def test_cross_posted_unit_collapses_to_one(self):
        dups = [self._unit(f"dup-{p}", ppm2=1500.0, area=200.0, beds=3, portal=p)
                for p in ("bayut", "opensooq", "facebook")]
        distinct = [self._unit("d1", ppm2=1000.0, area=150.0, beds=2),
                    self._unit("d2", ppm2=1100.0, area=181.0, beds=3)]
        reps, collapsed = collapse_near_duplicates(dups + distinct)
        self.assertEqual(collapsed, 2)          # 3 copies -> 1 representative
        self.assertEqual(len(reps), 3)          # 1 rep + 2 genuinely distinct units

    def test_distinct_price_is_not_over_collapsed(self):
        a = self._unit("a", ppm2=1000.0, area=180.0, beds=3)
        b = self._unit("b", ppm2=1100.0, area=180.0, beds=3)  # +10% price -> distinct
        reps, collapsed = collapse_near_duplicates([a, b])
        self.assertEqual(collapsed, 0)
        self.assertEqual(len(reps), 2)

    def test_different_bedrooms_are_not_collapsed(self):
        a = self._unit("a", ppm2=1000.0, area=180.0, beds=2)
        b = self._unit("b", ppm2=1000.0, area=180.0, beds=3)  # same area/price, diff beds
        _, collapsed = collapse_near_duplicates([a, b])
        self.assertEqual(collapsed, 0)

    def test_unknown_bedrooms_never_collapse(self):
        # conservative: without bedrooms we cannot confirm same unit, so keep both
        a = make_listing(listing_id="u1", area_m2=180.0, price_jd=180000.0)  # beds None
        b = make_listing(listing_id="u2", area_m2=180.0, price_jd=180000.0)  # beds None
        _, collapsed = collapse_near_duplicates([a, b])
        self.assertEqual(collapsed, 0)

    def test_representative_is_the_most_complete_row(self):
        sparse = self._unit("sparse", ppm2=1500.0, area=200.0, beds=3)
        rich = self._unit("rich", ppm2=1500.0, area=200.0, beds=3,
                          view="city", parking="covered", finish_quality="high",
                          floor_level=4, bathrooms=2)
        reps, collapsed = collapse_near_duplicates([sparse, rich])
        self.assertEqual(collapsed, 1)
        self.assertEqual(reps[0].listing_id, "rich")

    def test_duplicates_do_not_inflate_recommendation(self):
        base = [self._unit(f"g{i}", ppm2=800.0 + i * 40, area=180.0, beds=3) for i in range(8)]
        r_clean = recommend(subj(), bundle_of(base), AS_OF)
        spam = [self._unit(f"spam-{p}", ppm2=1800.0, area=210.0, beds=3, portal=p)
                for p in ("bayut", "opensooq", "facebook", "fb2", "os2")]
        r_spam = recommend(subj(), bundle_of(base + spam), AS_OF)
        drift = (abs(r_spam.recommended_price_jd_m2 - r_clean.recommended_price_jd_m2)
                 / r_clean.recommended_price_jd_m2)
        self.assertLess(drift, 0.06,
                        f"cross-posted duplicates moved the recommendation {drift*100:.1f}%")


# ---------------------------------------------------------------------------
# neighborhood spatial-context chip (non-priced; must never move the band)
# ---------------------------------------------------------------------------

class NeighborhoodGeoContextChip(unittest.TestCase):
    def _geo(self, neighborhood="Abdoun") -> NeighborhoodGeoContext:
        return NeighborhoodGeoContext(
            neighborhood=neighborhood, median_elevation_m=913.5, elevation_rank=4,
            median_population_density=25032.2, median_nightlight=80.57, dominant_aspect="NE",
            context="Dense, high-activity premium submarket on mid-elevation ground.",
            source_name="Copernicus DEM / GHS-POP / VIIRS",
            source_url="https://copernicus-dem-30m.s3.amazonaws.com | "
                       "https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php | "
                       "https://doi.org/10.7910/DVN/YGIVCD",
            capture_date="2026-07-07", confidence="M")

    def _bundle(self, geo: list) -> DataBundle:
        b = bundle_of(pool_around(10, base_ppm2=1000.0))
        b.geocontext = geo
        return b

    def test_chip_present_current_state_and_non_numeric(self):
        r = recommend(subj(neighborhood="Abdoun"), self._bundle([self._geo("Abdoun")]), AS_OF)
        chips = [e for e in r.evidence_objects if e["factor"] == "Neighborhood spatial context"]
        self.assertEqual(len(chips), 1)
        e = chips[0]
        self.assertEqual(e["category"], "current_state")
        self.assertNotRegex(e["adjustment"], r"\d")   # a label, never a number
        self.assertIn("does not move the price", e["explanation"])
        self.assertTrue(e["sources"] and all(s["url"].startswith("http") for s in e["sources"]))

    def test_chip_omitted_without_fabrication(self):
        r = recommend(subj(neighborhood="Abdoun"), self._bundle([]), AS_OF)
        self.assertFalse(any(e["factor"] == "Neighborhood spatial context"
                             for e in r.evidence_objects))
        # uncovered subject stays uncovered even when a different submarket has a row
        r2 = recommend(subj(neighborhood="Abdoun"), self._bundle([self._geo("Khalda")]), AS_OF)
        self.assertFalse(any(e["factor"] == "Neighborhood spatial context"
                             for e in r2.evidence_objects))

    def test_chip_does_not_change_price_band_or_confidence(self):
        with_geo = recommend(subj(neighborhood="Abdoun"),
                             self._bundle([self._geo("Abdoun")]), AS_OF)
        without = recommend(subj(neighborhood="Abdoun"), self._bundle([]), AS_OF)
        self.assertTrue(any(e["factor"] == "Neighborhood spatial context"
                            for e in with_geo.evidence_objects))
        self.assertEqual(
            (with_geo.min_safe_price_jd_m2, with_geo.recommended_price_jd_m2,
             with_geo.premium_price_jd_m2),
            (without.min_safe_price_jd_m2, without.recommended_price_jd_m2,
             without.premium_price_jd_m2))
        self.assertEqual(with_geo.confidence_numeric, without.confidence_numeric)


# ---------------------------------------------------------------------------
# HARD INVARIANTS on the rich sample bundle
# ---------------------------------------------------------------------------

class HardInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_sample_bundle(AS_OF)
        cls.r = recommend(Subject(neighborhood="Abdoun", property_type="apartment",
                                  area_m2=170, floor_level=5, view="city",
                                  parking="covered", building_age_years=0,
                                  finish_quality="high", elevator="y",
                                  location_id="inv-1"), cls.bundle, AS_OF)

    def test_every_applied_adjustment_has_evidence_object(self):
        ev_factors = [e["factor"] for e in self.r.evidence_objects]
        for comp in self.r.comparables:
            for adj in comp["adjustments"]:
                factor = adj["factor"]
                if factor in _CONTEXT_FACTORS:
                    continue
                covered = any(f == factor or f.startswith(factor) for f in ev_factors)
                self.assertTrue(covered, f"applied adjustment '{factor}' has no evidence object")

    def test_every_evidence_object_has_a_real_source_url(self):
        self.assertTrue(self.r.evidence_objects)
        for e in self.r.evidence_objects:
            self.assertTrue(e["sources"], f"evidence '{e['factor']}' has zero sources")
            for s in e["sources"]:
                url = (s.get("url") or "").strip()
                self.assertTrue(url, f"evidence '{e['factor']}' has an empty source url")
                self.assertNotEqual(url.lower(), "unknown",
                                    f"evidence '{e['factor']}' source url is the 'unknown' placeholder")

    def test_attribute_premium_evidence_cites_an_external_url(self):
        # market-derived attribute premiums must trace to a portal listing (http[s]),
        # never only an internal:// sentinel.
        attr_labels = ("View", "Covered parking", "Elevator", "Finish quality",
                       "Furnishing", "Floor level", "Building age", "Size (per m")
        for e in self.r.evidence_objects:
            if any(e["factor"].startswith(lbl) for lbl in attr_labels):
                urls = [(s.get("url") or "") for s in e["sources"]]
                self.assertTrue(any(u.startswith("http") for u in urls),
                                f"attribute evidence '{e['factor']}' cites no external url: {urls}")

    def test_evidence_objects_are_well_formed(self):
        required = {"factor", "adjustment", "confidence", "method", "datasets",
                    "sources", "category", "explanation"}
        for e in self.r.evidence_objects:
            self.assertTrue(required.issubset(e.keys()))
            self.assertIn(e["category"], ("current_state", "future_signal"))

    def test_derived_premiums_are_derived_with_sample_size(self):
        premiums = self.r.method_values["derived_premiums"]
        self.assertTrue(premiums)
        for p in premiums:
            self.assertGreater(p["sample_size"], 0)
            self.assertTrue(("differential" in p["method"]) or ("slope" in p["method"]),
                            f"premium '{p['factor']}' not derived from data: {p['method']}")
            self.assertNotIn("hardcod", p["method"].lower())


class NoHardcodedWeights(unittest.TestCase):
    """The whole project's central rule: attribute premiums are DERIVED, never constants.
    Scan EVERY engine module (not just three) for an attribute-name -> fraction map."""

    # Attribute-VALUE tokens only. "high"/"standard" are deliberately excluded: they
    # collide with confidence labels ("High": 1.0 is a source-trust weight, not a price).
    # Finish premiums are covered behaviourally by test_premiums_change_with_the_data.
    ATTR_FRACTION = re.compile(
        r"""["']?(sea|city|panoramic|garden|mountain|covered|open|luxury|basic)["']?\s*:\s*[-+]?1?\.\d""",
        re.IGNORECASE)
    MULT_TABLE = re.compile(r"_MULT\s*=\s*\{")

    def _engine_modules(self):
        skip = {"test_pipeline.py", "emit_sample.py"}
        for fn in os.listdir(_ENGINE_DIR):
            if fn.endswith(".py") and fn not in skip:
                yield fn

    def test_no_attribute_fraction_maps_in_any_engine_module(self):
        for fn in self._engine_modules():
            with open(os.path.join(_ENGINE_DIR, fn), encoding="utf-8") as fh:
                src = fh.read()
            self.assertIsNone(self.ATTR_FRACTION.search(src),
                              f"possible hardcoded attribute premium constant in engine/{fn}")
            self.assertIsNone(self.MULT_TABLE.search(src),
                              f"DGP multiplier table leaked into engine/{fn}")

    def test_premiums_change_with_the_data(self):
        # If premiums were hardcoded, two different pools would yield identical premiums.
        b1 = bundle_of(pool_around(10, base_ppm2=1000.0, view="city")
                       + pool_around(10, base_ppm2=1200.0, view="sea"))
        b2 = bundle_of(pool_around(10, base_ppm2=1000.0, view="city")
                       + pool_around(10, base_ppm2=1600.0, view="sea"))
        p1 = recommend(subj(view="sea"), b1, AS_OF).method_values["derived_premiums"]
        p2 = recommend(subj(view="sea"), b2, AS_OF).method_values["derived_premiums"]

        def view_prem(ps):
            for p in ps:
                if p["factor"].startswith("View"):
                    return p["derived_premium"]
            return None
        v1, v2 = view_prem(p1), view_prem(p2)
        self.assertIsNotNone(v1)
        self.assertIsNotNone(v2)
        self.assertNotAlmostEqual(v1, v2, places=3,
                                  msg="view premium did not change with the data — looks hardcoded")


_DB_PATH = os.path.join(os.path.dirname(_ENGINE_DIR), "..", "db", "jordan_re.sqlite")


@unittest.skipUnless(os.path.exists(_DB_PATH), "real DB not present")
class RealDbInvariantFuzz(unittest.TestCase):
    """Deterministic property-based sweep over the real DB: for hundreds of random but
    valid subjects, the price band and confidence must stay finite, ordered and bounded."""

    def test_invariants_hold_across_random_subjects(self):
        import random
        from app.engine.data import load_bundle_from_sqlite
        b = load_bundle_from_sqlite(_DB_PATH, AS_OF)
        rng = random.Random(7)
        nbhd = ("Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani")
        ptype = ("apartment", "villa", "land", "commercial")
        views = ("unknown", "none", "city", "garden", "mountain", "panoramic")
        finish = ("unknown", "basic", "standard", "high", "luxury")
        for _ in range(300):
            s = Subject(neighborhood=rng.choice(nbhd), property_type=rng.choice(ptype),
                        area_m2=rng.choice([25, 80, 150, 175, 300, 900, None]),
                        floor_level=rng.choice([None, 0, 3, 15, 40]),
                        view=rng.choice(views), finish_quality=rng.choice(finish),
                        building_age_years=rng.choice([None, 0, 5, 30]))
            r = recommend(s, b, AS_OF)
            self.assertTrue(_finite_nonneg(r), f"non-finite band for {s}")
            self.assertTrue(_ordered(r), f"band not ordered for {s}")
            self.assertTrue(0.0 <= r.confidence_numeric <= 1.0)
            self.assertIn(r.confidence_label, ("H", "M", "L"))
            if r.recommended_price_jd_m2 > 0:
                lo, hi = r.confidence_interval_jd_m2
                self.assertLess(lo, r.recommended_price_jd_m2)
                self.assertLess(r.recommended_price_jd_m2, hi)


if __name__ == "__main__":
    unittest.main(verbosity=2)
