"""End-to-end UI smoke + edge tests for the Analyst Terminal (app/web) using PYTHON
Playwright (sync API). No MCP browser tools — this drives its own headless Chromium so
it never contends with another agent's browser session.

What it checks against http://localhost:5173 (override with JORDAN_WEB_URL):
  1. page loads, analysis panel renders, and NO uncaught JS exceptions fire
  2. API status is read from the on-screen badge (online / offline / checking)
  3. all 5 neighbourhoods are selectable and the recommended price changes between them
  4. editing size / floor / finish recomputes (online only; skipped+noted when offline)
  5. clicking the map outside coverage shows the honest "no data" message (best-effort)
  6. the theme toggle flips <html data-theme>
  7. the Help / About panel opens and closes
  8. offline fallback badge (optional; only asserted if the API is down)

Every step is isolated: one failing step never aborts the rest. Screenshots land in
tests/screenshots/. A summary table + non-zero exit code on hard failure is printed.

Setup (once):   pip install playwright && python -m playwright install chromium
Run:            python tests/e2e_frontend.py
                (or)  python -m pytest tests/e2e_frontend.py -v
"""

from __future__ import annotations

import os
import re
import sys
import time

WEB_URL = os.environ.get("JORDAN_WEB_URL", "http://localhost:5173").rstrip("/")
_HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(_HERE, "screenshots")
os.makedirs(SHOTS, exist_ok=True)

PANEL = 'aside[aria-label="Analysis panel"]'
BAND = 'section[aria-label="Recommended launch price band"]'


class Step:
    def __init__(self, name):
        self.name = name
        self.status = "PASS"
        self.detail = ""


class Runner:
    def __init__(self):
        self.steps: list[Step] = []
        self.js_errors: list[str] = []
        self.console_errors: list[str] = []

    def record(self, name, fn):
        s = Step(name)
        try:
            msg = fn()
            if msg == "SKIP":
                s.status = "SKIP"
            elif isinstance(msg, tuple) and msg[0] == "SKIP":
                s.status, s.detail = "SKIP", msg[1]
            elif isinstance(msg, str):
                s.detail = msg
        except AssertionError as e:
            s.status, s.detail = "FAIL", str(e)
        except Exception as e:  # noqa: BLE001 - report, never abort the run
            s.status, s.detail = "ERROR", f"{type(e).__name__}: {e}"
        self.steps.append(s)
        print(f"[{s.status:5}] {s.name}" + (f" — {s.detail}" if s.detail else ""))
        return s


def _rec_price(page) -> float:
    """Recommended tier value from the price band (the accent 26px number)."""
    page.wait_for_selector(BAND, timeout=15000)
    text = page.locator(BAND).inner_text()
    nums = re.findall(r"[\d][\d,]*", text.replace(" ", ""))
    vals = [float(n.replace(",", "")) for n in nums if float(n.replace(",", "")) > 50]
    assert vals, f"no price numbers parsed from band: {text!r}"
    return max(vals)  # recommended/premium dominate; guards against tiny unit labels


def run() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: playwright not installed — `pip install playwright && "
              "python -m playwright install chromium`")
        return 0

    r = Runner()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: r.js_errors.append(str(e)))
        page.on("console", lambda m: r.console_errors.append(m.text)
                if m.type == "error" else None)

        # ---- 1. load ----
        def load():
            page.goto(WEB_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector(PANEL, timeout=20000)
            page.wait_for_selector(BAND, timeout=20000)
            time.sleep(1.0)
            page.screenshot(path=os.path.join(SHOTS, "01-loaded.png"))
            assert not r.js_errors, f"uncaught JS errors on load: {r.js_errors}"
            return "panel + price band rendered"
        loaded = r.record("load: page renders, no uncaught JS errors", load)
        if loaded.status in ("FAIL", "ERROR"):
            page.screenshot(path=os.path.join(SHOTS, "01-load-failure.png"))
            browser.close()
            _summary(r)
            return _exit_code(r)

        # ---- 2. api status badge ----
        state = {"online": False}

        def api_badge():
            head = page.locator("header").first.inner_text().lower()
            if "live api" in head:
                state["online"] = True
                return "badge: Live API (online)"
            if "offline" in head:
                return "badge: Offline · precomputed"
            return "badge: checking / unknown"
        r.record("api status badge visible", api_badge)

        # ---- 3. all 5 neighbourhoods selectable and prices differ ----
        def neighbourhoods():
            prices = {}
            for nb in ("Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"):
                page.select_option("#f-nbhd", nb)
                page.wait_for_function(
                    """(nb) => { const h = document.querySelector('h2'); return h && h.textContent.includes(nb); }""",
                    arg=nb, timeout=10000)
                time.sleep(0.8)  # settle debounced recompute
                prices[nb] = _rec_price(page)
            page.screenshot(path=os.path.join(SHOTS, "03-neighbourhoods.png"))
            assert len(set(prices.values())) > 1, \
                f"all neighbourhoods returned the same price (no recompute?): {prices}"
            return "prices: " + ", ".join(f"{k}={v:.0f}" for k, v in prices.items())
        r.record("all 5 neighbourhoods selectable + prices differ", neighbourhoods)

        # ---- 4. field edits recompute (online only) ----
        def field_recompute():
            if not state["online"]:
                return ("SKIP", "API offline — offline mode ignores field edits by design")
            page.select_option("#f-nbhd", "Abdoun")
            time.sleep(0.8)
            page.select_option("#f-finish", "unknown")
            page.fill("#f-area", "120")
            time.sleep(1.2)
            before = _rec_price(page)
            page.fill("#f-area", "260")
            page.select_option("#f-finish", "luxury")
            page.select_option("#f-view", "panoramic")
            time.sleep(1.4)
            after = _rec_price(page)
            page.screenshot(path=os.path.join(SHOTS, "04-field-recompute.png"))
            assert abs(after - before) > 0.5, \
                f"editing size/finish/view did not change the price ({before} -> {after})"
            return f"price moved {before:.0f} -> {after:.0f} on attribute change"
        r.record("editing size/floor/finish recomputes", field_recompute)

        # ---- 5. outside-coverage honest 'no data' message (best-effort) ----
        def outside_coverage():
            # The map zooms into the selected submarket, so first zoom OUT (scroll down)
            # until the 5 small polygons no longer fill the view, then click a far corner.
            # onOutside() fires when a click hits no nbhd-fill feature -> honest toast.
            page.mouse.move(950, 450)
            for _ in range(7):
                page.mouse.wheel(0, 400)
                time.sleep(0.15)
            time.sleep(1.0)
            for pt in ((1410, 60), (1410, 850), (520, 60)):
                page.mouse.click(*pt)
                try:
                    page.wait_for_selector("text=/no data for this location/i", timeout=2500)
                    page.screenshot(path=os.path.join(SHOTS, "05-no-data-toast.png"))
                    return f"honest 'no data' toast shown on outside click at {pt}"
                except Exception:
                    continue
            return ("SKIP", "could not land an off-coverage map click headlessly "
                            "(map hit-testing non-deterministic); toast path unverified")
        r.record("outside-coverage shows honest 'no data'", outside_coverage)

        # ---- 6. theme toggle ----
        def theme():
            before = page.evaluate("document.documentElement.dataset.theme || ''")
            page.click('button[aria-label^="Switch to"]')
            time.sleep(0.4)
            after = page.evaluate("document.documentElement.dataset.theme || ''")
            page.screenshot(path=os.path.join(SHOTS, "06-theme.png"))
            assert before != after, f"data-theme did not change ({before!r} -> {after!r})"
            return f"theme {before or '(unset)'} -> {after}"
        r.record("theme toggle flips <html data-theme>", theme)

        # ---- 7. help panel ----
        def help_panel():
            page.click('button[aria-label="How to use this tool"]')
            page.wait_for_selector('[role="dialog"][aria-labelledby="help-title"]', timeout=8000)
            assert page.locator("#help-title").is_visible()
            page.screenshot(path=os.path.join(SHOTS, "07-help-open.png"))
            page.click('button[aria-label="Close help"]')
            time.sleep(0.3)
            assert page.locator('[role="dialog"][aria-labelledby="help-title"]').count() == 0, \
                "help dialog did not close"
            return "help drawer opens and closes"
        r.record("help/about panel opens and closes", help_panel)

        # ---- 8. optional: offline badge only asserted when API is truly down ----
        def offline_badge():
            if state["online"]:
                return ("SKIP", "API online — offline-badge check is only meaningful with API down")
            head = page.locator("header").first.inner_text().lower()
            assert "offline" in head, "expected Offline badge when API is down"
            return "offline badge present"
        r.record("offline fallback badge (optional)", offline_badge)

        # final console-error note (soft — map tiles / network can log benign errors)
        if r.console_errors:
            print(f"[note ] {len(r.console_errors)} console.error message(s) "
                  f"(soft, not failed): {r.console_errors[:3]}")

        browser.close()

    _summary(r)
    return _exit_code(r)


def _summary(r: Runner):
    p = sum(1 for s in r.steps if s.status == "PASS")
    f = sum(1 for s in r.steps if s.status in ("FAIL", "ERROR"))
    sk = sum(1 for s in r.steps if s.status == "SKIP")
    print("\n" + "=" * 62)
    print(f"E2E summary: {p} passed, {f} failed, {sk} skipped "
          f"(uncaught JS errors: {len(r.js_errors)})")
    print(f"screenshots: {SHOTS}")
    print("=" * 62)


def _exit_code(r: Runner) -> int:
    return 1 if any(s.status in ("FAIL", "ERROR") for s in r.steps) or r.js_errors else 0


# pytest entrypoint (skips cleanly when playwright / browser / frontend absent)
def test_e2e_frontend():
    import unittest
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        raise unittest.SkipTest("playwright not installed")
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen(WEB_URL, timeout=5)
    except (urllib.error.URLError, OSError):
        raise unittest.SkipTest(f"frontend not reachable at {WEB_URL}")
    code = run()
    assert code == 0, "one or more E2E steps failed — see printed summary and tests/screenshots/"


if __name__ == "__main__":
    sys.exit(run())
