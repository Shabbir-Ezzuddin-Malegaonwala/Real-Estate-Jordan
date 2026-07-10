import type maplibregl from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { POI_CATEGORIES, GEO_OVERLAYS, type PoiCategory, type GeoOverlay } from "./poi";

// POI points render only from this zoom up — nationwide 9k points at country zoom
// would be noise; they reveal at neighbourhood/street level.
export const POI_MINZOOM = 11.5;

export const srcId = (key: string) => `poi-src-${key}`;
export const lyrId = (key: string) => `poi-lyr-${key}`;

const CATEGORY_BY_KEY = new Map(POI_CATEGORIES.map((c) => [c.key, c]));
const OVERLAY_BY_KEY = new Map(GEO_OVERLAYS.map((o) => [o.key, o]));

export function configFor(key: string): PoiCategory | GeoOverlay | undefined {
  return CATEGORY_BY_KEY.get(key) ?? OVERLAY_BY_KEY.get(key);
}
export function isOverlay(key: string): boolean {
  return OVERLAY_BY_KEY.has(key);
}

// Adds the source + layer for a POI category (circle) or a geo overlay (fill/line).
// Idempotent — returns early if the source already exists (e.g. after theme swap
// the caller re-adds from cached data).
export function addLayerFor(map: maplibregl.Map, key: string, data: FeatureCollection): void {
  if (map.getSource(srcId(key))) return;
  const cat = CATEGORY_BY_KEY.get(key);
  if (cat) {
    map.addSource(srcId(key), { type: "geojson", data });
    map.addLayer({
      id: lyrId(key),
      type: "circle",
      source: srcId(key),
      minzoom: POI_MINZOOM,
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 2.4, 16, 6],
        "circle-color": cat.color,
        "circle-opacity": 0.85,
        "circle-stroke-width": 0.6,
        "circle-stroke-color": "rgba(255,255,255,0.55)",
      },
    });
    return;
  }
  const ov = OVERLAY_BY_KEY.get(key);
  if (!ov) return;
  map.addSource(srcId(key), { type: "geojson", data });
  if (ov.kind === "fill") {
    map.addLayer({
      id: lyrId(key),
      type: "fill",
      source: srcId(key),
      paint: { "fill-color": ov.color, "fill-opacity": 0.28, "fill-outline-color": ov.color },
    });
  } else {
    map.addLayer({
      id: lyrId(key),
      type: "line",
      source: srcId(key),
      paint: {
        "line-color": ov.color,
        "line-opacity": 0.7,
        "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.8, 16, 3],
      },
    });
  }
}

export function setLayerVisible(map: maplibregl.Map, key: string, visible: boolean): void {
  const id = lyrId(key);
  if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
}

// Keeps POI points above the overlay fills regardless of toggle order.
export function raisePoiPoints(map: maplibregl.Map): void {
  for (const c of POI_CATEGORIES) {
    if (map.getLayer(lyrId(c.key))) map.moveLayer(lyrId(c.key));
  }
}
