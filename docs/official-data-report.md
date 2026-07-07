# Official / Macro Data Extraction Report

**Capture date:** 2026-07-07 · **Collected by:** gis-specialist
**Script:** `scrapers/official_data.py` (re-runnable; `--refresh` re-downloads, `--only cbj,dos,dls,zoning` runs a subset)
**Raw cache:** `data/raw/official/` · **Run log:** `data/raw/official/run_log.txt`

All CSVs follow the frozen `macro_series` header exactly (`macro_id` is DB-auto, not in the CSV):
`indicator, geography, period, value, unit, evidence_category, language, source_name, source_url, capture_date, collected_by, confidence, notes`. No blank required fields; every row carries a non-blank `source_name` / `source_url` / `capture_date` (contract §1). Zero provenance violations across all three files.

**Field conventions (per `db-contract.md` §2):** CBJ and DoS → `evidence_category=government`, `source_name=CBJ` / `DoS`, `confidence=H`. DLS → `evidence_category=news`, `source_name=<outlet>`, `confidence=L`. All → `language=en`, `collected_by=gis-specialist`, `capture_date=2026-07-07`. Uniqueness key `(indicator, geography, period)` holds within each file (idempotent reload).

## Summary

| # | Dataset | Status | Output | Rows/Features | Confidence |
|---|---------|--------|--------|--------------|-----------|
| 8 | CBJ Real Estate Price Index | ✅ full | `macro_cbj_price_index.csv` | 1,377 | H (official) |
| 10 | DoS building permits | ✅ full, current to 2024 | `macro_dos_permits.csv` | 540 | H (official) |
| 9 | DLS trading report | ⚠️ partial (news fallback) | `macro_dls_transactions.csv` | 10 | L (news) |
| 13 | GAM zoning | ⚠️ fallback only | `zoning_osm_landuse.geojson` | 675 | — (OSM proxy) |

Two of four sources delivered their primary official data. The other two (DLS, GAM) are network-unreachable from our location — documented below with the exact failure and the manual step required. No figure anywhere is fabricated.

---

## 1. CBJ Real Estate Price Index — P0, DELIVERED

**Source:** Central Bank of Jordan, [Jordan Real Estate Price Index](https://www.cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index) → direct download `real_estate.xls` (OLE2 .xls, parsed with `xlrd`).

**Output:** `data/processed/macro_cbj_price_index.csv` — 1,377 rows.

- **Base:** 2012 = 100 (Laspeyres). Verified: the General index reads exactly 100.0 for 2012. `unit = "index (base 2012=100)"`.
- **Two dimensions**, both extracted:
  - **By property type** (national): 14 series — Buildings (Residential, Villa, House, Apartment, Non-residential, Commercial, Industrial, Other), Lands (Land, Residential, Commercial, Industrial, Outside-regulation), and General. `geography = "Jordan (Kingdom)"`. Duplicate Arabic labels (سكني/تجاري/صناعي appear under both Buildings and Lands) are disambiguated by section prefix in the `indicator`.
  - **By governorate**: 13 governorates + Kingdom, all the General index. `geography = Amman, Irbid, Zarqa, Balqa, Mafraq, Karak, Tafilah, Ma'an, Madaba, Jerash, Ajloun, Aqaba, Kingdom`.
- **Periods:** 51 per series — annual **2005–2020** (`period = "YYYY"`) plus quarterly **2013-Q1 → 2021-Q3** (`period = "YYYY-Qn"`). The column mapper forward-fills the merged year cell across each 4-quarter group.
- Each row's `notes` carries the series' relative weight in the index.

**Caveat — recency (re-checked 2026-07-07):** the downloadable Excel ends at **2021-Q3**, and this is genuinely the latest obtainable from our location — not a parsing gap. The CBJ statistical database (`statisticaldb.cbj.gov.jo`) that would hold newer quarters is **geo-blocked** (connection timeout on HTTP and HTTPS, same Jordan-gov pattern as DLS/GAM); the public `real_estate.xls` returns no newer `Last-Modified`. Newer quarters were NOT fabricated. **MANUAL STEP** if the engine needs post-2021 index values: query the CBJ statistical DB from a Jordan IP / VPN, or have the research team source the last ~8 quarters from cited news (deep-research prompt R5 already covers this). The 2012→2021-Q3 series fully powers the time-adjustment factor for any listing dated within that window.

**Engine use:** time-adjustment factor = CBJ index(current period) ÷ CBJ index(listing period), by governorate (use Amman) or property type.

---

## 2. DoS Building Permits — P1, DELIVERED (current to 2024)

**Source:** Department of Statistics building-licenses census. The documented data pages (`dosweb.dos.gov.jo`) carry only methodology; the actual tables are served by a legacy Oracle PL/SQL (owa) query system on `www.dos.gov.jo`.

**Access note:** `www.dos.gov.jo` refuses **HTTPS** (port 443) from our location but serves over **HTTP** (port 80). The yearly data table is at
`http://www.dos.gov.jo/owa-user/owa/builds_YEAR.show_tables1_build?lang=E&year1=YYYY&t_no=1` (WINDOWS-1256 encoded HTML, parsed with `pandas.read_html`).

**Output:** `data/processed/macro_dos_permits.csv` — 540 rows = **6 years (2019–2024) × 5 issuing authorities × 18 indicators**.

- **Geography = issuing authority** (not governorate — this is the granularity DoS's yearly table offers): `Kingdom`, `Greater Amman Municipality`, `Municipalities`, `Joint district committees`, `Regional authorities`. **Greater Amman Municipality is our Amman proxy.**
- **Indicators** encode occupancy metric × license type: `Building licenses: {Residential|Nonresidential|Fences|Total number|Total area|Estimated costs} ({New buildings|Extension to existing buildings|Existing buildings})`.
- **Units:** counts → `licenses (count)`; `Total area` → `1000 m2`; `Estimated costs` → `1000 JD`.
- Values verified to differ correctly per year (e.g. Kingdom residential new-building licenses 2019→2024: 5179, 5395, 8493, 7911, 6633, 5961 — the 2021 post-COVID peak is visible).

**Caveat:** governorate-level (rather than authority-level) breakdown would require the DoS **quarterly** owa table (`builds.p_select_build`), not pulled here. The yearly authority series with Greater Amman Municipality broken out satisfies the supply-pipeline-trend feature.

**Engine use:** supply pipeline trend = time series of `Total number (New buildings)` and `Total area (New buildings)` for Greater Amman Municipality / Kingdom.

---

## 3. DLS Monthly Trading Report — P1, PARTIAL (news fallback)

**Primary source UNREACHABLE.** `dls.gov.jo` (and `www.dls.gov.jo`) time out on connection over both HTTP and HTTPS, all host variants — the same `193.188.x` Jordanian government IP block that geo-blocks GAM. The structured monthly report (trading volume/count by **governorate / property type / nationality**) lives only in the DLS Arabic PDF and **cannot be retrieved from our location**.

**Fallback taken** (per the plan's resilience map: "Homes-Jordan / news summaries of DLS data"): national aggregates transcribed from two reputable, dated articles that cite the DLS report directly. National-level only, `confidence = L`, each figure keeping its own `source_url`. This is real DLS-origin data via secondary sources — clearly marked, not fabricated.

**Output:** `data/processed/macro_dls_transactions.csv` — 10 rows, `geography = "Jordan"`:
- From [Zawya, 2025-09-10](https://www.zawya.com/en/economy/levant/jordan-real-estate-trading-volume-rises-3-in-first-eight-months-of-2025-yqqnnwmw): Jan–Aug 2025 trading volume JD 4.565 bn, Aug 2025 JD 686.7 m, revenues (cumulative + Aug), and non-Jordanian ownership value (cumulative JD 123.4 m + Aug JD 16.2 m).
- From [Jordan News, 2026-01-11](https://www.jordannews.jo/Section-33/Trade-Industry/Real-Estate-Trading-Volume-Reaches-JD-7-1-Billion-in-2025-48007): full-year 2025 trading volume JD 7.179 bn (+7% YoY), Dec 2025 JD 724.7 m, revenues (year + Dec).

Cumulative periods use `period = "2025-YTD-08"`; single months use `"2025-08"`, `"2025-12"`; full year `"2025"`. Every row's `notes` states it is a news-derived DLS figure, national only.

**MANUAL STEP to obtain the full official dataset:** access `dls.gov.jo` from a Jordan IP / VPN (or request from DLS), download the latest monthly تداولات PDF, and extract the governorate/type/nationality table (Arabic — may need LLM translation). The script re-checks DLS reachability on every run and will flag it in the log the moment the site becomes reachable.

---

## 4. GAM Zoning — P0, FALLBACK ONLY (official unavailable)

**All three official/mirror sources are unreachable from our location:**

1. **GAM ArcGIS REST** (`ammancitygis.gov.jo/arcgis/rest/services`) — connection timeout, HTTP + HTTPS. Confirmed geo-blocked to Jordan (matches the 2026-07-07 finding in the risk register).
2. **ArcGIS Online mirror `4909a23609c441408ba48660bdecbdd0`** (Zahran landuse) — HTTP 403, "You do not have permissions to access this resource" (item not publicly shared).
3. **ArcGIS Online mirror `f4e390d55fe94a5b9f3df0687d918321`** (AMMAN_PLOT) — HTTP 403, "Subscription is disabled, the item is not accessible" (owner's ArcGIS subscription is off).

**Fallback taken** (the plan's verified zoning fallback): **OSM landuse polygons** for the Amman bbox via Overpass.

**Output:** `data/processed/zoning_osm_landuse.geojson` — 675 polygons: residential 540, commercial 73, industrial 37, construction 13, retail 12. Each feature carries `"official": false` and a `note` stating it is a community landuse proxy, **not** an official GAM zoning class.

**Honest limitation:** OSM `landuse` is a coarse land-use proxy, **not** the official plot-level GAM zone classes (Res A/B/C/D, FAR, max height) the engine's `zone_class / FAR` feature ideally wants. It gives the frontend's zoning-layer placeholder real polygons to render and a rough residential/commercial/industrial split, but FAR and building-height regulation are absent. **MANUAL STEP for official zoning:** pull the GAM ArcGIS REST service through a Jordan-exit VPN, or obtain a verified public share of the ArcGIS Online items.

---

## Reproduce

```bash
cd C:\Rubicon\Real-Estate-Jordan
python scrapers/official_data.py                 # all four, cached raw
python scrapers/official_data.py --refresh        # re-download everything
python scrapers/official_data.py --only cbj,dos   # subset
```

## Data-quality caveats (roll-up)

- **CBJ** index stops at 2021-Q3 (source's own extent).
- **DoS** geography is issuing-authority, not governorate; Greater Amman Municipality is the Amman proxy.
- **DLS** is national-only news aggregates (confidence L) — no governorate/type/nationality breakdown until the DLS PDF is retrieved from a Jordan IP.
- **Zoning** is OSM landuse proxy, not official GAM classes — no FAR/height.
- DLS and GAM should be re-attempted from a Jordan-exit VPN before the demo if official granularity is required.
