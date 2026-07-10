"""Fetch the macro indicators the manager asked for (gold, dollar, rates, inflation) into
macro_series: gold price in JOD, USD/JOD, CBJ policy rate, CPI inflation.

Source policy (honest, no fabrication):
  * USD/JOD is fetched LIVE from a free no-key API (open.er-api.com). The dinar is a de-facto
    USD peg (~0.709), so this is near-constant; on network failure we fall back to the peg and
    flag confidence 'M'.
  * Gold (21K/24K JOD/gram), CBJ policy rate and CPI have no free no-key API. They are stored as
    the latest REAL official/quoted values with their own as-of date + source URL, flagged for
    periodic refresh from the cited page. No value is invented — each carries its provenance.

Every row is written with (indicator, geography, period=as_of, value, unit, source_url,
capture_date). Load with:  python db/load_csv.py data/processed/macro_indicators.csv \
    --table macro_series --replace

Usage:
    python scrapers/macro_indicators.py            # writes data/processed/macro_indicators.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
CAPTURE = date.today().isoformat()
COLLECTED_BY = "macro-pipeline-agent"

COLUMNS = [
    "indicator", "geography", "period", "value", "unit", "evidence_category", "language",
    "source_name", "source_url", "capture_date", "collected_by", "confidence", "notes",
]

# Latest REAL official/quoted values (fetched via research on the cited dates). No free no-key
# API exists for these, so they are refreshed from the source page — value + as-of + URL are real.
DOCUMENTED = [
    {
        "indicator": "Gold price 24K", "period": "2026-07-05", "value": 95.30, "unit": "JOD/gram",
        "source_name": "LivePriceofGold", "source_url": "https://www.livepriceofgold.com/jordan-gold-price.html",
        "confidence": "M",
        "notes": "24K spot, snapshot from cited page; no free no-key gold API — refresh periodically",
    },
    {
        "indicator": "Gold price 21K", "period": "2026-07-05", "value": 81.52, "unit": "JOD/gram",
        "source_name": "GoldPricez Jordan", "source_url": "https://goldpricez.com/jo/21k/gram",
        "confidence": "M",
        "notes": "21K is the local Jordanian retail benchmark; snapshot from cited page — refresh periodically",
    },
    {
        "indicator": "CBJ policy rate", "period": "2026-06-18", "value": 5.75, "unit": "%",
        "source_name": "Central Bank of Jordan", "source_url": "https://www.cbj.gov.jo/en/Pages/Maininterestrates",
        "confidence": "H",
        "notes": "Main policy (OMO) rate held at 5.75% on 2026-06-18; rediscount 7.5%; drives mortgage cost",
    },
    {
        "indicator": "CPI inflation (YoY)", "period": "2026-05", "value": 2.83, "unit": "% YoY",
        "source_name": "DoS Jordan", "source_url": "https://dosweb.dos.gov.jo/",
        "confidence": "H",
        "notes": "May 2026 YoY (highest since Apr 2023); Jan-May 2026 cumulative 1.88%; rent is top driver",
    },
]

PEG_FALLBACK = 0.709


def fetch_usd_jod() -> dict:
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
        rate = data["rates"]["JOD"]
        as_of = (data.get("time_last_update_utc") or CAPTURE)[:16]
        return {
            "indicator": "USD/JOD exchange rate", "period": CAPTURE, "value": round(rate, 4),
            "unit": "JOD per USD", "source_name": "open.er-api.com", "source_url": url,
            "confidence": "H",
            "notes": f"live fetch (updated {as_of}); dinar is a de-facto USD peg ~{PEG_FALLBACK}",
        }
    except Exception as exc:  # network unavailable -> fall back to the documented peg, flagged
        return {
            "indicator": "USD/JOD exchange rate", "period": CAPTURE, "value": PEG_FALLBACK,
            "unit": "JOD per USD", "source_name": "CBJ de-facto peg", "source_url": url,
            "confidence": "M",
            "notes": f"live fetch failed ({type(exc).__name__}); using CBJ de-facto peg {PEG_FALLBACK}",
        }


def to_csv_row(item: dict) -> dict:
    return {
        "indicator": item["indicator"], "geography": "Jordan", "period": item["period"],
        "value": item["value"], "unit": item["unit"], "evidence_category": "macro",
        "language": "en", "source_name": item["source_name"], "source_url": item["source_url"],
        "capture_date": CAPTURE, "collected_by": COLLECTED_BY,
        "confidence": item["confidence"], "notes": item["notes"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch macro indicators into macro_series CSV.")
    parser.add_argument("--out", type=Path,
                        default=_ROOT / "data" / "processed" / "macro_indicators.csv")
    args = parser.parse_args()

    items = [fetch_usd_jod(), *DOCUMENTED]
    rows = [to_csv_row(i) for i in items]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"macro_indicators: {len(rows)} rows written to {args.out} (capture {CAPTURE})")
    for i in items:
        print(f"  {i['indicator']:<26} {i['value']:>8} {i['unit']:<12} "
              f"as_of {i['period']:<12} [{i['confidence']}] {i['source_name']}")


if __name__ == "__main__":
    main()
