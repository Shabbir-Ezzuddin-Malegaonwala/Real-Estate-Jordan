# Research Extraction Report — Deep-Research Documents → Frozen Schema CSVs

**Author:** research-extractor · **Date:** 2026-07-07 · **Capture date on all rows:** 2026-07-07
**Contract:** `docs/db-contract.md` (schema `db/schema.sql` is source of truth) · **Plan:** `MASTER-PLAN.md` §3

## 1. Deliverables & Row Counts

All CSVs are UTF-8, schema-exact (headers verified against `db/schema.sql`), and were **test-loaded
into a throwaway copy of the DB with zero rejects** on the four DB-backed tables.

| File | Target table | Rows | Load result |
|------|-------------|------|-------------|
| `data/raw/research/projects_research.csv` | `projects` | 6 | 6 inserted, 0 rejected |
| `data/raw/research/cost_benchmarks_research.csv` | `cost_benchmarks` | 10 | 10 inserted, 0 rejected |
| `data/raw/research/evidence_items_research.csv` | `evidence_items` | 14 | 14 inserted, 0 rejected |
| `data/raw/research/neighborhood_profiles_research.csv` | `neighborhood_profiles` | 5 | 5 inserted, 0 rejected |
| `data/raw/research/price_benchmarks_research.csv` | *(cross-check, not a DB table)* | 35 | n/a |
| `docs/master-source-inventory.csv` | *(deduped URL inventory)* | 94 | n/a |

Every row carries the universal columns (`evidence_category`, `language`), full provenance
(`source_name`, `source_url`, `capture_date=2026-07-07`, `collected_by=research-extractor`,
`confidence`), and a `notes` field. `unknown` is used for every undeterminable categorical/numeric
value — never a blank guess. No number or URL was fabricated.

## 2. Source Material Read

- `Deep Research on Amman Residential Real Estate … (2023–2026).md` (main, 422 lines + 65 refs)
- `Deep Research Rerun – Amman Residential Market … .md` (adds Zeadat-2018 zoning table + land examples)
- `deep-research-report.md` / `(1)` / `(2)` / `(3)` (mostly methodology; `(2)` adds portal-derived per-m² points)
- `Perplexity.txt` (the source chat — duplicate of the two main markdown reports; no unique facts)
- `Gemini-Research.docx` (converted via python-docx → `gemini_extract.txt`, 1,327 lines, **16 tables**)

**The Gemini doc is by far the richest source**: it supplies specific per-m² sale AND rent points for
every one of the five submarkets, each tethered to a full source URL and date, plus a per-neighborhood
Low/Typical/High synthesis (tables 10–14) and a competitor-project table (table 15).

## 3. Notable Findings

### Real competitor projects (6 rows, each with a resolvable URL)
- **Abdoun Terraces Residence** (Jordan Properties) — 7× 4-bed 305–325 m², 495,000 JOD/305 m² ≈ **1,620 JD/m²** (Gemini synthesis quotes 1,803).
- **Edraj 395 m² Dabouq flats** — new-build baseline **1,100 JD/m²** (434,500 JOD/unit) — the only Dabouq new-build with an explicit price+URL.
- **The St. Regis Amman** (Eagle Hills), **DAMAC Tower** (DAMAC, Abdali — flagged as adjacent, not a target submarket), **Cloud 12** (Hamdan), **Helio-Abdoun** (Helio-Jordan) — all real, but price-on-enquiry.
- **Omitted** (no resolvable URL, only "Jordan Properties Registry"/"RealSooq Developer Hub" labels in Gemini table 15): GAIA Residence (1,846 JD/m²), Majestic Villas, Ayana Residences, Lucent/Jordan-Gate Towers. Flagged rather than invented.

### Construction cost = confirmed structural gap
No open source publishes numeric JD/m² residential construction costs for Amman. The one cited article
(ammanvoice.net, 2026, Arabic) states finishing level drives cost and that "economic"/"medium" grades
dominate, **but gives no numbers**. Recorded as 2 rows (basic/standard) with `cost_low/high = unknown`,
confidence **L**, gap noted. Per the task, **land-price benchmarks** were captured in the same file as
8 rows (`spec_class=unknown`, each noted "LAND PRICE benchmark"): Abdoun **1,000** & up to 2,667 JD/m²
(prime), Dabouq green-zoned **400** and villa plots **~1,000–1,100**, Khalda ~472–1,120, Shmeisani ~548–664.

### Price benchmarks (35 cross-check rows)
Anchored on **Taj Al Safa 2025** bands (Abdoun 1,500–2,500; Dabouq 1,300–2,200; Sweifieh 1,200–2,000;
Shmeisani 900–1,300) and corroborated with dated listing points from Bayut/Amaken/Homes-Jordan/Amman
Apartments/Hagzi/Edraj. Clear structural pattern captured in the notes and profiles:
- **Abdoun** — hybrid (high capital value ~850–1,500+ AND strong rent yield 98–125 JD/m²/yr).
- **Dabouq** — highest sale/m² but rent/m² diluted (33–68/yr) by large villa units; capital-preservation.
- **Sweifieh** — mid sale (~875–1,050) but **city-highest rent/m² (122–150/yr)** on small furnished units; cash-flow.
- **Khalda** — utilitarian (sale 500–1,050, typ 700–800; rent 30–58/yr); only new builds break 1,000.
- **Shmeisani** — widest dispersion: older stock 450–560 vs renovated/new 833–1,017; corporate rents 80–109/yr.

### Future infrastructure / policy (14 evidence rows)
Real, dated, cited items: inner-city **BRT Lines 1&2** (operational ~2024), **Amman–Zarqa BRT** (~86%
complete mid-2026, MOT official), **Sweileh–QAIA BRT** study (42 km, part of 3.47bn JOD package),
**Medical City / Sweileh–Naour** 15.8 km elevated corridor, **New Abdali Phase 2** (1.2M m², May 2024),
**GAM upgrades** (3.04M JOD), and the **2024 registration-fee/property-tax incentives** (policy;
`expected_effect` = "+19% apartment sales", quoted directly from DLS via Jordan News — the only
source-stated effect). Five `market_news` rows capture qualitative "why this price" drivers (views,
noise, calmness, transport, commercial mix) per neighborhood to back the adjustment reasons.

## 4. Low-Confidence / Uncited Items Flagged

- **Construction cost numbers**: none exist in open sources → cost rows are numeric-`unknown`, conf **L**.
- **Cloud 12** status/price inferred from marketing language → conf **L**.
- **Dabouq area guide URL** (`ev-area-dabouq`) path inferred from the Homes-Jordan article title; flagged in notes to verify.
- **Homes-Jordan Building & Land Tax Bill 2025** and **theigc.org FAR by-law** items exist but lacked a
  resolvable deep URL in the docs → **not** inserted as evidence rows (would violate the "real source_url"
  rule); recorded in the inventory at domain level instead.
- Several **land-price** rows draw on aggregated Bayut/Homes-Jordan index pages (page-518, sale?page=111)
  rather than per-listing URLs → conf **L/M** and noted.
- `deep-research-report(1)/(3).md` contained vaguely-attributed figures (e.g. "~500–600 JD/m² construction",
  "Sweifieh averaged ~813 JD/m² in 2010") with **no URLs** → deliberately excluded.

## 5. Master Source Inventory (94 deduped sources)

`docs/master-source-inventory.csv` — columns: `source_name, url, category (gov|portal|gis|news|market|
academic|other + builder), official(yes/no), data_available, auth_required(yes/no/unknown),
referenced_by, notes`. Duplicates across the six research docs are merged into one row with all
referencing docs listed (codes: DR1=main, DR2=rerun, V0–V3=deep-research-report variants, G=Gemini,
PX=Perplexity).

Approximate breakdown: **gov/official** 11 (CBJ, DLS, MOT, GAM/BRT, Petra, Mawared, JEA; GAM ArcGIS is
geo-blocked), **portals/builders** ~26 (Bayut, OpenSooq, Homes-Jordan, Amaken, Amman Apartments, Hagzi,
Abdoun RE, Dwaik, GoldenKeys, Konyare, BRG, Sakinni, Edraj, Jordan-Properties, Hamdan, Helio, Abu Judom,
DAMAC, dxb-offplan), **news** ~15 (Jordan News ×6, Jordan Times, Jordan Pulse, Petra, Gulf News, etc.),
**market/index** ~13 (Taj Al Safa, ARPI, Bright Levant, Homes-Jordan guides, Amman Apartments, Numbeo),
**academic/multilateral** ~18 (Zeadat-2018 zoning, World Bank ×3, Emerald, MDPI, IGC, T&F, UN-Habitat,
GIZ, Codatu), **other/reference** ~11 (Wikipedia ×2, LinkedIn ARPI ×2, Reddit, 3 internal client PDFs
with expiring signed S3 URLs).

## 6. Handoff Notes for db-architect

- Load order is irrelevant (loader auto-detects table by header). Suggested:
  `python db/load_csv.py data/raw/research/<file>.csv` for the four DB-backed CSVs.
- `price_benchmarks_research.csv` is a **cross-check artifact**, not a DB table — feed it to the Evidence/
  Comparable engines as corroboration, not a load target.
- `DAMAC Tower` carries `neighborhood=Abdali` (competitor context, not a target submarket) — filter if the
  engine restricts to the five submarkets.
- Land-price benchmarks live inside `cost_benchmarks` with `spec_class=unknown` and a "LAND PRICE" note —
  if a dedicated land-price table is later added (roadmap `neighborhood, land_type, price_jd_m2, date,
  source`), these 8 rows migrate cleanly.
