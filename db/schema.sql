-- Jordan Real Estate Intelligence Platform — structured database schema
-- Authority: MASTER-PLAN.md §3 (FROZEN collection schema) + K-PACKET.md §5 (exact junior CSV headers).
-- Target engine: SQLite 3.31+ (generated columns). SpatiaLite optional — see init_db.py.
--
-- Conventions enforced here (single source of truth for the loader, which parses this DDL):
--   * Universal columns on every collected table: evidence_category, language.
--   * Provenance columns on every collected table: source_name, source_url, capture_date,
--     collected_by, confidence, notes.
--   * Enum CHECK lists = the EXACT master-plan enum members, plus the sentinel 'unknown'
--     (blank is rejected by the loader; 'unknown' is the only legal null-object).
--   * Dates stored as ISO-8601 TEXT (YYYY-MM-DD); SQLite has no native date type.
--   * Money in JOD as published; no currency conversion. price_per_m2 is derived, never collected.
--   * Business logic (pricing weights/premiums) lives ONLY in the engine, never in this schema.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- schema_meta — capability + version flags read by the engine/frontend
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- ===========================================================================
-- A. MARKET / PRICING
-- ===========================================================================

-- listings — sale/rent asking-price records from portals (Bayut, OpenSooq, Homes-Jordan, FB).
-- CSV header (K-PACKET Dataset 4) has NO price_per_m2; it is derived below.
CREATE TABLE IF NOT EXISTS listings (
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
CREATE INDEX IF NOT EXISTS idx_listings_neighborhood  ON listings (neighborhood);
CREATE INDEX IF NOT EXISTS idx_listings_property_type ON listings (property_type);
CREATE INDEX IF NOT EXISTS idx_listings_listing_type  ON listings (listing_type);
CREATE INDEX IF NOT EXISTS idx_listings_capture_date  ON listings (capture_date);
CREATE INDEX IF NOT EXISTS idx_listings_nbhd_type     ON listings (neighborhood, property_type, listing_type);

-- projects — competitor new-launch developments.
CREATE TABLE IF NOT EXISTS projects (
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
CREATE INDEX IF NOT EXISTS idx_projects_neighborhood ON projects (neighborhood);
CREATE INDEX IF NOT EXISTS idx_projects_status       ON projects (status);
CREATE INDEX IF NOT EXISTS idx_projects_capture_date ON projects (capture_date);

-- ===========================================================================
-- B. SPATIAL / POI
-- ===========================================================================

-- poi — points of interest (K-PACKET Dataset 5 adds the 'exists' verification flag).
CREATE TABLE IF NOT EXISTS poi (
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
CREATE INDEX IF NOT EXISTS idx_poi_category     ON poi (category);
CREATE INDEX IF NOT EXISTS idx_poi_neighborhood ON poi (neighborhood);

-- districts — neighborhood/admin boundary polygons. Geometry stored as GeoJSON text
-- (SpatiaLite fallback); centroid_lat/lng give a cheap point for mapping + haversine.
CREATE TABLE IF NOT EXISTS districts (
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
CREATE INDEX IF NOT EXISTS idx_districts_neighborhood ON districts (neighborhood);

-- zoning_plots — plot-level land-use / zoning polygons (GAM ArcGIS or OSM landuse fallback).
CREATE TABLE IF NOT EXISTS zoning_plots (
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
CREATE INDEX IF NOT EXISTS idx_zoning_neighborhood ON zoning_plots (neighborhood);
CREATE INDEX IF NOT EXISTS idx_zoning_zone_class   ON zoning_plots (zone_class);

-- ===========================================================================
-- C. OFFICIAL / MACRO
-- ===========================================================================

-- macro_series — official time series (CBJ price index, DLS volumes, DoS permits...).
CREATE TABLE IF NOT EXISTS macro_series (
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
CREATE INDEX IF NOT EXISTS idx_macro_indicator ON macro_series (indicator);
CREATE INDEX IF NOT EXISTS idx_macro_geo_period ON macro_series (geography, period);

-- ===========================================================================
-- D. SIGNALS / SUPPORTING
-- ===========================================================================

-- evidence_items — Future-Signals pipeline: infrastructure/policy/market news.
CREATE TABLE IF NOT EXISTS evidence_items (
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
CREATE INDEX IF NOT EXISTS idx_evidence_type        ON evidence_items (type);
CREATE INDEX IF NOT EXISTS idx_evidence_impact_area ON evidence_items (impact_area);

-- neighborhood_profiles — researched context for AI explanations (P2).
CREATE TABLE IF NOT EXISTS neighborhood_profiles (
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
CREATE INDEX IF NOT EXISTS idx_nprofiles_neighborhood ON neighborhood_profiles (neighborhood);

-- cost_benchmarks — construction cost per m² by finishing class (cost-approach floor).
CREATE TABLE IF NOT EXISTS cost_benchmarks (
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
CREATE INDEX IF NOT EXISTS idx_cost_spec_class ON cost_benchmarks (spec_class);

-- ===========================================================================
-- E. GEO / TERRAIN CONTEXT (friend-sourced; NON-PRICED neighborhood context)
-- ===========================================================================
-- MASTER-PLAN decision: elevation/population/night-light do NOT correlate with price
-- (analysis showed ~0, sign-unstable). These tables are QUERYABLE CONTEXT ONLY — an
-- affluence/density/activity proxy, never a price lever. Columns match the friend CSVs
-- (data/raw/friend/*.csv) exactly; provenance cites Copernicus DEM / GHS-POP / VIIRS.

-- listing_geofeatures — per-listing terrain + density + night-light sample (open rasters).
CREATE TABLE IF NOT EXISTS listing_geofeatures (
    listing_id           TEXT PRIMARY KEY,
    elevation_m          REAL,
    slope_deg            REAL,
    aspect_deg           REAL,
    aspect_cardinal      TEXT,
    population_density   REAL,
    nightlight_intensity REAL,
    source_name          TEXT NOT NULL,
    source_url           TEXT NOT NULL,
    capture_date         TEXT NOT NULL,
    collected_by         TEXT,
    confidence           TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    notes                TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- neighborhood_geocontext — one median-summary row per target submarket + a human context
-- string. Feeds the non-priced "Neighborhood spatial context" evidence chip.
CREATE TABLE IF NOT EXISTS neighborhood_geocontext (
    neighborhood              TEXT PRIMARY KEY,
    median_elevation_m        REAL,
    elevation_rank            INTEGER,
    median_population_density REAL,
    median_nightlight         REAL,
    dominant_aspect           TEXT,
    context                   TEXT,
    source_name               TEXT NOT NULL,
    source_url                TEXT NOT NULL,
    capture_date              TEXT NOT NULL,
    collected_by              TEXT,
    confidence                TEXT NOT NULL CHECK (confidence IN ('H','M','L','unknown')),
    created_at                TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ===========================================================================
-- F. ENGINE OUTPUTS (written by the Decision Engine, never collected)
-- ===========================================================================

-- derived_premiums — the Adjustment Engine writes every attribute premium here.
-- HARD RULE (MASTER-PLAN §2d-2): premiums are DERIVED from current market data and
-- recomputed; they are NEVER hardcoded constants. derived_premium is a fraction (0.08 = +8%).
CREATE TABLE IF NOT EXISTS derived_premiums (
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
CREATE INDEX IF NOT EXISTS idx_premiums_factor ON derived_premiums (factor);
CREATE INDEX IF NOT EXISTS idx_premiums_nbhd   ON derived_premiums (neighborhood, property_type);

-- recommendations — persisted Decision-Engine output (RecommendationResult contract).
-- Scalar outputs are first-class columns; nested arrays are JSON blobs (see docs/db-contract.md).
CREATE TABLE IF NOT EXISTS recommendations (
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
CREATE INDEX IF NOT EXISTS idx_recommendations_neighborhood ON recommendations (neighborhood);
CREATE INDEX IF NOT EXISTS idx_recommendations_location     ON recommendations (location_id);
