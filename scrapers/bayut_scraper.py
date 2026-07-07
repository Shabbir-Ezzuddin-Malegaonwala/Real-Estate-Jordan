"""Bayut Jordan listings scraper (sale + rent) for 5 Amman neighborhoods.

Method: plain HTTP GET of the neighborhood listing pages. Each page embeds a
`window.state` blob (Algolia hits) with 24 fully-structured listing objects,
plus a JSON-LD block used only for the cover image URL. No per-detail fetches.

Re-runnable and date-parameterized:
    python bayut_scraper.py --date 20260707 --sale-pages 3 --rent-pages 2

Output: data/raw/listings_bayut_<date>.csv (UTF-8, frozen 33-col schema).
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listings_common as lc

BASE = "https://www.bayut.jo/en/amman/apartments-for-{tt}-in-{slug}/"
PAGE = "https://www.bayut.jo/en/amman/apartments-for-{tt}-in-{slug}/page-{n}/"

# canonical neighborhood -> Bayut location slug
SLUGS = {
    "Abdoun": "abdun",
    "Dabouq": "dabouq",
    "Sweifieh": "al-swaifyeh",
    "Khalda": "khalda",
    "Shmeisani": "shmeisani",
}

FURNISH = {"furnished": "full", "unfurnished": "no",
           "partly-furnished": "semi", "semi-furnished": "semi"}


def extract_window_state(html):
    marker = "window.state = "
    i = html.find(marker)
    if i < 0:
        return None
    i += len(marker)
    depth = 0
    for j in range(i, len(html)):
        c = html[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[i:j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def find_hits(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "hits" and isinstance(v, list) and v and isinstance(v[0], dict) and "externalID" in v[0]:
                return v
            r = find_hits(v)
            if r:
                return r
    elif isinstance(obj, list):
        for x in obj:
            r = find_hits(x)
            if r:
                return r
    return None


def jsonld_image_map(html):
    """externalID -> first image url, parsed from the JSON-LD ItemList."""
    m = re.search(r'application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
    out = {}
    if not m:
        return out
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return out
    for node in data.get("@graph", []):
        for it in node.get("mainEntity", {}).get("itemListElement", []) if isinstance(node.get("mainEntity"), dict) else []:
            item = it.get("item", {})
            url = item.get("url", "")
            ext = re.search(r'details-(\d+)', url)
            imgs = item.get("mainEntity", {}).get("image", [])
            if ext and imgs:
                out[ext.group(1)] = imgs[0]
    return out


def property_type_from_category(cat):
    if not isinstance(cat, list) or not cat:
        return "apartment"
    name = (cat[-1].get("name") or "").lower()
    if "villa" in name or "townhouse" in name:
        return "villa"
    if "land" in name or "plot" in name:
        return "land"
    if any(k in name for k in ["office", "shop", "commercial", "warehouse", "showroom"]):
        return "commercial"
    return "apartment"


def hit_to_row(hit, neighborhood, listing_type, img_map, capture_date):
    row = lc.blank_row(neighborhood, capture_date, "bayut", "Bayut", confidence="H")
    ext = str(hit.get("externalID", "")).strip()
    row["listing_id"] = f"bayut-{ext}"
    slug = hit.get("slug", f"details-{ext}")
    url = f"https://www.bayut.jo/en/property/{slug}.html"
    row["listing_url"] = url
    row["source_url"] = url
    row["listing_type"] = listing_type
    row["property_type"] = property_type_from_category(hit.get("category"))

    geo = hit.get("geography") or {}
    if isinstance(geo, dict):
        if geo.get("lat") is not None:
            row["lat"] = geo["lat"]
        if geo.get("lng") is not None:
            row["lng"] = geo["lng"]

    if hit.get("price") is not None:
        row["price_jd"] = hit["price"]
    if hit.get("area") is not None:
        # Bayut 'area' is built-up m2
        row["area_m2"] = round(float(hit["area"]), 2)
    if hit.get("rooms") is not None:
        row["bedrooms"] = hit["rooms"]
    if hit.get("baths") is not None:
        row["bathrooms"] = hit["baths"]

    fs = (hit.get("furnishingStatus") or "").lower()
    row["furnishing"] = FURNISH.get(fs, "unknown")

    title = hit.get("title") or ""
    row["description_raw"] = title.replace("\n", " ").strip()
    # conservative text-derived attributes (M-confidence signal; core stays H)
    row["view"] = lc.parse_view(title)
    row["parking"] = lc.parse_parking(title)
    row["finish_quality"] = lc.parse_finish(title)
    row["elevator"] = lc.parse_elevator(title)
    fl, flnote = lc.parse_floor(title)
    if fl is not None:
        row["floor_level"] = fl

    ts = hit.get("createdAt")
    if isinstance(ts, (int, float)):
        row["listing_date"] = datetime.datetime.fromtimestamp(
            ts, datetime.timezone.utc).strftime("%Y-%m-%d")

    cover = hit.get("coverPhoto")
    pid = None
    if isinstance(cover, dict) and cover.get("id"):
        pid = cover["id"]
    elif isinstance(hit.get("photoIDs"), list) and hit["photoIDs"]:
        pid = hit["photoIDs"][0]
    if pid:
        row["main_image_url"] = f"https://images.bayut.jo/thumbnails/{pid}-800x600.jpeg"
    else:
        row["main_image_url"] = img_map.get(ext, "")

    notes = []
    cs = hit.get("completionStatus")
    if cs:
        notes.append(f"completion={cs}")
    rf = hit.get("rentFrequency")
    if rf:
        notes.append(f"rent_freq={rf}")
    loc = hit.get("location")
    if isinstance(loc, list) and loc:
        notes.append("portal_locality=" + (loc[-1].get("name") or ""))
    if flnote:
        notes.append(flnote)
    notes.append("seller_type defaulted to agent (Bayut agency portal)")
    row["notes"] = "; ".join(notes)
    return row


def _detail_entity(html):
    """The schema.org RealEstateListing.mainEntity from a Bayut detail page."""
    for blk in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            d = json.loads(blk)
        except json.JSONDecodeError:
            continue
        for node in (d.get("@graph", [d]) if isinstance(d, dict) else d):
            if isinstance(node, dict) and isinstance(node.get("mainEntity"), dict):
                return node["mainEntity"]
    return None


def enrich_from_detail(row):
    """Fetch the listing detail page and upgrade text-only attributes from the full
    description + structured amenities. Returns True if the detail parsed, else False.
    Only fills fields still `unknown`/empty — never overwrites structured list data."""
    html = lc.fetch(row["listing_url"], retries=1)
    entity = _detail_entity(html)
    if entity is None:
        return False
    desc = (entity.get("description") or "").replace("\n", " ").strip()
    if desc:
        row["description_raw"] = desc[:2000]
    amenities = " ".join(a.get("name", "") for a in entity.get("amenityFeature", []) if isinstance(a, dict))
    blob = f"{row.get('description_raw', '')} {amenities}"
    if row["view"] == "unknown":
        row["view"] = lc.parse_view(blob)
    if row["parking"] == "unknown":
        row["parking"] = lc.parse_parking(blob)
    if row["finish_quality"] == "unknown":
        row["finish_quality"] = lc.parse_finish(desc)
    if row["elevator"] == "u":
        row["elevator"] = lc.parse_elevator(blob)
    return True


def enrich_rows(rows, delay=1.5, limit=0):
    """Detail-enrich rows in place. Aborts early if the site starts refusing (many
    consecutive detail pages without parseable JSON-LD = likely rate-limit/block)."""
    targets = rows if limit <= 0 else rows[:limit]
    ok = 0
    consecutive_fail = 0
    for i, row in enumerate(targets, 1):
        try:
            if enrich_from_detail(row):
                ok += 1
                consecutive_fail = 0
            else:
                consecutive_fail += 1
        except Exception as e:
            consecutive_fail += 1
            row["notes"] = (row.get("notes", "") + f"; detail enrich failed: {type(e).__name__}").strip("; ")
        if consecutive_fail >= 8:
            print(f"  [ABORT] {consecutive_fail} consecutive detail failures at row {i} — likely blocked; stopping enrichment")
            break
        if i % 25 == 0:
            print(f"  enriched {i}/{len(targets)} ({ok} ok)")
        time.sleep(delay)
    return ok


def scrape(date_str, sale_pages, rent_pages, delay=2.5):
    rows = []
    seen = set()
    per = {}  # (neighborhood, type) -> count
    plans = [("sale", "sale", sale_pages), ("rent", "rent", rent_pages)]
    for neighborhood, slug in SLUGS.items():
        for tt_key, listing_type, npages in plans:
            tt = "sale" if tt_key == "sale" else "rent"
            got = 0
            for n in range(1, npages + 1):
                url = BASE.format(tt=tt, slug=slug) if n == 1 else PAGE.format(tt=tt, slug=slug, n=n)
                try:
                    html = lc.fetch(url, retries=1)
                except Exception as e:
                    print(f"  [WARN] {neighborhood} {listing_type} page {n}: {e}")
                    break
                state = extract_window_state(html)
                hits = find_hits(state) if state else None
                if not hits:
                    print(f"  [info] {neighborhood} {listing_type} page {n}: no hits, stopping")
                    break
                img_map = jsonld_image_map(html)
                new = 0
                for hit in hits:
                    ext = str(hit.get("externalID", "")).strip()
                    key = f"bayut-{ext}"
                    if not ext or key in seen:
                        continue
                    seen.add(key)
                    rows.append(hit_to_row(hit, neighborhood, listing_type, img_map, date_str))
                    new += 1
                    got += 1
                print(f"  {neighborhood} {listing_type} page {n}: +{new} (total {got})")
                if new == 0:
                    break
                time.sleep(delay)
            per[(neighborhood, listing_type)] = got
    return rows, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--sale-pages", type=int, default=3)
    ap.add_argument("--rent-pages", type=int, default=2)
    ap.add_argument("--delay", type=float, default=2.5)
    ap.add_argument("--enrich-details", action="store_true",
                    help="fetch each listing's detail page to fill full description_raw + view/parking/finish/elevator")
    ap.add_argument("--enrich-delay", type=float, default=1.5)
    ap.add_argument("--enrich-limit", type=int, default=0, help="0 = all rows")
    args = ap.parse_args()

    capture_date = datetime.datetime.strptime(args.date, "%Y%m%d").strftime("%Y-%m-%d")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "data", "raw", f"listings_bayut_{args.date}.csv")

    print(f"Scraping Bayut -> {out}")
    rows, per = scrape(capture_date, args.sale_pages, args.rent_pages, args.delay)
    if args.enrich_details:
        print(f"Enriching {len(rows)} rows from detail pages (delay {args.enrich_delay}s)...")
        ok = enrich_rows(rows, args.enrich_delay, args.enrich_limit)
        view_n = sum(1 for r in rows if r["view"] not in ("", "unknown"))
        print(f"Detail enrichment: {ok} pages parsed; view now populated on {view_n}/{len(rows)}")
    lc.write_csv(out, rows)

    print("\n=== Bayut summary ===")
    sale = sum(1 for r in rows if r["listing_type"] == "sale")
    rent = sum(1 for r in rows if r["listing_type"] == "rent")
    print(f"TOTAL {len(rows)} (sale {sale}, rent {rent})")
    for k, v in per.items():
        print(f"  {k[0]:10} {k[1]:5} {v}")


if __name__ == "__main__":
    main()
