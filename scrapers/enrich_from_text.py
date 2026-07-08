"""C2 fix — populate view / parking / finish_quality / floor_level / elevator / furnishing
by mining listing free-text (English + Arabic), so the adjustment grid can actually fire.

The national ingest left these attribute columns ~empty (view/parking/elevator 0%,
finish 0.02%, floor 3.3%) because portals don't publish them as fields — but sellers
describe them in the text. This reads:
  * description_raw (OpenSooq/Homes/AbuJudom/Eureka — often Arabic),
  * Bayut `amenities` (joined back from the source ads.csv by external_id),
and extracts the attributes with bilingual keyword rules. It only FILLS blanks — it never
overwrites a value the portal already gave. Text-derived, so treated as Medium-confidence
downstream (the engine caps derived-premium confidence anyway).

Usage:
    python scrapers/enrich_from_text.py            # rewrites the national listings CSV in place
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

CSV = Path("data/processed/listings_national_20260708.csv")
BAYUT = Path("D:/Rubikon Labs/Project on Jordan/Data/Bayut_Jordan/output/ads.csv")

BLANK = ("", "unknown", "u")

# --- view ------------------------------------------------------------------
_VIEW_GATE = re.compile(r"\bview\b|اطلال|إطلال|اطلاله|اطلالة")
def extract_view(t: str, has_text: bool) -> str | None:
    if not _VIEW_GATE.search(t):
        return "none" if has_text else None
    if re.search(r"sea|بحر", t): return "sea"
    if re.search(r"panoram|بانورام", t): return "panoramic"
    if re.search(r"mountain|جبل", t): return "mountain"
    if re.search(r"garden|حديق", t): return "garden"
    return "city"  # a view is advertised but unspecified -> city (most common in Amman)

# --- parking ---------------------------------------------------------------
def extract_parking(t: str) -> str | None:
    if re.search(r"covered parking|underground parking|garage|كراج|كراش|مواقف مظلل|موقف مظلل", t):
        return "covered"
    if re.search(r"\bparking\b|carport|موقف سيارات|مواقف سيارات|موقف للسيارات", t):
        return "covered"  # apartment parking is typically covered/allocated
    return None

# --- finish ----------------------------------------------------------------
def extract_finish(t: str) -> str | None:
    if re.search(r"super deluxe|super-deluxe|luxur|فاخر|فخم|سوبر ديلوكس|سوبر ديلكس", t):
        return "luxury"
    if re.search(r"deluxe|high[- ]?end|high spec|ديلوكس|ديلكس|تشطيب ممتاز", t):
        return "high"
    if re.search(r"semi[- ]?finish|core (and|&) shell|unfinished|on bones|عظم|على العظم|نص تشطيب|نصف تشطيب", t):
        return "basic"
    if re.search(r"standard finish|good finish|تشطيب عادي|تشطيب جيد", t):
        return "standard"
    return None

# --- elevator --------------------------------------------------------------
def extract_elevator(t: str) -> str | None:
    if re.search(r"no elevator|no lift|بدون مصعد|بدون اصنصير", t):
        return "n"
    if re.search(r"\belevator\b|\blift\b|مصعد|اصنصير|أصنصير", t):
        return "y"
    return None

# --- furnishing ------------------------------------------------------------
def extract_furnishing(t: str) -> str | None:
    if re.search(r"semi[- ]?furnish|نص مفروش|نصف مفروش", t):
        return "semi"
    if re.search(r"unfurnish|not furnished|غير مفروش|بدون فرش", t):
        return "no"
    if re.search(r"\bfurnished\b|مفروش", t):
        return "full"
    return None

# --- floor -----------------------------------------------------------------
_AR_ORD = {"ارضي": 0, "أرضي": 0, "اول": 1, "أول": 1, "ثاني": 2, "ثالث": 3, "رابع": 4,
           "خامس": 5, "سادس": 6, "سابع": 7, "ثامن": 8, "تاسع": 9, "عاشر": 10}
_EN_ORD = {"ground": 0, "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
           "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}
def extract_floor(t: str) -> int | None:
    m = re.search(r"طابق\s*(?:ال)?(" + "|".join(_AR_ORD) + r")", t)
    if m: return _AR_ORD[m.group(1)]
    if re.search(r"طابق\s*(?:ال)?ارضي|طابق\s*(?:ال)?أرضي|ground floor|ground-floor", t):
        return 0
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*floor\b", t)
    if m and int(m.group(1)) <= 40: return int(m.group(1))
    m = re.search(r"\bfloor\s*(?:no\.?|number)?\s*(\d{1,2})\b", t)
    if m and int(m.group(1)) <= 40: return int(m.group(1))
    m = re.search(r"(" + "|".join(_EN_ORD) + r")\s*floor", t)
    if m: return _EN_ORD[m.group(1)]
    return None


def bayut_amenities() -> dict[str, str]:
    lut = {}
    for r in csv.DictReader(open(BAYUT, encoding="utf-8-sig")):
        a = (r.get("amenities") or "").strip()
        if a:
            lut["bayut_" + (r.get("external_id") or "").strip()] = a
    return lut


def main() -> None:
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    hdr = rows[0].keys()
    bayut = bayut_amenities()
    stat = {k: 0 for k in ("view", "parking", "finish_quality", "elevator", "furnishing", "floor_level")}

    for r in rows:
        text = (r.get("description_raw") or "")
        if r["portal"] == "Bayut":
            text += " " + bayut.get(r["listing_id"], "")
        t = text.lower()
        has_text = bool(text.strip())
        if not has_text:
            continue

        def fill(col, val):
            if val is not None and (r.get(col) or "").strip().lower() in BLANK:
                r[col] = str(val)
                stat[col] += 1

        fill("view", extract_view(t, has_text))
        fill("parking", extract_parking(t))
        fill("finish_quality", extract_finish(t))
        fill("elevator", extract_elevator(t))
        fill("furnishing", extract_furnishing(t))
        fill("floor_level", extract_floor(t))

    with CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hdr))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    print(f"enriched {n:,} rows from text. Newly filled:")
    for k, v in stat.items():
        filled = sum(1 for r in rows if (r.get(k) or "").strip().lower() not in BLANK)
        print(f"  {k:<16} +{v:>6,}  -> now {100*filled/n:5.1f}% populated")


if __name__ == "__main__":
    main()
