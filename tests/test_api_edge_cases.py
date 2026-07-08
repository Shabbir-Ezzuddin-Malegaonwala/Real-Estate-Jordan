"""Adversarial edge-case tests for the FastAPI layer (app/api/main.py).

Hits a running server (default http://127.0.0.1:8000, override with JORDAN_API_URL).
Uses only the standard library (urllib + threading) so the suite is dependency-free and
re-runnable. If the API is unreachable the whole module SKIPs (never errors).

Covers the QA brief:
  uncovered neighborhood -> 422 {detail} · negative area -> 422 · bad enum -> 422 ·
  missing required field -> 422 · empty body -> 422 · extreme area -> 200 ·
  all-optional-omitted (defaults) -> 200 · malformed JSON -> 4xx (not 500) ·
  response schema == db-contract §4 · prices finite & positive · min<=rec<=premium ·
  concurrent POSTs don't error · CORS header present for :5173 · /health, /neighborhoods,
  /comparables edge cases · injection & method-not-allowed robustness.

Run:  python -m pytest tests/test_api_edge_cases.py -v      (API must be up)
"""

from __future__ import annotations

import json
import math
import os
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("JORDAN_API_URL", "http://127.0.0.1:8000").rstrip("/")
ORIGIN_5173 = "http://localhost:5173"
_TIMEOUT = 15


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


def _request(method, path, *, data=None, raw=None, headers=None, timeout=_TIMEOUT) -> Resp:
    url = BASE + path
    body_bytes = raw if raw is not None else (
        json.dumps(data).encode("utf-8") if data is not None else None)
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body_bytes, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Resp(r.status, r.getheaders(), r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return Resp(e.code, list(e.headers.items()), e.read().decode("utf-8", "replace"))


def post_recommend(payload, **kw) -> Resp:
    return _request("POST", "/recommend", data=payload, **kw)


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


_VALID = {"neighborhood": "Abdoun", "property_type": "apartment", "area_m2": 175,
          "view": "city", "parking": "covered", "finish_quality": "high",
          "floor_level": 4, "elevator": "y"}


# ---------------------------------------------------------------------------
# validation: bad input must be 422 with a `detail`, never 500
# ---------------------------------------------------------------------------

class Validation422(unittest.TestCase):
    def _assert_422_with_detail(self, resp):
        self.assertEqual(resp.status, 422, f"expected 422, got {resp.status}: {resp.text[:200]}")
        self.assertIsNotNone(resp.body, "422 body was not JSON")
        self.assertIn("detail", resp.body)

    def test_uncovered_neighborhood(self):
        r = post_recommend({"neighborhood": "Atlantis"})
        self._assert_422_with_detail(r)
        self.assertIsInstance(r.body["detail"], str)
        self.assertIn("covered", r.body["detail"].lower())

    def test_negative_area(self):
        self._assert_422_with_detail(post_recommend({"neighborhood": "Abdoun", "area_m2": -5}))

    def test_zero_area(self):
        self._assert_422_with_detail(post_recommend({"neighborhood": "Abdoun", "area_m2": 0}))

    def test_bad_view_enum(self):
        r = post_recommend({"neighborhood": "Abdoun", "view": "ocean"})
        self._assert_422_with_detail(r)
        self.assertIsInstance(r.body["detail"], list)  # pydantic validation detail

    def test_bad_property_type_enum(self):
        self._assert_422_with_detail(post_recommend(
            {"neighborhood": "Abdoun", "property_type": "castle"}))

    def test_bad_parking_enum(self):
        self._assert_422_with_detail(post_recommend(
            {"neighborhood": "Abdoun", "parking": "helipad"}))

    def test_negative_bedrooms(self):
        self._assert_422_with_detail(post_recommend(
            {"neighborhood": "Abdoun", "bedrooms": -1}))

    def test_total_floors_below_one(self):
        self._assert_422_with_detail(post_recommend(
            {"neighborhood": "Abdoun", "total_floors": 0}))

    def test_missing_required_neighborhood(self):
        self._assert_422_with_detail(post_recommend({"property_type": "apartment"}))

    def test_empty_neighborhood_string(self):
        self._assert_422_with_detail(post_recommend({"neighborhood": ""}))

    def test_empty_body(self):
        self._assert_422_with_detail(post_recommend({}))

    def test_wrong_type_area_string(self):
        self._assert_422_with_detail(post_recommend(
            {"neighborhood": "Abdoun", "area_m2": "big"}))

    def test_malformed_json_is_4xx_not_500(self):
        r = post_recommend(None, raw=b"{ this is not json ")
        self.assertTrue(400 <= r.status < 500,
                        f"malformed JSON should be 4xx, got {r.status}")
        self.assertNotEqual(r.status, 500)

    def test_null_body_is_4xx_not_500(self):
        r = post_recommend(None, raw=b"null")
        self.assertTrue(400 <= r.status < 500, f"got {r.status}")


# ---------------------------------------------------------------------------
# robustness: hostile input must not 500
# ---------------------------------------------------------------------------

class Robustness(unittest.TestCase):
    def test_sql_injection_neighborhood_is_422_not_500(self):
        r = post_recommend({"neighborhood": "Abdoun'; DROP TABLE listings;--"})
        self.assertEqual(r.status, 422)
        # server still healthy afterwards
        self.assertEqual(_request("GET", "/health").status, 200)

    def test_very_long_neighborhood(self):
        r = post_recommend({"neighborhood": "x" * 5000})
        self.assertIn(r.status, (422,))

    def test_unknown_extra_field_is_ignored(self):
        r = post_recommend({**_VALID, "totally_unknown_field": 123})
        self.assertEqual(r.status, 200, r.text[:200])

    def test_get_recommend_method_not_allowed(self):
        self.assertEqual(_request("GET", "/recommend").status, 405)

    def test_unknown_route_404(self):
        self.assertEqual(_request("GET", "/does-not-exist").status, 404)

    def test_extreme_area_is_accepted(self):
        r = post_recommend({"neighborhood": "Abdoun", "area_m2": 1_000_000_000})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertGreater(r.body["recommended_price_jd_m2"], 0)


# ---------------------------------------------------------------------------
# happy path + defaults + response schema (db-contract §4)
# ---------------------------------------------------------------------------

class ResponseSchema(unittest.TestCase):
    TOP_KEYS = {"location_id", "neighborhood", "property_type", "min_safe_price_jd_m2",
                "recommended_price_jd_m2", "premium_price_jd_m2", "confidence",
                "evidence_objects", "comparables", "risk_factors",
                "alternative_scenarios", "narrative", "computed_date"}

    @classmethod
    def setUpClass(cls):
        r = post_recommend(_VALID)
        assert r.status == 200, r.text[:300]
        cls.body = r.body

    def test_all_top_level_keys_present(self):
        missing = self.TOP_KEYS - set(self.body.keys())
        self.assertFalse(missing, f"missing contract keys: {missing}")

    def test_confidence_is_nested_and_bounded(self):
        c = self.body["confidence"]
        # `components` (decomposed confidence) is an additive extension of the contract.
        self.assertTrue({"label", "numeric", "interval_jd_m2"}.issubset(c.keys()))
        self.assertIn(c["label"], ("H", "M", "L"))
        self.assertTrue(0.0 <= c["numeric"] <= 1.0)
        lo, hi = c["interval_jd_m2"]
        self.assertLess(lo, self.body["recommended_price_jd_m2"])
        self.assertLess(self.body["recommended_price_jd_m2"], hi)

    def test_prices_finite_positive_and_ordered(self):
        mn = self.body["min_safe_price_jd_m2"]
        rc = self.body["recommended_price_jd_m2"]
        pr = self.body["premium_price_jd_m2"]
        for v in (mn, rc, pr):
            self.assertIsInstance(v, (int, float))
            self.assertTrue(math.isfinite(v) and v > 0, f"non-finite/non-positive price {v}")
        self.assertLessEqual(mn, rc)
        self.assertLessEqual(rc, pr)

    def test_evidence_objects_each_have_sources_with_provenance(self):
        self.assertTrue(self.body["evidence_objects"])
        for e in self.body["evidence_objects"]:
            self.assertTrue({"factor", "adjustment", "confidence", "method", "datasets",
                             "sources", "category", "explanation"}.issubset(e.keys()))
            self.assertIn(e["category"], ("current_state", "future_signal"))
            self.assertTrue(e["sources"], f"evidence '{e['factor']}' has no sources")
            for s in e["sources"]:
                self.assertIn("name", s)
                self.assertTrue((s.get("url") or "").strip(),
                                f"evidence '{e['factor']}' source missing url")

    def test_comparables_expose_contract_fields(self):
        for c in self.body["comparables"]:
            self.assertIn("price_per_m2", c)
            self.assertIn("similarity", c)
            self.assertIn("adjustments_applied", c)

    def test_risk_factors_structured(self):
        for rk in self.body["risk_factors"]:
            self.assertEqual(set(rk.keys()), {"factor", "severity", "detail"})
            self.assertIn(rk["severity"], ("high", "medium", "low"))

    def test_three_scenarios(self):
        self.assertEqual(len(self.body["alternative_scenarios"]), 3)
        for s in self.body["alternative_scenarios"]:
            self.assertIn("recommended_price_jd_m2", s)
            self.assertIn("rationale", s)

    def test_defaults_when_only_neighborhood_supplied(self):
        r = post_recommend({"neighborhood": "Abdoun"})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertEqual(r.body["property_type"], "apartment")
        self.assertGreater(r.body["recommended_price_jd_m2"], 0)

    def test_neighborhood_resolution_is_case_and_whitespace_tolerant(self):
        r = post_recommend({"neighborhood": "  abdoun  "})
        self.assertEqual(r.status, 200, r.text[:200])
        self.assertEqual(r.body["neighborhood"], "Abdoun")

    def test_all_five_neighborhoods_price(self):
        for n in ("Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"):
            r = post_recommend({"neighborhood": n})
            self.assertEqual(r.status, 200, f"{n}: {r.text[:150]}")
            self.assertGreater(r.body["recommended_price_jd_m2"], 0, f"{n} priced 0")


# ---------------------------------------------------------------------------
# other endpoints
# ---------------------------------------------------------------------------

class OtherEndpoints(unittest.TestCase):
    def test_health(self):
        r = _request("GET", "/health")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body["status"], "ok")
        self.assertGreaterEqual(len(r.body["neighborhoods"]), 1)

    def test_neighborhoods_shape(self):
        r = _request("GET", "/neighborhoods")
        self.assertEqual(r.status, 200)
        self.assertIsInstance(r.body, list)
        self.assertTrue(r.body)
        for n in r.body:
            self.assertIn("name", n)
            self.assertIn("sale_listing_count", n)

    def test_comparables_valid(self):
        r = _request("GET", "/comparables?neighborhood=Abdoun&limit=5")
        self.assertEqual(r.status, 200)
        self.assertLessEqual(len(r.body["comparables"]), 5)
        if r.body["comparables"]:
            c = r.body["comparables"][0]
            self.assertIn("source", c)
            self.assertIn("url", c["source"])

    def test_comparables_uncovered_neighborhood(self):
        r = _request("GET", "/comparables?neighborhood=Atlantis")
        self.assertEqual(r.status, 422)
        self.assertIn("detail", r.body)

    def test_comparables_limit_out_of_range(self):
        self.assertEqual(_request("GET", "/comparables?neighborhood=Abdoun&limit=0").status, 422)
        self.assertEqual(_request("GET", "/comparables?neighborhood=Abdoun&limit=999").status, 422)

    def test_comparables_missing_required_query(self):
        self.assertEqual(_request("GET", "/comparables").status, 422)


# ---------------------------------------------------------------------------
# CORS + concurrency
# ---------------------------------------------------------------------------

class CorsAndConcurrency(unittest.TestCase):
    def test_cors_preflight_allows_5173(self):
        r = _request("OPTIONS", "/recommend", headers={
            "Origin": ORIGIN_5173,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertIn("access-control-allow-origin", r.headers)
        self.assertEqual(r.headers["access-control-allow-origin"], ORIGIN_5173)

    def test_cors_header_on_actual_post(self):
        r = post_recommend(_VALID, headers={"Origin": ORIGIN_5173})
        self.assertEqual(r.headers.get("access-control-allow-origin"), ORIGIN_5173)

    def test_concurrent_posts_all_succeed(self):
        payloads = [{"neighborhood": n} for n in
                    ("Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani")] * 4
        with ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(lambda p: post_recommend(p), payloads))
        statuses = [r.status for r in results]
        self.assertTrue(all(s == 200 for s in statuses),
                        f"some concurrent POSTs failed: {[s for s in statuses if s != 200]}")
        for r in results:
            self.assertGreater(r.body["recommended_price_jd_m2"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
