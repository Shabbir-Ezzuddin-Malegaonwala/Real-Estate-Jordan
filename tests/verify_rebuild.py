import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5188/"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)


def shot(page, name):
    page.screenshot(path=str(OUT / f"rebuild_{name}.png"))
    print("  shot:", name)


def step(fn):
    try:
        fn()
    except Exception as e:  # keep going so one failure doesn't lose all evidence
        print("  ! step failed:", fn.__name__, "->", repr(e)[:180])


def run(theme_seed=None):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))

        # 1. Role selector (fresh context → no persisted role)
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1200)
        page.wait_for_selector("text=One evidence base. Three ways to decide.", timeout=8000)
        shot(page, "01_role_selector")

        # 2. Builder workspace + opportunity heatmap
        page.click("text=I'm a Builder")
        page.wait_for_timeout(2500)  # map + opportunity fetch
        page.wait_for_selector("text=Opportunity to build", timeout=8000)  # legend
        shot(page, "02_builder_heatmap")

        # 3. Select an area via search → area intelligence panel
        def open_area():
            page.fill("#area-search", "Abdoun")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_selector("text=Opportunity score", timeout=8000)
            page.wait_for_timeout(1500)
            shot(page, "03_area_intelligence")
        step(open_area)

        # 4. Decomposed confidence visible in the panel
        def confidence():
            page.wait_for_selector("text=Confidence", timeout=5000)
            el = page.query_selector("text=Comparable quality") or page.query_selector("text=Data coverage")
            if el:
                el.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            shot(page, "04_confidence_breakdown")
        step(confidence)

        # 5. Evaluate a project → residual land value + scenario
        def evaluate():
            page.click("text=Evaluate a project here")
            page.wait_for_selector("text=Residual Land Value", timeout=6000)
            page.wait_for_timeout(1200)
            el = page.query_selector("text=Max defensible land price")
            if el:
                el.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            shot(page, "05_residual_land_value")
        step(evaluate)

        # 6. Scenario what-if — capture a value, move a slider, capture the change
        def scenario():
            sec = page.query_selector("text=Scenario — What-if")
            if sec:
                sec.scroll_into_view_if_needed()
            page.wait_for_timeout(600)
            shot(page, "06a_scenario_before")
            slider = page.query_selector("#sc-cost")  # construction cost
            if slider:
                slider.focus()
                for _ in range(4):
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(120)
            page.wait_for_timeout(900)
            shot(page, "06b_scenario_after")
        step(scenario)

        # 7. Expand an evidence/adjustment row
        def evidence():
            wf = page.query_selector("text=Adjustment Waterfall")
            if wf:
                wf.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            row = page.query_selector("section[aria-label='Adjustment waterfall'] button[aria-expanded='false']")
            if row:
                row.click()
                page.wait_for_timeout(600)
            shot(page, "07_evidence_expanded")
        step(evidence)

        # 8. Agent workspace + sales narrative
        def agent():
            page.click("button[role='tab']:has-text('Agent')")
            page.wait_for_timeout(2000)
            page.wait_for_selector("text=Sales narrative", timeout=6000)
            page.wait_for_timeout(600)
            shot(page, "08_agent_narrative")
        step(agent)

        # 9. Buyer workspace
        def buyer():
            page.click("button[role='tab']:has-text('Buyer')")
            page.wait_for_timeout(2000)
            page.wait_for_selector("text=Is this price fair?", timeout=6000)
            page.wait_for_timeout(600)
            shot(page, "09_buyer_summary")
        step(buyer)

        # 10. Light theme (builder)
        def light():
            page.click("button[role='tab']:has-text('Builder')")
            page.wait_for_timeout(1500)
            tgl = page.query_selector("button[aria-label*='theme'], button[aria-label*='Theme'], button[title*='theme']")
            if tgl:
                tgl.click()
                page.wait_for_timeout(1500)
            shot(page, "10_builder_light")
        step(light)

        print("CONSOLE ERRORS:", len(errors))
        for e in errors[:12]:
            print("   ", e[:200])
        ctx.close()
        b.close()


if __name__ == "__main__":
    run()
    print("DONE")
