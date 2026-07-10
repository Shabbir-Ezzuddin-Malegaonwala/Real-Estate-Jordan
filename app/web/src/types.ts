// Contract shared with the Decision Engine. The engine emits a
// RecommendationResult per selected location; the app also accepts a
// RecommendationBundle (a keyed map of results) for the 5-submarket demo.
// See MASTER-PLAN.md §2d (Evidence objects), §2d-2 (Decision Engine),
// §2e (Current State vs Future Signals), §2f (V1 success criteria).

export type EvidenceCategory = "current_state" | "future_signal";
export type ConfidenceLevel = "High" | "Medium" | "Low";
export type Direction = "increase" | "decrease" | "neutral";
export type Severity = "high" | "medium" | "low";

export interface EvidenceSource {
  name: string;
  url: string;
  capture_date: string; // ISO date
}

// How an evidence adjustment reads on the waterfall:
//  - "pct"        a market-derived percentage premium/discount (view, floor…)
//  - "anchor"     an absolute JD/m² cross-check (cost floor, income ceiling…)
//  - "positioning" a future signal that positions rather than moves today's band
export type EvidenceKind = "pct" | "anchor" | "positioning" | "context";

export interface EvidenceObject {
  factor: string; // e.g. "Panoramic / open view"
  adjustment: string; // display string as emitted by the engine, e.g. "+9.0%" / "550 JD/m²"
  adjustment_pct: number; // signed decimal for "pct" rows (0 for anchors)
  direction: Direction;
  confidence: ConfidenceLevel;
  method: string; // e.g. "paired listing comparison (n=16)"
  datasets: string[]; // e.g. ["listings"]
  sources: EvidenceSource[];
  category: EvidenceCategory;
  explanation: string;
  kind?: EvidenceKind; // defaults to "pct" for legacy/mock data
  per_unit?: boolean; // adjustment is per unit of the factor (e.g. per floor)
  expected_year?: number | null; // future_signal only
  impact_area?: string | null; // future_signal only
}

// One market adjustment applied to a single comparable to normalise it to the
// subject (only present on real-engine comparables).
export interface CompAdjustment {
  factor: string;
  adjustment: string; // e.g. "+4.9%"
  method: string;
  detail?: string;
}

export interface Comparable {
  id: string;
  portal: string;
  neighborhood: string;
  price_jd: number;
  area_m2: number;
  price_per_m2: number; // the comp's normalised (adjusted) price/m²
  bedrooms: number | null;
  bathrooms?: number | null;
  floor_level: number | null;
  view: string;
  parking?: string;
  building_age_years: number | null;
  seller_type: string;
  url: string;
  capture_date: string;
  distance_km: number;
  similarity: number; // 0..1
  lat?: number | null;
  lng?: number | null;
  // Real-engine reconciliation detail (absent on illustrative mock comps):
  original_ppm2?: number | null;
  adjusted_ppm2?: number | null;
  gross_adjustment?: number | null; // net |adjustment| as a fraction
  listing_date?: string | null;
  adjustments?: CompAdjustment[];
}

export interface RiskFactor {
  title: string;
  severity: Severity;
  detail: string;
}

export interface Confidence {
  level: ConfidenceLevel;
  score: number; // 0..100
  range_low: number; // JD/m²
  range_high: number; // JD/m²
  drivers: string[];
}

export interface RecommendationResult {
  neighborhood: string;
  name_ar?: string;
  tier?: string;
  property_type: string;
  as_of: string; // ISO date
  currency: string; // "JOD"
  unit: string; // "JD/m²"
  base_value_jd_m2: number;
  min_safe_jd_m2: number;
  recommended_jd_m2: number;
  premium_jd_m2: number;
  confidence: Confidence;
  evidence_objects: EvidenceObject[];
  comparables: Comparable[];
  risk_factors: RiskFactor[];
  narrative: string;
  centroid?: [number, number] | null; // lon, lat
  is_live?: boolean; // true = real Decision-Engine output; false/undefined = illustrative placeholder
  source_note?: string; // provenance line shown under the header (e.g. synthetic-fixture engine run)
  comps_considered?: number; // total comps the engine weighed (may exceed comparables.length shown)
}

export interface RecommendationBundle {
  generated_at: string;
  engine_version: string;
  disclaimer: string;
  currency: string;
  unit: string;
  results: Record<string, RecommendationResult>;
}

// GeoJSON property shapes actually present in the processed data ----------
export interface NeighborhoodProps {
  neighborhood: string;
  name_ar: string;
  approximate: boolean;
  radius_km: number;
}
export interface PoiProps {
  poi_id: string;
  category: string;
  name: string;
  name_ar: string;
  neighborhood: string;
}
export interface RoadProps {
  name: string;
  name_ar: string;
  highway: string;
  ref: string;
}
export interface ZoningProps {
  type: string; // OSM landuse class: residential, farmland, orchard, industrial…
  name: string;
  authenticity: string; // carries the "unofficial OSM landuse, not GAM zoning" caveat
}

export const POI_CATEGORIES = [
  "mosque",
  "school",
  "park",
  "hospital",
  "mall",
  "university",
  "transport",
] as const;
export type PoiCategory = (typeof POI_CATEGORIES)[number];
