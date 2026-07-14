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
}

/** Cost & Profit view (Land value / Profit margin / Build cost). */
export interface CostProfitData {
  landValueK: number;            // K JD / dunum
  marginPct: number;             // %
  buildCostJdM2: number;         // JD/m²
  finish: "Basic" | "Standard" | "Luxury";
  plotSizeDunum: number;
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

/** The data source the UI consumes. Mock now; real adapter later — same interface. */
export interface DataSource {
  listAreas(): AreaListItem[];
  getBundle(area: string): AreaBundle | null;
}

/** Which nav categories/subcategories exist (single source of truth for the sidebar). */
export interface NavSub { key: ViewKey; label: string }
export interface NavGroup { icon: string; label: string; subs: NavSub[] }
export const NAV: NavGroup[] = [
  { icon: "🏷️", label: "Pricing", subs: [
    { key: "price", label: "Launch price" }, { key: "comps", label: "Comparable evidence" }, { key: "trend", label: "Price trend" } ] },
  { icon: "💰", label: "Cost & Profit", subs: [
    { key: "land", label: "Land value" }, { key: "margin", label: "Profit margin" }, { key: "build", label: "Build cost" } ] },
  { icon: "📊", label: "Market", subs: [
    { key: "competitors", label: "Competitors" }, { key: "news", label: "Market news" } ] },
  { icon: "🗺️", label: "Location", subs: [
    { key: "nearby", label: "Amenities nearby" }, { key: "infra", label: "Infrastructure" } ] },
];
