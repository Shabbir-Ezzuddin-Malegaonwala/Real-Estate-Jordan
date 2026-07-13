"""Adversarial + contract tests for the intelligence-platform endpoints:

  POST /scenario · POST /residual-land-value · GET /opportunity · GET /areas ·
  /recommend?apply_height_view_premium.

Hits a running server (default http://127.0.0.1:8000, override with JORDAN_API_URL). Standard
library only, so the suite is dependency-free. If the API is unreachable the whole module SKIPs.

Covers: valid happy path, response schema, edge cases (uncovered submarket → 422 {detail};
invalid body → 422; not-500), and the invariants (prices finite/ordered; components bounded;
residual breakdown sums to the residual; opportunity scores 0-100 and ranked).

Run:  python -m pytest tests/test_intel_endpoints.py -v      (API must be up)
"""

from __future__ import annotations

import json
import math
import os
import unittest
import urllib.error
import urllib.request

BASE = os.environ.get("JORDAN_API_URL", "http://127.0.0.1:8000").rstrip("/")
_TIMEOUT = 20


class Resp:
    __slots__ = ("status", "headers", "body", "text")

    def __init__(self, status, headers, text):
        self.status = status
        self.headers = {k.lower(): v for k, v in headers}
        self.text = text
        try:
            self.body = json.loads(text) if text else None
        except (json.JSONDecodeError, ValueError):
            self.body = None


def _request(method, path, *, data=None, raw=None, timeout=_TIMEOUT) -> Resp:
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(BASE + path, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Resp(r.status, r.getheaders(), r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return Resp(e.code, list(e.headers.items()), e.read().decode("utf-8", "replace"))


def _api_up() -> bool:
    try:
        return _request("GET", "/health", timeout=5).status == 200
    except (urllib.error.URLError, OSError):
        return False


def setUpModule():
    if not _api_up():
        raise unittest.SkipTest(
            f"API not reachable at {BASE} — start it with "
            "`python -m uvicorn app.api.main:app --port 8000` and re-run")


# ---------------------------------------------------------------------------
# /recommend — decomposed confidence + height/view premium option
# ---------------------------------------------------------------------------

class RecommendIntel(unittest.TestCase):
    _COMPONENT_KEYS = {"data_coverage", "comp_quality", "gov_evidence",
                       "future_signals", "market_freshness"}

    def test_confidence_components_present_and_bounded(self):
        r = _request("POST", "/recommend", data={"neighborhood": "Abdoun", "area_m2": 175})
        self.assertEqual(r.status, 200, r.text[:200])
        comps = r.body["confidence"]["components"]
        self.assertEqual(set(comps), self._COMPONENT_KEYS)
        for name, c in comps.items():
            self.assertIn("reason", c)
            self.assertTrue(isinstance(c["reason"], str) and c["reason"])
            if c["score"] is not None:
                self.assertTrue(0 <= c["score"] <= 100, f"{name} out of range: {c['score']}")

    def test_height_view_premium_raises_price_and_surfaces_assumption(self):
        base = _request("POST", "/recommend",
                        data={"neighborhood": "Abdoun", "area_m2": 175, "floor_level": 18,
                              "total_floors": 22})
        lifted = _request("POST", "/recommend",
                          data={"neighborhood": "Abdoun", "area_m2": 175, "floor_level": 18,
                                "total_floors": 22, "apply_height_view_premium": True})
        self.assertEqual(lifted.status, 200, lifted.text[:200])
        self.assertGreater(lifted.body["recommended_price_jd_m2"],
                           base.body["recommended_price_jd_m2"])
        factors = [e["factor"].lower() for e in lifted.body["evidence_objects"]]
        self.assertTrue(any("height" in f for f in factors),
                        "height/view assumption not surfaced as evidence")
        self.assertLessEqual(lifted.body["min_safe_price_jd_m2"],
                             lifted.body["recommended_price_jd_m2"])
        self.assertLessEqual(lifted.body["recommended_price_jd_m2"],
                             lifted.body["premium_price_jd_m2"])

    def test_no_premium_below_threshold_floor(self):
        base = _request("POST", "/recommend",
                        data={"neighborhood": "Abdoun", "area_m2": 175, "floor_level": 3})
        lifted = _request("POST", "/recommend",
                          data={"neighborhood": "Abdoun", "area_m2": 175, "floor_level": 3,
                                "apply_height_view_premium": True})
        self.assertEqual(lifted.body["recommended_price_jd_m2"],
                         base.body["recommended_price_jd_m2"])


# ---------------------------------------------------------------------------
# /scenario
# ---------------------------------------------------------------------------

class Scenario(unittest.TestCase):
    def test_valid_scenario_shape(self):
        r = _request("POST", "/scenario", data={
            "neighborhood": "Abdoun", "area_m2": 175, "finish_quality": "standard",
            "floor_level": 3, "total_floors": 20,
            "overrides": {"finish_quality": "luxury", "target_floor": 16,
                          "construction_cost_delta_pct": 15, "apply_height_view_premium": True,
                          "floors": 20}})
        self.assertEqual(r.status, 200, r.text[:200])
        for k in ("base", "scenario", "deltas", "explanation", "levers_applied"):
            self.assertIn(k, r.body)
        self.assertEqual(set(r.body["deltas"]),
                         {"recommended_pct", "min_safe_pct", "premium_pct",
                          "confidence_change", "future_signals_change"})
        for res in (r.body["base"], r.body["scenario"]):
            for v in (res["min_safe_price_jd_m2"], res["recommended_price_jd_m2"],
                      res["premium_price_jd_m2"]):
                self.assertTrue(math.isfinite(v))
            self.assertLessEqual(res["min_safe_price_jd_m2"], res["recommended_price_jd_m2"])
            self.assertLessEqual(res["recommended_price_jd_m2"], res["premium_price_jd_m2"])

    def test_empty_overrides_is_noop(self):
        r = _request("POST", "/scenario", data={"neighborhood": "Abdoun", "area_m2": 175})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertEqual(r.body["deltas"]["recommended_pct"], 0.0)
        self.assertEqual(r.body["levers_applied"], [])

    def test_metro_delay_moves_future_signals(self):
        r = _request("POST", "/scenario", data={
            "neighborhood": "Abdoun", "area_m2": 175, "finish_quality": "high",
            "overrides": {"metro_delay_years": 6}})
        self.assertEqual(r.status, 200, r.text[:200])
        fsc = r.body["deltas"]["future_signals_change"]
        self.assertTrue(fsc is None or fsc <= 0)

    def test_uncovered_neighborhood_422(self):
        r = _request("POST", "/scenario", data={"neighborhood": "Atlantis"})
        self.assertEqual(r.status, 422)
        self.assertIn("detail", r.body)

    def test_bad_override_value_422_not_500(self):
        r = _request("POST", "/scenario", data={
            "neighborhood": "Abdoun", "overrides": {"metro_delay_years": 999}})
        self.assertEqual(r.status, 422)
        self.assertNotEqual(r.status, 500)


# ---------------------------------------------------------------------------
# /residual-land-value
# ---------------------------------------------------------------------------

class Residual(unittest.TestCase):
    def test_defaults_resolve_and_breakdown_sums(self):
        r = _request("POST", "/residual-land-value",
                     data={"neighborhood": "Abdoun", "buildable_area_m2": 1200})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertTrue(r.body["inputs"]["gdv_per_m2_defaulted"])
        line_sum = sum(l["value_jd"] for l in r.body["breakdown"])
        self.assertAlmostEqual(line_sum, r.body["residual_land_value_total_jd"], delta=1.0)
        self.assertAlmostEqual(r.body["residual_land_value_per_m2_jd"],
                               r.body["residual_land_value_total_jd"] / 1200, delta=1.0)

    def test_default_construction_is_dos_build_cost_not_land_price(self):
        r = _request("POST", "/residual-land-value",
                     data={"neighborhood": "Abdoun", "buildable_area_m2": 1200})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertTrue(r.body["inputs"]["construction_cost_defaulted"])
        cost = r.body["inputs"]["construction_cost_per_m2"]
        # DoS build floor is ~150-200 JD/m2, NOT the old land-price default (400-2667).
        self.assertLess(cost, 300, f"construction default {cost} looks like a land price")
        self.assertGreater(cost, 100)
        # the floor/upper-bound caveat must be surfaced
        self.assertTrue(r.body.get("caveat"))
        self.assertIn("floor", r.body["caveat"].lower())
        self.assertTrue(any("dos" in s["name"].lower() for s in r.body["sources"]))

    def test_explicit_inputs_viable(self):
        r = _request("POST", "/residual-land-value", data={
            "neighborhood": "Abdoun", "buildable_area_m2": 1200, "gdv_per_m2": 1100,
            "construction_cost_per_m2": 500, "developer_profit_pct": 0.18})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertTrue(r.body["viable"])
        self.assertGreater(r.body["residual_land_value_per_m2_jd"], 0)
        self.assertFalse(r.body["inputs"]["gdv_per_m2_defaulted"])
        self.assertTrue(r.body["sources"] == [] or all("name" in s for s in r.body["sources"]))

    def test_uncovered_neighborhood_422(self):
        r = _request("POST", "/residual-land-value",
                     data={"neighborhood": "Atlantis", "buildable_area_m2": 100})
        self.assertEqual(r.status, 422)
        self.assertIn("detail", r.body)

    def test_negative_area_422(self):
        r = _request("POST", "/residual-land-value",
                     data={"neighborhood": "Abdoun", "buildable_area_m2": -5})
        self.assertEqual(r.status, 422)

    def test_missing_required_area_422(self):
        r = _request("POST", "/residual-land-value", data={"neighborhood": "Abdoun"})
        self.assertEqual(r.status, 422)


# ---------------------------------------------------------------------------
# /opportunity + /areas
# ---------------------------------------------------------------------------

class Opportunity(unittest.TestCase):
    _COMPS = {"price_level", "price_growth", "demand_density", "supply_pressure"}

    @classmethod
    def setUpClass(cls):
        r = _request("GET", "/opportunity")
        assert r.status == 200, r.text[:200]
        cls.body = r.body

    def test_top_level_shape(self):
        self.assertIn("weights", self.body)
        self.assertIn("areas", self.body)
        self.assertEqual(self.body["version"], "v1-heuristic")
        self.assertAlmostEqual(sum(self.body["weights"].values()), 1.0, places=2)

    def test_each_area_scored_and_ranked(self):
        areas = self.body["areas"]
        self.assertGreaterEqual(len(areas), 1)
        scores = [a["score"] for a in areas]
        for s in scores:
            self.assertTrue(math.isfinite(s) and 0 <= s <= 100)
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_components_present_with_reasons(self):
        for a in self.body["areas"]:
            self.assertEqual(set(a["components"]), self._COMPS)
            for c in a["components"].values():
                self.assertIn("reason", c)
                if c["score"] is not None:
                    self.assertTrue(0 <= c["score"] <= 100)
            self.assertAlmostEqual(sum(a["weights_used"].values()), 1.0, places=2)

    def test_centroids_present_for_heatmap(self):
        for a in self.body["areas"]:
            self.assertIn("centroid_lat", a)
            self.assertIn("centroid_lng", a)

    def test_readiness_block_present_and_honest(self):
        self.assertIn("readiness_weights", self.body)
        dims = {"market_potential", "demand", "competition", "future_growth", "infrastructure",
                "regulatory_readiness", "pricing_confidence", "construction_feasibility"}
        for a in self.body["areas"]:
            r = a["readiness"]
            self.assertEqual(set(r["dimensions"]), dims)
            self.assertIn("overall", r)
            for d in r["dimensions"].values():
                self.assertEqual(set(d), {"score", "reason", "confidence"})
                self.assertIn(d["confidence"], ("high", "medium", "low"))
                if d["score"] is not None:
                    self.assertTrue(0 <= d["score"] <= 100)
            # still-pending dims are null (never fabricated); construction_feasibility is now
            # non-null where the DoS build-cost series covers the governorate (Amman here).
            for k in ("future_growth", "infrastructure", "regulatory_readiness"):
                self.assertIsNone(r["dimensions"][k]["score"])
            self.assertIsNotNone(r["dimensions"]["construction_feasibility"]["score"])
            self.assertAlmostEqual(sum(r["weights_used"].values()), 1.0, places=2)


class FeasibilityEndpoint(unittest.TestCase):
    _DIMS = {"regulatory_zoning", "construction_engineering", "operational_market",
             "environmental", "legal", "financial"}

    def test_valid_shape(self):
        r = _request("GET", "/feasibility?neighborhood=Abdoun")
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertEqual(set(r.body["dimensions"]), self._DIMS)
        for d in r.body["dimensions"].values():
            self.assertIn(d["status"], ("available", "partial", "not_available"))
            self.assertTrue(d["detail"])
            self.assertIsInstance(d["sources"], list)
        self.assertEqual(sum(r.body["summary"].values()), len(self._DIMS))

    def test_operational_market_available(self):
        r = _request("GET", "/feasibility?neighborhood=Khalda")
        self.assertEqual(r.body["dimensions"]["operational_market"]["status"], "available")

    def test_construction_available_from_dos(self):
        r = _request("GET", "/feasibility?neighborhood=Abdoun")
        d = r.body["dimensions"]["construction_engineering"]
        self.assertEqual(d["status"], "available")
        self.assertIn("construction_cost_jd_m2", d["value"])
        self.assertLess(d["value"]["construction_cost_jd_m2"], 300)  # build floor, not land price
        self.assertTrue(d["sources"])

    def test_aqaba_regulatory_available_via_asez(self):
        r = _request("GET", "/feasibility?neighborhood=Aqaba")
        self.assertEqual(r.status, 200, r.text[:200])
        reg = r.body["dimensions"]["regulatory_zoning"]
        self.assertEqual(reg["status"], "available")
        self.assertGreaterEqual(reg["value"]["foreign_ownership_rules"], 1)
        self.assertTrue(reg["sources"])

    def test_amman_regulatory_partial_osm(self):
        r = _request("GET", "/feasibility?neighborhood=Abdoun")
        self.assertEqual(r.body["dimensions"]["regulatory_zoning"]["status"], "partial")

    def test_uncovered_neighborhood_422(self):
        r = _request("GET", "/feasibility?neighborhood=Atlantis")
        self.assertEqual(r.status, 422)
        self.assertIn("detail", r.body)

    def test_missing_query_422(self):
        self.assertEqual(_request("GET", "/feasibility").status, 422)


class ScenarioCompareEndpoint(unittest.TestCase):
    def _body(self, n_scen=3):
        scen = [{"label": "Launch now", "overrides": {}},
                {"label": "+6mo luxury", "overrides": {"finish_quality": "luxury",
                                                       "launch_delay_months": 6}},
                {"label": "Floor 18 view", "overrides": {"target_floor": 18, "floors": 22,
                                                        "apply_height_view_premium": True}},
                {"label": "Cost +20%", "overrides": {"construction_cost_delta_pct": 20}}]
        return {"neighborhood": "Abdoun", "area_m2": 175, "finish_quality": "standard",
                "floor_level": 3, "total_floors": 20, "scenarios": scen[:n_scen]}

    def test_valid_shape(self):
        r = _request("POST", "/scenario/compare", data=self._body(3))
        self.assertEqual(r.status, 200, r.text[:200])
        for k in ("base", "scenarios", "best_by", "explanation"):
            self.assertIn(k, r.body)
        self.assertEqual(len(r.body["scenarios"]), 3)
        for s in r.body["scenarios"]:
            self.assertEqual(set(s), {"label", "result", "deltas_vs_base", "levers_applied"})
            self.assertGreater(s["result"]["recommended_price_jd_m2"], 0)
        self.assertEqual(set(r.body["best_by"]), {"recommended", "min_safe"})
        labels = {s["label"] for s in r.body["scenarios"]}
        self.assertIn(r.body["best_by"]["recommended"], labels)

    def test_too_few_scenarios_422(self):
        b = self._body(1)
        self.assertEqual(_request("POST", "/scenario/compare", data=b).status, 422)

    def test_too_many_scenarios_422(self):
        scen = [{"label": f"s{i}", "overrides": {}} for i in range(5)]
        b = {"neighborhood": "Abdoun", "scenarios": scen}
        self.assertEqual(_request("POST", "/scenario/compare", data=b).status, 422)

    def test_uncovered_neighborhood_422(self):
        b = {"neighborhood": "Atlantis",
             "scenarios": [{"label": "a", "overrides": {}}, {"label": "b", "overrides": {}}]}
        self.assertEqual(_request("POST", "/scenario/compare", data=b).status, 422)


class EncodingSafety(unittest.TestCase):
    """Every response body must be pure ASCII (no byte > 127) so no mis-configured decoder can
    mojibake JD/m2, ->, <=, etc. Regression guard for the double-encoding bug the frontend hit."""

    def _assert_ascii(self, method, path, data=None):
        req = urllib.request.Request(
            BASE + path, data=(json.dumps(data).encode() if data is not None else None),
            method=method, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            raw = r.read()
        offenders = [b for b in raw if b > 127]
        self.assertEqual(offenders, [], f"{path} emitted {len(offenders)} non-ASCII byte(s)")
        self.assertIn("charset=utf-8", (r.headers.get("content-type") or "").lower())

    def test_recommend_is_ascii(self):
        self._assert_ascii("POST", "/recommend",
                           {"neighborhood": "Abdoun", "area_m2": 175, "floor_level": 18,
                            "total_floors": 22, "apply_height_view_premium": True})

    def test_scenario_is_ascii(self):
        self._assert_ascii("POST", "/scenario", {
            "neighborhood": "Abdoun", "area_m2": 175,
            "overrides": {"finish_quality": "luxury", "target_floor": 16,
                          "construction_cost_delta_pct": 15, "metro_delay_years": 4}})

    def test_residual_is_ascii(self):
        self._assert_ascii("POST", "/residual-land-value",
                           {"neighborhood": "Abdoun", "buildable_area_m2": 1200})

    def test_opportunity_is_ascii(self):
        self._assert_ascii("GET", "/opportunity")

    def test_areas_is_ascii(self):
        self._assert_ascii("GET", "/areas")

    def test_feasibility_is_ascii(self):
        self._assert_ascii("GET", "/feasibility?neighborhood=Abdoun")

    def test_scenario_compare_is_ascii(self):
        self._assert_ascii("POST", "/scenario/compare", {
            "neighborhood": "Abdoun", "area_m2": 175,
            "scenarios": [{"label": "A", "overrides": {}},
                          {"label": "B", "overrides": {"target_floor": 18, "floors": 22,
                                                       "apply_height_view_premium": True}}]})


class Areas(unittest.TestCase):
    def test_catalog_shape_and_covered_flags(self):
        r = _request("GET", "/areas")
        self.assertEqual(r.status, 200)
        self.assertGreaterEqual(r.body["covered_count"], 1)
        self.assertGreater(r.body["total_count"], r.body["covered_count"])
        areas = r.body["areas"]
        # covered areas are listed first
        first = areas[0]
        self.assertTrue(first["covered"])
        for a in areas[:20]:
            self.assertIn("listing_count", a)
            self.assertIn("covered", a)
            self.assertNotEqual(a["name"].lower(), "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
