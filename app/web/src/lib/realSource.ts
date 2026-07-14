// Real-engine adapter fulfilling the same DataSource contract mock.ts fulfils
// with fixtures (see contract.ts). Reuses the existing engine clients verbatim
// (api.ts / intel.ts / adaptEngine.ts / loadData.ts) — no new network paths.
//
// getBundle() must be synchronous per the contract, but every real value comes
// from async endpoints. Resolved with a cache: listAreas() reads a cache primed
// once via primeAreas() (see dataSource.ts, called before first paint so the
// list is never empty on mount); getBundle() reads a per-area cache populated
// by prefetch(area), which callers trigger on selection (see store.tsx).
import type {
  AreaBundle,
  AreaListItem,
  AreaSummary,
  ConfidenceWord,
  CostProfitData,
  LocationData,
  MarketData,
  PricingData,
} from "./contract";
import { fetchNeighborhoods, requestRecommendation, type SubjectInput } from "./api";
import { fetchAreas, fetchAreaMonitoring, requestResidual } from "./intel";
import { adaptApiRecommendation } from "./adaptEngine";
import { loadAmenities } from "./loadData";
import type { AreaAmenities } from "./poi";
import type { AreaEntry, AreaMonitoring, RecommendationResult, ResidualBreakdown } from "../types";

// Matches lib/useEngine.ts's DEFAULT_SUBJECT — the representative unit priced
// when the caller hasn't customised it (kept identical so results agree).
const ENGINE_SUBJECT: Omit<SubjectInput, "neighborhood"> = {
  area_m2: 175,
  bedrooms: 3,
  floor_level: 4,
  building_age_years: 0,
  view: "unknown",
  parking: "unknown",
  finish_quality: "high",
};

// Matches components/ResidualLandValue.tsx's defaults (the engine's own
// professional-fees-on-construction convention, 5%).
const RESIDUAL_DEFAULTS = {
  buildable_area_m2: 2000,
  construction_cost_per_m2: 450,
  finance_pct: 6,
  fees_pct: 5,
  profit_pct: 20,
};

let areaListCache: AreaListItem[] = [];
const centroidCache = new Map<string, [number, number]>();
let amenitiesCache: Record<string, AreaAmenities> = {};
const bundleCache = new Map<string, AreaBundle>();
const inflight = new Map<string, Promise<void>>();

// --- priming (called once, before first paint — see dataSource.ts) ---------

// Only areas the engine can actually price are listed — real /areas also
// returns hundreds of context-only cells nationwide, which would blow up the
// map/search built for a handful of pins. Filtering to `covered` keeps the
// list the same shape/size the UI was built against.
export async function primeAreas(): Promise<AreaListItem[]> {
  const [neighborhoods, amenities] = await Promise.all([
    fetchNeighborhoods().catch(() => []),
    loadAmenities().catch(() => ({})),
  ]);
  amenitiesCache = amenities;

  const fallback: AreaEntry[] = neighborhoods.map((n) => ({
    name: n.name,
    covered: true,
    context: false,
    listing_count: n.listing_count,
    median_price_per_m2: n.median_price_per_m2,
    centroid_lat: n.centroid_lat,
    centroid_lng: n.centroid_lng,
  }));

  const areas = await fetchAreas(fallback);
  const covered = areas.filter(
    (a) =>
      a.covered &&
      typeof a.median_price_per_m2 === "number" &&
      typeof a.centroid_lat === "number" &&
      typeof a.centroid_lng === "number",
  );

  centroidCache.clear();
  areaListCache = covered.map((a) => {
    const centroid: [number, number] = [a.centroid_lng as number, a.centroid_lat as number];
    centroidCache.set(a.name, centroid);
    return { name: a.name, price: Math.round(a.median_price_per_m2 as number), centroid };
  });
  return areaListCache;
}

export function listAreas(): AreaListItem[] {
  return areaListCache;
}

export function getBundle(area: string): AreaBundle | null {
  return bundleCache.get(area) ?? null;
}

export function ready(area: string): boolean {
  return bundleCache.has(area);
}

export function prefetch(area: string): Promise<void> {
  if (bundleCache.has(area)) return Promise.resolve();
  const existing = inflight.get(area);
  if (existing) return existing;
  const p = buildBundle(area)
    .then((bundle) => {
      if (bundle) bundleCache.set(area, bundle);
    })
    .finally(() => inflight.delete(area));
  inflight.set(area, p);
  return p;
}

// --- mapping: real engine output -> the UI's plain contract shapes ---------

function confidenceWord(level: RecommendationResult["confidence"]["level"]): { word: ConfidenceWord; dots: 1 | 2 | 3 } {
  if (level === "High") return { word: "Strong", dots: 3 };
  if (level === "Medium") return { word: "Good", dots: 2 };
  return { word: "Fair", dots: 1 };
}

function toSummary(area: string, r: RecommendationResult, trend: number[]): AreaSummary {
  const { word, dots } = confidenceWord(r.confidence.level);
  const a = amenitiesCache[area];
  return {
    name: area,
    status: r.confidence.level === "Low" ? "REVIEW" : "READY",
    price: Math.round(r.recommended_jd_m2),
    minSafe: Math.round(r.min_safe_jd_m2),
    premium: Math.round(r.premium_jd_m2),
    confidence: word,
    confidenceDots: dots,
    comps: r.comps_considered ?? r.comparables.length,
    trend,
    land: 0, // filled in by toBundle once the residual value is known
    margin: 0, // filled in by toBundle
    amenities: {
      schools: a?.schools_n ?? 0,
      universities: a?.universities_n ?? 0,
      hospitals: a?.hospitals_n ?? 0,
      busStops: a?.transport_n ?? 0, // closest real proxy — engine has no bus-stop-only count
    },
    centroid: centroidCache.get(area),
  };
}

function toPricing(summary: AreaSummary, r: RecommendationResult): PricingData {
  const pctEvidence = r.evidence_objects.filter((e) => (e.kind ?? "pct") === "pct");
  const rows = (pctEvidence.length > 0 ? pctEvidence : r.evidence_objects).slice(0, 5);
  const reasons = rows.map((e) => ({
    ok: e.direction !== "decrease",
    text: `${e.factor} (${e.adjustment})`,
  }));
  const comparables = r.comparables.slice(0, 5).map((c) => ({
    size: Math.round(c.area_m2),
    asking: Math.round(c.original_ppm2 ?? c.price_per_m2),
    adjusted: Math.round(c.adjusted_ppm2 ?? c.price_per_m2),
  }));
  return { summary, reasons, comparables };
}

function toCostProfit(residual: ResidualBreakdown | null): CostProfitData {
  return {
    landValueK: residual ? Math.round(residual.max_land_value_per_m2) : 0,
    marginPct: RESIDUAL_DEFAULTS.profit_pct,
    buildCostJdM2: RESIDUAL_DEFAULTS.construction_cost_per_m2,
    finish: "Standard",
    plotSizeDunum: RESIDUAL_DEFAULTS.buildable_area_m2 / 1000,
  };
}

function toMarket(monitoring: AreaMonitoring | null, trend: number[]): MarketData {
  const rank = monitoring?.price_rank;
  const status = !rank
    ? "Market data pending"
    : rank.percentile >= 66
      ? "Market strong"
      : rank.percentile <= 33
        ? "Market soft"
        : "Market stable";
  const competitors = (monitoring?.peers ?? [])
    .filter((p) => !p.is_selected)
    .slice(0, 3)
    .map((p) => ({ name: p.name, price: Math.round(p.median_price) }));
  return {
    status,
    changesThisWeek: 0, // no live "changes this week" feed yet — honestly 0, not fabricated
    news: [], // no market-news endpoint wired to a single area yet
    competitors,
    trend,
  };
}

function toLocation(area: string): LocationData {
  const a = amenitiesCache[area];
  if (!a) return { verdicts: [], infrastructure: [] };
  const verdicts: LocationData["verdicts"] = [
    a.schools_n + a.universities_n > 0
      ? { tag: "good", title: "Education", subtitle: `${a.schools_n} schools + ${a.universities_n} universities nearby.` }
      : { tag: "watch", title: "Education", subtitle: "No schools or universities recorded nearby." },
    a.hospitals_n >= 1
      ? { tag: "good", title: "Healthcare", subtitle: `${a.hospitals_n} hospital(s) nearby.` }
      : { tag: "watch", title: "Healthcare", subtitle: "No hospital recorded nearby." },
    a.transport_n > 0
      ? { tag: "good", title: "Transport", subtitle: `${a.transport_n} transport stop(s) nearby.` }
      : { tag: "watch", title: "Transport", subtitle: "No transport stops recorded nearby." },
  ];
  return { verdicts, infrastructure: [] }; // infrastructure timeline not yet wired to a live endpoint
}

async function buildBundle(area: string): Promise<AreaBundle | null> {
  let result: RecommendationResult;
  try {
    const raw = await requestRecommendation({ ...ENGINE_SUBJECT, neighborhood: area });
    result = adaptApiRecommendation(raw, "Live API · computed on demand");
  } catch {
    return null;
  }

  const [residual, monitoring] = await Promise.all([
    requestResidual({ neighborhood: area, ...RESIDUAL_DEFAULTS }, result.recommended_jd_m2).catch(() => null),
    fetchAreaMonitoring(area).catch(() => null),
  ]);

  const trend = monitoring && monitoring.yearly_median.length > 1
    ? monitoring.yearly_median.map((y) => Math.round(y.median))
    : [Math.round(result.recommended_jd_m2), Math.round(result.recommended_jd_m2)];

  const summary = toSummary(area, result, trend);
  if (residual) summary.land = Math.round(residual.max_land_value_per_m2);
  summary.margin = RESIDUAL_DEFAULTS.profit_pct;

  return {
    summary,
    pricing: toPricing(summary, result),
    costProfit: toCostProfit(residual),
    market: toMarket(monitoring, trend),
    location: toLocation(area),
  };
}
