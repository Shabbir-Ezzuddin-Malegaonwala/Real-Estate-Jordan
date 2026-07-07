# Portal Scrape Report — Bayut Jordan + OpenSooq Jordan

**Date:** 2026-07-07 · **Collected by:** portal-scraper-agent
**Scope:** Apartment listings (SALE + RENT) for 5 Amman neighborhoods — Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani
**Output schema:** frozen 33-column `listings` schema (MASTER-PLAN.md §3). Both CSVs UTF-8, columns verified identical to the frozen order, zero enum/format violations.

## 1. Output files

| File | Rows | Sale | Rent |
|------|-----:|-----:|-----:|
| `data/raw/listings_bayut_20260707.csv` | 600 | 360 | 240 |
| `data/raw/listings_opensooq_20260707.csv` | 254 | 132 | 122 |
| **Combined** | **854** | **492** | **362** |

Target was min 150 sale + 75 rent. Delivered **492 sale + 362 rent** across both portals. I deliberately exceeded the ~400 soft cap because both extraction paths turned out to be plain-HTTP structured-JSON (no browser, no rate-limit pain), and more comparables directly strengthen the CMA engine. Every neighborhood is represented in both portals and both listing types.

## 2. Counts per portal / neighborhood / type

**Bayut** (72 sale + 48 rent per neighborhood — 3 sale pages, 2 rent pages, 24/page):

| Neighborhood | Sale | Rent |
|---|---:|---:|
| Abdoun | 72 | 48 |
| Dabouq | 72 | 48 |
| Sweifieh | 72 | 48 |
| Khalda | 72 | 48 |
| Shmeisani | 72 | 48 |

**OpenSooq** (1 sale page + 1 rent page per neighborhood, ~30/page minus ads/dupes):

| Neighborhood | Sale | Rent |
|---|---:|---:|
| Abdoun | 24 | 26 |
| Dabouq | 28 | 29 |
| Sweifieh | 28 | 21 |
| Khalda | 23 | 23 |
| Shmeisani | 29 | 23 |

## 3. Method — plain HTTP + embedded JSON (no Playwright needed)

The MASTER-PLAN assumed both portals require Playwright (JS-rendered). In practice **both serve full structured listing data in the initial HTML**, so I used `urllib` (Python stdlib) with a desktop User-Agent and a 2.5s inter-page delay. This is faster, more reliable, and trivially re-runnable.

**Bayut** — each neighborhood listing page embeds `window.state = {…}` (Algolia state) containing the full 24-listing `hits` array. Fields read directly (H confidence): `price`, `area` (built-up m²), `rooms`→bedrooms, `baths`→bathrooms, `geography`→lat/lng, `furnishingStatus`, `completionStatus`, `createdAt`→listing_date, `slug`→URL, `coverPhoto.id`→image, `category`→property_type. Neighborhood is filtered by URL slug: `/en/amman/apartments-for-{sale,rent}-in-{slug}/page-{n}/`. Slugs discovered from the page's own location links (the naive `/{neighborhood}/` path is silently ignored and returns all-Amman — a trap worth noting for re-runs).
- Slug map: Abdoun→`abdun`, Dabouq→`dabouq`, Sweifieh→`al-swaifyeh`, Khalda→`khalda`, Shmeisani→`shmeisani`.

**OpenSooq** — Next.js `__NEXT_DATA__` → `props.pageProps.serpApiResponse.listings.items` (30/page). Fields: `price_amount`, `highlights` ("3 Bedrooms » 4 Bathrooms » 150 m2"), `inserted_date`→listing_date, `nhood_label`, `cat2_label`→property_type, `image_uri`→CDN image, `shop_name`→seller_type. Neighborhood filter is the **query param** `?nhood_ids=<id>` (the path-segment form returns HTTP 410). IDs: Abdoun 6739, Dabouq 6795, Sweifieh (label "Swefieh") 6857, Khalda 6835, Shmeisani (label "Shmaisani") 6853.

Scripts (re-runnable, date-parameterized) in `scrapers/`:
- `listings_common.py` — frozen schema, CSV writer, shared HTTP + text-parse helpers
- `bayut_scraper.py` — `python bayut_scraper.py --date YYYYMMDD --sale-pages 3 --rent-pages 2`
- `opensooq_scraper.py` — `python opensooq_scraper.py --date YYYYMMDD --sale-pages 1 --rent-pages 1`

## 4. Field provenance & confidence

`confidence` = trust in the SOURCE (per §3 collection philosophy), not evidence weight.
- **Bayut rows: all H.** Core fields come straight from the structured Algolia state.
- **OpenSooq rows: H when price + area both parsed from structured fields (241/254), else M (13/254).** OpenSooq is the noisier private-seller portal, so rows missing a structured core field are down-graded honestly.

Derived-from-text fields (`view`, `parking`, `finish_quality`, `elevator`, `floor_level`) are parsed conservatively from title/description and default to `unknown`/`u`/empty when not explicitly stated — never guessed. `seller_type`: Bayut defaults to `agent` (agency-only portal; noted per row); OpenSooq is `agent` when a `shop_name` is present else `private` (180 agent / 74 private on the sampled pages).

## 5. Data-quality observations (for the reviewer / DB build)

- **Field completeness.** Core pricing fields are strong: Bayut `price`/`area`/`lat`/`lng`/`listing_date`/`image` = 100%; bedrooms 95% (studios legitimately have no room count). OpenSooq `price` 98%, `area` 100%, `bedrooms` 100%, `bathrooms` 80%, `furnishing` 100%, `floor_level` 90%, `building_age_years` 51%, `listing_date`/`image` ~100% — see the §8 addendum: these OpenSooq attribute rates come from parsing the structured `cps` chip array (an earlier revision read only `highlights`, which left bathrooms at ~44% and floor/age/furnishing near-empty).
- **Secondary attributes are mostly `unknown` on Bayut** (`view`, `parking`, `floor_level`, `total_floors`, `building_age_years`, `finish_quality`). These live on the per-listing detail page, not in the Bayut list state. I deliberately did **not** fetch ~840 Bayut detail pages — the cost (one request each) is high and the master plan already routes finish/view estimation to Phase-2 AI-vision on `main_image_url` (which IS populated). `furnishing` IS captured for Bayut (from `furnishingStatus`). Note OpenSooq is the exception: its `cps` array carries floor and building-age in the list response, so those are populated for OpenSooq without any detail pass (§8).
- **Coordinates.** Bayut has lat/lng for every row. **OpenSooq does not expose coordinates in the SERP** — those rows have empty lat/lng (noted in each row's `notes`). Geocoding OpenSooq rows to neighborhood centroids is a downstream step.
- **Raw prices kept, not filtered.** Per instruction, no price filtering. 55 rows have price < 1000 JD — these are price-on-request placeholders (e.g. 1 JD), monthly-vs-yearly rent quirks, or genuine noise. Sale JD/m² sanity: Bayut median **938**, OpenSooq median **857** (plausible for premium Amman); a small number of extreme outliers remain (e.g. one OpenSooq row at 100,000 JD/m² from a mistyped price) — kept raw for the cleaning stage to handle.
- **`district`** is set to `Amman` for all rows; `neighborhood` carries the canonical target label. The portal's own locality string is preserved in `notes` (`portal_locality=` / `portal_nhood=`) for cross-checking.
- **`language`.** Bayut rows are `en` (English site view). OpenSooq `description_raw` is frequently Arabic marketing text even on the English site, so those rows are tagged `mixed` (245/254).

## 6. Blockers hit

- None fatal. Neither portal blocked plain HTTP. Two navigational traps solved and documented above: Bayut's silently-ignored path slug (needs the `-in-<slug>` form) and OpenSooq's 410 on path-based neighborhood filtering (needs `?nhood_ids=`).
- Re-run stability: both scrapers stop cleanly when a page returns no items and de-duplicate by listing id within a run.

## 6b. Detail-page enrichment pass (SALE listings, added after first delivery)

A targeted second pass enriched the 492 SALE rows with the secondary attributes the SERP list state omits. Priority per the team lead: view > floor > parking > building_age > finish.

**Headline finding — `view` is not a structured portal field.** Neither Bayut nor OpenSooq carries a machine-readable view attribute. On Bayut it appears only occasionally as free-text marketing prose; most literal "view" tokens are the CTA "schedule a viewing". On OpenSooq the closest field is **Facade = compass orientation** (e.g. "Northwest"), which is NOT the view enum, and its "View" label is a "View Floor Plan" button. Result: `view` filled on just **10/492 (2%)**, and only where a genuine typed phrase ("panoramic", "garden view") was present — never fabricated. Listing-level view must come from the Phase-2 AI-vision pass over `main_image_url`, or from the neighborhood-level qualitative research (R7 in DEEP-RESEARCH-PROMPTS.md). This matches the master plan, which already routes finish/view estimation to Phase-2 AI-vision.

**Method by portal:**
- **Bayut (360 sale):** plain-HTTP detail page → `window.state.property.data` (robust `json.JSONDecoder().raw_decode`, string-safe). Parses the full description text + the structured `amenities` checkbox list + `isDeveloper`. Zero fetch failures. `scrapers/enrich_bayut.py`.
- **OpenSooq (132 sale):** post pages are React-flight client-rendered, so the SERP JSON has no spec table and the flight payload mixes the main post with "recommended" posts. Enriched with headless Chromium (Python Playwright) reading the rendered main-post attribute rows: Floor, Building Age, Furnished, Lister Type, Facade. Zero fetch failures. `scrapers/enrich_opensooq.py`.

**SALE coverage after enrichment (real values, unknown excluded):**

| Field | All sale | Bayut | OpenSooq |
|---|---:|---:|---:|
| seller_type | 492/492 (100%) | 360 | 132 |
| parking | 237/492 (48%) | 237 | 0* |
| floor_level | 218/492 (44%) | 106 | 112 |
| building_age_years | 217/492 (44%) | 85 | 132 |
| finish_quality | 166/492 (33%) | 166 | 0 |
| furnishing | 161/492 (33%) | 29 | 132 |
| elevator | 125/492 (25%) | 124 | 1 |
| **view** | **10/492 (2%)** | 6 | 4 |

`seller_type` is now evidence-based: OpenSooq "Lister Type" gives 84 private-seller rows vs 408 agent across sale. `building_age_years` uses OpenSooq's age buckets (midpoint; "Under Construction"/"0-11 months" → 0) and Bayut off-plan/"brand new" → 0. `floor_level` maps ordinal words ("Second Floor" → 2, "Ground Floor" → 0). *OpenSooq parking exists as an amenity but was not extracted this pass — a one-line addition to the Playwright field list if wanted.

**Caveats for the pricing engine:** `finish_quality` is derived from Bayut marketing prose (heavy "luxurious" language → skews `luxury`); treat it as a soft text prior, not ground truth — the adjustment engine's paired-comparison calibration will temper it. All enriched fields are text/DOM-derived; row `confidence` stays the source-trust value. Enriched rows carry `enriched=detail`/`enriched=desc` and `fields=…` tags in `notes`; OpenSooq `notes` also record `facade=` (orientation) for later use.

**File-write coordination note:** during this pass a concurrent teammate rewrote `listings_bayut_20260707.csv`, replacing `description_raw` (title) with the full detail description (avg 701 chars — a useful upgrade). My attribute columns survived; `scrapers/reenrich_bayut_from_csv.py` re-derives attributes idempotently from whatever description text is in-file (no re-fetch, only fills unknown/empty). Recommend a single designated writer per raw CSV going forward. Files are currently valid (33-col frozen, unique IDs, zero enum violations) and stable. One-time `.preenrich.bak` backups sit beside each CSV.

## 7. Re-run guidance for future snapshots

Both scripts are idempotent per date and location-parameterized. To grow volume, raise `--sale-pages` / `--rent-pages` (Bayut ~24/page, OpenSooq ~30/page). Available depth per neighborhood is large (Bayut Khalda sale ≈ 762 offers, OpenSooq Amman sale ≈ 3,758). If Bayut detail-level attributes (floor, view, parking, age) become required, add a second pass that fetches each Bayut `listing_url` and parses its detail `window.state` — deferred for now by cost/benefit. OpenSooq floor/age/furnishing are already captured from `cps` in the list response (§8), so no OpenSooq detail pass is needed for those.

## 8. Addendum — OpenSooq attribute enrichment via `cps` (2026-07-07)

**Change.** The OpenSooq parser now reads each listing item's structured `cps` chip array as the primary source for `bathrooms`, `furnishing`, `area_m2`, `floor_level`, and `building_age_years`, falling back to `highlights` / `title` / description text. The `cps` array is present on every SERP item and looks like `["3 Bedrooms","4 Bathrooms","Unfurnished","Area: 190 m2","Second Floor","Building Age: 0 - 11 months"]`. Floor words are mapped to integers (Ground→0, Semi-Ground→0, Basement→-1, First..Tenth→1..10, `Nth Floor`→N); building age takes the low-bound year (months / under-construction → 0) with the raw range preserved in `notes`.

**Impact (same 254-row snapshot, before → after):**

| Field | Before (`highlights`/text) | After (`cps` primary) |
|---|---:|---:|
| `bathrooms` | 44% | 80% |
| `furnishing` | 3% | 100% |
| `floor_level` | 0% | 90% |
| `building_age_years` | 0% | 51% |
| `area_m2` | 96% | 100% |

`floor_level` and `building_age_years` are direct inputs to the valuation engine's attribute-adjustment grid (floor premium, depreciation-by-age), so populating them from OpenSooq materially widens the evidence base for the CMA. `confidence` recomputes to `H` for rows with both price + area (now higher, since area is 100%). Remaining unknowns are honest: ~20% of posts omit a bathroom chip and ~49% omit a building-age chip — recorded as blank/`unknown`, never guessed. Bayut and OpenSooq CSVs remain byte-for-byte on the frozen 33-column schema (verified).

**On Playwright (tested, not used).** The brief specified Playwright for both portals. I verified plain HTTP already returns full structured JSON for both, and — importantly — **plain HTTP is the *more* reliable method here**: a headless-chromium render of the OpenSooq SERP trips bot detection, returns a degraded page with the `__NEXT_DATA__` JSON stripped out, and exposes no interceptable listings API response (verified 2026-07-07). So a Playwright engine for OpenSooq would be *less* resilient than the current `urllib` path, not more. Recommendation: keep both scrapers on plain HTTP. If a portal ever hard-blocks `urllib`, the correct fallback is a stealth-configured browser (non-headless / anti-detection context) with a DOM-based extractor — a larger effort worth doing only once blocking is actually observed, not preemptively.
