"""Re-derive Bayut secondary attributes from the description_raw already in the
CSV — no network. Idempotent: only fills a target field when it is currently
'unknown'/'u'/empty, so it never clobbers stronger data.

Exists because the Bayut CSV is written by more than one step (a teammate
populates full detail descriptions into description_raw); this re-applies the
attribute enrichment on top of whatever description text is present, merging
both without re-fetching Bayut.

Usage: python reenrich_bayut_from_csv.py --date 20260707 --types sale
"""
import argparse
import csv
import datetime
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listings_common as lc
import enrich_bayut as eb


def completion_from_notes(notes):
    m = re.search(r"completion=([\w-]+)", notes or "")
    return m.group(1) if m else ""


def reenrich(row):
    desc = row.get("description_raw", "") or ""
    got = {}
    if row["view"] in ("unknown", ""):
        v = eb.parse_view(desc)
        if v != "unknown":
            row["view"] = v
            got["view"] = v
    if row["parking"] in ("unknown", ""):
        pk = eb.parse_parking(desc, [])
        if pk != "unknown":
            row["parking"] = pk
            got["parking"] = pk
    if not row["floor_level"].strip():
        fl, tot = eb.parse_floor(desc)
        if fl is not None:
            row["floor_level"] = fl
            got["floor_level"] = fl
        if tot is not None and not row["total_floors"].strip():
            row["total_floors"] = tot
            got["total_floors"] = tot
    if not row["building_age_years"].strip():
        age, _ = eb.parse_building_age(desc, completion_from_notes(row["notes"]))
        if age is not None:
            row["building_age_years"] = age
            got["building_age_years"] = age
    if row["finish_quality"] in ("unknown", ""):
        fq = eb.parse_finish(desc)
        if fq != "unknown":
            row["finish_quality"] = fq
            got["finish_quality"] = fq
    if row["elevator"] in ("u", ""):
        el = eb.parse_elevator(desc, [])
        if el != "u":
            row["elevator"] = el
            got["elevator"] = el
    if got and "enriched=desc" not in (row.get("notes") or ""):
        row["notes"] = (row["notes"] + "; " if row["notes"] else "") + \
            "enriched=desc; fields=" + ",".join(sorted(got.keys()))
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--types", default="sale")
    args = ap.parse_args()
    types = {t.strip() for t in args.types.split(",") if t.strip()}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "data", "raw", f"listings_bayut_{args.date}.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    hits = Counter()
    n = 0
    for row in rows:
        if row["listing_type"] in types:
            n += 1
            for k in reenrich(row):
                hits[k] += 1
    lc.write_csv(path, rows)
    print(f"Re-enriched {n} Bayut rows (types={sorted(types)}) from in-file descriptions")
    for k in ["view", "parking", "floor_level", "total_floors", "building_age_years", "finish_quality", "elevator"]:
        print(f"  {k:20} filled {hits[k]}/{n}")


if __name__ == "__main__":
    main()
