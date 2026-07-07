// Normalises the Decision Engine's emitted output into the internal
// RecommendationResult the panel components consume. The engine emits a bundle
// keyed by neighbourhood (app/engine/sample_output.json); this is the single
// translation point. It invents no numbers — every value shown is carried
// straight from the engine payload.
import type {
  Comparable,
  CompAdjustment,
  Confidence,
  ConfidenceLevel,
  Direction,
  EvidenceKind,
  EvidenceObject,
  EvidenceSource,
  RecommendationResult,
  RiskFactor,
  Severity,
} from "../types";

// --- raw engine shapes (only the fields we read) ---------------------------
interface RawSource {
  name: string;
  url: string;
  capture_date: string;
}
interface RawEvidence {
  factor: string;
  adjustment: string;
  confidence: string;
  method: string;
  datasets: string[];
  sources: RawSource[];
  category: string;
  explanation: string;
  expected_year?: number | null;
  impact_area?: string | null;
}
interface RawCompAdjustment {
  factor: string;
  adjustment: string;
  method: string;
  detail?: string;
}
interface RawComp {
  listing_id: string;
  neighborhood: string;
  area_m2: number;
  original_ppm2: number;
  adjusted_ppm2: number;
  gross_adjustment: number;
  similarity: number;
  listing_date: string;
  adjustments: RawCompAdjustment[];
  source: RawSource;
}
interface RawRiskObj {
  factor: string;
  severity: string;
  detail: string;
}
interface RawConfidence {
  label: string;
  numeric: number;
  interval_jd_m2: [number, number];
}
interface RawMethodValues {
  comparison_asking?: number;
  cost_floor?: number;
  income_ceiling?: number;
  selection_notes?: string[];
}
export interface RawNeighborhood {
  location_id?: string;
  neighborhood: string;
  property_type: string;
  min_safe_price_jd_m2: number;
  recommended_price_jd_m2: number;
  premium_price_jd_m2: number;
  confidence: RawConfidence;
  narrative: string;
  evidence_objects: RawEvidence[];
  comparables: RawComp[];
  risk_factors: (string | RawRiskObj)[];
  method_values?: RawMethodValues;
  computed_date?: string;
}
export interface EngineBundle {
  generated_at?: string;
  source?: string;
  neighborhoods: Record<string, RawNeighborhood>;
}

export function isEngineBundle(x: unknown): x is EngineBundle {
  return (
    typeof x === "object" &&
    x !== null &&
    "neighborhoods" in x &&
    typeof (x as EngineBundle).neighborhoods === "object" &&
    (x as EngineBundle).neighborhoods !== null
  );
}

function normLevel(s: string): ConfidenceLevel {
  const c = s.trim().toLowerCase();
  if (c.startsWith("h")) return "High";
  if (c.startsWith("l")) return "Low";
  return "Medium";
}

function normSeverity(s: string): Severity {
  const c = s.trim().toLowerCase();
  return c === "high" || c === "medium" || c === "low" ? c : "medium";
}

const PCT_RE = /^\s*([+\-−])?\s*(\d+(?:\.\d+)?)\s*%/;

// Splits an engine adjustment string into the fields the waterfall needs. The
// engine emits three flavours: percentages ("+18.8%", "-1.6% per unit"),
// absolute anchors ("550 JD/m²"), and future-signal positioning text.
function parseAdjustment(
  raw: string,
  category: string,
): { pct: number; direction: Direction; kind: EvidenceKind; per_unit: boolean } {
  if (category === "future_signal") {
    return { pct: 0, direction: "neutral", kind: "positioning", per_unit: false };
  }
  const low = raw.trim().toLowerCase();
  if (low.startsWith("context") || low.includes("not a price adjustment")) {
    return { pct: 0, direction: "neutral", kind: "context", per_unit: false };
  }
  const m = PCT_RE.exec(raw);
  if (m) {
    const sign = m[1] === "-" || m[1] === "−" ? -1 : 1;
    const pct = (sign * Number(m[2])) / 100;
    const direction: Direction = pct > 0 ? "increase" : pct < 0 ? "decrease" : "neutral";
    return { pct, direction, kind: "pct", per_unit: /per unit/i.test(raw) };
  }
  // Anything with a JD/m² magnitude is an absolute cross-check anchor.
  return { pct: 0, direction: "neutral", kind: "anchor", per_unit: false };
}

function toSources(raw: RawSource[]): EvidenceSource[] {
  return raw.map((s) => ({ name: s.name, url: s.url, capture_date: s.capture_date }));
}

function adaptEvidence(e: RawEvidence): EvidenceObject {
  const { pct, direction, kind, per_unit } = parseAdjustment(e.adjustment, e.category);
  return {
    factor: e.factor,
    adjustment: e.adjustment,
    adjustment_pct: pct,
    direction,
    confidence: normLevel(e.confidence),
    method: e.method,
    datasets: e.datasets,
    sources: toSources(e.sources),
    category: e.category === "future_signal" ? "future_signal" : "current_state",
    explanation: e.explanation,
    kind,
    per_unit,
    expected_year: e.expected_year ?? null,
    impact_area: e.impact_area ?? null,
  };
}

function adaptComp(c: RawComp): Comparable {
  const adjustments: CompAdjustment[] = c.adjustments.map((a) => ({
    factor: a.factor,
    adjustment: a.adjustment,
    method: a.method,
    detail: a.detail,
  }));
  return {
    id: c.listing_id,
    portal: c.source?.name ?? "listing",
    neighborhood: c.neighborhood,
    price_jd: Math.round(c.adjusted_ppm2 * c.area_m2),
    area_m2: c.area_m2,
    price_per_m2: c.adjusted_ppm2,
    bedrooms: null,
    floor_level: null,
    view: "",
    building_age_years: null,
    seller_type: "",
    url: c.source?.url ?? "#",
    capture_date: c.source?.capture_date ?? "",
    distance_km: 0,
    similarity: c.similarity,
    lat: null,
    lng: null,
    original_ppm2: c.original_ppm2,
    adjusted_ppm2: c.adjusted_ppm2,
    gross_adjustment: c.gross_adjustment,
    listing_date: c.listing_date,
    adjustments,
  };
}

function adaptRisk(r: string | RawRiskObj): RiskFactor {
  if (typeof r !== "string") {
    return { title: r.factor, severity: normSeverity(r.severity), detail: r.detail };
  }
  const [head, ...rest] = r.split(" — ");
  const detail = rest.length > 0 ? rest.join(" — ") : r;
  const title = rest.length > 0 ? head : head.split(/(?<=\.)\s/)[0];
  const low = r.toLowerCase();
  const severity: Severity = /thin|sparse|only \d|few comp/.test(low)
    ? "high"
    : /diverge|caution|below the recommended|may not clear/.test(low)
      ? "medium"
      : "low";
  return { title: title.replace(/\.$/, ""), severity, detail };
}

// Normalises a single RecommendationResult from the on-demand API. Tolerates the
// engine emitting it bare or wrapped in { recommendation: {...} }.
export function adaptApiRecommendation(raw: unknown, sourceNote: string): RecommendationResult {
  const obj = raw as { recommendation?: RawNeighborhood } & Partial<RawNeighborhood>;
  const rec = obj.recommendation ?? (obj as RawNeighborhood);
  if (typeof rec.recommended_price_jd_m2 !== "number" || !rec.confidence) {
    throw new Error("API returned an unrecognised recommendation shape");
  }
  return adaptNeighborhood(rec, sourceNote);
}

export function adaptNeighborhood(r: RawNeighborhood, sourceNote: string): RecommendationResult {
  const mv = r.method_values ?? {};
  const conf = r.confidence;
  const [lo, hi] = conf.interval_jd_m2 ?? [r.min_safe_price_jd_m2, r.premium_price_jd_m2];

  const drivers: string[] = [];
  if (mv.selection_notes) drivers.push(...mv.selection_notes);
  if (mv.cost_floor != null) drivers.push(`cost floor ${Math.round(mv.cost_floor)} JD/m²`);
  if (mv.income_ceiling != null) drivers.push(`income ceiling ${Math.round(mv.income_ceiling)} JD/m²`);

  const confidence: Confidence = {
    level: normLevel(conf.label),
    score: Math.round((conf.numeric ?? 0) * 100),
    range_low: lo,
    range_high: hi,
    drivers,
  };

  return {
    neighborhood: r.neighborhood,
    property_type: r.property_type,
    as_of: r.computed_date ?? "",
    currency: "JOD",
    unit: "JD/m²",
    base_value_jd_m2: mv.comparison_asking ?? r.recommended_price_jd_m2,
    min_safe_jd_m2: r.min_safe_price_jd_m2,
    recommended_jd_m2: r.recommended_price_jd_m2,
    premium_jd_m2: r.premium_price_jd_m2,
    confidence,
    evidence_objects: r.evidence_objects.map(adaptEvidence),
    comparables: r.comparables.map(adaptComp),
    risk_factors: r.risk_factors.map(adaptRisk),
    narrative: r.narrative,
    centroid: null,
    is_live: true,
    source_note: sourceNote,
    comps_considered: r.comparables.length,
  };
}
