// THE UI DATA CONTRACT (reverse/contract-first build).
// The fresh UI is built against THESE shapes with mock data (see mock.ts). The backend
// adapter later maps the real engine output → these shapes, so the UI never changes.
// Shapes are intentionally plain and decision-first (what each view needs, nothing more).

import type { ViewKey } from "./store";
export type { ViewKey };

export type ConfidenceWord = "Strong" | "Good" | "Fair" | "Low";
export type LaunchStatus = "READY" | "WAIT" | "REVIEW";

/** The core per-area summary — drives the map card, the decision banner and Pricing. */
export interface AreaSummary {
  name: string;
  status: LaunchStatus;          // READY / WAIT / REVIEW
  price: number;                 // recommended launch price, JD/m²
  minSafe: number;               // safe floor, JD/m²
  premium: number;               // premium ceiling, JD/m²
  confidence: ConfidenceWord;    // one word
  confidenceDots: 1 | 2 | 3;     // 3-dot strength
  comps: number;                 // # nearby sales behind it
  trend: number[];               // last-N price points for the sparkline
  land: number;                  // most-you-can-pay-for-land, K JD/dunum
  margin: number;                // profit margin %
  amenities: { schools: number; universities: number; hospitals: number; busStops: number };
  centroid?: [number, number];   // [lng, lat] for the map
}

/** Pricing view (category: Pricing → Launch price / Comparable evidence / Price trend). */
export interface PricingData {
  summary: AreaSummary;
  reasons: { ok: boolean; text: string }[];           // why-this-price drivers (✓/✗)
  comparables: { size: number; asking: number; adjusted: number }[];
  // --- Optional depth (progressive disclosure): real adapter only, mock leaves these undefined ---
  /** Full per-factor adjustment waterfall behind the price (real evidence_objects, pct-kind only). */
  waterfall?: { factor: string; pct: number; positive: boolean }[];
  /** Deduped source list backing the evidence, ordered Official > Institutional > Portal. */
  evidence?: { name: string; url?: string; date?: string; what?: string }[];
  /** Sub-scores behind the headline confidence word (data coverage, comp quality, ...). */
  confidenceBreakdown?: { label: string; score: number; reason?: string }[];
  /** Risk factors flagged by the engine, with severity. */
  risks?: { factor: string; severity: "high" | "medium" | "low"; detail: string }[];
  /** One-paragraph plain-language summary of the pricing decision. */
  narrative?: string;
}

/** One of the 3 launch scenarios (Minimum-safe / Recommended / Premium launch). */
export interface LaunchScenario { name: string; price: number; rationale: string }

/** One structural buildability checklist row (Zoning, Slope, Soil, Access, Utilities...). */
export interface BuildabilityItem {
  label: string;
  status: "ok" | "partial" | "caution" | "risk" | "unknown"; // unknown = "Awaiting data — not yet collected"
  reason: string;
}

/** Cost & Profit view (Land value / Profit margin / Build cost / Scenarios / Buildability). */
export interface CostProfitData {
  landValueK: number;            // K JD / dunum
  marginPct: number;             // %
  buildCostJdM2: number;         // JD/m²
  finish: "Basic" | "Standard" | "Luxury";
  plotSizeDunum: number;
  // --- Optional depth (progressive disclosure): real adapter only, mock leaves these undefined ---
  /** The 3 launch scenarios (min-safe / recommended / premium), each with a plain-language rationale. */
  scenarios?: LaunchScenario[];
  /** Honest structural checklist — "unknown" status where data isn't collected yet, never fabricated. */
  buildability?: BuildabilityItem[];
}

/** Market view (Competitors / Market news). */
export interface MarketData {
  status: string;                // e.g. "Market stable"
  changesThisWeek: number;
  news: { date: string; text: string; action?: string }[];
  competitors: { name: string; price: number }[];
  trend: number[];
}

/** Location view (Amenities nearby / Infrastructure) — verdicts, not raw counts. */
export interface LocationData {
  verdicts: { tag: "good" | "watch"; title: string; subtitle: string }[];
  infrastructure: { when: string; text: string }[];
}

/** Everything the shell needs for one selected area. The adapter fills this from the engine. */
export interface AreaBundle {
  summary: AreaSummary;
  pricing: PricingData;
  costProfit: CostProfitData;
  market: MarketData;
  location: LocationData;
}

/** List item for the search dropdown + the map pins. */
export interface AreaListItem { name: string; price: number; centroid: [number, number]; }

/** Opportunity view (nationwide "where to build" ranking) — assembled client-side from
 *  useOpportunity()/useAreas() (lib/useEngine.ts), not a DataSource method (no per-area
 *  selection required — see views/OpportunityView.tsx). */
export interface OpportunityData {
  areas: { name: string; score: number; price: number }[];
  selectedScore?: number;
  selectedRank?: number;
}

/** The subject unit the developer is pricing — the customisable inputs to /recommend.
 *  Deliberately minimal: the four levers a builder actually sets at launch. */
export interface Subject {
  area_m2: number;                               // unit size
  bedrooms: number;
  floor_level: number;
  finish_quality: "basic" | "standard" | "high"; // engine's finish tiers
}

/** The representative unit priced when the developer hasn't customised anything. */
export const DEFAULT_SUBJECT: Subject = { area_m2: 175, bedrooms: 3, floor_level: 4, finish_quality: "high" };

/** The data source the UI consumes. Mock now; real adapter later — same interface. */
export interface DataSource {
  listAreas(): AreaListItem[];
  getBundle(area: string): AreaBundle | null;
  /**
   * Additive, optional (mock doesn't implement it): kicks off an async fetch+cache
   * for `area` so a later synchronous getBundle() call can return it. Safe to call
   * repeatedly — implementations must dedupe in-flight/cached work.
   */
  prefetch?(area: string): Promise<void>;
  /** Additive, optional: true once prefetch(area) has resolved and cached data. */
  ready?(area: string): boolean;
  /**
   * Additive, optional (mock ignores it): sets the subject unit fed to /recommend.
   * Clears cached bundles when the subject actually changes so the next
   * prefetch(area) reprices against the new unit.
   */
  setSubject?(subject: Subject): void;
}

/** Which nav categories/subcategories exist (single source of truth for the sidebar). */
export interface NavSub { key: ViewKey; label: string }
export interface NavGroup { icon: string; label: string; subs: NavSub[] }
export const NAV: NavGroup[] = [
  { icon: "🎯", label: "Opportunity", subs: [
    { key: "opportunity", label: "Where to build" }, { key: "ranking", label: "Area ranking" } ] },
  { icon: "🏷️", label: "Pricing", subs: [
    { key: "price", label: "Launch price" }, { key: "comps", label: "Comparable evidence" }, { key: "trend", label: "Price trend" },
    { key: "sell", label: "Value my property" } ] },
  { icon: "💰", label: "Cost & Profit", subs: [
    { key: "land", label: "Land value" }, { key: "margin", label: "Profit margin" }, { key: "build", label: "Build cost" },
    { key: "scenarios", label: "Launch scenarios" }, { key: "buildability", label: "Buildability" } ] },
  { icon: "📊", label: "Market", subs: [
    { key: "competitors", label: "Competitors" }, { key: "news", label: "Market news" } ] },
  { icon: "🗺️", label: "Location", subs: [
    { key: "nearby", label: "Amenities nearby" }, { key: "infra", label: "Infrastructure" } ] },
];
