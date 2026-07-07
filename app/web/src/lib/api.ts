// Client for the on-demand recommendation API (built by api-eng). The base URL
// is overridable via VITE_API_BASE; it defaults to the local backend. Every call
// is time-bounded so an absent/slow API degrades to the offline fallback rather
// than hanging the UI.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface NeighborhoodMeta {
  name: string;
  centroid_lat: number;
  centroid_lng: number;
  listing_count: number;
  median_price_per_m2: number;
}

// Subject property the builder is pricing. Only neighborhood + area are required;
// the rest sharpen the estimate when known.
export interface SubjectInput {
  neighborhood: string;
  area_m2: number;
  floor_level?: number;
  total_floors?: number;
  bedrooms?: number;
  bathrooms?: number;
  view?: string;
  parking?: string;
  finish_quality?: string;
  building_age_years?: number;
  furnishing?: string;
}

function timeout(ms: number): AbortSignal {
  return AbortSignal.timeout(ms);
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: timeout(2500) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchNeighborhoods(): Promise<NeighborhoodMeta[]> {
  const res = await fetch(`${API_BASE}/neighborhoods`, { signal: timeout(4000) });
  if (!res.ok) throw new Error(`/neighborhoods → ${res.status}`);
  return (await res.json()) as NeighborhoodMeta[];
}

// The API wants only fields the user actually supplied — blanks and the "unknown"
// sentinel are omitted so the engine applies its own unknown handling.
function cleanBody(input: SubjectInput): Record<string, unknown> {
  const out: Record<string, unknown> = { neighborhood: input.neighborhood, area_m2: input.area_m2 };
  for (const [k, v] of Object.entries(input)) {
    if (k === "neighborhood" || k === "area_m2") continue;
    if (v === undefined || v === null || v === "" || v === "unknown") continue;
    out[k] = v;
  }
  return out;
}

// Returns the raw engine RecommendationResult (adaptNeighborhood normalises it).
export async function requestRecommendation(input: SubjectInput): Promise<unknown> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(cleanBody(input)),
    signal: timeout(15000),
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // non-JSON error body — keep the status code
    }
    throw new Error(`/recommend → ${detail}`);
  }
  return res.json();
}
