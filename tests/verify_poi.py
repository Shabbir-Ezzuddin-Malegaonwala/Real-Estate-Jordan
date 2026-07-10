from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:4173/"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)
ARGS = ["--ignore-gpu-blocklist", "--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader"]


def shot(page, name):
    page.screenshot(path=str(OUT / f"poi_{name}.png"))
    print("  shot:", name)


def step(fn):
    try:
        fn()
    except Exception as e:
        print("  ! failed:", fn.__name__, "->", repr(e)[:160])


def run():
    with sync_playwright() as p:
        b = p.chromium.launch(args=ARGS)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        errs, netfail = [], []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append("PAGEERR:" + str(e)))
        page.on("requestfailed", lambda r: netfail.append(r.url.split("/")[-1]))

        page.goto(BASE, wait_until="networkidle")
        page.evaluate("localStorage.clear()")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.click("text=Explore Opportunities")
        page.wait_for_timeout(2800)

        # zoom in so POI points (minzoom 11.5) are clearly visible
        def zoom_in():
            for _ in range(3):
                page.click(".maplibregl-ctrl-zoom-in")
                page.wait_for_timeout(500)
        step(zoom_in)
        shot(page, "01_default_layers")  # transport + education on

        # toggle on Health + Shopping + Religious
        def more_categories():
            for label in ["Health", "Shopping", "Religious"]:
                cb = page.query_selector(f"input[aria-label='Toggle {label}']")
                if cb:
                    cb.check()
                    page.wait_for_timeout(700)
            page.wait_for_timeout(800)
            shot(page, "02_more_categories")
        step(more_categories)

        # select an area → nearby amenities panel
        def nearby():
            page.fill("#area-search", "Abdoun")
            page.wait_for_timeout(400)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2200)
            el = page.query_selector("text=What's nearby")
            if el:
                el.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            has_airport = page.query_selector("text=Nearest airport") is not None
            has_nearby = page.query_selector("text=What's nearby") is not None
            print("nearby panel:", has_nearby, "| airport row:", has_airport)
            shot(page, "03_nearby_amenities")
        step(nearby)

        # lazy-load Water (8.4 MB) — expect a loading state then a fill
        def water():
            cb = page.query_selector("input[aria-label='Toggle Water']")
            if cb:
                cb.check()
                page.wait_for_timeout(300)
                loading = page.query_selector("text=loading…") is not None
                print("water loading state shown:", loading)
                page.wait_for_timeout(4000)  # allow 8.4MB fetch+parse
            shot(page, "04_water_layer")
        step(water)

        # toggle everything on to stress-test performance/legibility
        def all_on():
            for label in ["Education", "Food & Leisure", "Recreation", "Transport", "Services", "Negatives", "Green / parks", "Major roads"]:
                cb = page.query_selector(f"input[aria-label='Toggle {label}']")
                if cb and not cb.is_checked():
                    cb.check()
                    page.wait_for_timeout(400)
            page.wait_for_timeout(1000)
            shot(page, "05_all_layers")
        step(all_on)

        print("CONSOLE ERRORS:", len(errs))
        for e in errs[:6]:
            print("   ", e[:150])
        from collections import Counter
        print("failed requests (top):", dict(Counter(netfail).most_common(5)))
        b.close()


if __name__ == "__main__":
    run()
    print("DONE")
