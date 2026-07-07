# Jordan Real Estate Intelligence — Text2SQL Semantic-Layer Training Document

_Generated 2026-07-07 from `db/jordan_re.sqlite`. This document follows the platform's strict 3-section training-document format (DDL / Business & Semantic Rules / Example Queries) so it can be ingested directly by the vectorization service, chunked, and indexed into Weaviate for natural-language querying. Every example query below was executed against the live database and returned without error (21/21 passing)._

## 1. DDL Schema of the Database

```sql
CREATE TABLE listings (
    listing_id         TEXT PRIMARY KEY,
    portal             TEXT NOT NULL,
    listing_url        TEXT NOT NULL,
    listing_type       TEXT NOT NULL CHECK (listing_type IN ('sale','rent','unknown')),
    property_type      TEXT NOT NULL CHECK (property_type IN ('apartment','villa','land','commercial','unknown')),
    neighborhood       TEXT NOT NULL,
    district           TEXT,
    lat                REAL,
    lng                REAL,
    price_jd           REAL,
    area_m2            REAL,
    price_per_m2       REAL GENERATED ALWAYS AS (
                          CASE WHEN price_jd IS NOT NULL AND area_m2 IS NOT NULL AND area_m2 > 0
                               THEN price_jd / area_m2 END) VIRTUAL,
    bedrooms           INTEGER,
    bathrooms          INTEGER,
    floor_level        INTEGER,
    total_floors       INTEGER,
    view               TEXT NOT NULL DEFAULT 'unknown' CHECK (view IN ('none','sea','city','garden','mountain','panoramic','unknown')),
    parking            TEXT NOT NULL DEFAULT 'unknown' CHECK (parking IN ('none','open','covered','unknown')),
    building_age_years INTEGER,
    furnishing         TEXT NOT NULL DEFAULT 'unknown' CHECK (furnishing IN ('no','semi','full','unknown')),
    elevator           TEXT NOT NULL DEFAULT 'unknown' CHECK (elevator IN ('y','n','u','unknown')),
    finish_quality     TEXT NOT NULL DEFAULT 'unknown' CHECK (finish_quality IN ('basic','standard','high','luxury','unknown')),
    seller_type        TEXT NOT NULL DEFAULT 'unknown' CHECK (seller_type IN ('agent','developer','private','unknown')),
    listing_date       TEXT,
    main_image_url     TEXT,
    description_raw    TEXT,
    evidence_category  TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language           TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name        TEXT NOT NULL,
    source_url         TEXT NOT NULL,
    capture_date       TEXT NOT NULL,
    collected_by       TEXT,
    confidence         TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes              TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE projects (
    project_id         TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    developer          TEXT,
    builder_tier       TEXT NOT NULL DEFAULT 'unknown' CHECK (builder_tier IN ('local','premium','luxury','unknown')),
    neighborhood       TEXT NOT NULL,
    lat                REAL,
    lng                REAL,
    status             TEXT NOT NULL CHECK (status IN ('planned','construction','selling','delivered','unknown')),
    unit_types         TEXT,
    launch_price_jd_m2 REAL,
    payment_plan       TEXT,
    launch_date        TEXT,
    units_total        INTEGER,
    evidence_category  TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language           TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name        TEXT NOT NULL,
    source_url         TEXT NOT NULL,
    capture_date       TEXT NOT NULL,
    collected_by       TEXT,
    confidence         TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes              TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE poi (
    poi_id            TEXT PRIMARY KEY,
    category          TEXT NOT NULL CHECK (category IN ('school','hospital','mall','mosque','park','university','transport','unknown')),
    name              TEXT NOT NULL,
    lat               REAL,
    lng               REAL,
    neighborhood      TEXT,
    "exists"          TEXT NOT NULL DEFAULT 'unknown' CHECK ("exists" IN ('yes','no','unknown')),
    evidence_category TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language          TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name       TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    capture_date      TEXT NOT NULL,
    collected_by      TEXT,
    confidence        TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes             TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE districts (
    district_id       TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    neighborhood      TEXT,
    zone_class        TEXT,
    far               REAL,
    max_height_m      REAL,
    geometry_geojson  TEXT,
    centroid_lat      REAL,
    centroid_lng      REAL,
    evidence_category TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language          TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name       TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    capture_date      TEXT NOT NULL,
    collected_by      TEXT,
    confidence        TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes             TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE zoning_plots (
    plot_id           TEXT PRIMARY KEY,
    zone_class        TEXT,
    far               REAL,
    max_height_m      REAL,
    land_use          TEXT,
    neighborhood      TEXT,
    district          TEXT,
    geometry_geojson  TEXT,
    centroid_lat      REAL,
    centroid_lng      REAL,
    evidence_category TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language          TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name       TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    capture_date      TEXT NOT NULL,
    collected_by      TEXT,
    confidence        TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes             TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE macro_series (
    macro_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator         TEXT NOT NULL,
    geography         TEXT NOT NULL,
    period            TEXT NOT NULL,
    "value"           REAL,
    unit              TEXT,
    evidence_category TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language          TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name       TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    capture_date      TEXT NOT NULL,
    collected_by      TEXT,
    confidence        TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes             TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (indicator, geography, period)
);

CREATE TABLE evidence_items (
    evidence_id       TEXT PRIMARY KEY,
    type              TEXT NOT NULL CHECK (type IN ('infrastructure','policy','market_news','unknown')),
    title             TEXT NOT NULL,
    summary_2_lines   TEXT,
    impact_area       TEXT,
    expected_year     INTEGER,
    expected_effect   TEXT,
    published_date    TEXT,
    evidence_category TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language          TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name       TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    capture_date      TEXT NOT NULL,
    collected_by      TEXT,
    confidence        TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes             TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE neighborhood_profiles (
    profile_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    neighborhood          TEXT NOT NULL,
    luxury_level          TEXT NOT NULL DEFAULT 'unknown' CHECK (luxury_level IN ('budget','mid','upper-mid','premium','luxury','unknown')),
    primary_buyer_type    TEXT,
    typical_property_type  TEXT,
    typical_price_range_jd_m2 TEXT,
    reputation_summary    TEXT,
    commercial_mix        TEXT,
    population_character   TEXT,
    evidence_category     TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language              TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name           TEXT NOT NULL,
    source_url            TEXT NOT NULL,
    capture_date          TEXT NOT NULL,
    collected_by          TEXT,
    confidence            TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes                 TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE cost_benchmarks (
    benchmark_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_class         TEXT NOT NULL CHECK (spec_class IN ('basic','standard','high','luxury','unknown')),
    cost_jd_per_m2_low  REAL,
    cost_jd_per_m2_high REAL,
    year               INTEGER,
    evidence_category  TEXT NOT NULL CHECK (evidence_category IN ('market','government','gis','infrastructure','macro','portal','builder','news','derived','unknown')),
    language           TEXT NOT NULL DEFAULT 'unknown' CHECK (language IN ('en','ar','mixed','unknown')),
    source_name        TEXT NOT NULL,
    source_url         TEXT NOT NULL,
    capture_date       TEXT NOT NULL,
    collected_by       TEXT,
    confidence         TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes              TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE derived_premiums (
    premium_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    factor          TEXT NOT NULL,
    neighborhood    TEXT,
    property_type   TEXT,
    derived_premium REAL NOT NULL,
    method          TEXT NOT NULL,
    source          TEXT,
    confidence      TEXT CHECK (confidence IN ('H','M','L','High','Medium','Low','unknown')),
    sample_size     INTEGER,
    computed_date   TEXT NOT NULL,
    notes           TEXT,
    UNIQUE (factor, neighborhood, property_type, computed_date)
);

CREATE TABLE recommendations (
    recommendation_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id             TEXT,
    neighborhood            TEXT NOT NULL,
    property_type           TEXT,
    min_safe_price_jd_m2    REAL,
    recommended_price_jd_m2 REAL,
    premium_price_jd_m2     REAL,
    confidence_label        TEXT CHECK (confidence_label IN ('H','M','L','unknown')),
    confidence_numeric      REAL,
    narrative               TEXT,
    evidence_objects_json   TEXT,
    comparables_json        TEXT,
    risk_factors_json       TEXT,
    alternative_scenarios_json TEXT,
    computed_date           TEXT NOT NULL,
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## 2. Documentation of Business Rules

- Domain: residential real-estate asking-price intelligence for Amman, Jordan. All money is in Jordanian Dinar (JOD, aka JD) exactly as published on the source portal — there is NO currency conversion anywhere in this database.
- COVERED SUBMARKETS: only five neighborhoods have decision-grade coverage — Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani. Filter listings.neighborhood to these five for any analysis meant to be reliable. Other neighborhoods exist in the listings table but were loaded for market density/context only and are not quality-reviewed.
- Listing prices are ASKING prices scraped from portals (Bayut, OpenSooq, Homes-Jordan, Facebook), NOT closed/registry transaction prices. To approximate a transaction-level figure, multiply an asking price by roughly 0.85 to 0.95 (a 5–15% asking-to-transaction gap).
- price_per_m2 is a DERIVED (GENERATED) column: price_per_m2 = price_jd / area_m2, computed by the database only when price_jd is not null and area_m2 > 0. Never recompute it manually; select the column directly. It is stored as REAL.
- The 'confidence' column (H / M / L) records TRUST IN THE SOURCE (official government = H, established news = H/M, blog/social = L). It is NOT a statement about price accuracy or listing reliability. Do not treat confidence='L' as 'cheap' or 'wrong price'.
- 'evidence_category' classifies where a row came from: market, government, gis, infrastructure, macro, portal, builder, news, derived, unknown.
- 'unknown' is the explicit null-object for categorical/enum columns (view, parking, furnishing, finish_quality, seller_type, listing_type, property_type, etc.). When counting rows that actually have a value, exclude 'unknown', e.g. WHERE view <> 'unknown'.
- listing_type enum = sale | rent | unknown. property_type enum = apartment | villa | land | commercial | unknown. Always constrain BOTH when comparing prices, because sale and rent price_per_m2 are not comparable, and land vs apartment are not comparable.
- Structural attributes are SPARSE in the listings table: view is populated on ~0.1% of rows, parking ~1.3%, floor_level ~1.4%, finish_quality ~1.0%. Aggregations on these columns are valid but rest on small samples — always report the COUNT alongside the aggregate.
- macro_series holds official time series. The CBJ/DoS real-estate price index (indicator LIKE 'Real estate price index%') runs from 2005 to 2021-Q3 and is a Laspeyres index (base year per source). Building-licence series (indicator LIKE 'Building licenses%') run 2019–2024. National trading volume/revenue rows are 2025-YTD. There is a multi-year gap between the newest macro data (2021-Q3 index) and the 2026 listing snapshot.
- macro_series.period is TEXT with MIXED formats: plain year ('2005'), quarter ('2021-Q3'), month ('2025-08'), and year-to-date ('2025-YTD-08'). Do NOT cast period to a number; filter it with string equality or LIKE, and sort lexically (which is chronological for same-format values).
- cost_benchmarks gives indicative construction cost per m² by finishing class (spec_class = basic | standard | high | luxury | unknown); it is a cost-approach FLOOR, not a per-project quote. Ranges are cost_jd_per_m2_low .. cost_jd_per_m2_high. IMPORTANT for this snapshot: most rows carry spec_class='unknown' and the basic/standard rows have NULL costs — to get usable figures filter on cost_jd_per_m2_low IS NOT NULL rather than filtering by spec_class.
- derived_premiums and recommendations are ENGINE-OUTPUT tables. In the current snapshot they are EMPTY (0 rows) — the decision engine sample run has not been persisted. Queries against them are valid but will return no rows until the engine writes to them.
- Column typing: in THIS database price_jd, area_m2, price_per_m2, macro_series.value, far, max_height_m, cost_jd_per_m2_* are stored as REAL and floor_level/bedrooms/bathrooms/expected_year as INTEGER — they are already numeric, so arithmetic works directly. (If you ever query a CSV-imported copy where these arrive as TEXT, wrap them in CAST(col AS REAL) before comparing or aggregating.)
- SQLite has no MEDIAN function. Compute a median with the ordered-subquery idiom: SELECT AVG(x) FROM (SELECT x FROM t WHERE <filter> AND x IS NOT NULL ORDER BY x LIMIT 2 - (SELECT COUNT(*) FROM t WHERE <filter> AND x IS NOT NULL) % 2 OFFSET (SELECT (COUNT(*)-1)/2 FROM t WHERE <filter> AND x IS NOT NULL)). Median is preferred over AVG for asking prices because portal outliers skew the mean.
- Geospatial: districts and zoning_plots store polygons as GeoJSON text in geometry_geojson, plus centroid_lat/centroid_lng for cheap point math. listings/poi/projects carry lat & lng directly. There is no spatial index; use centroid columns and bounding-box/haversine math for proximity.
- Table 'listings' = one sale-or-rent asking-price advert scraped from a property portal.
- Table 'projects' = a competitor new-launch development (off-plan / under-construction / selling).
- Table 'poi' = a point of interest (school, hospital, mall, mosque, park, university, transport) used for location scoring.
- Table 'districts' = an Amman neighborhood/admin boundary polygon with zoning (far, max_height_m).
- Table 'zoning_plots' = plot-level land-use / zoning polygons (official GAM data or OSM-landuse fallback).
- Table 'macro_series' = official government time series (price index, building licences, trading volume).
- Table 'evidence_items' = future-signal news items (infrastructure / policy / market_news) that may move prices.
- Table 'neighborhood_profiles' = researched qualitative context per submarket (luxury level, buyer type, reputation).
- Table 'cost_benchmarks' = construction cost per m² by finishing class (cost-approach floor).
- Table 'derived_premiums' = engine-derived attribute price premiums (fraction; 0.08 = +8%). Currently empty.
- Table 'recommendations' = persisted decision-engine pricing output per location. Currently empty.
- listings.neighborhood → districts.name : join a listing to its district/zoning polygon by neighborhood name (both use the human-readable Amman submarket name, e.g. 'Abdoun').
- listings.neighborhood → neighborhood_profiles.neighborhood : attach researched context (luxury_level, buyer type, reputation) to listings.
- listings.neighborhood → projects.neighborhood : compare resale asking prices against competitor new-launch prices in the same submarket.
- poi.neighborhood → districts.name : locate points of interest within a district.
- listings.finish_quality → cost_benchmarks.spec_class : map a listing's finish class to its construction-cost band (both use basic|standard|high|luxury).
- recommendations.neighborhood / derived_premiums.neighborhood → listings.neighborhood : engine outputs are keyed by the same submarket name.
- evidence_items.impact_area is FREE TEXT (e.g. 'Abdoun', but also 'West Amman incl. Khalda, Dabouq, Naour' or 'citywide'). It only SOMETIMES equals a district name — match it with LIKE '%<name>%', never an equality join, and expect citywide/corridor rows that touch several submarkets.

## 3. Example Queries

Q: What is the median asking price per m2 for apartments for sale in Abdoun?
```sql
SELECT AVG(price_per_m2) AS median
FROM (
  SELECT price_per_m2 FROM listings
  WHERE neighborhood = 'Abdoun' AND property_type = 'apartment' AND listing_type = 'sale' AND price_per_m2 IS NOT NULL
  ORDER BY price_per_m2
  LIMIT 2 - (SELECT COUNT(*) FROM listings WHERE neighborhood = 'Abdoun' AND property_type = 'apartment' AND listing_type = 'sale' AND price_per_m2 IS NOT NULL) % 2
  OFFSET (SELECT (COUNT(*) - 1) / 2 FROM listings WHERE neighborhood = 'Abdoun' AND property_type = 'apartment' AND listing_type = 'sale' AND price_per_m2 IS NOT NULL)
)
```

Q: Give me the median sale asking price per m2 for apartments in each of the five covered submarkets, cheapest first.
```sql
SELECT neighborhood,
       COUNT(*) AS n_sale_apartments,
       ROUND(AVG(price_per_m2), 1) AS avg_price_per_m2
FROM listings
WHERE neighborhood IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
  AND property_type = 'apartment' AND listing_type = 'sale'
  AND price_per_m2 IS NOT NULL
GROUP BY neighborhood
ORDER BY avg_price_per_m2 ASC
```

Q: Which covered submarket has the most sale listings?
```sql
SELECT neighborhood, COUNT(*) AS n_sale_listings
FROM listings
WHERE listing_type = 'sale' AND neighborhood IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
GROUP BY neighborhood
ORDER BY n_sale_listings DESC
LIMIT 1
```

Q: How many listings do we have per property type and listing type across the whole database?
```sql
SELECT property_type, listing_type, COUNT(*) AS n
FROM listings
GROUP BY property_type, listing_type
ORDER BY n DESC
```

Q: List future infrastructure projects (evidence items) affecting Khalda.
```sql
SELECT title, expected_year, expected_effect, source_name, source_url
FROM evidence_items
WHERE type = 'infrastructure'
  AND impact_area LIKE '%Khalda%'
ORDER BY expected_year
```

Q: What are the three cheapest covered submarkets by median sale price per m2 for apartments?
```sql
SELECT neighborhood, ROUND(AVG(price_per_m2), 1) AS avg_price_per_m2, COUNT(*) AS n
FROM listings
WHERE neighborhood IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
  AND property_type = 'apartment' AND listing_type = 'sale'
  AND price_per_m2 IS NOT NULL
GROUP BY neighborhood
ORDER BY avg_price_per_m2 ASC
LIMIT 3
```

Q: Show the 10 most expensive apartment sale listings in the covered submarkets by price per m2, with their source URL.
```sql
SELECT neighborhood, price_jd, area_m2, ROUND(price_per_m2, 1) AS price_per_m2, source_name, source_url
FROM listings
WHERE neighborhood IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
  AND property_type = 'apartment' AND listing_type = 'sale'
  AND price_per_m2 IS NOT NULL
ORDER BY price_per_m2 DESC
LIMIT 10
```

Q: What is the average monthly apartment rent (total price) in Sweifieh?
```sql
SELECT ROUND(AVG(price_jd), 1) AS avg_rent_jd, COUNT(*) AS n
FROM listings
WHERE neighborhood = 'Sweifieh'
  AND property_type = 'apartment' AND listing_type = 'rent'
  AND price_jd IS NOT NULL
```

Q: How many competitor new-launch projects are currently selling, and in which neighborhoods?
```sql
SELECT neighborhood, name, developer, launch_price_jd_m2
FROM projects
WHERE status = 'selling'
ORDER BY neighborhood
```

Q: What construction cost per m2 benchmarks do we have on file (with usable figures)?
```sql
SELECT spec_class, cost_jd_per_m2_low, cost_jd_per_m2_high, year, source_name
FROM cost_benchmarks
WHERE cost_jd_per_m2_low IS NOT NULL
ORDER BY cost_jd_per_m2_low ASC
```

Q: Give the latest available value of the general real-estate price index for Amman.
```sql
SELECT period, value, unit, source_name
FROM macro_series
WHERE indicator = 'Real estate price index - General'
  AND geography = 'Amman'
ORDER BY period DESC
LIMIT 1
```

Q: How many points of interest of each category do we have in the covered submarkets?
```sql
SELECT category, COUNT(*) AS n
FROM poi
WHERE neighborhood IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
GROUP BY category
ORDER BY n DESC
```

Q: Count the schools and hospitals near Abdoun (points of interest in Abdoun).
```sql
SELECT category, COUNT(*) AS n
FROM poi
WHERE neighborhood = 'Abdoun'
  AND category IN ('school', 'hospital')
GROUP BY category
```

Q: What is the zoning FAR and max height on record for each covered submarket district?
```sql
SELECT name AS district, zone_class, far, max_height_m
FROM districts
WHERE name IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
ORDER BY name
```

Q: Compare median apartment sale asking price per m2 in Dabouq against the neighborhood's researched luxury level.
```sql
SELECT l.neighborhood,
       np.luxury_level,
       np.primary_buyer_type,
       ROUND(AVG(l.price_per_m2), 1) AS avg_price_per_m2,
       COUNT(*) AS n
FROM listings l
JOIN neighborhood_profiles np ON np.neighborhood = l.neighborhood
WHERE l.neighborhood = 'Dabouq'
  AND l.property_type = 'apartment' AND l.listing_type = 'sale'
  AND l.price_per_m2 IS NOT NULL
GROUP BY l.neighborhood, np.luxury_level, np.primary_buyer_type
```

Q: Estimate a transaction-level price per m2 for Khalda apartments by discounting the average asking price by 10%.
```sql
SELECT ROUND(AVG(price_per_m2), 1) AS avg_asking_ppm2,
       ROUND(AVG(price_per_m2) * 0.90, 1) AS est_transaction_ppm2,
       COUNT(*) AS n
FROM listings
WHERE neighborhood = 'Khalda'
  AND property_type = 'apartment' AND listing_type = 'sale'
  AND price_per_m2 IS NOT NULL
```

Q: How many apartment sale listings actually disclose a parking attribute, per covered submarket?
```sql
SELECT neighborhood,
       SUM(CASE WHEN parking <> 'unknown' THEN 1 ELSE 0 END) AS with_parking_info,
       COUNT(*) AS total
FROM listings
WHERE neighborhood IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
  AND property_type = 'apartment' AND listing_type = 'sale'
GROUP BY neighborhood
ORDER BY total DESC
```

Q: Which portals supplied our listings and how many from each?
```sql
SELECT portal, COUNT(*) AS n
FROM listings
GROUP BY portal
ORDER BY n DESC
```

Q: List all future-signal evidence items expected in 2026 or later, newest expected first.
```sql
SELECT title, type, impact_area, expected_year, expected_effect
FROM evidence_items
WHERE expected_year >= 2026
ORDER BY expected_year DESC
```

Q: What is the median plot (land) sale price per m2 in Dabouq?
```sql
SELECT AVG(price_per_m2) AS median
FROM (
  SELECT price_per_m2 FROM listings
  WHERE neighborhood = 'Dabouq' AND property_type = 'land' AND listing_type = 'sale' AND price_per_m2 IS NOT NULL
  ORDER BY price_per_m2
  LIMIT 2 - (SELECT COUNT(*) FROM listings WHERE neighborhood = 'Dabouq' AND property_type = 'land' AND listing_type = 'sale' AND price_per_m2 IS NOT NULL) % 2
  OFFSET (SELECT (COUNT(*) - 1) / 2 FROM listings WHERE neighborhood = 'Dabouq' AND property_type = 'land' AND listing_type = 'sale' AND price_per_m2 IS NOT NULL)
)
```

Q: Give a price-band summary (min, median, max asking price per m2) for apartment sales in each covered submarket.
```sql
SELECT neighborhood,
       COUNT(*) AS n,
       ROUND(MIN(price_per_m2), 1) AS min_ppm2,
       ROUND(AVG(price_per_m2), 1) AS avg_ppm2,
       ROUND(MAX(price_per_m2), 1) AS max_ppm2
FROM listings
WHERE neighborhood IN ('Abdoun','Dabouq','Sweifieh','Khalda','Shmeisani')
  AND property_type = 'apartment' AND listing_type = 'sale'
  AND price_per_m2 IS NOT NULL
GROUP BY neighborhood
ORDER BY avg_ppm2 DESC
```
