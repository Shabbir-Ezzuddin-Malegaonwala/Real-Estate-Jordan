// Shapes shared across the chat UI. The backend streams SSE events (see api/server.py)
// and structured tool payloads; these types mirror them.

export interface Source {
  name?: string;
  url?: string;
  sql?: string;
  date?: string | null;
  kind?: string;
}

export interface MapCommand {
  action: "flyto" | "recommendation" | "comparables";
  lat?: number;
  lng?: number;
  label?: string;
  neighborhood?: string;
  centroid?: [number, number] | null;
  comparables?: { lat?: number; lng?: number; price_per_m2?: number }[];
}

// The engine's RecommendationResult (subset the card renders) + our honesty blocks.
export interface EngineResult {
  neighborhood: string;
  property_type: string;
  min_safe_price_jd_m2: number;
  recommended_price_jd_m2: number;
  premium_price_jd_m2: number;
  confidence: {
    label: string;
    numeric: number;
    interval_jd_m2: [number, number];
    components?: Record<string, unknown>;
  };
  evidence_objects?: { factor: string; adjustment: string; category?: string }[];
  comparables?: {
    price_per_m2?: number;
    original_ppm2?: number;
    area_m2?: number;
    bedrooms?: number;
    view?: string;
    source?: Source;
  }[];
  resolution?: {
    requested: string;
    resolved_to: string;
    centroid?: [number, number] | null;
    sale_comps_in_area: number;
  };
  coverage?: { thin_data: boolean; note: string };
}

export interface ToolActivity {
  tool: string;
  label: string;
  ok?: boolean;
  done: boolean;
  sql?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  activities: ToolActivity[];
  sources: Source[];
  engineResults: EngineResult[];
  streaming: boolean;
  error?: string;
}

// SSE event union from the backend.
export type StreamEvent =
  | { type: "status"; stage: string; message: string }
  | { type: "token"; text: string }
  | { type: "tool_start"; tool: string; label: string }
  | { type: "tool_end"; tool: string; ok: boolean; sources?: Source[]; sql?: string; engine_result?: EngineResult; map?: MapCommand }
  | { type: "done"; sources: Source[]; engine_results: EngineResult[] }
  | { type: "error"; message: string; rate_limited?: boolean };
