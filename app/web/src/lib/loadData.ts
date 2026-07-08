import type {
  FeatureCollection,
  Geometry,
  Point,
  Polygon,
  LineString,
} from "geojson";
import type {
  NeighborhoodProps,
  PoiProps,
  RoadProps,
  ZoningProps,
  RecommendationBundle,
  RecommendationResult,
} from "../types";
import { adaptNeighborhood, isEngineBundle } from "./adaptEngine";

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return (await res.json()) as T;
}

export interface GeoLayers {
  neighborhoods: FeatureCollection<Polygon, NeighborhoodProps>;
  pois: FeatureCollection<Point, PoiProps>;
  roads: FeatureCollection<LineString, RoadProps>;
  zoning: FeatureCollection<Polygon, ZoningProps>;
  // Gap-free Voronoi tessellation of every area we hold (from the geo agent).
  // Optional: when absent, the opportunity choropleth falls back to the
  // approximate neighbourhood polygons so the map still colours by opportunity.
  voronoi?: FeatureCollection<Polygon>;
  // Same 290 cells + baked opportunity score/components/raw-inputs per cell.
  opportunityHeatmap?: FeatureCollection<Polygon>;
}

export async function loadGeo(): Promise<GeoLayers> {
  const [neighborhoods, pois, roads, zoning, voronoi, opportunityHeatmap] = await Promise.all([
    getJson<FeatureCollection<Polygon, NeighborhoodProps>>("/data/neighborhoods.geojson"),
    getJson<FeatureCollection<Point, PoiProps>>("/data/poi.geojson"),
    getJson<FeatureCollection<LineString, RoadProps>>("/data/roads.geojson"),
    getJson<FeatureCollection<Polygon, ZoningProps>>("/data/zoning.geojson"),
    getJson<FeatureCollection<Polygon>>("/data/neighborhoods_voronoi.geojson").catch(() => null),
    getJson<FeatureCollection<Polygon>>("/data/opportunity_heatmap.geojson").catch(() => null),
  ]);
  return {
    neighborhoods,
    pois,
    roads,
    zoning,
    voronoi: voronoi ?? undefined,
    opportunityHeatmap: opportunityHeatmap ?? undefined,
  };
}

function isBundle(x: unknown): x is RecommendationBundle {
  return typeof x === "object" && x !== null && "results" in x;
}

function centroidOf(poly: Polygon): [number, number] {
  const ring = poly.coordinates[0] ?? [];
  let sx = 0;
  let sy = 0;
  for (const [x, y] of ring) {
    sx += x;
    sy += y;
  }
  const n = Math.max(1, ring.length);
  return [+(sx / n).toFixed(5), +(sy / n).toFixed(5)];
}

async function centroids(): Promise<Record<string, [number, number]>> {
  const gj = await getJson<FeatureCollection<Polygon, NeighborhoodProps>>(
    "/data/neighborhoods.geojson",
  );
  const map: Record<string, [number, number]> = {};
  for (const f of gj.features) map[f.properties.neighborhood] = centroidOf(f.geometry);
  return map;
}

// Loads the real Decision-Engine bundle (all five submarkets, keyed by
// neighbourhood) and adapts each result. If the engine output is unavailable it
// falls back to the illustrative shape-only mock so the interface still renders.
// Every result gets a centroid from the neighbourhood polygons for map framing.
export async function loadRecommendations(): Promise<RecommendationBundle> {
  const [mock, engineRaw, ct] = await Promise.all([
    getJson<unknown>("/mock_recommendation.json").catch(() => null),
    getJson<unknown>("/engine_output.json").catch(() => null),
    centroids(),
  ]);

  const results: Record<string, RecommendationResult> = {};

  // Mock first as a placeholder floor; live engine results overlay it.
  if (isBundle(mock)) {
    for (const [nb, r] of Object.entries(mock.results)) {
      results[nb] = {
        ...r,
        is_live: false,
        source_note: r.source_note ?? "Illustrative placeholder — engine run pending for this submarket.",
      };
    }
  }

  let liveCount = 0;
  if (isEngineBundle(engineRaw)) {
    const note = engineRaw.source
      ? `Live Decision-Engine output · ${engineRaw.source}`
      : "Live Decision-Engine output.";
    for (const [nb, rec] of Object.entries(engineRaw.neighborhoods)) {
      results[nb] = adaptNeighborhood(rec, note);
      liveCount++;
    }
  }

  if (Object.keys(results).length === 0) {
    throw new Error("No recommendation data: neither engine_output.json nor mock_recommendation.json loaded.");
  }

  for (const r of Object.values(results)) {
    if (!r.centroid && ct[r.neighborhood]) r.centroid = ct[r.neighborhood];
  }

  const src = isEngineBundle(engineRaw) ? engineRaw.source : undefined;
  const disclaimer =
    liveCount > 0
      ? `Launch prices are computed by the Decision Engine (CMA + evidence method${src ? `, ${src}` : ""}). Portal listings are asking prices calibrated to transaction level; figures are decision-support, not a formal valuation. Neighbourhood polygons are approximate radii and land-use is unofficial OSM data (GAM regulatory zoning pending).`
      : "Illustrative figures for interface demonstration; the data shape is the production contract. Neighbourhood polygons are approximate.";

  return {
    generated_at: new Date().toISOString(),
    engine_version: liveCount > 0 ? `decision-engine · ${liveCount} submarkets` : "mock",
    disclaimer,
    currency: "JOD",
    unit: "JD/m²",
    results,
  };
}

export function poiCategoryCounts(
  pois: FeatureCollection<Geometry, PoiProps>,
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const f of pois.features) {
    const c = f.properties.category;
    counts[c] = (counts[c] ?? 0) + 1;
  }
  return counts;
}
