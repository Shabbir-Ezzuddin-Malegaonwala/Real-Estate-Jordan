# DLS VPN Fetch Report

**Capture date:** 2026-07-08 (Netherlands VPN window)
**Source:** Jordan Department of Lands and Survey (DLS / دائرة الأراضي والمساحة), https://www.dls.gov.jo
**Saved to:** `C:\Rubicon\Real-Estate-Jordan\data\raw\dls_vpn\`
**Confidence:** H (official government source, real registered-transaction data — NOT asking prices)

---

## 1. Executive summary

Secured **18 raw PDF/data files** from DLS while the VPN was up, including **6 monthly real-estate trading reports** (Nov 2025 → June 2026) that contain the real transaction volumes, counts, governorate splits, property-type splits, and non-Jordanian buyer data we have been missing. The **June 2026 report was fully parsed** into a tidy CSV (60 rows). The other 5 monthly reports are saved raw and render correctly — they need the same parse pass (all are image-based scans; see §5).

Headline (June 2026, Kingdom-wide, real registered transactions):
- Monthly trading volume: **584,336,633 JD** (+7% YoY, +23% MoM)
- H1 2026 trading volume: **3,042,318,880 JD** (-3% vs H1 2025)
- Sales (properties): **11,884** in June; **62,023** in H1 2026 (-8% YoY)
- Non-Jordanian purchases June: **186 properties, 24,311,296 JD** (+145% value YoY)

---

## 2. Files downloaded (all validated, render correctly)

### Monthly real-estate trading reports — حركة تداولات سوق العقار (THE PRIZE — real transaction data)
| File | Coverage | Pages | Size |
|------|----------|-------|------|
| `monthly_trading_2026-06_June_AR.pdf` | June 2026 + H1 2026 | 14 | 1.56 MB |
| `monthly_trading_2026-05_May_AR.pdf` | May 2026 | 13 | 1.52 MB |
| `monthly_trading_2026-04_April_AR.pdf` | April 2026 | 14 | 1.49 MB |
| `monthly_trading_2026-01_January_AR.pdf` | January 2026 | 8 | 0.82 MB |
| `monthly_trading_2025-12_December_AR.pdf` | December 2025 | 14 | 1.53 MB |
| `monthly_trading_2025-11_November_AR.pdf` | November 2025 | 14 | 0.62 MB |

Each report contains: national trading volume (JD) + DLS revenue, sale counts, and cross-tabs by **governorate** (Amman vs rest), **property type** (apartments/شقق vs land/أراضي), **apartment size band** (<120 / 120-150 / >150 m²), and **non-Jordanian buyers by nationality** (count + estimated value). All Arabic.

### Other DLS statistics (Arabic)
| File | Coverage |
|------|----------|
| `mortgage_by_governorate_2025_AR.pdf` | Mortgage (rahn) transaction counts by governorate & directorate, 2025 |
| `mortgage_by_governorate_2024_AR.pdf` | Same, 2024 |
| `property_owners_by_gov_gender_2025_AR.pdf` | Property owner counts by governorate/directorate/gender, end-2025 |
| `property_owners_by_gov_gender_2024_AR.pdf` | Same, end-2024 |

### Annual reports
| File | Year | Lang |
|------|------|------|
| `annual_report_2023_AR.pdf` | 2023 | Arabic |
| `annual_report_2018_EN.pdf` … `annual_report_2012_EN.pdf` | 2012–2018 (7 files) | English |

---

## 3. Parsed data (June 2026)

`dls_june2026_extracted.csv` — 60 tidy rows, UTF-8-BOM. Schema:
`source_name, source_url, capture_date, confidence, period, property_type, governorate, nationality, metric, transaction_count, transaction_value_jd, notes`

Contents: headline volume/revenue/counts (June + H1); Table 1 & 2 (sale counts by governorate × property type, June & H1); Table 3 & 4 (apartments by size band); Table 5 & 6 (non-Jordanian possession counts + values, June & H1); nationality breakdowns (Iraqi/Saudi/Syrian/Palestinian/American/British) by count and value.

Key extracted figures:

| Metric | June 2026 | H1 2026 | YoY |
|--------|-----------|---------|-----|
| Trading volume (JD) | 584,336,633 | 3,042,318,880 | +7% / -3% |
| DLS revenue (JD) | 24,207,316 | 128,864,281 | +39% / +5% |
| Sales (properties) | 11,884 | 62,023 | +12% / -8% |
| Apartment sales | 2,990 | 15,533 | +12% / -5% |
| Land sales | 8,894 | 46,490 | +12% / -9% |
| Non-Jordanian purchases (count) | 186 | 1,046 | +27% / -6% |
| Non-Jordanian value (JD) | 24,311,296 | 100,034,214 | +145% / +10% |

Governorate split (June 2026 sales): Amman 2,073 apts + 2,718 land; rest of Kingdom 917 apts + 6,176 land.
Owner gender: 35.05% female / 64.95% male.
Top non-Jordanian buyer nationalities H1 2026 (by value): Iraqi 46.96M JD (47%), Palestinian 7.94M, Syrian 6.49M, American 5.90M, British 4.75M, Saudi 4.16M.

---

## 4. Still needed (Jordan IP / login / not enumerable)

- **Feb & March 2026 monthly reports** — exist per the listing (17 pages of docs) but filenames don't follow a guessable pattern (probed guesses returned 404). The listing page `/AR/List/مؤشرات_عقارية` uses server-side pagination that WebFetch cannot traverse (only page 1 returned).
- **Older 2025 monthly reports (Jan–Oct 2025)** — same pagination limitation.
- **DLS/CBJ Real Estate Price Index (الرقم القياسي لأسعار العقارات)** — listed as a category but no direct PDF link surfaced on page 1; would fill the CBJ-2021-Q3 gap. Needs deeper site navigation.
- **e-services plot/valuation inquiry** (`portal.dls.gov.jo`, `tracking.dls.gov.jo`) — require login; NOT attempted (per instructions).
- **Open Data Portal** (`opendata.gov.jo`) — dead: serves only a default nginx page. No datasets.
- DoS building-licenses page — not fetched (deprioritized vs DLS transaction data; low remaining VPN certainty).

---

## 5. Follow-up parse pass (recommended)

All monthly reports are **image-based scans** (no text layer — `pdftotext` returns nothing). Extraction method that works, reproducible offline (no VPN needed — files are local):

1. `pip install pymupdf` (installed).
2. Render pages to PNG: `fitz.open(f).load_page(i).get_pixmap(matrix=fitz.Matrix(2,2)).save(...)`.
3. Read the PNGs visually (Read tool) — Arabic tables are legible at 2x; numerals are Western digits.
4. Append rows to the CSV using the same schema. Tables are identically structured across months (Table 1–6), so the June parse in `build_csv.py` is a direct template.

Priority order for the parse pass: May 2026 → April 2026 → December 2025 → November 2025 → January 2026 (Jan is only 8 pages / abbreviated). This yields a continuous monthly transaction-volume + count + non-Jordanian series Nov 2025–June 2026.

Helper scripts saved: `build_csv.py` (June CSV builder / template), `_dl2.sh` / `_dl3.sh` (resilient resume-loop downloaders), `_dl.log`.

---

## 6. Notes on the VPN session

- dls.gov.jo throughput over the NL VPN was ~600–700 B/s and stalled repeatedly; large files needed resume-loop curl (`-C -`, `--speed-limit`/`--speed-time`, up to 30 retries). The origin server is also slow server-side (WebFetch timed out on the 1.5 MB PDFs).
- Data extraction was done from the **local rendered PDFs**, not over the network — so it is not VPN-dependent and can continue after the window closes.
- All 18 files validate (%PDF header, correct page counts on render). Nothing fabricated; all figures trace to a named source PDF + page.
