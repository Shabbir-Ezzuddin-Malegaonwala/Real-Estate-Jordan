# Jordan Real Estate Intelligence Platform — Master Plan (Single Source of Truth)

**Deadline:** 2026-07-09 · **Scope:** Amman — Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani
**Deliverable (decided by team — manager delegated the call, no questions to him):** simplest-but-best — (1) structured database FIRST (the prior goal), (2) secured web app on top: interactive map + BI-grade charts + evidence-backed pricing panel, (3) methodology & roadmap document
**Governance:** User = Project Lead (final decision on any disagreement) · Claude Code = Technical Lead (owns engineering decisions) · ChatGPT = Solution/Design Reviewer (owns business-alignment review; quality gate) · Gemini/Perplexity = research team · Junior = data collection into frozen schema. Both AIs argue their case on disputes; the user decides.

---

## 1. Business Goal

Help a builder/developer scientifically decide and **justify** launch prices with transparent, evidence-backed reasoning. Explainability is the product; the price is the conclusion. v1 engine = CMA with evidenced adjustment grid (asking prices calibrated by 5–15% ask-to-transaction gap) + cost-approach floor + income-approach ceiling. Hedonic/AVM/ML = Phase 2+ roadmap (requires 300–500 transactions per client's own PDF).

## 2. Master Dataset Inventory

Priority: P0 = demo breaks without it · P1 = strengthens demo · P2 = roadmap mention only · P3 = drop for v1

### A. Market / Pricing (the core evidence)

| # | Dataset | Source | Authenticity | Freq | Method | Pri | Owner |
|---|---------|--------|-------------|------|--------|-----|-------|
| 1 | Sale listings (price, m², beds, floor, view, parking, age, neighborhood) | Bayut.jo | Market/asking | snapshot | **Playwright** (JS-rendered) | P0 | Claude |
| 2 | Sale listings (volume segment, private sellers) | OpenSooq.com/jo | Market/asking, noisier | snapshot | **Playwright** (infinite scroll) | P0 | Claude |
| 3 | Rental listings (both portals) — feeds income approach / yield ceiling | Bayut, OpenSooq | Market/asking | snapshot | **Playwright** | P0 | Claude |
| 4 | Premium-segment listings | Homes-Jordan.com | Curated, small volume | snapshot | Manual / AI research | P1 | Junior |
| 5 | Competitor new-launch projects (name, developer, unit mix, launch prices, payment plans) | Developer sites, Facebook pages, news | Mixed — record source per row | one-time | **AI deep research** | P1 | Junior |
| 6 | Ask-to-transaction discount factor | Client PDF (5–15%) + any broker anecdote | Documented assumption | static | Cite client PDF | P0 | ChatGPT (document it) |
| 7 | Facebook group listing samples (sentiment, private-seller pricing) | FB public groups | Low, unstructured | one-time sample | AI research | P2 | Junior |

### B. Official / Macro (context, trend, credibility)

| # | Dataset | Source | Authenticity | Freq | Method | Pri | Owner |
|---|---------|--------|-------------|------|--------|-----|-------|
| 8 | Real Estate Price Index by governorate & type, 2012→now | CBJ (cbj.gov.jo price-index page) | Official | quarterly | Direct Excel download | P0 | Claude |
| 9 | Monthly trading volume & count by governorate/type | DLS monthly reports (Arabic PDF) | Official | monthly | Manual download + translate 1–2 latest | P1 | Claude |
| 10 | Building permits (supply pipeline) by governorate | DoS building-licenses page | Official | monthly | Manual PDF download | P1 | Claude |
| 11 | Population/census, CPI shelter component | DoS | Official (census 2015, dated) | static | Manual | P2 | Junior |
| 12 | Macro cards (lending rates, GDP, tourism) | CBJ bulletins | Official | static | AI research w/ citations | P2 | Junior |

### C. Spatial / Regulatory (the map layer)

| # | Dataset | Source | Authenticity | Freq | Method | Pri | Owner |
|---|---------|--------|-------------|------|--------|-----|-------|
| 13 | Zoning classifications (Res A/B/C/D, commercial…) plot-level | **GAM ArcGIS REST API** (ammancitygis.gov.jo/arcgis/rest/services) | Official, programmatic | one-time pull | HTTP → GeoJSON | P0 | Claude |
| 14 | District & neighborhood boundary polygons (needed to geocode listings) | GAM ArcGIS / OSM | Official/community | one-time | HTTP / Geofabrik | P0 | Claude |
| 15 | POIs: schools, hospitals, mosques, malls, parks, universities | OSM Jordan (Geofabrik daily extract) | Community — validate target areas | one-time | Bulk download | P0 | Claude (extract) + Junior (verify) |
| 16 | Road network & hierarchy | OSM | Community | one-time | Same extract | P1 | Claude |
| 17 | Master plan / development corridors / future infrastructure | GAM planning PDFs (Arabic), Urban Observatory | Official, dated | one-time | AI research + manual | P1 | Junior |

### D. Signals / Supporting

| # | Dataset | Source | Authenticity | Freq | Method | Pri | Owner |
|---|---------|--------|-------------|------|--------|-----|-------|
| 18 | Infrastructure & development news (metro/BRT, roads, mega-projects) w/ URL + date | News sites, gov announcements | Verify each item | one-time | **AI deep research** (citation required) | P1 | Junior |
| 19 | Construction cost benchmarks JD/m² by spec class (cost-approach floor) | Industry reports, quantity-survey refs | Cite every figure | static | **AI deep research** | P1 | Junior |
| 20 | Rental yields by neighborhood | Derived from #1 + #3 | Computed | derived | Engine | P0 | Claude |
| 21 | Absorption / demand velocity | Not available publicly | — | — | Roadmap only (methodology section) | P2 | ChatGPT |
| 22 | Crime / environmental quality | No reliable public Jordan source found in client PDF | — | — | Drop unless junior finds authentic source | P3 | — |
| 23 | Broker/WhatsApp deal intelligence | Human relationships | High value, weeks of effort | — | Roadmap only | P2 | ChatGPT |

## 2b. Source Resilience Map (dataset-first — if a source dies, swap the source, never the dataset)

| Dataset | Primary | Secondary | Fallback |
|---------|---------|-----------|----------|
| Sale listings | Bayut | OpenSooq | Homes-Jordan / FB groups / manual sample |
| Rental listings | Bayut | OpenSooq | Homes-Jordan |
| POIs | OSM (Geofabrik) | Google Places (free-tier, selective) | AI research + manual pinning |
| Zoning / land use | GAM ArcGIS (geo-blocked — needs VPN) | OSM landuse polygons | ArcGIS Online community mirrors (verify) |
| District boundaries | GAM ArcGIS | OSM admin polygons | Manual digitization of 5 target areas |
| Price trend index | CBJ | DLS monthly reports | Homes-Jordan blog summaries of DLS data |
| Supply pipeline | DoS permits | News reports | — |
| Competitor projects | Developer websites | Bayut new-projects | Facebook pages |
| Future infrastructure | GAM master plan / gov announcements | News (cited) | — |
| Construction costs | QS/industry references | AI research w/ citations | Client PDF cost-approach ranges |

## 2c. Feature Inventory (the pricing engine consumes features, not raw datasets)

**Current-state features** (from Current State datasets):
| Feature | Derived from |
|---------|-------------|
| price_per_m2 (sale, rent) | listings: price ÷ area |
| Neighborhood median & dispersion price/m² | listings aggregated |
| Attribute premiums: view, floor, parking, age, finish | paired comparison of listings differing in one attribute (the market-evidenced adjustment grid) |
| rental_yield | annual rent/m² ÷ sale price/m² |
| dist_nearest_school/hospital/mall/park | POIs + haversine (routing/travel-time = Phase 2) |
| POI density score (walkability proxy) | POIs per radius |
| Accessibility score | road hierarchy proximity (OSM) |
| zone_class / FAR | zoning dataset |
| Time-adjustment factor | CBJ index ratio (current ÷ at-listing-date) |
| Supply pipeline trend | DoS permits time series |
| Competition score | competitor projects within radius + their pricing |
| Ask-to-transaction calibration | documented 5–15% factor (client PDF) |
| Confidence score | comp count, dispersion, recency, source quality |

**Future-signal features** (from Future Signals pipeline): development score per area = Σ evidence_items weighted by (proximity × timeline certainty × source confidence); appreciation narrative inputs (metro/BRT, road widening, mega-projects, planned amenities).

**Roadmap datasets/features (Phase 2 — acknowledged, not collected now):** travel-time matrix to CBD/airport/hospitals/schools/malls (routing API); land price benchmarks per neighborhood (`neighborhood, land_type, price_jd_m2, date, source` — required for the residual land value calculator); AI-vision finish/condition/view estimation from `main_image_url`.

## 2d. Evidence Engine (first-class component — the heart of explainability)

Every pricing adjustment is a structured **evidence object**; the recommendation is base value + ordered evidence objects → range + confidence. Nothing appears in the UI without one.

```json
{
  "factor": "Sea/City View",
  "adjustment": "+8%",
  "confidence": "High",
  "method": "paired listing comparison (n=14)",
  "datasets": ["listings"],
  "sources": [{"name": "Bayut", "url": "...", "capture_date": "2026-07-08"}],
  "category": "current_state | future_signal",
  "explanation": "Comparable units with view list 8% higher than matched units without, same building band."
}
```

Pipeline: `Recommended Price ← reconciliation ← [evidence objects] ← features ← datasets ← sources`. Each object renders as one row of the adjustment waterfall with source chips.

## 2d-2. Decision Engine (the brain — reasons over evidence, produces the recommendation)

Full pipeline: `Sources → Collection → Database → Feature Engineering → Evidence Engine → Decision Engine → Visualization`. Business logic lives ONLY here — never in the frontend, never in the database.

Five sub-engines, clean separation:
1. **Comparable Analysis Engine** — selects/weights comparable listings & projects (recency, proximity, similarity; fewer/smaller adjustments = more weight)
2. **Adjustment Engine** — applies attribute adjustments. **HARD RULE: no hardcoded weights.** Every premium (view, floor, parking, age…) is a *derived value* stored as `{factor, derived_premium, method, source, confidence, computed_date}` recomputed from current market data — never a constant in code
3. **Evidence Engine** — produces structured evidence objects (§2d)
4. **Confidence Engine** — scores recommendation reliability (comp count, dispersion, recency, source quality, cross-method agreement)
5. **Recommendation Engine** — outputs Minimum Safe / Recommended / Premium launch price + narrative + risk factors + alternative scenarios

## 2f. V1 Success Criteria (the acceptance test — feature additions stop here)

V1 succeeds when this end-to-end workflow demonstrably works for the 5 target submarkets:
1. User selects a project/location on the map
2. System loads comparable listings
3. System loads official context (zoning, POIs, infrastructure, macro)
4. System computes engineered features
5. Adjustment Engine applies evidence-backed adjustments
6. Confidence Engine scores the recommendation
7. Recommendation Engine outputs Minimum Safe / Recommended / Premium
8. Dashboard shows reasoning, supporting evidence, and source chips

Anything not required by these 8 steps is Phase 2.

## 2e. Current State vs Future Signals (two pipelines, never mixed)

- **Current State** (what is): listings, rentals, POIs, zoning, roads, index, permits → feeds the valuation grid (today's justified range)
- **Future Signals** (what's coming): planned roads, metro/BRT, malls, hospitals, schools, gov projects, master-plan corridors → feeds the appreciation narrative & positioning story (why the launch price holds and grows — the "raise later, never reduce" strategy)
- UI: two distinct panel sections; evidence objects carry a `category` tag

## 3. Collection Schema (FROZEN — junior collects into this, never invents columns)

Every table carries provenance columns: `source_name, source_url, capture_date, collected_by, confidence(H/M/L), notes`

Universal columns on EVERY table (in addition to provenance): `evidence_category(market|government|gis|infrastructure|macro|portal|builder|news|derived)`, `language(en|ar|mixed)`.
Confidence philosophy: `confidence` at collection = trust in the SOURCE only. Evidence-level confidence (does it move price, how much) is computed later by the Evidence Engine from recency, agreement, officiality — never mixed with collection confidence.

**listings** — `listing_id, portal, listing_url, listing_type(sale|rent), property_type(apartment|villa|land|commercial), neighborhood, district, lat, lng(if shown), price_jd, area_m2, price_per_m2(derived), bedrooms, bathrooms, floor_level, total_floors, view(none|sea|city|garden|mountain|panoramic|unknown), parking(none|open|covered|unknown), building_age_years, furnishing(no|semi|full|unknown), elevator(y/n/u), finish_quality(basic|standard|high|luxury|unknown), seller_type(agent|developer|private), listing_date, main_image_url(future AI-vision use), description_raw` + universal + provenance

**projects** — `project_id, name, developer, builder_tier(local|premium|luxury|unknown), neighborhood, lat, lng, status(planned|construction|selling|delivered), unit_types, launch_price_jd_m2, payment_plan, launch_date, units_total` + universal + provenance

**poi** — `poi_id, category(school|hospital|mall|mosque|park|university|transport), name, lat, lng, neighborhood` + provenance

**zoning_plots / districts** — GeoJSON as delivered by GAM API + `zone_class, far, max_height_m` where present

**macro_series** — `indicator, geography, period, value, unit` + provenance

**evidence_items** (news/infrastructure) — `evidence_id, type(infrastructure|policy|market_news), title, summary_2_lines, impact_area(neighborhood/citywide), expected_year, expected_effect(ONLY what the source itself explicitly states, else unknown — interpretation happens in the Evidence Engine, never at collection), source_url, published_date` + universal + provenance

**neighborhood_profiles** (P2, context for AI explanations) — `neighborhood, luxury_level, primary_buyer_type, typical_property_type, typical_price_range_jd_m2, reputation_summary, commercial_mix, population_character` + universal + provenance

**cost_benchmarks** — `spec_class, cost_jd_per_m2_low, cost_jd_per_m2_high, year, source_url` + provenance

Format: CSV (UTF-8) per table. One row per record. Unknown = `unknown`, never blank guesses.

## 4. AI Orchestration Map

| Tool | Assigned tasks |
|------|---------------|
| **Claude Code** | All execution: Playwright scrapes (#1–3), GAM ArcGIS pulls (#13–14), OSM processing (#15–16), official downloads (#8–10), database build, pricing engine, frontend, verification of junior's CSVs |
| **ChatGPT** | Methodology & adjustment-grid design, pricing-justification narrative template, ask-gap documentation, roadmap sections, risk register, questions-for-manager, critical review of engine outputs |
| **Perplexity** (junior + user) | Citation-backed fact discovery: construction costs (#19), infrastructure news (#18), source verification (is X portal/page live, latest DLS report date) |
| **Gemini deep research** (junior) | Wide-net synthesis: competitor projects (#5), neighborhood profiles, POI verification (#15), Arabic master-plan summaries (#17) |
| **Junior** | Runs the prompts we hand him, outputs into frozen schema CSVs; datasets #4, 5, 7, 11, 12, 15(verify), 17, 18, 19 |

## 5. Playwright vs AI-research split

**CORRECTED FINDING (2026-07-07, verified in execution):** Playwright is NOT needed for the portals. Both embed full structured JSON in the initial HTML — Bayut in `window.state` (Algolia), OpenSooq in `__NEXT_DATA__` (serpApiResponse). Plain-HTTP + stdlib parsing is faster, re-runnable, and more reliable; headless chromium actually TRIPS OpenSooq bot-detection and returns a degraded page. Scrapers ship on plain HTTP (scrapers/bayut_scraper.py, opensooq_scraper.py, listings_common.py). A stealth non-headless browser fallback is only worth building if urllib ever gets blocked. Everything else unchanged: official data = direct file downloads; OSM = Overpass/Geofabrik; GAM = geo-blocked (fallback OSM landuse); news/costs/competitors = AI research with mandatory citations.

## 6. Dashboard Design Principles (from enterprise GIS/finance pattern review)

Full-bleed MapLibre map + docked left analysis panel (ArcGIS/CoStar pattern) · layer toggles (zoning, POIs, comps, future infra) · click parcel/project → panel updates · **adjustment-grid waterfall table** as the explainability centerpiece (Bloomberg-style: base value → each evidenced adjustment → recommended range) · price shown as range + confidence, never a naked point estimate · every fact carries an inline source chip (source + date, hover for URL) · comparables as compact cards with photos-optional · dark neutral analytical theme, max 2 accent colors, zero decorative animation.

## 7. Risk Register (top 5)

1. ~~Deliverable definition unconfirmed~~ RESOLVED: team defines it (manager said figure it out) — structured DB + secured website + methodology doc
2. Portal anti-scraping blocks → fallback: smaller manual sample + AI-research extraction
3. GAM ArcGIS **CONFIRMED UNREACHABLE from outside Jordan (TCP refused, 2026-07-07)** → fallbacks in order: (a) free VPN w/ Jordan/regional exit, (b) OSM landuse polygons from Geofabrik (works, verified 200), (c) community ArcGIS Online mirrors found: item `4909a23609c441408ba48660bdecbdd0` (landuse Zahran district), item `f4e390d55fe94a5b9f3df0687d918321` (AMMAN_PLOT) — unofficial, verify before use. Verified reachable: CBJ ✓, Geofabrik ✓, Bayut ✓
4. Junior data quality → provenance columns + Claude verification pass before merge
5. Time — cut order if slipping: #17 → #12 → #11 → #7 → #4

## 8. Deliverable Definition (team decision — manager delegated)

- Structured, clean database is the prior goal — platform is built on top of it, never before it
- Secured website (simple auth is enough for v1), professional BI-grade presentation: interactive map (MapLibre), charts (price/m² by neighborhood, index trend, supply pipeline), evidence/explanation panel with adjustment waterfall
- English UI for v1; Amman premium submarkets vertical slice
- Presented from user's machine or simple free-tier hosting — decided day 2
