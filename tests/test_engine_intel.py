"""Requirement-driven tests for the intelligence layer added on top of the pricing engine:

  * decomposed confidence (five product components, 0-100 or null-with-reason)
  * builder height/city-view premium (explicit assumption) + residual land value
  * scenario simulation (levers flow through the engine, never a hand-set price)
  * opportunity score + area catalogue

Pure functions are tested directly; the engine-integration cases run on the real DB when it is
present (skipped otherwise) and on tiny synthetic bundles for the not-computable (null) paths.

Run:  python -m pytest tests/test_engine_intel.py -v      (from repo root)
"""

from __future__ import annotations

import math
import os
import unittest
from datetime import date

from app.engine import builder, opportunity, scenario
from app.engine.data import DataBundle
from app.engine.models import Listing, Subject
from app.engine.pipeline import recommend

AS_OF = date(2026, 7, 8)
_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "db", "jordan_re.sqlite")
_COVERED = ["Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"]
_SEQ = [0]


def _listing(neighborhood="Abdoun", ppm2=1000.0, area=180.0, **over) -> Listing:
    _SEQ[0] += 1
    lid = f"intel-{_SEQ[0]:04d}"
    row = dict(listing_id=lid, portal="synthetic", listing_url=f"https://x.invalid/{lid}",
               listing_type="sale", property_type="apartment", neighborhood=neighborhood,
               price_jd=str(ppm2 * area), area_m2=str(area), listing_date="2026-05-01",
               source_name="Synthetic", source_url=f"https://x.invalid/{lid}",
               capture_date="2026-07-08", confidence="M")
    row.update({k: str(v) for k, v in over.items()})
    return Listing.from_row(row)


def _bundle(listings, **kw) -> DataBundle:
    return DataBundle(listings=listings, as_of=AS_OF, **kw)


class DecomposedConfidence(unittest.TestCase):
    _KEYS = {"data_coverage", "comp_quality", "gov_evidence",
             "future_signals", "market_freshness"}

    def _components(self, result):
        return result.to_dict()["confidence"]["components"]

    def test_all_five_components_present_with_score_and_reason(self):
        b = _bundle([_listing(ppm2=1000 + i) for i in range(12)])
        comps = self._components(recommend(Subject(neighborhood="Abdoun", area_m2=180), b, AS_OF))
        self.assertEqual(set(comps), self._KEYS)
        for name, c in comps.items():
            self.assertIn("score", c)
            self.assertIn("reason", c)
            self.assertIsInstance(c["reason"], str)
            self.assertTrue(c["reason"])
            if c["score"] is not None:
                self.assertTrue(0 <= c["score"] <= 100, f"{name}={c['score']} out of range")

    def test_future_signals_null_when_no_evidence_collected(self):
        b = _bundle([_listing(ppm2=1000 + i) for i in range(12)])  # no evidence_items
        comps = self._components(recommend(Subject(neighborhood="Abdoun", area_m2=180), b, AS_OF))
        self.assertIsNone(comps["future_signals"]["score"])
        self.assertIn("no infrastructure", comps["future_signals"]["reason"].lower())

    def test_gov_evidence_null_when_no_index_and_no_cost(self):
        b = _bundle([_listing(ppm2=1000 + i) for i in range(12)])  # no price index, no cost bench
        comps = self._components(recommend(Subject(neighborhood="Abdoun", area_m2=180), b, AS_OF))
        self.assertIsNone(comps["gov_evidence"]["score"])

    def test_overall_confidence_unchanged_by_decomposition(self):
        b = _bundle([_listing(ppm2=1000 + i) for i in range(12)])
        r = recommend(Subject(neighborhood="Abdoun", area_m2=180), b, AS_OF)
        self.assertEqual(r.to_dict()["confidence"]["numeric"], r.confidence_numeric)


class HeightViewPremium(unittest.TestCase):
    def test_no_premium_at_or_below_threshold(self):
        self.assertEqual(builder.height_view_premium(5, 20)["fraction"], 0.0)
        self.assertEqual(builder.height_view_premium(1, 20)["fraction"], 0.0)
        self.assertEqual(builder.height_view_premium(None, 20)["fraction"], 0.0)

    def test_ramps_and_caps_at_max(self):
        top = builder.height_view_premium(20, 20)["fraction"]
        self.assertAlmostEqual(top, builder.HEIGHT_VIEW_PREMIUM_MAX, places=4)
        mid = builder.height_view_premium(12, 20)["fraction"]
        self.assertTrue(0 < mid < top)

    def test_never_exceeds_configured_max(self):
        for f in range(0, 60):
            frac = builder.height_view_premium(f, 30)["fraction"]
            self.assertLessEqual(frac, builder.HEIGHT_VIEW_PREMIUM_MAX + 1e-9)

    def test_assumption_parameters_surfaced(self):
        a = builder.height_view_premium(15, 20)["assumption"]
        self.assertIn("max_premium_pct", a)
        self.assertIn("floor_threshold", a)
        self.assertIn("not data-derived", a["basis"].lower())

    def test_custom_max_is_respected(self):
        frac = builder.height_view_premium(30, 30, max_premium=0.25)["fraction"]
        self.assertAlmostEqual(frac, 0.25, places=4)

    def test_apply_uplifts_recommended_and_keeps_order(self):
        b = _bundle([_listing(ppm2=1000 + i) for i in range(12)])
        r = recommend(Subject(neighborhood="Abdoun", area_m2=180, floor_level=18), b, AS_OF)
        base_rec = r.recommended_price_jd_m2
        r2 = builder.apply_height_view_premium(r, 18, 22)
        self.assertGreater(r2.recommended_price_jd_m2, base_rec)
        self.assertLessEqual(r2.min_safe_price_jd_m2, r2.recommended_price_jd_m2)
        self.assertLessEqual(r2.recommended_price_jd_m2, r2.premium_price_jd_m2)
        lo, hi = r2.confidence_interval_jd_m2
        self.assertLess(lo, r2.recommended_price_jd_m2)
        self.assertLess(r2.recommended_price_jd_m2, hi)
        self.assertTrue(any("height" in e["factor"].lower() for e in r2.evidence_objects))


class ResidualLandValue(unittest.TestCase):
    def test_breakdown_sums_to_residual(self):
        r = builder.residual_land_value(1000, 1100, 500,
                                        finance_pct=0.06, professional_fees_pct=0.05,
                                        developer_profit_pct=0.2)
        line_sum = sum(l["value_jd"] for l in r["breakdown"])
        self.assertAlmostEqual(line_sum, r["residual_land_value_total_jd"], places=1)

    def test_per_m2_matches_total(self):
        r = builder.residual_land_value(1000, 1100, 500)
        self.assertAlmostEqual(r["residual_land_value_per_m2_jd"],
                               r["residual_land_value_total_jd"] / 1000, places=1)

    def test_manual_arithmetic(self):
        r = builder.residual_land_value(1000, 1000, 400,
                                        finance_pct=0.0, professional_fees_pct=0.0,
                                        developer_profit_pct=0.0)
        # GDV 1_000_000 - construction 400_000 = 600_000
        self.assertAlmostEqual(r["residual_land_value_total_jd"], 600000.0, places=1)

    def test_negative_residual_flagged_not_crashed(self):
        r = builder.residual_land_value(1000, 500, 900, developer_profit_pct=0.2)
        self.assertLess(r["residual_land_value_total_jd"], 0)
        self.assertFalse(r["viable"])
        self.assertIn("negative residual", r["explanation"].lower())


class ScenarioSimulation(unittest.TestCase):
    def _bundle(self):
        # 20 comps so a finish upgrade actually has adjustable comps.
        ls = [_listing(ppm2=980 + i * 5, finish_quality="standard") for i in range(10)]
        ls += [_listing(ppm2=1180 + i * 5, finish_quality="luxury") for i in range(10)]
        return _bundle(ls)

    def test_no_overrides_is_a_noop_delta(self):
        b = self._bundle()
        out = scenario.simulate(Subject(neighborhood="Abdoun", area_m2=180), b, {}, AS_OF)
        self.assertEqual(out["deltas"]["recommended_pct"], 0.0)
        self.assertEqual(out["levers_applied"], [])
        self.assertIn("base", out)
        self.assertIn("scenario", out)

    def test_finish_upgrade_moves_recommended(self):
        b = self._bundle()
        out = scenario.simulate(Subject(neighborhood="Abdoun", area_m2=180,
                                        finish_quality="standard"), b,
                                {"finish_quality": "luxury"}, AS_OF)
        self.assertIsNotNone(out["deltas"]["recommended_pct"])
        self.assertNotEqual(out["deltas"]["recommended_pct"], 0.0)
        self.assertTrue(out["levers_applied"])

    def test_deltas_have_all_keys(self):
        b = self._bundle()
        out = scenario.simulate(Subject(neighborhood="Abdoun", area_m2=180), b,
                                {"target_floor": 12}, AS_OF)
        self.assertEqual(set(out["deltas"]),
                         {"recommended_pct", "min_safe_pct", "premium_pct",
                          "confidence_change", "future_signals_change"})

    def test_height_premium_lever_uplifts_scenario_only(self):
        b = self._bundle()
        out = scenario.simulate(Subject(neighborhood="Abdoun", area_m2=180, floor_level=3), b,
                                {"target_floor": 18, "floors": 22,
                                 "apply_height_view_premium": True}, AS_OF)
        self.assertGreater(out["scenario"]["recommended_price_jd_m2"],
                           out["base"]["recommended_price_jd_m2"])


class OpportunityScore(unittest.TestCase):
    _COMPS = {"price_level", "price_growth", "demand_density",
              "supply_pressure", "future_signals"}

    def _bundle(self):
        ls = []
        for i, (n, ppm2) in enumerate([("Abdoun", 1100), ("Dabouq", 1050),
                                       ("Sweifieh", 900), ("Khalda", 750),
                                       ("Shmeisani", 770)]):
            ls += [_listing(neighborhood=n, ppm2=ppm2 + j) for j in range(15)]
        return _bundle(ls)

    def test_scores_finite_ranked_and_bounded(self):
        out = opportunity.opportunity_scores(self._bundle(), _COVERED, AS_OF)
        self.assertEqual(len(out), 5)
        scores = [r["score"] for r in out]
        for s in scores:
            self.assertTrue(math.isfinite(s) and 0 <= s <= 100)
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_components_present_and_weights_renormalize(self):
        out = opportunity.opportunity_scores(self._bundle(), _COVERED, AS_OF)
        for r in out:
            self.assertEqual(set(r["components"]), self._COMPS)
            self.assertAlmostEqual(sum(r["weights_used"].values()), 1.0, places=2)

    def test_missing_geocontext_yields_null_demand_not_crash(self):
        out = opportunity.opportunity_scores(self._bundle(), _COVERED, AS_OF)
        # synthetic bundle has no geocontext → demand_density is null with a reason
        for r in out:
            self.assertIsNone(r["components"]["demand_density"]["score"])
            self.assertTrue(r["components"]["demand_density"]["reason"])


class AreaCatalog(unittest.TestCase):
    def test_covered_flagged_and_unknown_excluded(self):
        ls = ([_listing(neighborhood="Abdoun") for _ in range(3)]
              + [_listing(neighborhood="Marj Al Hamam") for _ in range(2)]
              + [_listing(neighborhood="unknown")])
        cat = opportunity.area_catalog(_bundle(ls), {"Abdoun"},
                                       {"abdoun": (31.9, 35.8)})
        names = {a["name"]: a for a in cat}
        self.assertIn("Abdoun", names)
        self.assertIn("Marj Al Hamam", names)
        self.assertNotIn("unknown", names)
        self.assertTrue(names["Abdoun"]["covered"])
        self.assertFalse(names["Marj Al Hamam"]["covered"])
        self.assertEqual(names["Abdoun"]["listing_count"], 3)


class DecisionReadiness(unittest.TestCase):
    _DIMS = {"market_potential", "demand", "competition", "future_growth", "infrastructure",
             "regulatory_readiness", "pricing_confidence", "construction_feasibility"}
    _NULL_DIMS = {"future_growth", "infrastructure", "regulatory_readiness",
                  "construction_feasibility"}

    def _bundle(self):
        ls = []
        for n, ppm2 in [("Abdoun", 1100), ("Khalda", 780)]:
            ls += [_listing(neighborhood=n, ppm2=ppm2 + j) for j in range(15)]
        return _bundle(ls)

    def _readiness(self):
        out = opportunity.opportunity_scores(self._bundle(), ["Abdoun", "Khalda"], AS_OF)
        return out[0]["readiness"]

    def test_structure(self):
        r = self._readiness()
        self.assertEqual(set(r["dimensions"]), self._DIMS)
        self.assertIn("overall", r)
        self.assertEqual(r["version"], "v1-heuristic")
        for name, d in r["dimensions"].items():
            self.assertEqual(set(d), {"score", "reason", "confidence"})
            self.assertIn(d["confidence"], ("high", "medium", "low"))
            self.assertTrue(d["reason"])
            if d["score"] is not None:
                self.assertTrue(0 <= d["score"] <= 100)

    def test_unavailable_dims_are_null_with_enrichment_reason(self):
        dims = self._readiness()["dimensions"]
        for k in self._NULL_DIMS:
            self.assertIsNone(dims[k]["score"], f"{k} must be null (not fabricated)")
            self.assertIn("enrichment", dims[k]["reason"].lower())
            self.assertEqual(dims[k]["confidence"], "low")

    def test_computed_dims_present(self):
        dims = self._readiness()["dimensions"]
        # pricing_confidence + competition are always computable from the bundle
        self.assertIsNotNone(dims["pricing_confidence"]["score"])
        self.assertIsNotNone(dims["competition"]["score"])

    def test_overall_is_weighted_mean_over_non_null_and_weights_renormalize(self):
        r = self._readiness()
        self.assertIsNotNone(r["overall"]["score"])
        self.assertTrue(0 <= r["overall"]["score"] <= 100)
        self.assertAlmostEqual(sum(r["weights_used"].values()), 1.0, places=2)
        # every weight_used key corresponds to a non-null dimension
        for k in r["weights_used"]:
            self.assertIsNotNone(r["dimensions"][k]["score"])

    def test_construction_feasibility_non_null_with_dos_cost(self):
        from app.engine.data import ConstructionCost
        cc = ConstructionCost(174.8, 157.4, 12, "2026-Q1", "DoS", "internal://dos",
                              "2026-07-08", "floor caveat")
        ls = [_listing(neighborhood="Abdoun", ppm2=1100 + j) for j in range(15)]
        ls += [_listing(neighborhood="Khalda", ppm2=780 + j) for j in range(15)]
        bundle = DataBundle(listings=ls, construction_cost=cc, as_of=AS_OF)
        out = opportunity.opportunity_scores(bundle, ["Abdoun", "Khalda"], AS_OF)
        cf = out[0]["readiness"]["dimensions"]["construction_feasibility"]
        self.assertIsNotNone(cf["score"])
        self.assertEqual(cf["confidence"], "medium")
        self.assertTrue(0 <= cf["score"] <= 100)


class Feasibility(unittest.TestCase):
    _DIMS = {"regulatory_zoning", "construction_engineering", "operational_market",
             "environmental", "legal", "financial"}

    def _bundle(self):
        from app.engine.data import CostBenchmark
        ls = [_listing(neighborhood="Abdoun", ppm2=1100 + j) for j in range(10)]
        costs = [CostBenchmark("standard", 480, 560, 2026, "TestSrc", "https://x.invalid/c",
                               "2026-07-08", "M")]
        return DataBundle(listings=ls, cost_benchmarks=costs, as_of=AS_OF)

    def test_all_dims_present_with_valid_status(self):
        f = opportunity.feasibility_for(self._bundle(), "Abdoun")
        self.assertEqual(set(f["dimensions"]), self._DIMS)
        for name, d in f["dimensions"].items():
            self.assertIn(d["status"], ("available", "partial", "not_available"))
            self.assertTrue(d["detail"])
            self.assertIsInstance(d["sources"], list)
        self.assertEqual(sum(f["summary"].values()), len(self._DIMS))

    def test_operational_available_from_listings(self):
        f = opportunity.feasibility_for(self._bundle(), "Abdoun")
        self.assertEqual(f["dimensions"]["operational_market"]["status"], "available")
        self.assertIn("median_sale_jd_m2", f["dimensions"]["operational_market"]["value"])

    def test_construction_available_with_dos_cost(self):
        cons = {"value": 174.8, "authority": "Greater Amman",
                "source": {"name": "DoS", "url": "internal://dos", "capture_date": "2026-07-08"}}
        f = opportunity.feasibility_for(self._bundle(), "Abdoun", construction=cons)
        d = f["dimensions"]["construction_engineering"]
        self.assertEqual(d["status"], "available")
        self.assertAlmostEqual(d["value"]["construction_cost_jd_m2"], 174.8, places=1)
        self.assertIn("floor", d["detail"].lower())

    def test_construction_not_available_without_dos(self):
        f = opportunity.feasibility_for(self._bundle(), "Abdoun")
        self.assertEqual(f["dimensions"]["construction_engineering"]["status"], "not_available")

    def test_regulatory_partial_only_with_zoning_else_not_available(self):
        without = opportunity.feasibility_for(self._bundle(), "Abdoun")
        self.assertEqual(without["dimensions"]["regulatory_zoning"]["status"], "not_available")
        with_z = opportunity.feasibility_for(
            self._bundle(), "Abdoun",
            zoning={"kind": "osm", "plot_count": 2244,
                    "source": {"name": "OSM", "url": "internal://z", "capture_date": "2026-07-07"}})
        self.assertEqual(with_z["dimensions"]["regulatory_zoning"]["status"], "partial")

    def test_aqaba_regulatory_available_via_asez(self):
        from app.engine.data import EvidenceItem
        rules = [EvidenceItem(f"asez-{i}", "policy", f"ASEZ rule {i}", "sum", "Aqaba", None,
                              "unknown", None, "ASEZA", "https://aseza.jo/r", "2026-07-08", "H")
                 for i in range(6)]
        ls = [_listing(neighborhood="Aqaba", ppm2=700 + j) for j in range(8)]
        bundle = DataBundle(listings=ls, evidence_items=rules, as_of=AS_OF)
        f = opportunity.feasibility_for(
            bundle, "Aqaba",
            zoning={"kind": "asez", "plot_count": 118,
                    "source": {"name": "Aqaba ASEZ official", "url": "x", "capture_date": "2026-07-07"}})
        reg = f["dimensions"]["regulatory_zoning"]
        self.assertEqual(reg["status"], "available")
        self.assertEqual(reg["value"]["foreign_ownership_rules"], 6)
        self.assertEqual(reg["value"]["official_zoning_polygons"], 118)
        self.assertTrue(reg["sources"])

    def test_never_fabricates_unavailable_dims(self):
        f = opportunity.feasibility_for(self._bundle(), "Abdoun")
        for k in ("environmental", "legal", "financial"):
            self.assertEqual(f["dimensions"][k]["status"], "not_available")
            self.assertNotIn("value", f["dimensions"][k])


class ScenarioCompare(unittest.TestCase):
    def _bundle(self):
        ls = [_listing(neighborhood="Abdoun", ppm2=980 + j * 5, finish_quality="standard")
              for j in range(10)]
        ls += [_listing(neighborhood="Abdoun", ppm2=1180 + j * 5, finish_quality="luxury")
               for j in range(10)]
        return _bundle(ls)

    def test_shape_and_best_by(self):
        base = Subject(neighborhood="Abdoun", area_m2=180, finish_quality="standard",
                       floor_level=3)
        out = scenario.compare(base, self._bundle(), [
            {"label": "Launch now", "overrides": {}},
            {"label": "Floor 18 view", "overrides": {"target_floor": 18, "floors": 22,
                                                     "apply_height_view_premium": True}},
        ])
        self.assertIn("base", out)
        self.assertEqual(len(out["scenarios"]), 2)
        for s in out["scenarios"]:
            self.assertEqual(set(s), {"label", "result", "deltas_vs_base", "levers_applied"})
            self.assertGreater(s["result"]["recommended_price_jd_m2"], 0)
        self.assertEqual(set(out["best_by"]), {"recommended", "min_safe"})
        self.assertIn(out["best_by"]["recommended"], {"Launch now", "Floor 18 view"})
        # the height/view scenario should win recommended
        self.assertEqual(out["best_by"]["recommended"], "Floor 18 view")

    def test_empty_override_scenario_is_zero_delta(self):
        base = Subject(neighborhood="Abdoun", area_m2=180)
        out = scenario.compare(base, self._bundle(), [
            {"label": "A", "overrides": {}}, {"label": "B", "overrides": {"target_floor": 10}}])
        self.assertEqual(out["scenarios"][0]["deltas_vs_base"]["recommended_pct"], 0.0)


@unittest.skipUnless(os.path.exists(_DB_PATH), "real DB not present")
class RealDbIntel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.engine.data import load_bundle_from_sqlite
        cls.bundle = load_bundle_from_sqlite(_DB_PATH, AS_OF)

    def test_opportunity_over_real_db(self):
        out = opportunity.opportunity_scores(self.bundle, _COVERED, AS_OF)
        self.assertEqual(len(out), 5)
        for r in out:
            self.assertTrue(0 <= r["score"] <= 100)

    def test_scenario_cost_delta_flows_to_floor_on_real_db(self):
        base = Subject(neighborhood="Abdoun", area_m2=175, finish_quality="high")
        out = scenario.simulate(base, self.bundle, {"construction_cost_delta_pct": 50}, AS_OF)
        # cost delta may or may not bind (depends on whether a cost floor exists), but the
        # call must succeed and produce well-formed, finite deltas.
        self.assertIn("min_safe_pct", out["deltas"])
        self.assertTrue(out["scenario"]["recommended_price_jd_m2"] > 0)

    def test_metro_delay_moves_future_signals_component(self):
        base = Subject(neighborhood="Abdoun", area_m2=175, finish_quality="high")
        out = scenario.simulate(base, self.bundle, {"metro_delay_years": 6}, AS_OF)
        self.assertLessEqual(out["deltas"]["future_signals_change"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
