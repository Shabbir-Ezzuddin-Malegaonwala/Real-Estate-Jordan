// Loads the whole-Jordan map data (neighbourhood/voronoi geometry, the
// Decision-Engine bundle, and opportunity scores) once for MapRegion — mirrors
// the original App.tsx's map-data effect, trimmed to what MapView/MapLayers/
// OpportunityLegend actually consume. Kept separate from lib/dataSource.ts,
// which serves the sidebar's simpler per-area AreaBundle (summary/pricing/etc);
// the map itself needs the friend's richer, nationwide RecommendationBundle.
import { useEffect, useState } from "react";
import { loadGeo, loadRecommendations, type GeoLayers } from "../lib/loadData";
import { checkHealth, fetchNeighborhoods, type NeighborhoodMeta } from "../lib/api";
import { fetchAreas, fetchOpportunity } from "../lib/intel";
import { DEFAULT_POI_ON } from "../lib/poi";
import type { LayerState } from "../components/MapLayers";
import type { AreaEntry, OpportunityScore, RecommendationBundle } from "../types";

const DEFAULT_LAYERS: LayerState = {
  zoning: false,
  pois: false, // superseded by the per-category amenity layers (MapLayers)
  comparables: true,
  future: true,
  roads: true,
  areaPrices: true, // nationwide asking-price coverage on by default
  listings: false, // 19k dots — opt-in to avoid clutter on first load
};

function areasFromBundle(
  bundle: RecommendationBundle,
  meta: Record<string, NeighborhoodMeta>,
): AreaEntry[] {
  return Object.values(bundle.results).map((r) => {
    const m = meta[r.neighborhood];
    return {
      name: r.neighborhood,
      name_ar: r.name_ar,
      covered: true,
      context: false,
      listing_count: m?.listing_count ?? r.comps_considered,
      median_price_per_m2: m?.median_price_per_m2 ?? r.base_value_jd_m2,
      centroid_lat: r.centroid?.[1],
      centroid_lng: r.centroid?.[0],
    };
  });
}

export interface MapData {
  geo: GeoLayers | null;
  bundle: RecommendationBundle | null;
  opportunity: OpportunityScore[];
  error: string | null;
  layers: LayerState;
  setLayers: React.Dispatch<React.SetStateAction<LayerState>>;
  poiState: Record<string, boolean>;
  togglePoi: (key: string) => void;
  layerLoading: Record<string, boolean>;
  onLayerLoading: (key: string, loading: boolean) => void;
}

export function useMapData(): MapData {
  const [geo, setGeo] = useState<GeoLayers | null>(null);
  const [bundle, setBundle] = useState<RecommendationBundle | null>(null);
  const [opportunity, setOpportunity] = useState<OpportunityScore[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [layers, setLayers] = useState<LayerState>(DEFAULT_LAYERS);
  const [poiState, setPoiState] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(DEFAULT_POI_ON.map((k) => [k, true])),
  );
  const [layerLoading, setLayerLoading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [g, b] = await Promise.all([loadGeo(), loadRecommendations()]);
        if (!alive) return;
        setGeo(g);
        setBundle(b);

        let meta: Record<string, NeighborhoodMeta> = {};
        const ok = await checkHealth();
        if (!alive) return;
        if (ok) {
          try {
            const list = await fetchNeighborhoods();
            for (const n of list) meta[n.name] = n;
          } catch {
            meta = {};
          }
        }

        const liveAreas = await fetchAreas(areasFromBundle(b, meta));
        if (!alive) return;
        const opp = await fetchOpportunity(liveAreas, g.opportunityHeatmap);
        if (alive) setOpportunity(opp);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const togglePoi = (key: string) => setPoiState((s) => ({ ...s, [key]: !s[key] }));
  const onLayerLoading = (key: string, loading: boolean) =>
    setLayerLoading((s) => ({ ...s, [key]: loading }));

  return { geo, bundle, opportunity, error, layers, setLayers, poiState, togglePoi, layerLoading, onLayerLoading };
}
