# Jordan Real Estate Intelligence Project — Research Briefing & Data Collection Packet (FROZEN v2)

> **How to use this file:** If you are the researcher — read Sections 1–4, then execute Section 5. If you are an AI assistant (Claude / ChatGPT / Gemini / Perplexity) that this file was given to — this document contains the complete project context and your user's exact assignments. Help your user complete the assignments in Section 5, following every rule in Section 4 strictly. Do not redesign the schemas, do not add columns, do not change the scope.

--- 

## 1. The Scenario (read this first — it puts us on the same page)

We are a small team delivering an AI-powered **Real Estate Intelligence Platform** for a client in **Jordan**, most likely a **builder/developer**. **Hard deadline: 9 July 2026.**

The client's problem is NOT "predict property prices." A builder finishing a new tower must decide the **launch price** — and once launched, prices can be raised later but must **never** be reduced (a public price cut destroys buyer trust and stalls sales). So the launch price must be right the first time, and it must be **justified with evidence**: Why this price? Which factors contribute? What proof supports each adjustment? Where did that proof come from? How trustworthy is it?

We are building an **evidence-backed pricing decision-support system**, not a prediction model. One mindset governs everything:

> **We are not collecting data. We are collecting EVIDENCE.** Every row you deliver should be able to answer: "What pricing decision can this support?"

**The special difficulty of Jordan:** the government does NOT publish individual property sale prices (confidential by law). Official sources give only governorate-level totals and indices. So market intelligence must be reconstructed by combining many sources: property portals (asking prices), GIS/zoning, official statistics, news, and points of interest. That reconstruction is what this collection effort feeds.

## 2. The Team & Where You Fit

- **Lead (my friend):** coordinates the project, runs architecture with ChatGPT (Solution Architect) and Claude Code (Engineering Lead), builds the database, pricing engine, and web platform.
- **You:** parallel research & data collection — our extra hands on the datasets in Section 5. Your output plugs directly into the shared database, which is why format rules are strict.
- Claude Code machine-verifies every row before merge. **Consistency beats volume.**

## 3. What We Are Building (so you know what your data powers)

1. **A structured database** (FIRST — the foundation; your CSVs land here)
2. **A secured professional web platform**: interactive map of Amman (click a project/area → analysis panel updates), BI-grade charts, and an **evidence panel** showing the recommended price range (minimum-safe / recommended / premium) as an adjustment waterfall — each adjustment backed by the sources you collect
3. **A methodology document** mapping everything to established valuation practice (sales comparison, cost approach, income approach)

Two kinds of intelligence — keep them separate:
- **Current State** (what exists today): listings, rents, POIs, zoning → justifies today's value
- **Future Signals** (what's coming): metro/BRT, roads, malls, hospitals, master-plan projects → justifies future appreciation and launch positioning

## 4. The Rules (non-negotiable)

1. **Fill the CSV columns exactly as given in Section 5. Never add, rename, remove, or reorder columns.**
2. Every row MUST have `source_url` and `capture_date` (date you collected it). **No source = row rejected.** Provenance IS the product.
3. If a value is unknown, write `unknown`. Never guess, never leave blank.
4. **Collection is objective. Interpretation is our job.** You record what sources SAY, never your opinion of what it means for prices. (See `expected_effect` rule in Dataset 2.)
5. `confidence` (H/M/L) means **how much you trust the SOURCE** (official gov page = H, established news = H/M, blog/social = L) — NOT whether the fact matters for pricing. Those are different concepts; only source trust is yours to judge.
6. Two universal columns appear in every dataset — fill them on every row:
   - `evidence_category` = market | government | gis | infrastructure | macro | portal | builder | news | derived
   - `language` = en | ar | mixed (language of the source content)
7. Geographic scope ONLY: **Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani** (premium Amman submarkets). Citywide items (metro, airport, mega-projects) allowed for Dataset 2.
8. Files: **CSV, UTF-8**, named `datasetname_YYYYMMDD.csv`. Send each file as soon as it's done — don't batch.

Use ANY AI tool (Perplexity, Gemini Deep Research, ChatGPT, Claude) — prompts provided. Perplexity for citation-heavy tasks; Gemini Deep Research for wide sweeps.

**Deadline: end of day 8 July 2026. Priority order: Dataset 1 → 2 → 3 → 4 → 5 → 6 → 7.**
*(Rationale for the order: builders sell stories before they sell concrete — competition and future appreciation shape launch positioning; construction cost only protects the floor.)*

---

## 5. Your Assignments

### Dataset 1 — Competitor / New Development Projects (PRIORITY 1)

*Why:* the launch price must be positioned against competing projects. Feeds Competition Score + comparables panel. Brand matters too — a luxury builder commands a premium — hence `builder_tier`.

**File:** `projects_YYYYMMDD.csv`
**Columns (exact, in order):**
`project_id, name, developer, builder_tier, neighborhood, lat, lng, status, unit_types, launch_price_jd_m2, payment_plan, launch_date, units_total, evidence_category, language, source_name, source_url, capture_date, collected_by, confidence, notes`
- `builder_tier` = local | premium | luxury | unknown (only if publicly inferable — reputation, portfolio, positioning; else `unknown`)
- `status` = planned | construction | selling | delivered · `evidence_category` here is usually `builder` or `news`

**Prompt (Gemini Deep Research / Perplexity):**
> Find all residential development projects currently selling, under construction, or recently launched in Amman, Jordan — specifically in Abdoun, Dabouq, Sweifieh, Khalda, and Shmeisani. For each project give: project name, developer name, developer's market positioning (local/premium/luxury if evident from their portfolio and branding), neighborhood, status (planned/construction/selling/delivered), unit types offered, price per square meter in JOD if published, payment plan details, launch date, total units. Only include facts you can cite with a URL (developer website, Bayut new-projects section, news article, official Facebook page). Present as a table with the source URL for every project.

### Dataset 2 — Future Infrastructure & Development News (PRIORITY 1)

*Why:* this is the entire **Future Signals** pipeline — evidence for the appreciation story ("prices here will rise because the BRT extension opens in 2027"). Future signals justify premium pricing.

**File:** `evidence_items_YYYYMMDD.csv`
**Columns:** `evidence_id, type, title, summary_2_lines, impact_area, expected_year, expected_effect, published_date, evidence_category, language, source_name, source_url, capture_date, collected_by, confidence, notes`
- `type` = infrastructure | policy | market_news · `impact_area` = neighborhood name or `citywide`
- **`expected_effect`: fill ONLY if the source itself explicitly states an expected impact** (e.g., an article says "expected to raise property values"). Quote/paraphrase what the source says. If the source states nothing, write `unknown`. **Never your own opinion — our engine does the interpretation.**

**Prompt (Perplexity / Gemini):**
> List all announced or planned infrastructure and development projects in Amman, Jordan from 2024 onwards: BRT/bus rapid transit expansions, new roads or road widening, new hospitals, schools, universities, shopping malls, government mega-projects, and anything from the Greater Amman Municipality master plan. For each: project title, 2-line summary, which district/neighborhood it affects (or citywide), expected completion year, publication date of the announcement, any impact on the area explicitly stated by the source itself, and the exact source URL (news article or government page). Only verified announcements — no rumors without a source.

### Dataset 3 — Construction Cost Benchmarks (PRIORITY 1)

*Why:* powers the cost-approach price FLOOR (land + construction − depreciation = minimum sensible price).

**File:** `cost_benchmarks_YYYYMMDD.csv`
**Columns:** `spec_class, cost_jd_per_m2_low, cost_jd_per_m2_high, year, evidence_category, language, source_name, source_url, capture_date, collected_by, confidence, notes`
- `spec_class` = basic | standard | high | luxury

**Prompt (Perplexity — citations mandatory):**
> What is the current construction cost per square meter in Amman, Jordan for residential buildings, broken down by finishing level (basic, standard, high-end, luxury)? Give figures in Jordanian Dinar per m², the year each figure refers to, and cite the exact source URL for every number (quantity surveyor reports, contractor publications, industry articles, engineering association data). I need a low and high range per category. Do not estimate without a source.

### Dataset 4 — Premium Listings from Homes-Jordan (PRIORITY 2)

*Why:* extra comparables in the premium segment. (Bayut/OpenSooq are scraped by us — do NOT collect those.)

**File:** `listings_homesjordan_YYYYMMDD.csv`
**Columns:** `listing_id, portal, listing_url, listing_type, property_type, neighborhood, district, lat, lng, price_jd, area_m2, bedrooms, bathrooms, floor_level, total_floors, view, parking, building_age_years, furnishing, elevator, finish_quality, seller_type, listing_date, main_image_url, description_raw, evidence_category, language, source_name, source_url, capture_date, collected_by, confidence, notes`
- `view` = none | sea | city | garden | mountain | panoramic | unknown (pick the closest; free-text impressions go in `notes`)
- `main_image_url` = URL of the primary listing photo if available (future AI-vision use; else `unknown`)
- `parking` = none | open | covered | unknown · `furnishing` = no | semi | full | unknown · `elevator` = y | n | u · `finish_quality` = basic | standard | high | luxury | unknown · `seller_type` = agent | developer | private · `evidence_category` = portal

**Method:** browse https://www.homes-jordan.com/en/property/sale (and /rent) manually or with AI help. Target ~30–60 listings across our 5 neighborhoods, one row per listing, the listing's own URL in `listing_url`. BONUS: check their blog (https://www.homes-jordan.com/en/blogs) — if a recent post summarizes official DLS market data, add it as a row in Dataset 2 with `type` = market_news.

### Dataset 5 — POI Verification (PRIORITY 2)

*Why:* our map data comes from OpenStreetMap, which can be incomplete. You verify the amenities that drive prices.

**File:** `poi_verified_YYYYMMDD.csv`
**Columns:** `poi_id, category, name, lat, lng, neighborhood, exists, evidence_category, language, source_name, source_url, capture_date, collected_by, confidence, notes`
- `category` = school | hospital | mall | mosque | park | university | transport · `exists` = yes | no | unknown · `evidence_category` = gis

**Prompt (Gemini):**
> List the major schools (especially international schools), hospitals, shopping malls, universities, and parks located in or immediately adjacent to these Amman neighborhoods: Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani. For each give: name, category, neighborhood, approximate coordinates if known, and a URL where possible (official website or Google Maps link).

### Dataset 6 — Neighborhood Profiles (PRIORITY 2)

*Why:* our datasets know properties, but not neighborhoods. This gives the AI context for explanations ("Abdoun is Amman's premier diplomatic district…").

**File:** `neighborhood_profiles_YYYYMMDD.csv`
**Columns:** `neighborhood, luxury_level, primary_buyer_type, typical_property_type, typical_price_range_jd_m2, reputation_summary, commercial_mix, population_character, evidence_category, language, source_name, source_url, capture_date, collected_by, confidence, notes`
- `luxury_level` = budget | mid | upper-mid | premium | luxury · one row per neighborhood (5 rows total, more sources = better `notes`)
- Report what sources SAY about reputation — cite them; this is researched characterization, not your opinion.

**Prompt (Gemini Deep Research / Perplexity):**
> Create a profile of each of these Amman, Jordan neighborhoods: Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani. For each: market positioning (budget/mid/premium/luxury), who typically buys or lives there (families, diplomats, expats, investors), typical property types, typical apartment price range per m² in JOD, general reputation, commercial character (retail, offices, embassies), and population character. Cite a URL for every claim (real estate guides, market reports, news articles).

### Dataset 7 — Facebook Group Price Samples (ONLY IF TIME REMAINS)

**File:** `listings_facebook_YYYYMMDD.csv` — same columns as Dataset 4, with `portal` = facebook, `evidence_category` = market.
Search public groups (عقارات عمان / شقق للبيع عمان / أراضي للبيع), collect 20–30 sale posts in target areas. Post URL in `listing_url`. Arabic text raw into `description_raw` (`language` = ar) — we translate.

---

## 6. Quality Self-Check Before Sending

- [ ] Columns match this file exactly (count them)
- [ ] Every row has `source_url` + `capture_date` + `evidence_category` + `language`
- [ ] No blanks — `unknown` where not found
- [ ] No personal opinions anywhere — only what sources state
- [ ] Only the 5 target neighborhoods (except citywide items in Dataset 2)
- [ ] CSV UTF-8, named `datasetname_YYYYMMDD.csv`
- [ ] Doubts recorded in `notes`, not improvised

## 7. What NOT to do

- Don't scrape Bayut or OpenSooq — handled on our side with dedicated tooling.
- Don't convert currencies — JOD only, as published.
- Don't average, clean, or "fix" data — deliver raw with sources; cleaning is our job.
- Don't judge whether something affects prices — that's the engine's job, not collection's.
- Don't spend more than ~30 minutes stuck on one item — mark `unknown` in `notes`, move on. Coverage of all P1 datasets beats perfection on one.

*Questions → message the lead. Otherwise: start with Dataset 1 now.*
