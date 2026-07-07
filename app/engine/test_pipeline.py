"""Requirement-driven tests for the Decision Engine.

Each test maps to a requirement from the task brief:
  * happy path                -> full contract, ordered price band, evidence coverage
  * thin market               -> low confidence + risk flag + wider range
  * stale comps               -> CBJ time-adjustment applied + evidenced
  * missing attributes        -> no crash, degrades gracefully, risk surfaced
  * NO hardcoded weights      -> premiums derived (runtime) + source scan
  * JSON contract             -> keys match recommendations table, serialisable
  * confidence range          -> H/M/L + numeric + interval low<point<high

Run:  python -m pytest app/engine/test_pipeline.py   (or)   python app/engine/test_pipeline.py
"""

from __future__ import annotations

import json
import os
import re
import unittest
from datetime import date

from app.engine.fixtures import load_sample_bundle
from app.engine.models import Subject
from app.engine.pipeline import recommend

AS_OF = date(2026, 7, 7)
_ENGINE_DIR = os.path.dirname(__file__)

_CONTEXT_FACTORS = {"Time (market movement)", "Net adjustment cap"}
# top-level keys of to_dict() — matches docs/db-contract.md §4
_REQUIRED_KEYS = {
    "location_id", "neighborhood", "property_type",
    "min_safe_price_jd_m2", "recommended_price_jd_m2", "premium_price_jd_m2",
    "confidence", "narrative", "evidence_objects", "comparables", "risk_factors",
    "alternative_scenarios", "computed_date",
}


def _abdoun(**over) -> Subject:
    base = dict(neighborhood="Abdoun", property_type="apartment", area_m2=170,
                floor_level=5, view="city", parking="covered", building_age_years=0,
                finish_quality="high", elevator="y")
    base.update(over)
    return Subject(**base)


class HappyPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_sample_bundle(AS_OF)
        cls.result = recommend(_abdoun(location_id="t-1"), cls.bundle, AS_OF)

    def test_contract_keys_present(self):
        d = self.result.to_dict()
        self.assertTrue(_REQUIRED_KEYS.issubset(d.keys()),
                        f"missing: {_REQUIRED_KEYS - set(d.keys())}")
        self.assertEqual(set(d["confidence"].keys()), {"label", "numeric", "interval_jd_m2"})

    def test_risk_factors_are_structured_objects(self):
        for rk in self.result.risk_factors:
            self.assertEqual(set(rk.keys()), {"factor", "severity", "detail"})
            self.assertIn(rk["severity"], ("high", "medium", "low"))

    def test_scenarios_use_contract_price_key(self):
        for s in self.result.alternative_scenarios:
            self.assertIn("recommended_price_jd_m2", s)
            self.assertIn("rationale", s)

    def test_comparables_expose_contract_fields(self):
        for c in self.result.comparables:
            self.assertIn("price_per_m2", c)
            self.assertIn("similarity", c)
            self.assertIn("adjustments_applied", c)

    def test_output_is_json_serialisable(self):
        json.dumps(self.result.to_dict())  # raises if any value is not serialisable

    def test_price_band_is_ordered(self):
        r = self.result
        self.assertGreater(r.recommended_price_jd_m2, 0)
        self.assertLessEqual(r.min_safe_price_jd_m2, r.recommended_price_jd_m2)
        self.assertLessEqual(r.recommended_price_jd_m2, r.premium_price_jd_m2)

    def test_prices_are_plausible_for_abdoun(self):
        # sanity band for a premium Amman submarket (synthetic but realistic magnitude)
        self.assertTrue(600 <= self.result.recommended_price_jd_m2 <= 2500)

    def test_every_applied_adjustment_has_evidence_with_source(self):
        ev_factors = [e["factor"] for e in self.result.evidence_objects]
        for comp in self.result.comparables:
            for adj in comp["adjustments"]:
                factor = adj["factor"]
                if factor in _CONTEXT_FACTORS:
                    continue
                covered = any(f == factor or f.startswith(factor) for f in ev_factors)
                self.assertTrue(covered, f"no evidence object for applied factor '{factor}'")

    def test_every_evidence_object_carries_a_source(self):
        for e in self.result.evidence_objects:
            self.assertTrue(e["sources"], f"evidence '{e['factor']}' has no source")
            for s in e["sources"]:
                self.assertIn("name", s)
                self.assertIn("url", s)

    def test_evidence_objects_are_well_formed(self):
        required = {"factor", "adjustment", "confidence", "method", "datasets",
                    "sources", "category", "explanation"}
        for e in self.result.evidence_objects:
            self.assertTrue(required.issubset(e.keys()))
            self.assertIn(e["category"], ("current_state", "future_signal"))

    def test_three_scenarios_present(self):
        names = [s["name"] for s in self.result.alternative_scenarios]
        self.assertEqual(len(names), 3)
        self.assertIn("Recommended launch", names)


class Confidence(unittest.TestCase):
    def test_range_and_label(self):
        r = recommend(_abdoun(), load_sample_bundle(AS_OF), AS_OF)
        self.assertIn(r.confidence_label, ("H", "M", "L"))
        self.assertTrue(0.0 <= r.confidence_numeric <= 1.0)
        lo, hi = r.confidence_interval_jd_m2
        self.assertLess(lo, r.recommended_price_jd_m2)
        self.assertLess(r.recommended_price_jd_m2, hi)


class ThinMarket(unittest.TestCase):
    def test_dabouq_is_low_confidence_with_risk_and_wider_range(self):
        bundle = load_sample_bundle(AS_OF)
        thin = recommend(Subject(neighborhood="Dabouq", property_type="apartment",
                                 area_m2=250, view="panoramic", parking="covered",
                                 finish_quality="luxury", floor_level=3,
                                 building_age_years=2), bundle, AS_OF)
        rich = recommend(_abdoun(), bundle, AS_OF)
        self.assertIn(thin.confidence_label, ("L", "M"))
        self.assertLessEqual(thin.confidence_numeric, rich.confidence_numeric)
        self.assertTrue(any("thin" in rk["factor"].lower() for rk in thin.risk_factors),
                        f"expected a thin-market risk, got {thin.risk_factors}")

        def width(r):
            return (r.premium_price_jd_m2 - r.min_safe_price_jd_m2) / r.recommended_price_jd_m2
        self.assertGreater(width(thin), width(rich))


class StaleComps(unittest.TestCase):
    def test_time_adjustment_applied_and_evidenced(self):
        r = recommend(_abdoun(), load_sample_bundle(AS_OF), AS_OF)
        timed = [c for c in r.comparables
                 if any(a["factor"] == "Time (market movement)" for a in c["adjustments"])]
        self.assertTrue(timed, "expected at least one stale comp to be time-adjusted")
        for c in timed:
            self.assertNotAlmostEqual(c["original_ppm2"], c["time_adjusted_ppm2"], places=1)
        self.assertTrue(any(e["factor"] == "Time (market movement)"
                            for e in r.evidence_objects),
                        "time-adjustment must produce an evidence object")

    def test_time_evidence_cites_cbj_index(self):
        r = recommend(_abdoun(), load_sample_bundle(AS_OF), AS_OF)
        te = [e for e in r.evidence_objects if e["factor"] == "Time (market movement)"]
        self.assertTrue(te)
        self.assertIn("CBJ", te[0]["method"])
        self.assertEqual(te[0]["datasets"], ["macro_series (CBJ index)"])


class MissingAttributes(unittest.TestCase):
    def test_unknown_attributes_do_not_crash_and_surface_risk(self):
        r = recommend(_abdoun(view="unknown", parking="unknown", finish_quality="unknown"),
                      load_sample_bundle(AS_OF), AS_OF)
        self.assertGreater(r.recommended_price_jd_m2, 0)
        self.assertTrue(any("unknown" in (rk["factor"] + rk["detail"]).lower()
                            for rk in r.risk_factors),
                        f"expected a missing-attribute risk, got {r.risk_factors}")

    def test_unpriceable_submarket_returns_safe_empty(self):
        r = recommend(Subject(neighborhood="Nowhere-Land", property_type="apartment",
                              area_m2=150), load_sample_bundle(AS_OF), AS_OF)
        self.assertEqual(r.recommended_price_jd_m2, 0.0)
        self.assertTrue(r.risk_factors)


class NoHardcodedWeights(unittest.TestCase):
    def test_every_derived_premium_is_actually_derived(self):
        r = recommend(_abdoun(), load_sample_bundle(AS_OF), AS_OF)
        premiums = r.method_values["derived_premiums"]
        self.assertTrue(premiums, "no premiums were derived")
        for p in premiums:
            self.assertTrue(p["sample_size"] and p["sample_size"] > 0)
            self.assertNotIn("hardcod", p["method"].lower())
            self.assertTrue(("differential" in p["method"]) or ("slope" in p["method"]),
                            f"premium '{p['factor']}' not derived from data: {p['method']}")
            self.assertIn("computed_date", p)

    def test_engine_source_has_no_attribute_premium_constants(self):
        # An attribute->fraction map (e.g. {"city": 1.08} or view = 0.08) would be a
        # hardcoded weight. The DGP multiplier tables live ONLY in the fixture generator.
        forbidden = re.compile(
            r"""["']?(sea|city|panoramic|garden|mountain|covered|open|luxury|basic)["']?\s*:\s*[-+]?1?\.\d""",
            re.IGNORECASE)
        mult_table = re.compile(r"_MULT\s*=\s*\{")
        for mod in ("adjustment.py", "recommendation.py", "evidence.py"):
            src = _read_engine(mod)
            self.assertIsNone(forbidden.search(src),
                              f"possible hardcoded attribute premium in {mod}")
            self.assertIsNone(mult_table.search(src),
                              f"DGP multiplier table leaked into {mod}")


_DB_PATH = os.path.join(_ENGINE_DIR, "..", "..", "db", "jordan_re.sqlite")


@unittest.skipUnless(os.path.exists(_DB_PATH), "real DB not present")
class RealDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.engine.data import load_bundle_from_sqlite
        cls.bundle = load_bundle_from_sqlite(_DB_PATH, AS_OF)

    def test_all_five_neighborhoods_price_and_are_traceable(self):
        for nbhd in ("Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"):
            r = recommend(_abdoun(neighborhood=nbhd, view="unknown", parking="unknown",
                                  finish_quality="unknown"), self.bundle, AS_OF)
            self.assertGreater(r.recommended_price_jd_m2, 200, f"{nbhd} priced implausibly low")
            self.assertLessEqual(r.min_safe_price_jd_m2, r.recommended_price_jd_m2)
            self.assertLessEqual(r.recommended_price_jd_m2, r.premium_price_jd_m2)
            self.assertTrue(r.comparables, f"{nbhd} has no comps")
            for e in r.evidence_objects:
                self.assertTrue(e["sources"] and e["sources"][0].get("url"),
                                f"{nbhd} evidence '{e['factor']}' lacks a source URL")

    def test_outliers_do_not_distort_median(self):
        # Abdoun raw max is ~9746 and min 0; a plausible recommendation must be far below.
        r = recommend(_abdoun(view="unknown", parking="unknown", finish_quality="unknown"),
                      self.bundle, AS_OF)
        self.assertLess(r.recommended_price_jd_m2, 3000)
        self.assertGreater(r.recommended_price_jd_m2, 400)


def _read_engine(name: str) -> str:
    with open(os.path.join(_ENGINE_DIR, name), encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    unittest.main(verbosity=2)
