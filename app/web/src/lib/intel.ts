// Client for the intelligence-platform endpoints (built in parallel by the
// backend agent). Every call tries the live endpoint first and, if it is not yet
// deployed or errors, falls back to a transparent LOCAL computation tagged
// `source: "local"` so the UI can label it honestly. No fallback fabricates a
// number the user can't trace — residual value and scenario deltas are
// deterministic formulae; opportunity is a stated heuristic over real counts.
import { API_BASE } from "./api";
import type {
  AreaEntry,
  Confidence,
  ConfidenceComponent,
  OpportunityComponents,
  OpportunityScore,
  RecommendationResult,
  ResidualBreakdown,
  ResidualInputs,
  ScenarioBand,
  ScenarioOverrides,
  ScenarioResult,
} from "../types";

function timeout(ms: number): AbortSignal {
  return AbortSignal.timeout(ms);
}

// The new endpoints double-encode UTF-8 (² → "Â²", → → "â†'"). Defensive repair
// that only fires when the tell-tale bytes are present, so correct strings pass
// through untouched. (Reported upstream — remove once the backend fixes it.)
export function fixText(s: string): string {
  if (typeof s !== "string" || !/[ÃÂâ]/.test(s)) return s;
  try {
    return decodeURIComponent(escape(s));
  } catch {
    return s;
  }
}

async function tryGet<T>(path: string, ms = 4000): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { signal: timeout(ms) });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function tryPost<T>(path: string, body: unknown, ms = 12000): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: timeout(ms),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// --- Decomposed confidence --------------------------------------------------

export const COMPONENT_ORDER = [
  "data_coverage",
  "comp_quality",
  "gov_evidence",
  "future_signals",
  "market_freshness",
] as const;

export const COMPONENT_LABELS: Record<string, string> = {
  data_coverage: "Data coverage",
  comp_quality: "Comparable quality",
  gov_evidence: "Official evidence",
  future_signals: "Future signals",
  market_freshness: "Market freshness",
};

// Returns the 5 decomposed bars. Uses the engine's own components when present;
// otherwise derives an honest local estimate from what the result already tells
// us (comps considered, evidence mix, band width) — clearly a `local` estimate.
export function confidenceComponents(r: RecommendationResult): {
  components: ConfidenceComponent[];
  source: "live" | "local";
} {
  if (r.confidence.components && r.confidence.components.length > 0) {
    return { components: r.confidence.components, source: "live" };
  }

  const comps = r.comps_considered ?? r.comparables.length;
  const govCount = r.evidence_objects.filter((e) =>
    e.datasets.some((d) => /cbj|dos|dls|gam|official|permit|index/i.test(d)),
  ).length;
  const futureCount = r.evidence_objects.filter((e) => e.category === "future_signal").length;
  const bandWidth =
    r.recommended_jd_m2 > 0
      ? (r.confidence.range_high - r.confidence.range_low) / r.recommended_jd_m2
      : 1;

  const clamp = (n: number) => Math.max(0, Math.min(100, Math.round(n)));
  const components: ConfidenceComponent[] = [
    {
      key: "data_coverage",
      label: COMPONENT_LABELS.data_coverage,
      score: clamp(Math.min(100, comps * 4)),
      reason: `${comps} comparables weighed for this submarket`,
    },
    {
      key: "comp_quality",
      label: COMPONENT_LABELS.comp_quality,
      score: clamp(100 - bandWidth * 90),
      reason:
        bandWidth > 0.5
          ? "wide evidenced band — comps disperse"
          : "tight band — comparable prices agree",
    },
    {
      key: "gov_evidence",
      label: COMPONENT_LABELS.gov_evidence,
      score: clamp(govCount > 0 ? 40 + govCount * 20 : 25),
      reason:
        govCount > 0
          ? `${govCount} official/index cross-check${govCount > 1 ? "s" : ""} applied`
          : "asking-price portals only — official cross-checks pending",
    },
    {
      key: "future_signals",
      label: COMPONENT_LABELS.future_signals,
      score: clamp(futureCount > 0 ? 45 + futureCount * 18 : 20),
      reason:
        futureCount > 0
          ? `${futureCount} forward signal${futureCount > 1 ? "s" : ""} collected`
          : "no infrastructure/policy signals collected yet",
    },
    {
      key: "market_freshness",
      label: COMPONENT_LABELS.market_freshness,
      score: clamp(r.as_of ? 70 : 50),
      reason: r.as_of ? `computed ${r.as_of}` : "recency of underlying listings",
    },
  ];
  return { components, source: "local" };
}

// --- Areas (GET /areas) -----------------------------------------------------

// Live shape: { covered_count, total_count, areas: [{ name, covered,
// listing_count, sale_listing_count, centroid_lat, centroid_lng }] }. Medians
// aren't on /areas, so they're merged in from the /neighborhoods-derived
// fallback where names match.
export async function fetchAreas(fallback: AreaEntry[]): Promise<AreaEntry[]> {
  const live = await tryGet<{ areas?: unknown } | unknown[]>("/areas");
  const rows = Array.isArray(live) ? live : (live as { areas?: unknown })?.areas;
  if (!Array.isArray(rows) || rows.length === 0) return fallback;

  const medians = new Map(fallback.map((a) => [a.name, a.median_price_per_m2]));
  return (rows as Record<string, unknown>[]).map((a) => {
    const name = fixText(String(a.name ?? ""));
    const covered = Boolean(a.covered);
    return {
      name,
      name_ar: a.name_ar ? fixText(String(a.name_ar)) : undefined,
      covered,
      context: !covered,
      listing_count: typeof a.listing_count === "number" ? a.listing_count : undefined,
      sale_listing_count: typeof a.sale_listing_count === "number" ? a.sale_listing_count : undefined,
      median_price_per_m2:
        typeof a.median_price_per_m2 === "number" ? a.median_price_per_m2 : medians.get(name),
      centroid_lat: typeof a.centroid_lat === "number" ? a.centroid_lat : undefined,
      centroid_lng: typeof a.centroid_lng === "number" ? a.centroid_lng : undefined,
    };
  });
}

// --- Opportunity (GET /opportunity) -----------------------------------------

function pctRank(value: number, all: number[]): number {
  const valid = all.filter((v) => Number.isFinite(v) && v > 0);
  if (valid.length <= 1) return 50;
  const below = valid.filter((v) => v < value).length;
  return Math.round((below / (valid.length - 1)) * 100);
}

// Local opportunity heuristic over REAL portal counts + medians. Stated openly:
// higher price level = higher GDV headroom; higher sale demand = absorption;
// lower active-supply = less competition. Growth + future signals stay neutral
// (50) until the backend attaches DLS trend + infrastructure evidence.
export function localOpportunity(areas: AreaEntry[]): OpportunityScore[] {
  const prices = areas.map((a) => a.median_price_per_m2 ?? 0);
  const demand = areas.map((a) => a.sale_listing_count ?? 0);
  const supply = areas.map((a) => a.listing_count ?? 0);

  return areas
    .filter((a) => a.covered || (a.median_price_per_m2 ?? 0) > 0)
    .map((a) => {
      const price_level = pctRank(a.median_price_per_m2 ?? 0, prices);
      const demand_density = pctRank(a.sale_listing_count ?? 0, demand);
      const supply_pressure = 100 - pctRank(a.listing_count ?? 0, supply);
      const price_growth = 50;
      const future_signals = 50;
      const score = Math.round(
        price_level * 0.3 +
          demand_density * 0.25 +
          supply_pressure * 0.15 +
          price_growth * 0.15 +
          future_signals * 0.15,
      );
      return {
        area: a.name,
        score,
        components: { price_level, price_growth, demand_density, supply_pressure, future_signals },
        covered: a.covered,
        reason: "Local heuristic over portal counts — growth & future signals pending backend.",
        source: "local" as const,
      };
    })
    .sort((x, y) => y.score - x.score);
}

const OPP_KEYS: (keyof OpportunityComponents)[] = [
  "price_level",
  "price_growth",
  "demand_density",
  "supply_pressure",
  "future_signals",
];

// Below this listing count an area's opportunity is noise, not signal — the
// supply-scarcity driver inflates thin cells. Such cells are muted on the map
// and flagged in the panel, never presented as ranked build opportunities.
export const LOW_N_THRESHOLD = 10;

// Parses the baked 290-cell heatmap geojson into panel-ready scores. Flat
// numeric components; `growth` maps to price_growth. Carries listing_count as
// the confidence signal + the low_data flag.
export function heatmapToOpportunity(fc: {
  features?: { properties?: Record<string, unknown> | null }[];
}): OpportunityScore[] {
  const feats = fc.features ?? [];
  return feats
    .map((f) => {
      const p = f.properties ?? {};
      const n = typeof p.listing_count === "number" ? p.listing_count : 0;
      const low_data = n < LOW_N_THRESHOLD;
      const num = (v: unknown) => Math.round(Number(v ?? 0));
      const reasons: Partial<Record<keyof OpportunityComponents, string>> = {};
      if (low_data) reasons.supply_pressure = `only ${n} listing${n === 1 ? "" : "s"} — scarcity is noise here`;
      return {
        area: fixText(String(p.neighborhood ?? "")),
        score: num(p.score),
        components: {
          price_level: num(p.price_level),
          price_growth: num(p.growth),
          demand_density: num(p.demand_density),
          supply_pressure: num(p.supply_pressure),
          future_signals: num(p.future_signals),
        },
        component_reasons: reasons,
        covered: Boolean(p.is_covered),
        listing_count: n,
        low_data,
        governorate: p.governorate ? String(p.governorate) : undefined,
        reason: low_data
          ? `Low data (${n} listing${n === 1 ? "" : "s"}) — shown for context, not ranked as an opportunity.`
          : undefined,
        source: "heatmap" as const,
      };
    })
    .filter((o) => o.area.length > 0);
}

// Merges the baked heatmap (all 290 cells, gap-free) with the live engine
// opportunity (the 5 covered areas, richer reasons). Live overrides the covered
// cells; listing_count is carried across so low-n muting still applies. Sort
// keeps trustworthy high-n areas on top and pushes low-data cells to the bottom.
export async function fetchOpportunity(
  areas: AreaEntry[],
  heatmap?: { features?: { properties?: Record<string, unknown> | null }[] } | null,
): Promise<OpportunityScore[]> {
  const base = heatmap ? heatmapToOpportunity(heatmap) : localOpportunity(areas);
  const byName = new Map(base.map((o) => [o.area, o]));

  const live = await tryGet<{ areas?: unknown }>("/opportunity");
  const rows = (live as { areas?: unknown })?.areas;
  if (Array.isArray(rows)) {
    for (const o of rows as Record<string, unknown>[]) {
      const rawComp = (o.components ?? {}) as Record<string, { score?: number; reason?: string }>;
      const components = {} as OpportunityComponents;
      const component_reasons: Partial<Record<keyof OpportunityComponents, string>> = {};
      for (const k of OPP_KEYS) {
        components[k] = Math.round(rawComp[k]?.score ?? 0);
        if (rawComp[k]?.reason) component_reasons[k] = fixText(rawComp[k].reason as string);
      }
      const area = fixText(String(o.area ?? ""));
      const prior = byName.get(area);
      byName.set(area, {
        area,
        score: Math.round(Number(o.score ?? prior?.score ?? 0)),
        components,
        component_reasons,
        covered: true,
        reason: o.reason ? fixText(String(o.reason)) : undefined,
        listing_count: prior?.listing_count,
        low_data: prior?.low_data ?? false,
        governorate: prior?.governorate,
        source: "live",
      });
    }
  }

  return [...byName.values()].sort(
    (x, y) => Number(!!x.low_data) - Number(!!y.low_data) || y.score - x.score,
  );
}

// --- Scenario (POST /scenario) ----------------------------------------------

function bandOf(r: RecommendationResult): ScenarioBand {
  return {
    min_safe_jd_m2: r.min_safe_jd_m2,
    recommended_jd_m2: r.recommended_jd_m2,
    premium_jd_m2: r.premium_jd_m2,
  };
}

const FINISH_PREMIUM: Record<string, number> = {
  basic: -0.06,
  standard: 0,
  high: 0.08,
  luxury: 0.16,
};

// Deterministic local what-if. Builder-configurable premiums (floor→city-view,
// finish) are explicit assumptions, NOT derived from asking-price listings —
// exactly the engine limit called out in the briefing. Every lever contributes a
// labelled, signed delta so the total is fully traceable.
export function localScenario(
  r: RecommendationResult,
  ov: ScenarioOverrides,
): ScenarioResult {
  const base = bandOf(r);
  const deltas: ScenarioResult["deltas"] = [];

  if (ov.apply_height_view_premium && ov.target_floor != null && ov.floors != null && ov.floors > 0) {
    // Builder assumption: city-view premium grows with height, capped near the top.
    const frac = Math.min(1, ov.target_floor / ov.floors);
    const premium = +(frac * 0.12).toFixed(4); // up to +12% at the top floor
    if (premium > 0)
      deltas.push({
        label: `City-view premium · floor ${ov.target_floor}/${ov.floors}`,
        delta_pct: premium,
        detail: "Builder assumption (not derived from asking-price listings): higher floor → city view.",
      });
  }

  if (ov.finish && ov.finish in FINISH_PREMIUM && FINISH_PREMIUM[ov.finish] !== 0) {
    deltas.push({
      label: `Finish · ${ov.finish}`,
      delta_pct: FINISH_PREMIUM[ov.finish],
      detail: "Builder finish premium (configurable assumption).",
    });
  }

  if (ov.construction_cost_delta_pct) {
    // Cost rise compresses the achievable margin → modest downward pressure on
    // the defensible launch (roughly a third of the cost move passes through).
    const d = -(ov.construction_cost_delta_pct / 100) * 0.35;
    deltas.push({
      label: `Construction cost ${ov.construction_cost_delta_pct > 0 ? "+" : ""}${ov.construction_cost_delta_pct}%`,
      delta_pct: +d.toFixed(4),
      detail: "Higher build cost erodes margin; ~35% passes to the defensible launch.",
    });
  }

  if (ov.metro_delay_years && ov.metro_delay_years > 0) {
    const d = -Math.min(0.05, ov.metro_delay_years * 0.015);
    deltas.push({
      label: `Metro delayed ${ov.metro_delay_years} yr`,
      delta_pct: +d.toFixed(4),
      detail: "Deferred infrastructure discounts the forward-signal premium.",
    });
  }

  if (ov.launch_delay_months && ov.launch_delay_months > 0) {
    // Carrying cost of a later launch — small, time-proportional.
    const d = -(ov.launch_delay_months / 12) * 0.02;
    deltas.push({
      label: `Launch delayed ${ov.launch_delay_months} mo`,
      delta_pct: +d.toFixed(4),
      detail: "Holding/finance carry over the delay window.",
    });
  }

  const net = deltas.reduce((a, d) => a + d.delta_pct, 0);
  const scale = (v: number) => Math.round(v * (1 + net));
  const scenario: ScenarioBand = {
    min_safe_jd_m2: scale(base.min_safe_jd_m2),
    recommended_jd_m2: scale(base.recommended_jd_m2),
    premium_jd_m2: scale(base.premium_jd_m2),
  };

  const explanation =
    deltas.length === 0
      ? "No levers applied — scenario equals the base recommendation."
      : `Net effect ${net >= 0 ? "+" : "−"}${Math.abs(net * 100).toFixed(1)}% on the defensible launch, from ${deltas.length} lever${deltas.length > 1 ? "s" : ""}. Builder premiums are stated assumptions, not listing-derived.`;

  return { base, scenario, deltas, explanation, source: "local" };
}

interface LiveBand {
  min_safe_price_jd_m2?: number;
  recommended_price_jd_m2?: number;
  premium_price_jd_m2?: number;
}
function adaptLiveBand(b: LiveBand | undefined, fallback: ScenarioBand): ScenarioBand {
  if (!b) return fallback;
  return {
    min_safe_jd_m2: Math.round(b.min_safe_price_jd_m2 ?? fallback.min_safe_jd_m2),
    recommended_jd_m2: Math.round(b.recommended_price_jd_m2 ?? fallback.recommended_jd_m2),
    premium_jd_m2: Math.round(b.premium_price_jd_m2 ?? fallback.premium_jd_m2),
  };
}

// Live shape: { base, scenario (both recommendation-shaped, *_price_jd_m2),
// deltas: {recommended_pct,...}, explanation, levers_applied: string[] }. The
// per-lever pct isn't broken out live, so the applied levers render as labelled
// rows and the headline delta is read from base→scenario bands.
export async function requestScenario(
  r: RecommendationResult,
  ov: ScenarioOverrides,
): Promise<ScenarioResult> {
  const live = await tryPost<{
    base?: LiveBand;
    scenario?: LiveBand;
    explanation?: string;
    levers_applied?: string[];
  }>("/scenario", { neighborhood: r.neighborhood, area_m2: 175, overrides: ov });

  if (live && live.scenario && live.base) {
    const base = adaptLiveBand(live.base, bandOf(r));
    const scenario = adaptLiveBand(live.scenario, bandOf(r));
    const deltas: ScenarioResult["deltas"] = (live.levers_applied ?? []).map((l) => ({
      label: fixText(l),
      delta_pct: 0,
      detail: "",
    }));
    return {
      base,
      scenario,
      deltas,
      explanation: fixText(live.explanation ?? ""),
      source: "live",
    };
  }
  return localScenario(r, ov);
}

// --- Residual land value (POST /residual-land-value) ------------------------

// Standard residual method: Max land = GDV − construction − finance − fees −
// developer profit. A pure formula, so the local path is exact (not a guess);
// it only differs from live if the backend enriches GDV or cost benchmarks.
export function localResidual(input: ResidualInputs, recommendedJdM2: number): ResidualBreakdown {
  const gdvPerM2 = input.gdv_per_m2 ?? recommendedJdM2;
  const gdv = gdvPerM2 * input.buildable_area_m2;
  const construction_cost = input.construction_cost_per_m2 * input.buildable_area_m2;
  const finance_cost = construction_cost * (input.finance_pct / 100);
  const fees = gdv * (input.fees_pct / 100);
  const developer_profit = gdv * (input.profit_pct / 100);
  const max_land_value = gdv - construction_cost - finance_cost - fees - developer_profit;
  return {
    gdv,
    gdv_per_m2: gdvPerM2,
    construction_cost,
    finance_cost,
    fees,
    developer_profit,
    max_land_value,
    max_land_value_per_m2: input.buildable_area_m2 > 0 ? max_land_value / input.buildable_area_m2 : 0,
    source: "local",
    note: "Residual method computed locally — deterministic formula, exact.",
  };
}

interface LiveResidual {
  inputs?: { gdv_per_m2?: number };
  breakdown?: { label: string; value_jd: number; basis?: string }[];
  gdv_total_jd?: number;
  residual_land_value_total_jd?: number;
  residual_land_value_per_m2_jd?: number;
}

// Live request uses fractions (0..1) + property_type/finish_quality/gdv_per_m2
// and returns a labelled breakdown array. Percentage-point inputs are converted
// and the sub-lines are pulled from the breakdown by label match.
export async function requestResidual(
  input: ResidualInputs,
  recommendedJdM2: number,
): Promise<ResidualBreakdown> {
  const body = {
    neighborhood: input.neighborhood,
    buildable_area_m2: input.buildable_area_m2,
    property_type: "apartment",
    finish_quality: "standard",
    gdv_per_m2: input.gdv_per_m2 ?? recommendedJdM2,
    construction_cost_per_m2: input.construction_cost_per_m2,
    finance_pct: input.finance_pct / 100,
    professional_fees_pct: input.fees_pct / 100,
    developer_profit_pct: input.profit_pct / 100,
  };
  const live = await tryPost<LiveResidual>("/residual-land-value", body);
  if (live && typeof live.residual_land_value_total_jd === "number") {
    const line = (needle: RegExp) =>
      Math.abs(live.breakdown?.find((b) => needle.test(b.label))?.value_jd ?? 0);
    const gdv = live.gdv_total_jd ?? 0;
    return {
      gdv,
      gdv_per_m2: live.inputs?.gdv_per_m2 ?? body.gdv_per_m2,
      construction_cost: line(/construction/i),
      finance_cost: line(/finance/i),
      fees: line(/fee/i),
      developer_profit: line(/profit/i),
      max_land_value: live.residual_land_value_total_jd,
      max_land_value_per_m2: live.residual_land_value_per_m2_jd ?? 0,
      source: "live",
      note: "Residual method from the engine (cost + finance benchmarks).",
    };
  }
  return localResidual(input, recommendedJdM2);
}

// Derives the confidence badge label consistently for scenario/opportunity chips.
export function levelFromScore(score: number): Confidence["level"] {
  return score >= 66 ? "High" : score >= 40 ? "Medium" : "Low";
}
