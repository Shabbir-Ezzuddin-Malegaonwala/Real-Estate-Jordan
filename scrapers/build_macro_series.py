"""Assemble final macro_series.csv from CBJ + DoS partials, applying the FROZEN schema:
indicator, geography, period, value, unit, evidence_category, language,
source_name, source_url, capture_date, collected_by, confidence, notes
"""
import csv

PROC = r"C:\Rubicon\Real-Estate-Jordan\data\processed"
COLS = ["indicator", "geography", "period", "value", "unit", "evidence_category",
        "language", "source_name", "source_url", "capture_date", "collected_by",
        "confidence", "notes"]
CAPTURE = "2026-07-07"
COLLECTED_BY = "official-data-agent"


def load(name, evidence_category):
    rows = []
    with open(f"{PROC}\\{name}", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "indicator": r["indicator"],
                "geography": r["geography"],
                "period": r["period"],
                "value": r["value"],
                "unit": r["unit"],
                "evidence_category": evidence_category,
                "language": "en",
                "source_name": r["source_name"],
                "source_url": r["source_url"],
                "capture_date": CAPTURE,
                "collected_by": COLLECTED_BY,
                "confidence": "H",
                "notes": r["notes"],
            })
    return rows


def main():
    rows = load("_cbj_rows.csv", "macro") + load("_dos_rows.csv", "government")
    out = f"{PROC}\\macro_series.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    by_ind = Counter(r["indicator"] for r in rows)
    print(f"macro_series.csv rows={len(rows)} -> {out}")
    print(f"indicators={len(by_ind)} geographies={len(set(r['geography'] for r in rows))}")
    print(f"period span: {min(r['period'] for r in rows)} -> {max(r['period'] for r in rows)}")
    for ind, n in sorted(by_ind.items()):
        print(f"  {n:4d}  {ind}")


if __name__ == "__main__":
    main()
