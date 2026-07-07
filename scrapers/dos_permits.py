"""Task C: DoS building permits via JorInfo PxWeb API (BUILD_T3, by governorate).
Pulls No. of Licenses + Total Area for all governorates, recent years, all quarters.
Sums over wall material (Stone + Cement Bricks). Emits macro_series partial rows.
"""
import csv
import json
import requests

requests.packages.urllib3.disable_warnings()
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Content-Type": "application/json"}
TABLE = "https://jorinfo.dos.gov.jo/Databank/api/v1/en/DOS_Database/19/BUILD_T3"
RAW = r"C:\Rubicon\Real-Estate-Jordan\data\raw\dos\BUILD_T3_response.json"
OUT = r"C:\Rubicon\Real-Estate-Jordan\data\processed\_dos_rows.csv"
CAPTURE = "2026-07-07"
PAGE_URL = "https://dosweb.dos.gov.jo/industry/building-licenses/"

GOV = {"11": "Amman", "12": "Balqa", "13": "Zarqa", "14": "Madaba", "21": "Irbid",
       "22": "Mafraq", "23": "Jerash", "24": "Ajloun", "31": "Karak", "32": "Tafila",
       "33": "Ma'an", "34": "Aqaba"}
KIND = {"1": "No. of Licenses", "2": "Total Area"}
YEARS = ["2020", "2021", "2022", "2023", "2025", "2026"]
ROUNDS = {"1": "Q1", "2": "Q2", "3": "Q3", "4": "Q4"}


def query():
    body = {
        "query": [
            {"code": "KIND_BUILD", "selection": {"filter": "item", "values": ["1", "2"]}},
            {"code": "MAT_BUILD", "selection": {"filter": "item", "values": ["1", "2"]}},
            {"code": "GOV", "selection": {"filter": "item", "values": list(GOV.keys())}},
            {"code": "ROUND", "selection": {"filter": "item", "values": ["1", "2", "3", "4"]}},
            {"code": "TIME", "selection": {"filter": "item", "values": YEARS}},
        ],
        "response": {"format": "json"},
    }
    r = requests.post(TABLE, headers=H, data=json.dumps(body), timeout=90, verify=False)
    r.raise_for_status()
    return json.loads(r.content.decode("utf-8-sig"))


def main():
    j = query()
    with open(RAW, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    # key order matches query var order: KIND_BUILD, MAT_BUILD, GOV, ROUND, TIME
    agg = {}  # (kind,gov,round,time) -> summed value over material
    for rec in j.get("data", []):
        kind, mat, gov, rnd, time = rec["key"]
        raw = rec["values"][0]
        if raw in ("", ".", "..", "-", None):
            continue
        try:
            val = float(raw)
        except ValueError:
            continue
        k = (kind, gov, rnd, time)
        agg[k] = agg.get(k, 0.0) + val

    future = {"2026-Q2", "2026-Q3", "2026-Q4"}  # not yet reported as of capture date
    rows = []
    for (kind, gov, rnd, time), val in sorted(agg.items()):
        period = f"{time}-{ROUNDS[rnd]}"
        if period in future:
            continue
        metric = "dos_building_licenses_count" if kind == "1" else "dos_building_licensed_area_thousand_m2"
        unit = "licenses" if kind == "1" else "thousand_m2"
        rows.append({
            "indicator": metric,
            "geography": GOV[gov],
            "period": period,
            "value": round(val, 1),
            "unit": unit,
            "source_name": "Department of Statistics (JorInfo Databank, Building Licenses Table 3)",
            "source_url": PAGE_URL,
            "notes": f"New residential+non-residential buildings, sum of Stone+Cement Bricks walls. {KIND[kind]}. Area in THOUSANDS of m2 (000 M2) per DoS convention. Governorate level. PxWeb BUILD_T3. Note: 2024 absent from source.",
        })
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    periods = sorted(set(r["period"] for r in rows))
    print(f"rows={len(rows)} data_cells={len(j.get('data',[]))}")
    print("periods:", periods)
    amman = [r for r in rows if r["geography"] == "Amman"]
    print(f"Amman rows={len(amman)}; sample:")
    for r in amman[-6:]:
        print("  ", r["indicator"], r["period"], r["value"], r["unit"])


if __name__ == "__main__":
    main()
