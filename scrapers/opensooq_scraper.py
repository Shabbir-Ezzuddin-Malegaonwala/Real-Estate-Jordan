"""OpenSooq Jordan listings scraper (sale + rent) for 5 Amman neighborhoods.

Method: plain HTTP GET of neighborhood-filtered SERP pages. OpenSooq is a
Next.js site; each page embeds `__NEXT_DATA__` with a structured
`serpApiResponse.listings.items` array (30 per page). Neighborhoods are
filtered with the query param `?nhood_ids=<id>`; pages with `&page=<n>`.

Re-runnable and date-parameterized:
    python opensooq_scraper.py --date 20260707 --sale-pages 2 --rent-pages 1

Output: data/raw/listings_opensooq_<date>.csv (UTF-8, frozen 33-col schema).
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

SALE = "https://jo.opensooq.com/en/amman/property/apartments-for-sale?nhood_ids={nid}&page={n}"
RENT = "https://jo.opensooq.com/en/amman/property/apartments-for-rent?nhood_ids={nid}&page={n}"
IMG_BASE = "https://opensooq-images.os-cdn.com/previews/2048x0/"

# canonical neighborhood -> OpenSooq nhood_id
NHOOD_IDS = {
    "Abdoun": 6739,
    "Dabouq": 6795,
    "Sweifieh": 6857,   # OpenSooq label "Swefieh"
    "Khalda": 6835,
    "Shmeisani": 6853,  # OpenSooq label "Shmaisani"
}

ARABIC = re.compile(r"[؀-ۿ]")


def extract_items(html):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return []
    try:
        d = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    return d.get("props", {}).get("pageProps", {}).get("serpApiResponse", {}).get(
        "listings", {}).get("items", [])


def _first(*vals):
    for v in vals:
        if v is not None:
            return v
    return None


def parse_price(price_amount):
    if not price_amount:
        return None
    m = re.search(r"[\d,]+", str(price_amount))
    if not m:
        return None
    val = int(m.group(0).replace(",", ""))
    return val if val > 0 else None


def parse_highlights(text):
    """'3 Bedrooms » 4 Bathrooms » 150 m2' -> (beds, baths, area_m2)."""
    beds = baths = area = None
    if not text:
        return beds, baths, area
    t = text.lower()
    if "studio" in t:
        beds = 0
    else:
        m = re.search(r"(\d+)\s*bedroom", t)
        if m:
            beds = int(m.group(1))
    m = re.search(r"(\d+)\s*bathroom", t)
    if m:
        baths = int(m.group(1))
    m = re.search(r"([\d,.]+)\s*m2", t)
    if m:
        try:
            area = round(float(m.group(1).replace(",", "")), 2)
        except ValueError:
            pass
    return beds, baths, area


def property_type_from_cat(cat2_label):
    t = (cat2_label or "").lower()
    if "villa" in t or "townhouse" in t or "house" in t:
        return "villa"
    if "land" in t or "farm" in t:
        return "land"
    if any(k in t for k in ["office", "shop", "commercial", "warehouse", "showroom"]):
        return "commercial"
    return "apartment"


def parse_furnishing(text):
    t = (text or "").lower()
    if "semi" in t and "furnish" in t:
        return "semi"
    if "unfurnished" in t or "not furnished" in t:
        return "no"
    if "furnished" in t or "furnishing" in t:
        return "full"
    return "unknown"


ORDINAL_FLOOR = {"ground": 0, "first": 1, "second": 2, "third": 3, "fourth": 4,
                 "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9,
                 "tenth": 10}


def parse_cps(cps):
    """The `cps` chip array is OpenSooq's structured attribute list, e.g.
    ['3 Bedrooms', '4 Bathrooms', 'Unfurnished', 'Area: 190 m2',
     'Second Floor', 'Building Age: 0 - 11 months']. Returns a dict of the
    fields it can resolve (missing keys omitted)."""
    out = {}
    if not isinstance(cps, list):
        return out
    for chip in cps:
        c = str(chip).strip()
        cl = c.lower()
        m = re.match(r"(\d+)\s*bedroom", cl)
        if m:
            out["bedrooms"] = int(m.group(1))
        elif "studio" in cl:
            out["bedrooms"] = 0
        elif re.match(r"(\d+)\s*bathroom", cl):
            out["bathrooms"] = int(re.match(r"(\d+)", cl).group(1))
        elif re.search(r"area:?\s*([\d,.]+)\s*m", cl):
            val = re.search(r"area:?\s*([\d,.]+)\s*m", cl).group(1)
            out["area_m2"] = round(float(val.replace(",", "")), 2)
        elif parse_furnishing(cl) != "unknown":
            out["furnishing"] = parse_furnishing(cl)
        elif _cps_floor(cl) is not None:
            out["floor_level"] = _cps_floor(cl)
        elif "building age" in cl:
            out["building_age_years"] = _cps_age(cl)
            out["age_raw"] = c
    return out


def _cps_floor(cl):
    if "floor" not in cl:
        return None
    if "basement" in cl:
        return -1
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s*floor", cl)
    if m:
        return int(m.group(1))
    for word, n in ORDINAL_FLOOR.items():
        if word in cl:
            return n
    return None


def _cps_age(cl):
    """Low-bound integer years. Months / under-construction -> 0."""
    if "month" in cl or "under construction" in cl:
        return 0
    m = re.search(r"(\d+)", cl.split(":", 1)[-1])
    return int(m.group(1)) if m else ""


def item_to_row(it, neighborhood, listing_type, capture_date):
    row = lc.blank_row(neighborhood, capture_date, "opensooq", "OpenSooq")
    lid = str(it.get("id", "")).strip()
    row["listing_id"] = f"opensooq-{lid}"
    post = it.get("post_url") or f"/search/{lid}"
    url = "https://jo.opensooq.com/en" + post if post.startswith("/") else post
    row["listing_url"] = url
    row["source_url"] = url
    row["listing_type"] = listing_type
    row["property_type"] = property_type_from_cat(it.get("cat2_label"))

    price = parse_price(it.get("price_amount"))
    if price is not None:
        row["price_jd"] = price

    # `cps` is the structured chip array (primary); highlights + title fill gaps.
    cps = parse_cps(it.get("cps"))
    hb, hba, ha = parse_highlights(it.get("highlights"))
    tb, tba, ta = parse_highlights(it.get("title"))
    beds = _first(cps.get("bedrooms"), hb, tb)
    baths = _first(cps.get("bathrooms"), hba, tba)
    area = _first(cps.get("area_m2"), ha, ta)
    if beds is not None:
        row["bedrooms"] = beds
    if baths is not None:
        row["bathrooms"] = baths
    if area is not None:
        row["area_m2"] = area
    if "floor_level" in cps:
        row["floor_level"] = cps["floor_level"]
    if "building_age_years" in cps:
        row["building_age_years"] = cps["building_age_years"]

    title = it.get("title") or ""
    desc = it.get("masked_description") or title
    blob = f"{title} {desc}"
    row["furnishing"] = cps.get("furnishing") or parse_furnishing(blob)
    row["view"] = lc.parse_view(blob)
    row["parking"] = lc.parse_parking(blob)
    row["finish_quality"] = lc.parse_finish(blob)
    row["elevator"] = lc.parse_elevator(blob)
    if row["floor_level"] == "":
        fl, _ = lc.parse_floor(blob)
        if fl is not None:
            row["floor_level"] = fl

    row["description_raw"] = desc.replace("\n", " ").strip()[:2000]
    row["language"] = "mixed" if ARABIC.search(desc) else "en"

    d = it.get("inserted_date")
    if d and re.match(r"\d{4}-\d{2}-\d{2}", str(d)):
        row["listing_date"] = str(d)[:10]

    img = it.get("image_uri")
    if img:
        row["main_image_url"] = IMG_BASE + img

    shop = (it.get("shop_name") or "").strip()
    row["seller_type"] = "agent" if shop else "private"

    # confidence: H when core structured fields (price + area) both present,
    # else M (source is the noisier private-seller portal)
    row["confidence"] = "H" if (row["price_jd"] != "" and row["area_m2"] != "") else "M"

    notes = ["lat/lng not exposed in OpenSooq SERP",
             f"portal_nhood={it.get('nhood_label')}"]
    if shop:
        notes.append(f"shop={shop}")
    if cps.get("age_raw"):
        notes.append(cps["age_raw"])
    row["notes"] = "; ".join(str(x) for x in notes)
    return row


def scrape(date_str, sale_pages, rent_pages, delay=2.5):
    rows, seen, per = [], set(), {}
    plans = [(SALE, "sale", sale_pages), (RENT, "rent", rent_pages)]
    for neighborhood, nid in NHOOD_IDS.items():
        for tmpl, listing_type, npages in plans:
            got = 0
            for n in range(1, npages + 1):
                url = tmpl.format(nid=nid, n=n)
                try:
                    html = lc.fetch(url, retries=1)
                except Exception as e:
                    print(f"  [WARN] {neighborhood} {listing_type} page {n}: {e}")
                    break
                items = extract_items(html)
                if not items:
                    print(f"  [info] {neighborhood} {listing_type} page {n}: no items, stopping")
                    break
                new = 0
                for it in items:
                    lid = str(it.get("id", "")).strip()
                    key = f"opensooq-{lid}"
                    if not lid or key in seen:
                        continue
                    seen.add(key)
                    rows.append(item_to_row(it, neighborhood, listing_type, date_str))
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
    ap.add_argument("--sale-pages", type=int, default=2)
    ap.add_argument("--rent-pages", type=int, default=1)
    ap.add_argument("--delay", type=float, default=2.5)
    args = ap.parse_args()

    capture_date = datetime.datetime.strptime(args.date, "%Y%m%d").strftime("%Y-%m-%d")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "data", "raw", f"listings_opensooq_{args.date}.csv")

    print(f"Scraping OpenSooq -> {out}")
    rows, per = scrape(capture_date, args.sale_pages, args.rent_pages, args.delay)
    lc.write_csv(out, rows)

    print("\n=== OpenSooq summary ===")
    sale = sum(1 for r in rows if r["listing_type"] == "sale")
    rent = sum(1 for r in rows if r["listing_type"] == "rent")
    print(f"TOTAL {len(rows)} (sale {sale}, rent {rent})")
    for k, v in per.items():
        print(f"  {k[0]:10} {k[1]:5} {v}")


if __name__ == "__main__":
    main()
