from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:4173/"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)
ARGS = ["--ignore-gpu-blocklist", "--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader"]


def shot(page, name):
    page.screenshot(path=str(OUT / f"refactor_{name}.png"))
    print("  shot:", name)


def step(fn):
    try:
        fn()
    except Exception as e:
        print("  ! failed:", fn.__name__, "->", repr(e)[:160])


def run():
    with sync_playwright() as p:
        b = p.chromium.launch(args=ARGS)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        errs = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append("PAGEERR:" + str(e)))
        # start fresh — no persisted entry
        page.goto(BASE, wait_until="networkidle")
        page.evaluate("localStorage.clear()")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 1. Landing: two entry points, NO role selector
        page.wait_for_selector("text=Decide where to build, and what to launch at.", timeout=8000)
        has_role = page.query_selector("text=I'm a Builder") is not None
        has_explore = page.query_selector("text=Explore Opportunities") is not None
        has_evaluate = page.query_selector("text=Evaluate My Land") is not None
        print(f"landing: explore={has_explore} evaluate={has_evaluate} role_selector_present={has_role}")
        shot(page, "01_landing")

        # 2. Explore → opportunity map + step 1
        page.click("text=Explore Opportunities")
        page.wait_for_timeout(2800)
        page.wait_for_selector("text=Step 1 of 7", timeout=6000)
        shot(page, "02_explore_opportunity")

        # 3. Select a covered area → readiness
        page.fill("#area-search", "Abdoun")
        page.wait_for_timeout(400)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2500)
        step(lambda: page.wait_for_selector("text=Decision readiness", timeout=6000))
        # scroll readiness into view
        el = page.query_selector("text=Regulatory Readiness")
        if el:
            el.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        has_na = page.query_selector("text=data not yet available") is not None
        print("decision readiness has honest nulls:", has_na)
        shot(page, "03_decision_readiness")

        # 4. Navigate the 7 steps
        for n, key in [(2, "feasibility"), (3, "market"), (4, "economics"), (5, "pricing"), (6, "sales"), (7, "monitoring")]:
            def go(n=n, key=key):
                page.click(f"button[aria-label='Step {n}: {key.capitalize()}']")
                page.wait_for_timeout(1800)
                page.wait_for_selector(f"text=Step {n} of 7", timeout=5000)
                shot(page, f"04_step{n}_{key}")
            step(go)

        # 5. Pricing step detail (scenario + compare present)
        def pricing_detail():
            page.click("button[aria-label='Step 5: Pricing']")
            page.wait_for_timeout(1800)
            cmp = page.query_selector("text=Compare scenarios")
            if cmp:
                cmp.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            shot(page, "05_pricing_scenario_compare")
        step(pricing_detail)

        # 6. Evaluate My Land entry → lands on feasibility
        def evaluate_entry():
            page.evaluate("localStorage.clear()")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1200)
            page.click("text=Evaluate My Land")
            page.wait_for_timeout(2500)
            page.wait_for_selector("text=Step 2 of 7", timeout=6000)
            shot(page, "06_evaluate_entry_feasibility")
        step(evaluate_entry)

        print("CONSOLE ERRORS:", len(errs))
        for e in errs[:8]:
            print("   ", e[:160])
        ctx.close()
        b.close()


if __name__ == "__main__":
    run()
    print("DONE")
