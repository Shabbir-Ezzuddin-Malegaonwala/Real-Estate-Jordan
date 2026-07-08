# Jordan Real-Estate Platform — Data-Acquisition Plan

**Prepared:** 2026-07-08 · **Technical Lead:** Claude Code · **Status:** research-grounded, cited
**Scope:** for every data category we want, the best real, current (2026) source for **Jordan specifically** — how to get it, cost/access, freshness, effort, and priority — plus the proposed **map-layer taxonomy** and **left-panel spec**.

> Every claim below is backed by a URL pulled from live searches on 2026-07-07/08. Where a source could not be verified for Jordan, it is flagged as a **GAP** rather than assumed.

---

## 0. What we already have (baseline — do not re-acquire)

| Asset | Use in engine |
|---|---|
| ~52k portal listings | Asking-price surface, per-area price/m² |
| DLS transactions (monthly reports) | Ground-truth sale prices, transaction volume |
| DoS construction cost + building permits | Replacement-cost approach, supply pipeline |
| CBJ price index (lagging) | Macro trend, index anchoring |
| OSM POIs | Accessibility / amenity scoring |
| Satellite DEM / population / nightlights | Terrain, density, economic-activity proxy |
| Aqaba official zoning + ownership rules | Aqaba-specific FAR/height/foreign-ownership |

The two structural gaps this plan must close for a credible demo: **(1) rental/yield data** (no income approach today) and **(2) live macro signals** the manager asked for (gold, FX, rates, inflation).

---

## 1. Priority Acquisition Table

Access legend: **FREE** · **PAID** · **SCRAPE** (public but ToS-bound) · **GEO** (needs Jordan IP). Priority: **P1** demo-critical · **P2** strong value · **P3** nice-to-have.

### 1.1 RENTAL prices / yields — *current GAP, P1*

| Source | What it gives | Access | Freshness | Effort |
|---|---|---|---|---|
| **OpenSooq** `jo.opensooq.com/en/amman/real-estate-for-rent/apartments-for-rent` | ~3,800+ live Amman rental listings, tagged by neighbourhood (Abdoun, Deir Ghbar, Jubaiha, Khalda, Rabiah…) — the deepest per-area rent inventory in Jordan | SCRAPE | Live | Med |
| **Bayut Jordan** `bayut.jo/en/amman/apartments-for-rent/` | Structured rent listings, agent data, area filters; cleaner schema than OpenSooq | SCRAPE | Live | Med |
| **ammanapts.co** rental market report | Editorial rent ranges per district (Abdoun 650–900, Deir Ghbar 550–750, Jabal Amman/Weibdeh 500–800 JOD for 100–140 m²) — usable as sanity anchors | SCRAPE/FREE | Monthly | Low |
| **Numbeo Amman** `numbeo.com/property-investment/in/Amman` | Price-to-rent ratio, gross yield, city-centre vs outside rent for 1/3-BR — instant yield proxy | FREE (scrape/CSV) | Rolling | Low |
| **Global Property Guide — Jordan** `globalpropertyguide.com/middle-east/jordan/rent-price-trends` | Independent rent & yield trend series | FREE (page) | Quarterly | Low |
| Homes Jordan, FLATJO, Amaken.jo | Secondary West-Amman + furnished/expat rent inventory | SCRAPE | Live | Low |

**Engine mapping:** derive **median rent per m² per area** from OpenSooq+Bayut, cross-check against ammanapts ranges; compute **gross yield = annual rent / DLS sale price per m²** per area → powers the **income approach** and a **Yield** map layer.
**Note:** *Aqarmap does not operate in Jordan* (Egypt/GCC focused) — do not plan around it. OpenSooq is the Jordanian equivalent.

### 1.2 MACRO indicators — *P1 (manager explicitly asked)*

| Indicator | Best source | What / value found | Access | Freshness |
|---|---|---|---|---|
| **Gold price (JOD)** | GoldAPI.io `goldapi.io` (supports JOD directly); display refs goldpricez.com/jo, livepriceofgold.com | 24K ≈ **95.3 JOD/g**, 21K **81.52**, 18K **71.47** (2026-07-05). 21K is the local retail benchmark | FREE tier (API key) | Real-time |
| **USD/JOD** | Any FX API (exchangerate.host, open.er-api.com); GoldAPI also returns JOD | De-facto **peg ≈ 0.709 JOD/USD** (officially pegged to IMF SDR since 1995, but USD-stable) | FREE | Real-time (but ~flat) |
| **CBJ policy / mortgage rates** | CBJ `cbj.gov.jo/en/Pages/Maininterestrates`; Jordan News Agency (Petra) | **Policy rate 5.75%** (held 2026-06-18); rediscount **7.5%**; avg lending **~8.48%** — drives mortgage affordability | FREE (page scrape) | Per-meeting (~8×/yr) |
| **Inflation / CPI** | DoS `dosweb.dos.gov.jo` + monthly `cpi_MMYYYY` pages | **1.88%** (Jan–May 2026); rent is the top driver (+0.68pp) — directly relevant | FREE | Monthly |
| **FX reserves / macro health** | Petra / CBJ | Reserves **$27.2B** (May 2026) — confidence signal | FREE | Monthly |

**Engine mapping:** a small **macro service** polls these daily/weekly into a `macro_indicators` table (canonical units, snake_case at API boundary). Feeds a **market-context banner** and a **mortgage-affordability calculator** (rate → monthly payment → implied buyer budget). Peg means FX is near-constant; gold is the volatile "alternative-asset" signal the manager watches.

### 1.3 Richer POIs — *P2 (Overture) / P3 (Google Places)*

| Source | What it gives | Access | Verdict |
|---|---|---|---|
| **Overture Maps** `docs.overturemaps.org/guides/places` | **75M+ global POIs** (schools, hospitals, businesses, landmarks) as GeoParquet on AWS S3 / Azure; blends Meta + **Foursquare** open data. CDLA-permissive licence | **FREE** (bulk download) | **Best free upgrade over raw OSM** — richer categories, dedup'd. Filter to Jordan bbox, load to PostGIS |
| **Foursquare OS Places** `opensource.foursquare.com/os-places` | Open POI dataset (categories) — the quality layer inside Overture | FREE | Use via Overture |
| **Google Places API** `developers.google.com/maps/documentation/places` | Ratings, opening hours, **popularity/foot-traffic**, phone, photos | **PAID**, tiered: Place Details ≈ **$17/1k** (Pro 10k–100k) → **$9.60/1k** (1–5M) → **$2.40/1k** (5M+); no free monthly credit after Feb 2025 | **On-demand only** — do NOT bulk-crawl Jordan. Use for the specific POIs shown in a left-panel (schools/malls near a parcel) where ratings/hours add value |

**Engine mapping:** **Overture = the amenity base layer** (replaces/augments OSM in the accessibility score). **Google Places = lazy enrichment** — called only when a user opens an area card, cached aggressively to stay in the cheap tier. Realistic cost: a few hundred $/mo at demo scale if capped.

### 1.4 FUTURE infrastructure & mega-projects — *P1 for narrative, P2 for data*

Verified status (this is a common source of stale claims — corrected here):

| Project | **Verified 2026 status** | Source |
|---|---|---|
| **Amman BRT** | **OPERATIONAL.** Route 1 (Sweileh–Ras Al-Ain) opened Jul 2021; Route 2 (Sweileh–Mahatta) Aug 2022; **Amman–Zarqa** line opened **May 2024**. Designed for 315k pax/day | Wikipedia *Amman BRT*; ammanbrt.jo |
| **Amman Metro** | **NOT built — still feasibility/planning.** CREM (China Railway) study confirmed topography is viable; no construction. Treat as speculative | transitguide.org/amman-metro; araburban.org |
| **Jordan National Railway (Aqaba–Amman)** | **$2.3B deal signed Apr 2026**, UAE JV (L'imad Holding 50:50). Phase 1: 360km freight Aqaba↔Shidiya/Ghor Al-Safi; northern extension toward **Madounah (Amman)** planned | The National; Arab News; Dar Al-Handasah |
| **Hejaz Railway revival** | Jordan–Syria–Türkiye trilateral transport pact (Apr 2026); Amman–Damascus passenger link targeted end-2026 | The National |
| **Marsa Zayed (Aqaba)** | **$10B**, under implementation since 2024; 3.2 km² mixed-use, high-rise residential + marina | araburban.org/infohub |

**How to monitor:** **Jordan News Agency (Petra) `petra.gov.jo`** is the authoritative official feed; supplement with Arab News / The National / Jordan Times business sections and GAM press. Set a lightweight news-watch (keyword feed) rather than a formal API — no structured "projects API" exists (**GAP**).
**Engine mapping:** hand-curate a **`future_projects` GeoJSON** (points/lines with status + year) → a toggleable **"Future Infrastructure" layer**; parcels within a buffer of a *funded* project (rail station, Marsa Zayed) get an **uplift factor** in the engine. Keep speculative (Metro) visually distinct from funded (Railway, BRT).

### 1.5 GAM zoning / height / FAR — *P1 for Amman, GEO-blocked*

| Source | What it gives | Access |
|---|---|---|
| **Amman City GIS** `ammancitygis.gov.jo` ("Amman City Explorer" ArcGIS) | Official parcel/zoning viewer; Residential **A/B/C/D** classes each with plot area, floor count, setbacks, permitted build area | **GEO** — public portal, but full services expect a **Jordan IP** (confirms manager's note). ArcGIS REST endpoints may be queryable if reachable |
| **RJGC** `rjgc.gov.jo/en/node/166` (Royal Jordanian Geographic Centre) | National ArcGIS interactive maps, base cadastral layers | Partly FREE, some GEO |
| **NextGIS Jordan** `data.nextgis.com/en/region/JO-AM` | Ready-made Amman vector data (admin, roads) in Shapefile/GeoJSON | FREE | 
| GAM construction-licensing regulation (2026) | Legal FAR/height rules text (A/B/C/D setbacks, Dabouq = 2 floors + roof, etc.) | FREE (jordannews.jo) |

**Open alternative?** No fully-open GAM FAR raster exists. Practical path: **(a)** query the ArcGIS REST layer from a Jordan-resident IP / small proxy and cache the zoning polygons locally; **(b)** encode the A/B/C/D rule table from the published regulation as a lookup so the engine can apply FAR/height even where the polygon is coarse. **Effort: High** (the single hardest acquisition after rentals).
**Engine mapping:** zoning polygon → **max buildable (FAR × plot)** → residual land-value / development-potential score; a **Zoning** map layer coloured by class.

### 1.6 Environmental (flood / geotech / air / noise) — *P2 flood & air, P3 rest*

| Layer | Source | Access | Notes |
|---|---|---|---|
| **Flood risk** | ThinkHazard! `thinkhazard.org/en/report/130-jordan/FL` (qualitative rating); HDX `data.humdata.org/group/jor`; academic GIS (Gumbel 25/50/100-yr, AHP flash-flood) | FREE | No single official open flood polygon (**GAP**). Best pragmatic layer: **derive flash-flood susceptibility from our DEM + slope + drainage** (methodology matches published Jordan studies) — western/mountainous & wadi-adjacent = higher risk |
| **Air quality** | **WAQI/aqicn API** `aqicn.org/api` (free token; Amman US-Embassy, GAM, Al-Zmeileh stations; PM2.5/PM10/NO2/SO2/CO/O3); **OpenWeatherMap Air Pollution** `openweathermap.org/api/air-pollution` (free 1M calls/mo, any lat/lon) | FREE | OpenWeather is better for arbitrary parcel coordinates; WAQI for real station values |
| **Soil / geotech** | No open Jordan geotech grid found | — | **GAP** — omit for demo; note as future (NRA/MEMR data is offline) |
| **Noise** | No open Jordan noise map | — | **GAP** — proxy from road-network density (OSM/Overture) if needed |

**Engine mapping:** flood-susceptibility and air-quality become **environmental penalty modifiers** and optional map layers; both are "transparency" layers more than price drivers at demo stage.

### 1.7 Tourism / footfall / economic-activity — *P2*

| Source | What it gives | Access | Freshness |
|---|---|---|---|
| **Ministry of Tourism & Antiquities (MoTA)** via Petra `petra.gov.jo` | Site-level visitor counts (Petra 15,244; Jerash 9,825; Jordan Museum 11,812 in Jan 1–14 2026); **3.29M arrivals H1 2026 (+18%)**; foreign 75% | FREE (reports) | Weekly/monthly |
| **Nightlights (already have)** + Overture POI density | Commercial-activity proxy per area | FREE | — |
| Airbtics / AirDNA (Amman) | Short-let revenue, occupancy, ADR by area — direct tourism-yield signal | PAID | Monthly |

**Engine mapping:** tourism intensity → **short-let yield uplift** for touristic zones (Downtown/Rainbow St, Petra, Aqaba, Jerash) and a **Tourism/Footfall** heat layer. For the demo, MoTA site counts + nightlights + POI density are enough; Airbtics only if budget allows.

### 1.8 Demographics per area — *P2*

| Source | What it gives | Access |
|---|---|---|
| **DoS PxWeb databank** `jorinfo.dos.gov.jo/Databank/pxweb/en/` | Population by governorate/district/locality, household size, sex — machine-queryable | FREE (API-ish) |
| **DoS 2015 Census tables** + **2025 population estimates** (by governorate/locality/household) | Density, household counts | FREE |
| **DoS HEIS** (Household Expenditure & Income Survey) | **Income proxy** by governorate — the key affordability variable beyond raw census | FREE (report) |
| citypopulation.de/en/jordan/admin | Clean district population + geometry for quick joins | FREE |

**Engine mapping:** income-per-household + household-size join to areas → **affordability/demand modifier** and a **Demographics** choropleth (income proxy). HEIS is the piece the raw census lacks.

### 1.9 Property market reports / developer launch prices — *P2/P3*

| Source | What it gives | Access |
|---|---|---|
| **Statista — Residential Real Estate Jordan** | Market-size, forecast, price/m² outlook | PAID (partial free) |
| **Taj Al-Safa**, **Homes Jordan** blogs | Local developer-view trends, area commentary, launch chatter | FREE |
| **Global Property Guide — Jordan** | Independent price/rent trend + yield | FREE |
| Government policy | **50% registration-fee exemption for apartments >150 m²** — demand lever to model | FREE (news) |
| Developer sites (direct) | Launch prices for new projects | SCRAPE, ad-hoc |

**Engine mapping:** narrative/context layer + calibration cross-checks; no structured developer-price feed exists (**GAP**) — curate manually per launch.

### 1.10 Other genuinely-useful, missing

- **Interest-rate → mortgage affordability calculator** (from §1.2 CBJ rate) — cheap, high-impact for a *buyer* persona.
- **Registration-fee / tax rules** (the >150 m² exemption, DLS fees) — turns "price" into "true cost to buy".
- **Serviced-land / infrastructure availability** (water, electricity, sewer reach) — no open Jordan layer found (**GAP**); proxy from built-up + road density.

---

## 2. Map-Layer Taxonomy (toggleable)

Grouped so a user toggles by intent. Suggested default = **Price** + **Transactions** on; rest off.

| # | Layer | Icon | Source | Type |
|---|---|---|---|---|
| 1 | **Asking Price /m²** | 🏷️ | Portal listings | Choropleth |
| 2 | **Transaction Price /m²** (DLS) | 🧾 | DLS | Choropleth |
| 3 | **Rental /m²** | 🔑 | OpenSooq/Bayut | Choropleth |
| 4 | **Gross Yield %** | 📈 | Rent ÷ DLS | Choropleth (diverging) |
| 5 | **Zoning class (A/B/C/D) + FAR** | 📐 | GAM GIS | Parcel polygons |
| 6 | **Development potential** | 🏗️ | FAR × plot − built | Choropleth |
| 7 | **Amenities / POIs** | 📍 | Overture (+Google on click) | Points, category-filtered |
| 8 | **Accessibility / transit** | 🚌 | BRT + roads (Overture/OSM) | Lines + isochrones |
| 9 | **Future infrastructure** | 🚄 | Curated `future_projects` | Lines/points, status-styled |
| 10 | **Tourism / footfall** | 🧭 | MoTA + nightlights + POI density | Heat |
| 11 | **Demographics (income proxy)** | 👥 | DoS HEIS + census | Choropleth |
| 12 | **Flood susceptibility** | 🌊 | DEM-derived + ThinkHazard | Choropleth |
| 13 | **Air quality** | 🌫️ | WAQI / OpenWeather | Points + interpolated |
| 14 | **Terrain / slope** | ⛰️ | DEM (have) | Hillshade |
| 15 | **Nightlights (activity)** | 💡 | Satellite (have) | Raster |

Funded infra (BRT, National Railway, Marsa Zayed) styled **solid**; speculative (Metro) **dashed** — visual honesty the manager wants.

---

## 3. Left-Panel Spec (per area / parcel) — full transparency, per user type

A single area card, with sections that expand by persona. Everything canonical-unit from API; the frontend formats (JOD, %, dates).

**Always shown (all users)**
- Area name, governorate/district; quick stats: **median sale /m² (DLS)**, **median asking /m²**, **median rent /m²**, **gross yield %**, transaction count (12 mo).
- Mini price-trend sparkline (DLS index vs CBJ index).
- Macro banner: gold (21K JOD/g), USD/JOD, CBJ policy rate, latest CPI — with as-of dates.

**Builder / Developer view**
- **Zoning class + FAR + max height + setbacks**; **max buildable m²** and **development-potential score**.
- Land value vs build cost (DoS construction cost) → **residual/margin estimate**.
- Permit-pipeline density (supply coming); future-infra proximity uplift.
- Flood/slope constraints; utility-reach proxy.

**Agent / Investor view**
- **Income approach**: rent /m², gross & (net est.) yield, short-let uplift if touristic.
- Comparable recent DLS transactions; asking-vs-sold gap (negotiation headroom).
- Demand signals: demographics/income, tourism/footfall, days-on-market proxy.
- **Mortgage-affordability** at current CBJ rate.

**Buyer view**
- "True cost to buy": price + **DLS registration fees** (and >150 m² exemption if eligible).
- Monthly mortgage at current rate; affordability vs area income.
- Livability: amenities within walk (Overture), transit (BRT), schools/hospitals, air quality, flood risk.
- Plain-language pros/cons.

Each figure carries a **source + as-of date tooltip** (DLS / DoS / CBJ / OpenSooq / MoTA) — transparency is the product.

---

## 4. Honest gaps (be upfront with the manager)

1. **No open GAM FAR/zoning polygon** — portal is Jordan-IP gated; needs a proxy/cache strategy. *Highest-effort P1.*
2. **No structured "future projects" or developer-launch-price API** — must curate from Petra/news. Manual but small.
3. **No official open flood polygon, no geotech, no noise map** — flood is derivable from our DEM; geotech/noise omitted for demo.
4. **Rental data is scrape-only** — no official rent registry; quality depends on OpenSooq/Bayut cleaning and dedup.
5. **Google Places is genuinely paid** — usable but must be capped/lazy; not a bulk source.
6. **CBJ price index lags** — keep DLS as ground truth; use CBJ only for trend/anchoring.

---

## 5. Recommended P1 sprint for the demo

1. **Rental + yield pipeline** (OpenSooq + Bayut scrape → per-area rent/m² → yield vs DLS). *Unlocks the income approach — the biggest missing capability.*
2. **Macro service** (gold JOD, USD/JOD, CBJ rate, CPI) → banner + mortgage calculator. *Cheap, exactly what the manager asked for.*
3. **Overture POI load** (Jordan bbox → PostGIS) → upgraded amenities/accessibility layer, free.
4. **Curated future-infrastructure layer** (BRT operational, National Railway funded, Marsa Zayed, Metro=speculative) with proximity uplift. *High narrative impact, low effort.*
5. **GAM zoning cache** (ArcGIS REST via Jordan IP + A/B/C/D rule lookup) → zoning + development-potential layers. *Start now; highest effort.*

P2 fast-follows: DoS HEIS income choropleth, MoTA tourism heat, WAQI/OpenWeather air quality, DEM-derived flood.

---

### Source index (primary)
Rentals: opensooq.com, bayut.jo, ammanapts.co, numbeo.com/property-investment/in/Amman, globalpropertyguide.com/middle-east/jordan · Macro: cbj.gov.jo/en/Pages/Maininterestrates, dosweb.dos.gov.jo, petra.gov.jo, goldapi.io · POIs: docs.overturemaps.org, opensource.foursquare.com/os-places, developers.google.com/maps/documentation/places/web-service/usage-and-billing · Infra: en.wikipedia.org/wiki/Amman_Bus_Rapid_Transit, thenationalnews.com (2026-04 rail), arabnews.com/node/2640112, araburban.org · Zoning: ammancitygis.gov.jo, rjgc.gov.jo, jordannews.jo · Environment: thinkhazard.org/en/report/130-jordan/FL, data.humdata.org/group/jor, aqicn.org/api, openweathermap.org/api/air-pollution · Tourism: petra.gov.jo, travelandtourworld.com · Demographics: jorinfo.dos.gov.jo/Databank, dosweb.dos.gov.jo/censuses, citypopulation.de/en/jordan/admin · Market: statista.com/outlook/fmo/real-estate/jordan, tajalsafa.com, homes-jordan.com
