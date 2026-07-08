"""Ingest the 6 Project-on-Jordan portal scrapes into ONE canonical listings CSV.

Reads the raw per-portal outputs (Bayut, OpenSooq, Homes-Jordan, EurekaJo, AbuJudom,
4321Property), maps each portal's columns onto the FROZEN `listings` schema
(db/schema.sql), attaches per-row provenance, and writes a single UTF-8 CSV ready for
`db/load_csv.py --table listings`.

Scope: nationwide (all governorates present in the sources). Neighborhood granularity =
portal 'area' where available, else city; district = city. Currency is JOD throughout.

Usage:
    python scrapers/ingest_national.py --out data/processed/listings_national_20260708.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from neighborhoods import canon as canon_nbhd  # noqa: E402

# Raw source root (the separate data-collection tree).
SRC = Path("D:/Rubikon Labs/Project on Jordan/Data")

CANON_COLUMNS = [
    "listing_id", "portal", "listing_url", "listing_type", "property_type",
    "neighborhood", "district", "lat", "lng", "price_jd", "area_m2",
    "bedrooms", "bathrooms", "floor_level", "total_floors", "view", "parking",
    "building_age_years", "furnishing", "elevator", "finish_quality", "seller_type",
    "listing_date", "main_image_url", "description_raw",
    "evidence_category", "language", "source_name", "source_url",
    "capture_date", "collected_by", "confidence", "notes",
]

# ---------------------------------------------------------------------------
# value mappers → schema enums
# ---------------------------------------------------------------------------

def map_ptype(raw: str) -> str:
    s = (raw or "").lower()
    if "apartment" in s or "flat" in s:
        return "apartment"
    if "land" in s:
        return "land"
    if any(k in s for k in ("villa", "house", "townhouse", "chalet", "farm")):
        return "villa"
    if any(k in s for k in ("office", "shop", "commercial", "building", "showroom",
                            "warehouse", "restaurant", "cafe", "complex", "business",
                            "investment", "development", "store")):
        return "commercial"
    return "unknown"


def map_listing_type(purpose: str, default: str = "unknown") -> str:
    s = (purpose or "").lower()
    if "rent" in s:
        return "rent"
    if "sale" in s or "buy" in s:
        return "sale"
    return default


def map_furnishing(raw: str) -> str:
    s = (raw or "").lower()
    if s in ("", "unknown"):
        return "unknown"
    if "unfurnished" in s or s == "no":
        return "no"
    if "semi" in s or "partly" in s or "partial" in s:
        return "semi"
    if "furnished" in s or s in ("yes", "full"):
        return "full"
    return "unknown"


def map_finish(raw: str) -> str:
    s = (raw or "").lower()
    if "luxury" in s:
        return "luxury"
    if "super deluxe" in s or "deluxe" in s or "high" in s:
        return "high"
    if "standard" in s:
        return "standard"
    if "basic" in s:
        return "basic"
    return "unknown"


_NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def num(raw) -> str:
    """Return a clean numeric string or '' (blank → loader stores NULL)."""
    if raw is None:
        return ""
    s = str(raw).strip().replace(",", "")
    if s == "" or s.lower() in ("unknown", "none", "null", "n/a"):
        return ""
    m = _NUM_RE.match(str(raw).strip())
    if not m:
        return ""
    v = m.group(0).replace(",", "")
    try:
        f = float(v)
    except ValueError:
        return ""
    if f <= 0:
        return ""
    return v


def norm_nbhd(*candidates: str) -> str:
    """First non-blank candidate, normalized. Latin → Title Case; Arabic kept as-is."""
    for c in candidates:
        c = (c or "").strip()
        if not c or c.lower() in ("unknown", "none", "null"):
            continue
        c = re.sub(r"\s+", " ", c)
        # Title-case only if it's Latin script; keep Arabic/other untouched.
        if re.search(r"[A-Za-z]", c) and not re.search(r"[؀-ۿ]", c):
            c = c.title()
        return canon_nbhd(c)
    return ""


def iso_from_unix(raw) -> str:
    try:
        ts = float(raw)
        if ts > 1e12:  # milliseconds
            ts /= 1000.0
        return dt.datetime.utcfromtimestamp(ts).date().isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


def normalize_rent_monthly(row: dict) -> None:
    """Rewrite a RENT row's price_jd to a MONTHLY figure (engine annualizes ×12).

    Portals mix periodicity: Bayut quotes rent YEARLY (median ~72 JD/m²/yr), OpenSooq
    MONTHLY (~7.5 JD/m²/mo). A monthly residential rent in Jordan is ~3–15 JD/m²/mo;
    anything above ~25 JD/m²/mo is really an annual figure → divide by 12. Rows without
    area keep their value (they can't be yield comps anyway).
    """
    if row.get("listing_type") != "rent":
        return
    p = _to_f(row.get("price_jd"))
    a = _to_f(row.get("area_m2"))
    if p is None or a is None or a <= 0:
        return
    if p / a > 25:  # annual quote → monthly
        row["price_jd"] = str(round(p / 12.0, 2))
        row["notes"] = (row.get("notes") + "; " if row.get("notes") else "") + "rent normalized annual→monthly"


def _to_f(x):
    try:
        return float(str(x).replace(",", "")) if str(x).strip() else None
    except ValueError:
        return None


def read(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)


def base(row: dict, **over) -> dict:
    """A canonical row prefilled with common defaults; override with mapped values."""
    r = {c: "" for c in CANON_COLUMNS}
    r.update({
        "view": "unknown", "parking": "unknown", "furnishing": "unknown",
        "elevator": "unknown", "finish_quality": "unknown", "seller_type": "unknown",
        "evidence_category": "portal", "collected_by": "scraper", "confidence": "M",
    })
    r.update(over)
    return r


# ---------------------------------------------------------------------------
# per-portal mappers  (each yields canonical rows)
# ---------------------------------------------------------------------------

def from_bayut():
    p = SRC / "Bayut_Jordan/output/ads.csv"
    for row in read(p):
        if (row.get("currency") or "JOD").strip() not in ("JOD", ""):
            continue
        url = (row.get("url") or "").strip()
        if not url:
            continue
        yield base(
            row,
            listing_id="bayut_" + (row.get("external_id") or row.get("object_id") or "").strip(),
            portal="Bayut", listing_url=url,
            listing_type=map_listing_type(row.get("purpose")),
            property_type=map_ptype(row.get("category_slug")),
            neighborhood=norm_nbhd(row.get("location_area"), row.get("location_subarea"),
                                   row.get("location_city")),
            district=norm_nbhd(row.get("location_city")),
            lat=num(row.get("latitude")), lng=num(row.get("longitude")),
            price_jd=num(row.get("price")), area_m2=num(row.get("area_sqm")),
            bedrooms=num(row.get("bedrooms")), bathrooms=num(row.get("bathrooms")),
            furnishing=map_furnishing(row.get("furnishing_status")),
            seller_type="agent" if (row.get("agent_name") or "").strip() else "unknown",
            listing_date=iso_from_unix(row.get("created_at")),
            main_image_url=(row.get("cover_photo") or "").strip(),
            language="en", source_name="Bayut", source_url=url,
            capture_date="2026-07-06",
        )


def from_opensooq(fname, ltype):
    p = SRC / f"OpenSooq_Jordan/output/{fname}"
    for row in read(p):
        if (row.get("price_currency") or "JOD").strip() not in ("JOD", ""):
            continue
        url = (row.get("listing_url") or row.get("deep_link") or "").strip()
        if not url:
            continue
        yield base(
            row,
            listing_id="opensooq_" + (row.get("listing_id") or "").strip(),
            portal="OpenSooq", listing_url=url, listing_type=ltype,
            property_type=map_ptype(row.get("subcategory")),
            neighborhood=norm_nbhd(row.get("neighborhood"), row.get("city")),
            district=norm_nbhd(row.get("city")),
            price_jd=num(row.get("price_value")), area_m2=num(row.get("area_sqm")),
            bedrooms=num(row.get("bedrooms")), bathrooms=num(row.get("bathrooms")),
            floor_level=num(row.get("floor")),
            building_age_years=num(row.get("building_age")),
            furnishing=map_furnishing(row.get("furnishing")),
            description_raw=(row.get("description") or "").strip()[:2000],
            main_image_url=(row.get("image_url") or "").strip(),
            language="mixed", source_name="OpenSooq", source_url=url,
            capture_date="2026-07-06",
        )


def from_homes(fname, ltype):
    p = SRC / f"Homes_Jordan/output/{fname}"
    for row in read(p):
        url = (row.get("listing_url") or "").strip()
        if not url:
            continue
        yield base(
            row,
            listing_id="homes_" + ltype[0] + "_" + (row.get("reference") or row.get("ad_number") or "").strip(),
            portal="Homes-Jordan", listing_url=url, listing_type=ltype,
            property_type=map_ptype(row.get("property_type")),
            neighborhood=norm_nbhd(row.get("area"), row.get("city")),
            district=norm_nbhd(row.get("city")),
            price_jd=num(row.get("price_value")),
            area_m2=num(row.get("built_up_area_sqm")) or num(row.get("plot_area_sqm")),
            bedrooms=num(row.get("bedrooms")), bathrooms=num(row.get("bathrooms")),
            seller_type="agent",
            description_raw=(row.get("description") or "").strip()[:2000],
            main_image_url=(row.get("image_url") or "").strip(),
            language="en", source_name="Homes-Jordan", source_url=url,
            capture_date="2026-07-06",
        )


def from_eureka():
    p = SRC / "EurekaJo/output/eureka_listings.csv"
    for row in read(p):
        url = (row.get("listing_url") or "").strip()
        if not url:
            continue
        yield base(
            row,
            listing_id="eureka_" + (row.get("listing_id") or "").strip(),
            portal="EurekaJo", listing_url=url,
            listing_type=map_listing_type(row.get("purpose")),
            property_type=map_ptype(row.get("category_en")),
            neighborhood=norm_nbhd(row.get("location_ar")),
            price_jd=num(row.get("price_value")), area_m2=num(row.get("area_sqm")),
            bedrooms=num(row.get("bedrooms")), bathrooms=num(row.get("bathrooms")),
            total_floors=num(row.get("floors")),
            main_image_url=(row.get("image_url") or "").strip(),
            description_raw=(row.get("title_ar") or "").strip()[:500],
            language="ar", source_name="EurekaJo", source_url=url,
            capture_date="2026-07-07",
            notes="location/title Arabic (untranslated)",
        )


def from_abujudom():
    p = SRC / "AbuJudom_Jordan/output/abujudom_listings.csv"
    for row in read(p):
        url = (row.get("listing_url") or "").strip()
        if not url:
            continue
        yield base(
            row,
            listing_id="abujudom_" + (row.get("listing_id") or row.get("property_id") or "").strip(),
            portal="AbuJudom", listing_url=url,
            listing_type=map_listing_type(row.get("purpose")),
            property_type=map_ptype(row.get("property_type")),
            neighborhood=norm_nbhd(row.get("neighborhood"), row.get("city")),
            district=norm_nbhd(row.get("city")),
            price_jd=num(row.get("price_value")),
            area_m2=num(row.get("property_area_sqm")) or num(row.get("land_area_sqm")),
            bedrooms=num(row.get("bedrooms")), bathrooms=num(row.get("bathrooms")),
            seller_type="agent",
            description_raw=(row.get("description") or "").strip()[:2000],
            main_image_url=(row.get("image_url") or "").strip(),
            language="en", source_name="AbuJudom", source_url=url,
            capture_date="2026-07-07",
        )


def from_4321():
    p = SRC / "Property4321_Jordan/output/property4321_listings.csv"
    for row in read(p):
        url = (row.get("listing_url") or "").strip()
        if not url:
            continue
        yield base(
            row,
            listing_id="p4321_" + (row.get("ad_id") or "").strip(),
            portal="4321Property", listing_url=url,
            listing_type=map_listing_type(row.get("purpose")),
            property_type=map_ptype(row.get("property_type")),
            neighborhood=norm_nbhd(row.get("neighborhood"), row.get("city")),
            district=norm_nbhd(row.get("city")),
            lat=num(row.get("latitude")), lng=num(row.get("longitude")),
            price_jd=num(row.get("price_value")), area_m2=num(row.get("area_sqm_text")),
            bedrooms=num(row.get("bedrooms")), bathrooms=num(row.get("bathrooms")),
            floor_level=num(row.get("floor_level")), total_floors=num(row.get("no_of_floors")),
            building_age_years=num(row.get("age_years")),
            furnishing=map_furnishing(row.get("furnished")),
            finish_quality=map_finish(row.get("finish_grade")),
            description_raw=(row.get("description") or "").strip()[:2000],
            language="en", source_name="4321Property", source_url=url,
            capture_date="2026-07-07",
        )


# Governorate/city name canonicalization. Outside Amman the geocoded data is too
# sparse for submarket circles, so we pool each secondary city under one canonical
# name and price it at CITY level (Amman keeps submarket granularity).
_CITY_ALIASES = {
    "amman": "Amman",
    "salt": "Al Salt", "al salt": "Al Salt", "balqa": "Al Salt", "al balqa": "Al Salt", "alsalt": "Al Salt",
    "irbid": "Irbid", "ramtha": "Irbid", "ar ramtha": "Irbid",
    "zarqa": "Zarqa", "az zarqa": "Zarqa",
    "aqaba": "Aqaba", "madaba": "Madaba", "jerash": "Jerash", "jarash": "Jerash",
    "mafraq": "Mafraq", "al mafraq": "Mafraq",
    "karak": "Karak", "al karak": "Karak",
    "ajlun": "Ajloun", "ajloun": "Ajloun",
    "maan": "Ma'an", "ma'an": "Ma'an", "ma`an": "Ma'an",
    "tafielah": "Tafilah", "tafila": "Tafilah", "tafilah": "Tafilah", "at tafilah": "Tafilah",
    "al ghor": "Jordan Valley", "ghor": "Jordan Valley", "jordan valley": "Jordan Valley",
    "dead sea": "Jordan Valley",
}


def canon_city(d: str) -> str:
    d = (d or "").strip()
    if not d:
        return ""
    if re.search(r"[؀-ۿ]", d):
        return d
    return _CITY_ALIASES.get(d.lower(), d.title())


SOURCES = [
    ("Bayut", from_bayut),
    ("OpenSooq-sale", lambda: from_opensooq("for-sale.csv", "sale")),
    ("OpenSooq-rent", lambda: from_opensooq("for-rent.csv", "rent")),
    ("Homes-sale", lambda: from_homes("sale.csv", "sale")),
    ("Homes-rent", lambda: from_homes("rent.csv", "rent")),
    ("EurekaJo", from_eureka),
    ("AbuJudom", from_abujudom),
    ("4321Property", from_4321),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=Path("data/processed/listings_national_20260708.csv"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    counts: dict[str, int] = {}
    kept = dropped_dup = dropped_bad = 0

    with args.out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CANON_COLUMNS)
        w.writeheader()
        for label, fn in SOURCES:
            n = 0
            for r in fn():
                lid = r["listing_id"]
                if not lid or lid.endswith("_"):
                    dropped_bad += 1
                    continue
                if not r["neighborhood"]:
                    r["neighborhood"] = r.get("district") or "Unknown"
                # City-level pooling for secondary governorates (Amman keeps submarkets).
                r["district"] = canon_city(r["district"])
                if r["district"] and r["district"] != "Amman":
                    r["neighborhood"] = r["district"]
                normalize_rent_monthly(r)
                if lid in seen:
                    dropped_dup += 1
                    continue
                seen.add(lid)
                w.writerow(r)
                n += 1
                kept += 1
            counts[label] = n
            print(f"  {label:16s} {n:>7,}")

    print(f"\nTOTAL kept: {kept:,}  | dup dropped: {dropped_dup:,} | bad-id dropped: {dropped_bad:,}")
    print("written -> " + str(args.out))


if __name__ == "__main__":
    main()
