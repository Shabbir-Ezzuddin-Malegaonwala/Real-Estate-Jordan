# Deep Research Prompt Pack — run tonight (2026-07-07)

**How to use:** Paste each prompt into the deep-research mode of ChatGPT, Gemini, and Perplexity (and claude.ai Research if available). Same prompt → multiple AIs → independent results. Save every output (copy to a file named `research_<topic>_<ai>_YYYYMMDD.md` in this folder, or export). Claude Code will parse, merge, dedupe, and keep the best-cited rows. **A claim without a source URL gets discarded — tell the AI that.**

**Priority order: R1 → R2 → R3 → R4 → R5.** If you only have time for three runs per AI, do R1–R3.

---

## R1 — Neighborhood Price Benchmarks (fills our biggest gap fast)

> I am researching the residential real estate market in Amman, Jordan for these specific neighborhoods: Abdoun, Dabouq, Sweifieh, Khalda, and Shmeisani. For EACH neighborhood, find: (1) current typical ASKING price per square meter in JOD for apartments (sale), with low/typical/high range; (2) typical monthly rent for a standard 3-bedroom apartment (~150–180 m²) and rent per m² if available; (3) how prices have moved over 2023–2026; (4) what premium factors matter most there (view, floor, new building, proximity to what). Use property portals (Bayut Jordan, OpenSooq, Homes-Jordan), market reports, real estate agency publications, and news. Every figure MUST have a source URL and the date it refers to. Figures without sources should be excluded. Present as one table per neighborhood.

## R2 — Competitor / New Development Projects

> Find all residential development projects that are currently selling, under construction, or launched since 2023 in Amman, Jordan — specifically in or near Abdoun, Dabouq, Sweifieh, Khalda, and Shmeisani. For each project: project name, developer name, developer market tier (local/premium/luxury judged from their portfolio and branding), neighborhood, status (planned/construction/selling/delivered), unit types and sizes, price per square meter in JOD if published, payment plan details, launch date, total units. Sources: developer websites, Bayut new-projects, news articles, official Facebook pages. Present as a table. Every row must include the source URL. No rumors — only documented projects.

## R3 — Future Infrastructure & Development Signals

> List all announced or planned infrastructure and urban development projects in Amman, Jordan from 2024 onwards that could affect residential property values: BRT/bus rapid transit expansions, new roads and road widening, new hospitals, international schools, universities, shopping malls, government mega-projects, Greater Amman Municipality master plan initiatives, and major private investments. For each: title, 2-line summary, which district/neighborhood it affects (or citywide), announced/expected completion year, current status, publication date of the announcement, and whether the SOURCE ITSELF states any expected impact on the area (quote it if so — do not add your own opinion). Every item must have a source URL from a news outlet or government page.

## R4 — Construction Costs & Land Prices

> Part A: What is the current construction cost per square meter in Amman, Jordan for residential buildings, broken down by finishing level (basic, standard, high-end, luxury)? Give low and high figures in JOD per m², the year each figure refers to, and the exact source URL for every number (quantity surveyor data, contractor publications, Jordan Engineers Association, industry articles). Part B: What are current LAND prices per square meter (or per dunum) in these Amman neighborhoods: Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani? Use land listings on portals and any published land transaction commentary. Same rule: every figure needs a source URL and date. No estimates without sources.

## R5 — Jordan Market Context & the Ask-vs-Sale Gap

> I need documented context on the Amman, Jordan residential market for 2024–2026: (1) What is the typical gap between asking prices and final transaction prices in Jordan's residential market (any published broker commentary, market reports, or studies)? (2) What do the latest Department of Lands and Survey (DLS) monthly/annual reports say about transaction volumes and market direction? (3) What does the Central Bank of Jordan Real Estate Price Index show for Amman apartments over the last 8 quarters? (4) What are the main demand drivers right now (expat/Gulf buyers, Jordanian diaspora, interest rates, population growth)? (5) Any published data on which Amman districts are appreciating fastest? Every claim needs a source URL. Prefer official sources (dls.gov.jo, cbj.gov.jo, dosweb.dos.gov.jo) and established news/market reports.

## R6 — (BONUS, only if time) Amman Zoning Data Access

> I need programmatic or downloadable access to zoning / land-use GIS data for Amman, Jordan. The official source is the Greater Amman Municipality GIS portal (ammancitygis.gov.jo) with an ArcGIS REST API, but it appears to be accessible only from inside Jordan. Find: (1) any mirrors of GAM zoning/land-use layers on ArcGIS Online, ArcGIS Hub, or academic repositories; (2) any downloadable Amman zoning shapefiles/GeoJSON from research projects, World Bank, UN-Habitat, or universities; (3) any documentation of GAM's zoning categories (Residential A/B/C/D rules: floor-area ratio, max heights, setbacks) in English or Arabic. Include direct URLs to every dataset or document found.

## R7 — Qualitative Neighborhood Attributes (feeds the "why this price" reasons)

> For each of these Amman neighborhoods — Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani — describe the qualitative lived experience that affects property desirability and price. Cover: typical VIEWS (city, hills, green, open, blocked), NOISE level (quiet/residential vs busy/commercial), general CALMNESS and ambience, AIR quality and breeze/elevation (is it on high ground, good airflow?), SCENERY and greenery, ROAD access and traffic congestion, proximity to MAJOR ROADS/highways, public TRANSPORT (bus, BRT, planned metro), PARKING availability (on-street vs private), walkability, safety/prestige, and any nuisance (industrial, highway noise, crowding). For EACH claim give a source URL (real estate guides, neighborhood reviews, news, forums, Google Maps/area descriptions, Numbeo, expat guides). Present one section per neighborhood with the factor, a short description, a +/− desirability note, and the source. Do not invent — if a factor is unknown for an area, say so.

Output rows map to the `neighborhood_profiles` and `evidence_items` tables — each qualitative factor becomes an evidence item with its source URL, so it can appear as a cited "reason" in the platform's price justification.

---

**After running:** put all outputs in this folder (any format — markdown, PDF export, copied text). Claude Code merges them with the junior's CSVs and the scraped portal data into the master database, keeping source URLs as provenance.
