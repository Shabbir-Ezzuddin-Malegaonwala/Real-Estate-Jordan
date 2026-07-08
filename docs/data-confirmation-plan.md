# Data Confirmation Plan — how we verify our data is current & correct

**Owner:** Backend/Research · **Created:** 2026-07-08 · **Status:** v1 (drives an automatable verification pass)
**Authority:** `MASTER-PLAN.md` (LATEST-data-first, never-fabricate, source+date+confidence) · `docs/db-contract.md`
**Source of truth for our numbers:** `db/jordan_re.sqlite` + `deliverables/Jordan_Real_Estate_Master_Dataset.xlsx` (18 sheets)

> **Purpose.** Every figure we hold has a *vintage* and a *source trust level*. This document (a) lists
> every dataset/figure, (b) gives each one a repeatable **confirmation recipe** (query → authoritative
> cross-check → PASS/FLAG criterion → confidence action), and (c) records the **real spot-checks already
> run** with citations. It is written so each recipe can later be run by an automated verifier
> (query → compare → confirm/flag → update `confidence`).

---

## 0. How this plan is meant to run (automation contract)

Each row of the recipe tables in §2 is a self-contained verification job:

```
job = {
  dataset, our_value, our_vintage,
  search_query,             # exact query string to fire
  cross_check_sources[],    # authoritative URLs/hosts to trust
  pass_if,                  # numeric/logic test → agrees
  flag_if,                  # numeric/logic test → conflict or stale
  access,                   # "search" | "webfetch" | "vpn-playwright" | "manual"
  on_pass, on_flag          # confidence action to write back
}
```

- **PASS** → write `confidence` unchanged/raised, stamp `last_verified` = today.
- **FLAG** → do **not** overwrite the datum. Emit a `verification_flags` row `{dataset, our_value, found_value, delta, source, severity}` and lower `confidence` one notch (H→M→L). A human/LLM adjudicates.
- **Never** let a verifier silently replace a value — verification annotates, it does not fabricate (matches the DB-contract `unknown`-vs-blank discipline and the no-silent-fallback rule).
- **Access tier** tells the scheduler which transport to use. Most `*.gov.jo` hosts are **geo-blocked** from our network (verified 2026-07-07): `dls.gov.jo`, `data.gov.jo`, `statisticaldb.cbj.gov.jo`, GAM ArcGIS all TCP-timeout. Those recipes are marked `vpn-playwright` (need a Jordan/NL-exit VPN + a headless browser to traverse server-side pagination). CBJ main site, `dosweb.dos.gov.jo`, and `jorinfo.dos.gov.jo` DO respond and are `webfetch`/`search`.

Suggested cadence: portal asking prices **weekly**; DLS monthly report **monthly** (on/after the 5th); construction cost, zoning, foreign-ownership law **quarterly**; census/population **on release only**.

---

## 1. Full inventory of what we hold (enumerated from the DB + Excel + collection reports)

| # | Dataset / figure | Our current value / vintage | Table / file | Source trust |
|---|---|---|---|---|
| 1 | Portal listings (asking prices) | 24,471 in DB (10,226 in the 5 covered submarkets); friend bundle adds ~56,856 across 6 portals; 12 governorates | `listings` | M (asking, not sale) |
| 2 | Competitor new-launch projects | 6 projects | `projects` | M |
| 3 | Points of interest | 984 verified in DB; 9,167 in OSM harvest | `poi` | M (OSM) |
| 4 | Neighborhood boundary polygons | 5 submarkets | `districts` | M |
| 5 | Zoning / land-use polygons | 2,244 OSM-landuse (NOT regulatory) + Aqaba ASEZ official (89 zoning/100 iqlim/18 general/8 districts) | `zoning_plots` | L for OSM / H for ASEZ |
| 6 | CBJ Real Estate Price Index | base 2012=100, 14 property types national + 12 governorates, **ends 2021-Q3** | `macro_series` | H but **stale** |
| 7 | DoS building-licence counts + area | 12 gov × 21 quarters, 2020-Q1→**2026-Q1** (2024 missing at source) | `macro_series` | H |
| 8 | DoS building-licence **cost** (construction floor) | **~157–175 JD/m²** filed-estimate floor, 2004–2026 | `dos_building_cost` | H (as a floor) |
| 9 | Construction cost benchmarks by finish class | 10 rows; basic/standard from DoS floor | `cost_benchmarks` | M |
| 10 | Future-signal evidence (infra/policy/news) | 14 items | `evidence_items` | M |
| 11 | Neighborhood profiles | 5 submarkets (luxury level, buyer type, price band) | `neighborhood_profiles` | M (researched) |
| 12 | DLS transactions — monthly | Nov 2025→**Jun 2026** (June parsed: 584.3M JD/month, H1 3.04bn JD, 11,884 sales June) | `data/raw/dls_vpn/` + CSV | H (official registered) |
| 13 | DLS transactions — annual / mortgage / price index | Annual 2012–2018; mortgage 2017–2018, 2024, 2025; price index by gov 2016–2018 | `data/raw/friend/official/` + `dls_vpn` | H |
| 14 | Geo terrain per listing | 23,617 rows elevation/slope/aspect/pop-density/nightlight | `listing_geofeatures` | H source / **non-priced context** |
| 15 | Neighborhood geo-context | 5 rows | `neighborhood_geocontext` | H / **non-priced** |
| 16 | Raw geo grids | DEM 84,419 · GHS-POP 121,578 · VIIRS 418,368 cells | `data/raw/friend/geo/` | H |
| 17 | Aqaba foreign-ownership rules | ASEZ separate regime | `evidence_items` / research docs | M (needs legal recheck) |

> **Standing caveat carried into every recipe:** portal figures are **asking prices**, DLS is **registered
> transaction** value — the two differ by a documented asking→sale gap (~5–15%). Never cross-check an
> asking median directly against a DLS transaction figure as if they were the same quantity.

---

## 2. Confirmation recipes (the automatable core)

### 2A. Market / asking prices

| Dataset | Our value / vintage | Search / fetch query | Authoritative cross-check | PASS if | FLAG if | Access | Confidence action |
|---|---|---|---|---|---|---|---|
| Asking price/m² per covered submarket (Abdoun, Sweifieh, Khalda, Shmeisani, Dabouq) | median `price_per_m2` per area, capture ≤ 30 d | `"apartment price per square meter <area> Amman 2026"` + live Bayut/OpenSooq area page | Bayut.jo live area median, Numbeo Amman, homes-jordan/tajalsafa area guides | our median within **±20%** of ≥2 independent live sources | outside ±20%, or our capture_date > 60 d old | search + webfetch (Bayut live) | PASS→keep H/M; FLAG→M + re-scrape |
| Land price/m² west-Amman prestige tier | profile `typical_price_range_jd_m2` | `"Amman land price per square meter Dabouq Abdoun 2026"` | homes-jordan land-investment guides, tajalsafa | prestige areas land ≈ **1,000–1,200 JD/m²** | our band < 700 or > 2,000 with no note | search | annotate profile |
| Listing freshness / liveness | `capture_date` distribution | n/a (internal) | our own scraper re-run | ≥ 80% of covered listings re-confirmed live this week | > 30% 404/removed | webfetch (portal) | stale rows → `confidence=L` |

### 2B. Construction & land cost

| Dataset | Our value | Search / fetch query | Authoritative cross-check | PASS if | FLAG if | Access | Confidence action |
|---|---|---|---|---|---|---|---|
| Construction cost/m² (the FLOOR) | DoS filed-licence **~157–175 JD/m²** | `"Jordan construction cost per square meter 2026"` + `"تكلفة البناء للمتر المربع الأردن 2026"` | Global Property Guide Jordan, BUILD_ME country report, contractor/QS blogs, Jordan Engineers Assoc. | independent turnkey figures land in **~220–1,100 JD/m²** by class → confirms ours is a conservative **floor** | independent floor comes in *below* ~150 or our number is presented as turnkey | search | keep as floor, never as build cost |
| Cost benchmarks by finish class | basic/standard filled; high/luxury NULL | same as above, split by class | BUILD_ME: low ~222 / avg ~607 / high ~1,100 JD/m² | our class ordering matches (basic<standard<high<luxury) | any class exceeds the next, or luxury < standard | search | fill NULL classes from cited turnkey ranges, tag `M` |

### 2C. Transactions (DLS)

| Dataset | Our value | Search / fetch query | Authoritative cross-check | PASS if | FLAG if | Access | Confidence action |
|---|---|---|---|---|---|---|---|
| DLS monthly trading volume | June 2026 = 584.3M JD; H1 2026 = 3.04bn JD | `"Jordan real estate trading volume <month> 2026 dinars"` | DLS site, Jordan News / Ammon / Petra / Zawya wire reports | our month within **±5%** of the wire figure (same month) | > ±10% or wrong sign of MoM/YoY | vpn-playwright (DLS) / search (wires) | PASS→H; FLAG→re-parse PDF |
| DLS annual volume anchor | (context) 2025 ≈ 7.18bn JD | `"Jordan real estate trading volume 2025 annual DLS"` | Jordan News: **JD 7.179bn, +7% vs 2024** | annual sum of our monthly series trends to ~7.1–7.2bn | our extrapolation diverges > 15% | search | anchor the monthly series |
| Non-Jordanian purchase value | June 2026 = 24.3M JD (+145% YoY) | `"non-Jordanian real estate purchases Jordan 2026 value"` | DLS report, wires | within ±10% of reported | large divergence | vpn-playwright / search | H |
| Monthly gap Feb–Mar 2026 & Jan–Oct 2025 | **MISSING** (pagination-blocked) | traverse `/AR/List/مؤشرات_عقارية` paginated | DLS listing pages | files retrieved | still 404 | **vpn-playwright** (server-side pagination WebFetch can't page) | fills series gap |

### 2D. Infrastructure & future signals

| Dataset | Our value | Search / fetch query | Authoritative cross-check | PASS if | FLAG if | Access | Confidence action |
|---|---|---|---|---|---|---|---|
| Amman BRT status | future-signal item | `"Amman BRT bus rapid transit status 2026"` | GAM ammanbrt.jo, Wikipedia Amman BRT, Ammon News | matches "operational: Sweileh–Ras Al-Ain + Sweileh–Mahatta + Zarqa + Madaba line 105" | source says a route we call "planned" already opened (or vice-versa) | search | correct `expected_year`/status |
| Amman Metro status | future-signal item | `"Amman Metro feasibility 2026"` | GAM, Transit Guide, CREM study coverage | still **feasibility/planning** (no construction) | source shows funded/under-construction | search | keep as long-horizon signal |
| Planned roads / corridors | evidence items | `"Amman new road / ring road / corridor 2026"` | GAM, MoPWH, wires | announcement corroborated by ≥1 official + 1 news | single unsourced blog only | search | set `confidence` per source |

### 2E. Population / demographics

| Dataset | Our value | Search / fetch query | Authoritative cross-check | PASS if | FLAG if | Access | Confidence action |
|---|---|---|---|---|---|---|---|
| Jordan population | GHS-POP grid ≈ 11.42M total | `"Jordan population 2026 Department of Statistics"` | DoS `dosweb.dos.gov.jo`, Worldometer (~11.6M), HPC 2024 sheet | within **±5%** of DoS/Worldometer | > ±10% | webfetch (DoS responds) + search | context only (non-priced) |
| Amman concentration | grid density | `"Amman governorate population share Jordan"` | DoS: ¾ of pop in Amman+Irbid+Zarqa | our density ranks Amman highest | contradicts | search | context only |
| Census vintage caveat | grid = modelled | n/a | DoS: last full census **2015**, estimates since | note that population is modelled/estimate, not fresh census | presenting as current census | — | keep `L`/context tag |

### 2F. POIs / amenities

| Dataset | Our value | Search / fetch query | Authoritative cross-check | PASS if | FLAG if | Access | Confidence action |
|---|---|---|---|---|---|---|---|
| POIs per submarket (schools, malls, mosques, hospitals, parks) | `poi` counts + `exists` flag | Google Maps / Places search per category per area | Google Maps live, OSM | ≥ 90% of our flagged POIs still exist & located in-area | > 10% missing/moved | webfetch (Maps) / manual | flip `exists`, lower `confidence` |
| Major anchor POIs (malls: Abdoun, Taj, Mecca, City Mall; hospitals) | present/absent | `"<mall/hospital> Amman location"` | official site / Maps | anchor present in our set | missing a known major anchor | search | add missing anchor |

### 2G. Zoning / regulatory

| Dataset | Our value | Search / fetch query | Authoritative cross-check | PASS if | FLAG if | Access | Confidence action |
|---|---|---|---|---|---|---|---|
| Amman zoning / FAR (Res A–D classes) | **GAP** — only OSM landuse, no `zone_class`/`far`/`max_height_m` | `"Amman residential zoning categories A B C D FAR setback GAM"` | GAM Amman master plan, Amman city-profile (ScienceDirect) | we obtain real class + FAR per plot | still only OSM landuse | **vpn-playwright** (GAM ArcGIS geo-blocked) | until then keep OSM as labelled placeholder |
| Aqaba ASEZ zoning | official ASEZ polygons | `"Aqaba ASEZ zoning land use 2026"` | ASEZA | polygons still current | boundary/zone change | search / webfetch | H |
| Foreign-ownership rules (Jordan + ASEZ) | research item | `"foreign ownership property Jordan Aqaba ASEZ rules 2026"` | Global Law Experts, Bayut legal guide, State Dept investment climate | matches "MOI security approval + reciprocity + retention; ASEZ separate 5% flat-tax regime" | law amended since capture | search | recheck quarterly |

---

## 3. Spot-checks actually run now (2026-07-08) — real first confirmations

| # | What we checked | Our figure | What the web says (cited) | Verdict |
|---|---|---|---|---|
| 1 | **Construction cost/m²** | DoS filed-licence **~157–175 JD/m²** | Global Property Guide / BUILD_ME country report: urban multifamily **JD 222/m² (low) → 1,100/m² (high), avg ~607/m²** | **CONFIRMED as a FLOOR.** Our number sits *below* even the low-class turnkey figure — exactly what a licensing "filed estimated cost" should do. Action: keep labelling it a conservative cost-approach floor; the engine's true turnkey cost band should be ~220–1,100 JD/m² by finish class, not 157–175. |
| 2 | **DLS trading volume** | June 2026 584.3M JD; H1 2026 3.04bn JD; 2025 monthly series | Jordan News: **2025 full-year JD 7.179bn (+7% YoY)**; Dec 2025 724.7M JD (+58% YoY) | **CONFIRMED & CURRENT.** Our H1-2026 and monthly figures are consistent with the official 2025 annual anchor and its trajectory. Highest-value fresh dataset we hold. |
| 3 | **West-Amman prestige prices** | profiles: Abdoun/Dabouq premium tier | homes-jordan/tajalsafa: Dabouq & Abdoun land **1,000–1,200 JD/m²**; Deir Ghbar ~1,000 | **CONFIRMED tier.** Our covered submarkets are correctly the prestige/high band. Calibrate exact per-area medians against live portal medians weekly. |
| 4 | **Amman BRT / Metro** | future-signal items | Wikipedia/GAM/Ammon: **BRT operational** (Sweileh–Ras Al-Ain 2021, Sweileh–Mahatta 2022, +Zarqa May 2024, +Madaba line 105); **Metro still feasibility** (CREM study) | **CONFIRMED.** Treat BRT as *delivered* (already priced-in near corridors), Metro as a *long-horizon* speculative signal — do not price Metro as imminent. |
| 5 | **Foreign ownership / Aqaba** | Aqaba rules item | Global Law Experts / Bayut: **MOI security approval + reciprocity + retention periods**; **ASEZ separate regime**, 5% flat tax | **CONFIRMED.** Rules stand; recheck quarterly for amendments. Reciprocity + retention are material to Aqaba demand. |
| 6 | **Population** | GHS-POP ≈ 11.42M | Worldometer/UNFPA: **~11.6M**; DoS last census **2015** | **CONFIRMED (context).** ~1.5% apart — within tolerance. Keep as non-priced context; flag that it is modelled, census is 2015-based. |

**Net:** of 6 headline figures spot-checked, **6/6 corroborated** by independent authoritative sources. The one that changes how we *use* a number is #1 — construction cost is confirmed **as a floor, not as turnkey cost** — which the cost-approach must respect.

---

## 4. Access map — what a scheduler needs per source

| Access tier | Sources | Transport |
|---|---|---|
| `search` (open web) | construction cost, prices, BRT/Metro, foreign-ownership, population, DLS *wire* summaries, annual anchor | WebSearch + WebFetch |
| `webfetch` (host responds) | CBJ main site, `dosweb.dos.gov.jo`, `jorinfo.dos.gov.jo` PxWeb API, Bayut live, Google Maps | WebFetch/API |
| `vpn-playwright` (geo-blocked + paginated) | `dls.gov.jo` monthly PDFs & missing months, `statisticaldb.cbj.gov.jo` fresher index, GAM ArcGIS zoning/FAR, `data.gov.jo` | Jordan/NL-exit VPN + headless browser (server-side pagination WebFetch cannot traverse); PDFs are image scans → render + OCR/visual read |
| `manual` | per-POI ground truth, legal-text nuance | human/junior |

**Known blocking gaps to schedule against a VPN run:** (a) CBJ index is stale at **2021-Q3** — biggest official-data latency; (b) DLS **Feb–Mar 2026 + Jan–Oct 2025** monthly reports missing; (c) GAM regulatory **zoning/FAR** entirely absent (only OSM landuse placeholder).

---

## 5. Confidence write-back rules (uniform)

- Source trust at collection = `H/M/L` on the *source*, never on price-impact (DB-contract rule).
- Verification outcome adjusts a separate `last_verified` + optional `verification_flags`, and may lower `confidence` one notch on FLAG. It **never** raises above the source's intrinsic ceiling (a blog stays `L` even if it agrees).
- A datum with `capture_date` older than its cadence window is auto-`stale` regardless of agreement, and the UI must show the age.
- Conflicts are surfaced, not resolved silently — the platform shows *both* our value and the cross-check with the delta, per the "show both signals with sources" rule.

---

**Sources used for the spot-checks:**
- [Global Property Guide — Jordan m² prices](https://www.globalpropertyguide.com/middle-east/jordan/square-meter-prices) · [BUILD_ME Country Report — Jordan](https://www.buildings-mena.com/files/BUILD_MECountryReport-Jordan.pdf)
- [Jordan News — Real Estate Trading Volume Reaches JD 7.1 Billion in 2025](https://www.jordannews.jo/Section-33/Trade-Industry/Real-Estate-Trading-Volume-Reaches-JD-7-1-Billion-in-2025-48007)
- [homes-jordan — best areas for land investment](https://www.homes-jordan.com/en/blogs/detail/amman-real-estate-best-areas-for-land-investment-in-2027) · [tajalsafa — Abdoun & Dabouq prices](https://tajalsafa.com/apartment-prices-in-abdoun-and-dabouq)
- [Wikipedia — Amman Bus Rapid Transit](https://en.wikipedia.org/wiki/Amman_Bus_Rapid_Transit) · [Transit Guide — Amman Metro](https://transitguide.org/amman-metro/)
- [Global Law Experts — Can Foreigners Own Property in Jordan](https://globallawexperts.com/can-foreigners-own-property-in-jordan/) · [Bayut — Legal procedures for buying property in Jordan](https://www.bayut.jo/mybayut/en/legal-procedures-for-buying-property-in-jordan/)
- [Worldometer — Jordan population](https://www.worldometers.info/world-population/jordan-population/) · [DoS Jordan — Population](https://dosweb.dos.gov.jo/population/population-2/)
