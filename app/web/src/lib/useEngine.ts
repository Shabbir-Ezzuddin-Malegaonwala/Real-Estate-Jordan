// Typed hooks over the existing engine clients (lib/api.ts, lib/intel.ts,
// lib/loadData.ts, lib/adaptEngine.ts). Every hook returns {data, loading,
// error} and reuses those modules' own time-bounded fetches and offline/
// precomputed fallbacks verbatim — no new network timeouts or fallback logic
// is introduced here, only composition.
import { useEffect, useMemo, useState } from "react";
import type {
  AreaEntry,
  AreaMonitoring,
  Comparable,
  OpportunityScore,
  RecommendationBundle,
  RecommendationResult,
  ResidualBreakdown,
  ResidualInputs,
} from "../types";
import {
  checkHealth,
  fetchNeighborhoods,
  requestRecommendation,
  type NeighborhoodMeta,
  type SubjectInput,
} from "./api";
import { fetchAreaMonitoring, fetchAreas, fetchOpportunity, requestResidual } from "./intel";
import { adaptApiRecommendation } from "./adaptEngine";
import { loadGeo, loadRecommendations } from "./loadData";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

function asError(e: unknown): Error {
  return e instanceof Error ? e : new Error(String(e));
}

const IDLE: AsyncState<never> = { data: null, loading: false, error: null };

// The representative unit the engine prices when the caller hasn't customised
// it — matches App.tsx's DEFAULT_SUBJECT (kept in sync with scrapers/emit_national.py).
const DEFAULT_SUBJECT: Omit<SubjectInput, "neighborhood"> = {
  area_m2: 175,
  bedrooms: 3,
  floor_level: 4,
  building_age_years: 0,
  view: "unknown",
  parking: "unknown",
  finish_quality: "high",
};

// Mirrors App.tsx's local areasFromBundle helper (not exported there) — turns
// the precomputed bundle into AreaEntry rows, enriched with /neighborhoods
// meta when the API is online.
function bundleToAreas(bundle: RecommendationBundle, meta: Record<string, NeighborhoodMeta>): AreaEntry[] {
  return Object.values(bundle.results).map((r) => {
    const m = meta[r.neighborhood];
    return {
      name: r.neighborhood,
      name_ar: r.name_ar,
      covered: true,
      context: false,
      listing_count: m?.listing_count ?? r.comps_considered,
      sale_listing_count: (m as { sale_listing_count?: number } | undefined)?.sale_listing_count,
      median_price_per_m2: m?.median_price_per_m2 ?? r.base_value_jd_m2,
      centroid_lat: r.centroid?.[1],
      centroid_lng: r.centroid?.[0],
    };
  });
}

// --- useAreas ----------------------------------------------------------------

// GET /areas (with the precomputed-bundle + /neighborhoods fallback App.tsx
// already relies on). Every consumer of area lists should read from this one
// hook so a change on one side reflects everywhere.
export function useAreas(): AsyncState<AreaEntry[]> {
  const [state, setState] = useState<AsyncState<AreaEntry[]>>({ data: null, loading: true, error: null });

  useEffect(() => {
    let alive = true;
    setState({ data: null, loading: true, error: null });

    (async () => {
      try {
        const [bundle, online] = await Promise.all([loadRecommendations(), checkHealth()]);
        let meta: Record<string, NeighborhoodMeta> = {};
        if (online) {
          try {
            const list = await fetchNeighborhoods();
            meta = Object.fromEntries(list.map((n) => [n.name, n]));
          } catch {
            meta = {};
          }
        }
        const areas = await fetchAreas(bundleToAreas(bundle, meta));
        if (alive) setState({ data: areas, loading: false, error: null });
      } catch (e) {
        if (alive) setState({ data: null, loading: false, error: asError(e) });
      }
    })();

    return () => {
      alive = false;
    };
  }, []);

  return state;
}

// --- useRecommendation --------------------------------------------------------

// POST /recommend when the API is reachable; falls back to the precomputed
// bundle (loadRecommendations) for the area, same contract as App.tsx's
// recompute(). `subject` excludes neighborhood — that's `area`.
export function useRecommendation(
  area: string | null,
  subject: Omit<SubjectInput, "neighborhood"> = DEFAULT_SUBJECT,
): AsyncState<RecommendationResult> {
  const subjectKey = JSON.stringify(subject);
  const [state, setState] = useState<AsyncState<RecommendationResult>>({ data: null, loading: false, error: null });

  useEffect(() => {
    if (!area) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    let alive = true;
    setState({ data: null, loading: true, error: null });

    (async () => {
      const subj: SubjectInput = { ...subject, neighborhood: area };
      try {
        const online = await checkHealth();
        if (!online) throw new Error("API offline");
        const raw = await requestRecommendation(subj);
        const res = adaptApiRecommendation(raw, "Live API · computed on demand");
        if (alive) setState({ data: res, loading: false, error: null });
      } catch (e) {
        try {
          const bundle = await loadRecommendations();
          const pre = bundle.results[area];
          if (!pre) throw e;
          if (alive) {
            setState({
              data: {
                ...pre,
                source_note: `Offline — showing precomputed defaults (${asError(e).message}).`,
              },
              loading: false,
              error: null,
            });
          }
        } catch (fallbackErr) {
          if (alive) setState({ data: null, loading: false, error: asError(fallbackErr) });
        }
      }
    })();

    return () => {
      alive = false;
    };
    // subjectKey is the stable proxy for subject's contents.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area, subjectKey]);

  return state;
}

// --- useComparables ------------------------------------------------------------

// There is no standalone /comparables client in lib/api.ts or lib/intel.ts —
// comparables ship embedded in RecommendationResult.comparables. This hook
// reuses useRecommendation rather than adding a second network path.
export function useComparables(area: string | null): AsyncState<Comparable[]> {
  const rec = useRecommendation(area);
  return useMemo(
    () => ({
      data: rec.data ? rec.data.comparables : null,
      loading: rec.loading,
      error: rec.error,
    }),
    [rec.data, rec.loading, rec.error],
  );
}

// --- useResidualLandValue ------------------------------------------------------

// POST /residual-land-value. Needs a GDV/m² anchor — derived from the area's
// live/precomputed recommendation (recommended_jd_m2) exactly like App.tsx
// does before calling requestResidual.
export function useResidualLandValue(
  area: string | null,
  inputs: Omit<ResidualInputs, "neighborhood">,
): AsyncState<ResidualBreakdown> {
  const rec = useRecommendation(area, { ...DEFAULT_SUBJECT, area_m2: inputs.buildable_area_m2 || DEFAULT_SUBJECT.area_m2 });
  const inputsKey = JSON.stringify(inputs);
  const [state, setState] = useState<AsyncState<ResidualBreakdown>>({ data: null, loading: false, error: null });

  useEffect(() => {
    if (!area) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    if (rec.loading) {
      setState({ data: null, loading: true, error: null });
      return;
    }
    if (rec.error || !rec.data) {
      setState({ data: null, loading: false, error: rec.error ?? new Error("No recommendation available to derive GDV") });
      return;
    }
    let alive = true;
    setState({ data: null, loading: true, error: null });
    requestResidual({ ...inputs, neighborhood: area }, rec.data.recommended_jd_m2)
      .then((data) => {
        if (alive) setState({ data, loading: false, error: null });
      })
      .catch((e) => {
        if (alive) setState({ data: null, loading: false, error: asError(e) });
      });
    return () => {
      alive = false;
    };
    // inputsKey is the stable proxy for inputs' contents.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area, inputsKey, rec.loading, rec.error, rec.data]);

  return state;
}

// --- useOpportunity ------------------------------------------------------------

// GET /opportunity merged with the baked 290-cell heatmap, same as App.tsx's
// fetchOpportunity(liveAreas, geo.opportunityHeatmap) call.
export function useOpportunity(): AsyncState<OpportunityScore[]> {
  const areas = useAreas();
  const [state, setState] = useState<AsyncState<OpportunityScore[]>>({ data: null, loading: true, error: null });

  useEffect(() => {
    if (areas.loading) {
      setState({ data: null, loading: true, error: null });
      return;
    }
    if (areas.error || !areas.data) {
      setState({ data: null, loading: false, error: areas.error });
      return;
    }
    const areaEntries = areas.data;
    let alive = true;
    setState({ data: null, loading: true, error: null });
    loadGeo()
      .then((geo) => fetchOpportunity(areaEntries, geo.opportunityHeatmap))
      .then((data) => {
        if (alive) setState({ data, loading: false, error: null });
      })
      .catch((e) => {
        if (alive) setState({ data: null, loading: false, error: asError(e) });
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [areas.loading, areas.error, areas.data]);

  return state;
}

// --- useAreaMonitoring ----------------------------------------------------------

// GET /area-monitoring — every value is server-computed; no local fallback
// (matches lib/intel.ts's fetchAreaMonitoring contract: null means "unreachable").
export function useAreaMonitoring(area: string | null): AsyncState<AreaMonitoring> {
  const [state, setState] = useState<AsyncState<AreaMonitoring>>(IDLE);

  useEffect(() => {
    if (!area) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    let alive = true;
    setState({ data: null, loading: true, error: null });
    fetchAreaMonitoring(area)
      .then((data) => {
        if (!alive) return;
        setState(
          data
            ? { data, loading: false, error: null }
            : { data: null, loading: false, error: new Error("Area monitoring unavailable") },
        );
      })
      .catch((e) => {
        if (alive) setState({ data: null, loading: false, error: asError(e) });
      });
    return () => {
      alive = false;
    };
  }, [area]);

  return state;
}
