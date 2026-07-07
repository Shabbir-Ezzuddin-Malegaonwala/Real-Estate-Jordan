"""Detail-page enrichment for OpenSooq listings (Playwright-rendered).

OpenSooq post pages are client-rendered (React flight streaming), so the SERP
list JSON does not carry the per-listing spec table. This script renders each
listing with headless Chromium and reads the main-post attribute rows:
Floor, Building Age, Furnished/Unfurnished, Lister Type, Facade.

Field mapping into the frozen schema:
  Floor        -> floor_level        ("Ground Floor"->0, "Second Floor"->2, ...)
  Building Age -> building_age_years  (bucket midpoint; "Under Construction"->0)
  Furnished    -> furnishing          (full/no/semi)
  Lister Type  -> seller_type         (Landlord->private, Office/Company->agent)
  Facade       -> recorded in notes   (compass orientation — NOT the `view` enum)

IMPORTANT: OpenSooq has no structured `view` field (Facade = orientation). `view`
is left as-is (unknown) — never fabricated.

Usage:
    python enrich_opensooq.py --date 20260707 --types sale
Writes back to data/raw/listings_opensooq_<date>.csv (one-time .preenrich.bak).
"""
import argparse
import csv
import datetime
import os
import re
import shutil
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listings_common as lc
from playwright.sync_api import sync_playwright

EXTRACT_JS = r"""() => {
  const wanted=['Floor','Building Age','Furnished/Unfurnished','Lister Type','Facade'];
  const nodes=Array.from(document.querySelectorAll('a,span,div,li,p'));
  const out={};
  for(const w of wanted){for(const n of nodes){const t=(n.textContent||'').trim();
    if(t===w){let v='';if(n.nextElementSibling)v=n.nextElementSibling.textContent.trim();
      if(!v&&n.parentElement){const k=Array.from(n.parentElement.children).map(c=>c.textContent.trim()).filter(x=>x&&x!==w);v=k[0]||'';}
      if(v&&!out[w])out[w]=v.slice(0,40);}}}
  return out;
}"""

ORDINALS = {"ground": 0, "semi ground": 0, "basement": 0, "first": 1, "second": 2,
            "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
            "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}

AGE_BUCKET = {"under construction": 0, "0 - 11 months": 0, "0-11 months": 0,
              "1 - 5 years": 3, "1-5 years": 3, "6 - 9 years": 7, "6-9 years": 7,
              "10 - 19 years": 14, "10-19 years": 14, "+20 years": 20,
              "20+ years": 20, "more than 20 years": 20}


def map_floor(v):
    t = v.lower().strip()
    for word, num in ORDINALS.items():
        if t.startswith(word):
            return num
    m = re.search(r"(\d{1,2})", t)
    if m and int(m.group(1)) <= 40:
        return int(m.group(1))
    return None


def map_age(v):
    return AGE_BUCKET.get(v.lower().strip())


def map_furnishing(v):
    t = v.lower()
    if "semi" in t:
        return "semi"
    if "unfurnished" in t or "not furnished" in t:
        return "no"
    if "furnished" in t:
        return "full"
    return None


def map_seller(v):
    t = v.lower()
    if any(k in t for k in ["office", "company", "agent", "agency", "developer", "showroom"]):
        return "agent"
    if "landlord" in t or "owner" in t or "individual" in t:
        return "private"
    return None


def apply(row, attrs):
    got = {}
    if "Floor" in attrs:
        f = map_floor(attrs["Floor"])
        if f is not None:
            row["floor_level"] = f
            got["floor_level"] = f
    if "Building Age" in attrs:
        a = map_age(attrs["Building Age"])
        if a is not None:
            row["building_age_years"] = a
            got["building_age_years"] = a
    if "Furnished/Unfurnished" in attrs:
        fu = map_furnishing(attrs["Furnished/Unfurnished"])
        if fu:
            row["furnishing"] = fu
            got["furnishing"] = fu
    if "Lister Type" in attrs:
        st = map_seller(attrs["Lister Type"])
        if st:
            row["seller_type"] = st
            got["seller_type"] = st
    tags = ["enriched=detail"]
    if "Facade" in attrs:
        tags.append("facade=" + attrs["Facade"])  # orientation, not view
    tags.append("fields=" + (",".join(sorted(got.keys())) if got else "none"))
    base = row.get("notes", "")
    row["notes"] = (base + "; " if base else "") + "; ".join(tags)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--types", default="sale")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    types = {t.strip() for t in args.types.split(",") if t.strip()}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "data", "raw", f"listings_opensooq_{args.date}.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    targets = [r for r in rows if r["listing_type"] in types]
    if args.limit:
        targets = targets[:args.limit]
    print(f"Enriching {len(targets)} OpenSooq rows (types={sorted(types)}) via Playwright")

    if not args.dry_run:
        bak = path + ".preenrich.bak"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
            print(f"  backup -> {bak}")

    fieldhits = Counter()
    ok = fail = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(user_agent=lc.UA)
        page.set_default_timeout(45000)
        for n, row in enumerate(targets, 1):
            url = row["listing_url"]
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(int(args.delay * 1000) + 1500)
                attrs = page.evaluate(EXTRACT_JS)
            except Exception as e:
                fail += 1
                print(f"  [{n}/{len(targets)}] {row['listing_id']} ERR {str(e)[:60]}")
                if fail >= 8 and fail > ok:
                    print("  Too many failures — stopping, keeping progress.")
                    break
                continue
            got = apply(row, attrs)
            for k in got:
                fieldhits[k] += 1
            ok += 1
            if n % 15 == 0 or n == len(targets):
                print(f"  [{n}/{len(targets)}] ok={ok} fail={fail} floors={fieldhits['floor_level']} ages={fieldhits['building_age_years']}")
            if not args.dry_run and n % 25 == 0:
                lc.write_csv(path, rows)
        # write final result BEFORE closing so a close-race can't lose data
        if not args.dry_run:
            lc.write_csv(path, rows)
        try:
            browser.close()
        except Exception:
            pass

    print(f"\n=== OpenSooq enrichment done: ok={ok} fail={fail} ===")
    for k in ["floor_level", "building_age_years", "furnishing", "seller_type"]:
        print(f"  {k:20} filled {fieldhits[k]}/{ok}")
    print("  view: NOT enriched — OpenSooq has no structured view field (Facade=orientation)")


if __name__ == "__main__":
    main()
