"""Detail-page enrichment for Bayut listings.

Fetches each listing's detail page, parses the embedded
`window.state.property.data` (full description text + structured amenities +
isDeveloper) and fills the secondary attributes that the SERP list state does
NOT carry: view, floor_level, total_floors, parking, building_age_years,
finish_quality, elevator, seller_type.

Genuine absence stays 'unknown'/'u'/empty — never fabricated. Enriched fields
are text-derived (confidence philosophy = source trust stays the row's H; the
per-field origin is recorded in notes).

Usage:
    python enrich_bayut.py --date 20260707 --types sale
    python enrich_bayut.py --date 20260707 --types sale,rent

Writes back to the SAME CSV (data/raw/listings_bayut_<date>.csv) after saving a
one-time <file>.preenrich.bak. Progress is flushed every 25 rows so a mid-run
block loses nothing.
"""
import argparse
import csv
import datetime
import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listings_common as lc


def get_property_data(html):
    marker = "window.state = "
    i = html.find(marker)
    if i < 0:
        return None
    try:
        state, _ = json.JSONDecoder().raw_decode(html, i + len(marker))
    except json.JSONDecodeError:
        return None
    return (state or {}).get("property", {}).get("data")


def clean_desc(html_desc):
    t = re.sub(r"<[^>]+>", " ", html_desc or "")
    return re.sub(r"\s+", " ", t).strip()


def amenity_slugs(prop):
    return [a.get("slug", "") for g in prop.get("amenities", []) for a in g.get("amenities", [])]


def parse_view(text):
    # NOTE: exclude CTA noise ("schedule a viewing", "to view the property").
    # Only genuine typed-view phrases map to an enum value.
    t = text.lower()
    if "sea view" in t or "overlooking the sea" in t:
        return "sea"
    if "panoram" in t:
        return "panoramic"
    if any(k in t for k in ["mountain view", "mountains view", "overlooking the mountain",
                            "views of the mountain"]):
        return "mountain"
    if any(k in t for k in ["garden view", "green view", "overlooking the garden",
                            "views of the greenery", "greenery view", "park view"]):
        return "garden"
    if any(k in t for k in ["city view", "overlooking the city", "city skyline",
                            "views of the city", "views of amman", "open view",
                            "unobstructed view"]):
        return "city"
    return "unknown"


def parse_parking(text, slugs):
    joined = " ".join(slugs)
    if any(k in joined for k in ["covered-parking", "underground-parking", "basement-parking", "garage"]):
        return "covered"
    if "parking" in joined:
        return "open"
    t = text.lower()
    if any(k in t for k in ["covered parking", "underground parking", "basement parking", "private garage", "garage"]):
        return "covered"
    if "parking" in t:
        return "open"
    return "unknown"


def parse_floor(text):
    """Return (floor_level, total_floors) parsed from description, or (None, None)."""
    t = text.lower()
    floor = total = None
    if "ground floor" in t:
        floor = 0
    else:
        m = re.search(r"(?:on the|located on the|the)\s*(\d{1,2})(?:st|nd|rd|th)\s*floor", t)
        if not m:
            m = re.search(r"floor\s*(?:number|no\.?|:)\s*(\d{1,2})", t)
        if not m:
            m = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s*floor", t)
        if m:
            v = int(m.group(1))
            if v <= 40:
                floor = v
    m = re.search(r"(\d{1,2})\s*(?:-|\s)?(?:storey|story|floors?)\s*building", t)
    if not m:
        m = re.search(r"building\s*(?:of|with)\s*(\d{1,2})\s*floors?", t)
    if m:
        v = int(m.group(1))
        if v <= 40:
            total = v
    return floor, total


def parse_building_age(text, completion_status):
    """Years since built. Off-plan/under-construction -> 0 (brand new).
    Returns (age_years or None, note)."""
    cs = (completion_status or "").lower()
    t = text.lower()
    if cs in ("off-plan", "off_plan", "under-construction", "under_construction"):
        return 0, "off-plan/under-construction -> age 0"
    if any(k in t for k in ["brand new", "brand-new", "newly built", "newly constructed", "never lived"]):
        return 0, "brand new (text)"
    m = re.search(r"built in (\d{4})", t)
    if m:
        yr = int(m.group(1))
        if 1970 <= yr <= 2026:
            return 2026 - yr, f"built in {yr} (text)"
    m = re.search(r"(\d{1,2})\s*years?\s*old", t)
    if m:
        return int(m.group(1)), "age from text"
    return None, None


def parse_finish(text):
    t = text.lower()
    if any(k in t for k in ["super deluxe", "super-deluxe", "ultra luxury", "ultra-luxury", "luxurious finish", "luxury finish"]):
        return "luxury"
    if any(k in t for k in ["deluxe", "high-end", "high end", "premium finish", "top finish", "excellent finish"]):
        return "high"
    if any(k in t for k in ["semi-finished", "semi finished", "core and shell", "core & shell", "unfinished"]):
        return "basic"
    if any(k in t for k in ["standard finish", "good finish", "well finished"]):
        return "standard"
    if "luxur" in t:
        return "high"
    return "unknown"


def parse_elevator(text, slugs):
    if any("elevator" in s or "lift" in s for s in slugs):
        return "y"
    if re.search(r"\b(elevator|lift)\b", text.lower()):
        return "y"
    return "u"


def enrich_row(row, prop):
    """Mutate row in place from detail property data. Returns dict of which
    target fields got a real (non-unknown) value."""
    desc = clean_desc(prop.get("description"))
    slugs = amenity_slugs(prop)
    got = {}

    v = parse_view(desc)
    if v != "unknown":
        row["view"] = v
        got["view"] = v

    pk = parse_parking(desc, slugs)
    if pk != "unknown":
        row["parking"] = pk
        got["parking"] = pk

    fl, tot = parse_floor(desc)
    if fl is not None:
        row["floor_level"] = fl
        got["floor_level"] = fl
    if tot is not None:
        row["total_floors"] = tot
        got["total_floors"] = tot

    age, agenote = parse_building_age(desc, prop.get("completionStatus"))
    if age is not None:
        row["building_age_years"] = age
        got["building_age_years"] = age

    fq = parse_finish(desc)
    if fq != "unknown":
        row["finish_quality"] = fq
        got["finish_quality"] = fq

    el = parse_elevator(desc, slugs)
    if el != "u":
        row["elevator"] = el
        got["elevator"] = el

    if prop.get("isDeveloper") is True:
        row["seller_type"] = "developer"
        got["seller_type"] = "developer"

    # keep a compact provenance note without clobbering the original
    tags = ["enriched=detail"]
    if got:
        tags.append("fields=" + ",".join(sorted(got.keys())))
    else:
        tags.append("fields=none")
    base = row.get("notes", "")
    row["notes"] = (base + "; " if base else "") + "; ".join(tags)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--types", default="sale", help="comma list: sale,rent")
    ap.add_argument("--delay", type=float, default=2.2)
    ap.add_argument("--limit", type=int, default=0, help="0 = all matching rows")
    ap.add_argument("--dry-run", action="store_true", help="don't write CSV")
    args = ap.parse_args()

    types = {t.strip() for t in args.types.split(",") if t.strip()}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "data", "raw", f"listings_bayut_{args.date}.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    targets = [r for r in rows if r["listing_type"] in types]
    if args.limit:
        targets = targets[:args.limit]
    print(f"Enriching {len(targets)} Bayut rows (types={sorted(types)}) from {path}")

    if not args.dry_run:
        bak = path + ".preenrich.bak"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
            print(f"  backup -> {bak}")

    from collections import Counter
    fieldhits = Counter()
    ok = fail = 0
    for n, row in enumerate(targets, 1):
        eid = row["listing_id"].replace("bayut-", "")
        url = f"https://www.bayut.jo/en/property/details-{eid}.html"
        try:
            html = lc.fetch(url, retries=1)
            prop = get_property_data(html)
        except Exception as e:
            fail += 1
            print(f"  [{n}/{len(targets)}] {eid} FETCH-ERR {e}")
            if fail >= 8 and fail > ok:
                print("  Too many consecutive failures — stopping, keeping progress.")
                break
            continue
        if not prop:
            fail += 1
            print(f"  [{n}/{len(targets)}] {eid} no property data")
            continue
        got = enrich_row(row, prop)
        for k in got:
            fieldhits[k] += 1
        ok += 1
        if n % 20 == 0 or n == len(targets):
            print(f"  [{n}/{len(targets)}] ok={ok} fail={fail} viewhits={fieldhits['view']}")
        if not args.dry_run and n % 25 == 0:
            lc.write_csv(path, rows)
        time.sleep(args.delay)

    if not args.dry_run:
        lc.write_csv(path, rows)
    print(f"\n=== enrichment done: ok={ok} fail={fail} ===")
    for k in ["view", "parking", "floor_level", "total_floors", "building_age_years", "finish_quality", "elevator", "seller_type"]:
        print(f"  {k:20} filled {fieldhits[k]}/{ok}")


if __name__ == "__main__":
    main()
