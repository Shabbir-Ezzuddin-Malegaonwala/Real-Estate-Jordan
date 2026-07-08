# MASTER TRACKER — Jordan Real Estate Platform
**Single source of truth for the whole project.** Update as we go.
**Last updated:** 2026-07-08

> Purpose (per Project Lead): keep track of EVERYTHING — every idea shared, every decision, what's implemented vs pending, what data we have vs need, which research is done/pending, and which AI/agent produces which data. If it's not here, it's at risk of being forgotten.

---

## 1. PRODUCT VISION (converged with ChatGPT)
- A **Builder Decision Intelligence Platform** — builder-first, evidence-backed, **explainable (no black box)**. Pricing is ONE capability inside a broader Decision Engine.
- **One evidence base** serving builder + agent + buyer (NOT separate modes/logins).
- Must answer **5 core questions** (every screen serves one): 1) Is this a good place to build? 2) What should I build? 3) What should I pay for land? 4) What should I sell for? 5) Why should I trust this recommendation?
- The **MAP is the operating system** of the platform — everything revolves around it.
- The **LEFT PANEL = a "Decision Brief"**, not a form: Overview → Investment Score → Why → Pricing → Risks → Future Signals → Comparable Projects → AI Summary → Sales Narrative. Every statement **clickable/traceable**.
- The **"WOW" moment**: click a location → within seconds a **sourced** Investment Score + recommended price + confidence + top drivers + top risks, every statement clickable.
- Add a **TIMELINE** (past → today → future, e.g. 2022→2024→2026→2028) so builders see appreciation, not just today.
- Principle (ChatGPT, agreed): **stop adding major new concepts**; focus on making every recommendation **traceable, explainable, actionable**.

## 2. GOVERNANCE / ROLES
- **Project Lead** = Husain/Shabbir (final decisions).
- **Technical/Engineering Lead** = Claude (execution + orchestrates specialized agent team).
- **Solution/Design reviewer** = ChatGPT (via user relay).
- **Deep research** = Gemini / Perplexity (Gemini preferred for Google Maps, being Google's).
- **Junior friend** = data collection (provided the big bundle already mined).
- **Manager** = Mohammad Bhai Jamaal (UAE) — business owner; reviews deliverables. **HAS NOT reviewed the report or replied yet** (busy). Current prep = ours to do while waiting.

## 3. DECISIONS — STATUS
| Decision | Status | Note |
|---|---|---|
| Interface direction | Map-first **recommended**; PENDING manager | 3 approaches presented in report |
| AI / LLM in platform | Strong **yes-lean**; PENDING manager + API key | grounded, cited, says "I don't know" |
| Map technology | OSM/MapLibre base + optional satellite + 3D terrain (Phase 2); **Google Maps deep-research PENDING** (Gemini) | satellite not default |
| Platform name | **PENDING manager** (placeholders used) | asked in report |
| **Hosting** | **AI Studio Platform (manager decided 2026-07-08)** — study IN PROGRESS | lets us use THEIR LLM |
| Data refresh cadence | per-dataset table proposed; PENDING | |

## 4. WHAT'S BUILT (on GitHub, verified)
- **Web app** (builder-first): role selector dropped; two entry points (Explore Opportunities / Evaluate My Land); **7-step journey** (Opportunity→Feasibility→Market→Economics→Pricing→Sales→Monitoring); Decision Readiness (9 dims, honest nulls); Evidence Explorer; scenario what-if + compare; sales drafts (exec summary + narrative); AI copilot scaffold.
- **Decision Engine** (Python, no hardcoded weights): sales-comparison grid + cost floor (real DoS cost) + income ceiling (real yields) + competitor + submarket-median anchor → Min-Safe/Recommended/Premium + decomposed confidence + sourced adjustment waterfall.
- **API endpoints**: /recommend (+confidence.components), /scenario, /scenario/compare, /residual-land-value, /opportunity (+readiness), /feasibility, /areas, /comparables. 182 tests green, ASCII-safe.
- **Map**: 290-area gap-free Voronoi + opportunity heatmap; 9,444 POIs in 12 layers (**wiring to map IN PROGRESS**).
- **Deliverable**: `deliverables/JRE_Report/` (detailed report + 4 approach files + 20-sheet Excel + screenshots) — on Drive; single folder, no duplicates.

## 5. DATA — WHAT WE HAVE (source)
- ✅ 52,647 listings, 12 governorates (6 portals: Bayut/OpenSooq/EurekaJo/Homes/Property4321/AbuJudom)
- ✅ DLS transactions (monthly Nov'25–Jun'26 via VPN + annual 2012–18)
- ✅ **DoS construction cost** (dos_building_cost, ~157 Kingdom / ~175 Amman JD/m² — filed-licence FLOOR)
- ✅ DoS building permits · ⚠️ CBJ price index (lags ~2021)
- ✅ **POIs 9,444** (OSM, 9 categories) + water/green/roads + **area_amenities** (290 areas: counts + km-to-airport/highway)
- ✅ **Rentals/yields** (area_yields, 207 areas, OpenSooq → income approach now real; Abdoun 8.5% etc.)
- ✅ **Macro**: USD/JOD 0.709, gold ~81.5 JOD/g, CBJ rate 5.75%, CPI 2.83%
- ✅ Geo: DEM elevation, GHS population, VIIRS nightlights
- ✅ Zoning: OSM (Amman) + **Aqaba ASEZ official** (118 polygons) + foreign-ownership rules
- ✅ Competitor projects (6), neighborhood profiles (5), evidence items, cost/land benchmarks
- ✅ Future signals: BRT operational, Jordan National Railway (signed Apr'26), Marsa Zayed, Metro=planning-only

## 6. DATA — PENDING / TO COLLECT
- ⏳ **FULL area-wise Jordan coverage — cover EVERY area, leave none** (many areas still thin). Divide Jordan area-wise; collect missing.
- ⏳ **Google Maps POIs** (richer than OSM) via **Gemini/Places** + **costing research** — PENDING
- ⏳ The **big feature census per area** (see §8): hotels, cafés, clubs, apartments/buildings/towers, shops, schools, forests, barren land, clear land, best/luxury/poor areas, borders, highways, airports + land near airports, cities/villages, government buildings, police, fire stations, universities, hospitals (by tier), malls, stadiums, etc. — how many, is it new/closed/coming-soon
- ⏳ More rentals (thin areas); **gold live API key** (currently cited recent value)
- ⏳ **GAM official zoning / FAR** (needs Jordan IP / VPN)
- ⏳ Environmental: flood, soil, air quality, noise (proxies / roadmap)
- ⏳ Future infra from news (ongoing monitor)
- ⏳ **Area-name normalization** (dups: Deir Ghbar/Dair Ghbar, Rabyeh/Al Rabiah)
- ⏳ Automate the data-confirmation pass (6/6 spot-checks done manually)

## 7. RESEARCH TASKS — WHO / STATUS
| Task | Owner | Status |
|---|---|---|
| Product/architecture vision debate | ChatGPT | ✅ DONE (map-as-OS, layer groups, zoom detail, static/dynamic/derived, Decision-Brief panel, 5 questions, timeline) → **converge + implement** |
| LLM skills / scripts / instructions design | ChatGPT + Claude | ⏳ PENDING (next debate) |
| **AI Studio** study (arch/theme/LLM/how-we-fit) | Claude agent team | ✅ DONE (docs/aistudio-study.md) — fit as 1 microservice + frontend route; LLM = pick a tier, NO key; clone their grounded agent + expose engine as MCP tool |
| **Google Maps** data + integration + **costing** | Gemini (deep research) | ⏳ PENDING (draft prompt) |
| Area-wise full-Jordan feature census | Gemini/others (deep research) | ⏳ PENDING (draft prompt) |
| Data-source acquisition plan | Claude agent | ✅ DONE (docs/data-acquisition-plan.md) |
| Price-factors + edge-cases catalogue | Claude agent | ✅ DONE (docs/price-factors-edge-cases.md) |
| Data-confirmation plan (+6/6 spot-checks) | Claude agent | ✅ DONE (docs/data-confirmation-plan.md) |
| POI/amenities collection (9,444) | Claude agent | ✅ DONE |
| Rental/yield + macro pipelines | Claude agent | ✅ DONE |

## 8. FULL DATA-CATEGORY LIST (for area-wise Jordan collection + Gemini research)
**Market**: listings/asking ✓, transactions ✓, land prices, construction cost ✓, rentals/yields ✓, price index.
**Macro**: gold ✓, USD/JOD ✓, interest/mortgage rates ✓, inflation ✓, GDP/tourism.
**Property stock per area**: apartments, buildings, towers, villas, shops/retail units — counts, new vs old, under-construction, coming-soon.
**Amenities/POIs** (map layers): education (schools + **premium/international schools**, universities, colleges), health (**hospital vs specialty vs clinic**, pharmacies), shopping (malls, supermarkets, markets), food/lifestyle (restaurants, **cafés, gyms, clubs, entertainment, waterfront, walking streets**), recreation (parks, playgrounds, **stadiums**, tourist attractions, **theatres/cinemas, film/industry**), religious (mosques, churches), transport (bus/BRT, rail/metro-planned, **airports + land near airports**, main highways, parking, fuel), services (banks, **police, fire stations**, government buildings, courts), **employment** (office districts, business parks, industrial zones — demand follows jobs), tourism (hotels, attractions, convention centers).
**Geographic/land**: terrain/elevation ✓, hills/slope, rivers/wadis, **water reserves**, forests, green areas, **barren land, clear/vacant land**, **best areas, luxury/posh areas, poor areas**, **borders**, cities vs **villages**, scenery, sunrise/sunset.
**Environmental**: flood, soil, air quality, noise, heat.
**Mobility**: commute time, congestion, accessibility.
**Regulatory**: zoning height/FAR, land use, constraints, ownership rules.
**Future signals** (each needs Source + Date + **Status: Planned/Approved/Under-Construction/Completed** + Confidence — never treat equally): metro/rail/BRT/roads, new malls/hospitals/universities, mega-projects.

## 9. ARCHITECTURE NOTES (ChatGPT recommendation, to adopt)
Separate data into **Static** (roads, schools, hospitals, boundaries) / **Dynamic** (listings, prices, projects, news) / **Derived** (Investment Score, confidence, recommendation, premiums). Map layer **groups** (Market / Infrastructure / Community / Commercial / Regulatory / Environmental) with **zoom-based detail** (country→city→submarket→neighborhood→parcel→property→POI) — never show everything at once.

## 10. IDEAS SHARED BY PROJECT LEAD (running log — so none are lost)
Multi-perspective (builder/agent/buyer) → consolidated to builder-first with baked-in perspectives · high-floor **city-view premium** (Jordan has no sea; tower height = city view/sunrise/fresh air) · Voronoi gap-free map · connected search↔map↔panel · in-app grounded **AI/LLM** (data + engine + browse, cited, "I don't know") · **charts** (price up/down) · **timeline** past→future · cover **whole Jordan area-wise, leave no area** · **Google Maps via Gemini** + costing · edge-case matrix · **feedback via mailto** (shabbirmalegaon786@gmail.com) · ask manager the **platform name** · **map options** (satellite/3D) · **no duplicates**, single JRE_Report folder · **latest-data-only** (2026-to-date, vintage labelled) · **keep Excel current** + remind to replace on Drive · verify/confirm our data via Google (6/6 done) · **LLM skills/scripts/instructions** to design · **host in AI Studio** + use their LLM · voice-notes to manager in Lisan-ud-Dawat.

## 11. NEXT STEPS (priority order)
1. ✅ **POI map wiring** + "what's nearby" panel DONE (9 grouped layers + geography, per-area amenity counts w/ honest zeros, airport/highway distance). Minor follow-up: the small "Market Overview" panel still shows the old 984 POI total — refresh to the 9,444 set.
2. 🔄 **AI Studio study** (agents) → synthesize → **ChatGPT discussion** (hosting fit + use-their-LLM + skills).
3. ⏳ **Gemini Google-Maps deep-research** (data + integration + costing) — draft prompt.
4. ⏳ **Area-wise full-Jordan collection** plan + execute (cover every area).
5. ⏳ Design **LLM skills / scripts / instructions** (with ChatGPT).
6. ⏳ **Regen Excel** once data wave settles → remind Lead to replace on Drive; commit data checkpoint to GitHub.
7. ⏳ Area-name normalization; automate confirmation; adopt static/dynamic/derived + layer groups + timeline + Decision-Brief panel.
