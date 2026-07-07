"""Shared helpers for portal listing scrapers (Bayut, OpenSooq).

Frozen 33-column listings schema per MASTER-PLAN.md section 3 and the
team-lead task brief. Column order is FROZEN: never add/rename/remove.
"""
import csv
import re
import time
import urllib.request

COLUMNS = [
    "listing_id", "portal", "listing_url", "listing_type", "property_type",
    "neighborhood", "district", "lat", "lng", "price_jd", "area_m2",
    "bedrooms", "bathrooms", "floor_level", "total_floors", "view", "parking",
    "building_age_years", "furnishing", "elevator", "finish_quality",
    "seller_type", "listing_date", "main_image_url", "description_raw",
    "evidence_category", "language", "source_name", "source_url",
    "capture_date", "collected_by", "confidence", "notes",
]

# Five target Amman neighborhoods (canonical labels)
NEIGHBORHOODS = ["Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def fetch(url, timeout=30, retries=1):
    """GET a URL as text. Retries once on transient failure."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            })
            return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
        except Exception as e:  # transient network / rate-limit
            last = e
            if attempt < retries:
                time.sleep(4)
    raise last


def blank_row(neighborhood, capture_date, portal, source_name, confidence="H"):
    """A row pre-filled with schema defaults; unknown enums = 'unknown',
    unknown numerics = '' (empty)."""
    return {
        "listing_id": "", "portal": portal, "listing_url": "",
        "listing_type": "", "property_type": "apartment",
        "neighborhood": neighborhood, "district": "Amman",
        "lat": "", "lng": "", "price_jd": "", "area_m2": "",
        "bedrooms": "", "bathrooms": "", "floor_level": "", "total_floors": "",
        "view": "unknown", "parking": "unknown", "building_age_years": "",
        "furnishing": "unknown", "elevator": "u", "finish_quality": "unknown",
        "seller_type": "agent", "listing_date": "", "main_image_url": "",
        "description_raw": "", "evidence_category": "portal", "language": "en",
        "source_name": source_name, "source_url": "", "capture_date": capture_date,
        "collected_by": "portal-scraper-agent", "confidence": confidence, "notes": "",
    }


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---- conservative text parsing for secondary attributes ----

_VIEW_TYPES_EN = [
    ("sea", ["sea", "water", "beach"]),
    ("panoramic", ["panoramic", "panorama"]),
    ("mountain", ["mountain", "hill"]),
    ("garden", ["garden", "green area", "greenery", "landscape"]),
    ("city", ["city", "downtown", "skyline"]),
]
_VIEW_TYPES_AR = [
    ("sea", ["بحر"]),
    ("panoramic", ["بانورام"]),
    ("mountain", ["جبل"]),
    ("garden", ["حديق", "خضر"]),
    ("city", ["مدين"]),
]


def parse_view(text):
    """Map free text to the view enum (none|sea|city|garden|mountain|panoramic|unknown).
    Precision-first: needs an explicit 'X view/views' or 'overlooking X' phrase (EN) or an
    إطلالة/تطل + type pattern (AR). A generic 'view' with no stated type stays 'unknown', and
    a bare place name ('Sports City') never matches. EN + AR."""
    if not text:
        return "unknown"
    t = text.lower()
    for enum, kws in _VIEW_TYPES_EN:
        for kw in kws:
            if re.search(rf"\b{kw}[\s-]*views?\b", t) or re.search(rf"overlook\w*\s+(?:the\s+|a\s+)?{kw}", t):
                return enum
    if any(c in text for c in ["إطلال", "اطلال", "تطل", "مطل"]):
        for enum, kws in _VIEW_TYPES_AR:
            if any(k in text for k in kws):
                return enum
    return "unknown"


def parse_parking(text):
    t = text.lower()
    if any(k in t for k in ["covered parking", "underground parking", "basement parking", "garage"]):
        return "covered"
    if "parking" in t:
        return "open"
    return "unknown"


def parse_finish(text):
    t = text.lower()
    if any(k in t for k in ["luxury", "super deluxe", "super-deluxe", "luxurious"]):
        return "luxury"
    if any(k in t for k in ["high end", "high-end", "deluxe", "premium"]):
        return "high"
    if any(k in t for k in ["standard finish", "good finish"]):
        return "standard"
    if "basic" in t:
        return "basic"
    return "unknown"


def parse_elevator(text):
    t = text.lower()
    if any(k in t for k in ["elevator", "lift", "مصعد"]):
        return "y"
    return "u"


def parse_floor(text):
    """Return (floor_level, note) if a floor is mentioned, else (None, None)."""
    t = text.lower()
    if "ground floor" in t or "ground-floor" in t:
        return 0, "ground floor (text)"
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s*floor", t)
    if m:
        return int(m.group(1)), "floor from text"
    return None, None
