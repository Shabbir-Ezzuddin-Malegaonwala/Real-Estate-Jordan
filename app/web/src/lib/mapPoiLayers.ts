import type maplibregl from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { POI_CATEGORIES, GEO_OVERLAYS, type PoiCategory, type GeoOverlay } from "./poi";

// POI points render from this zoom up. Set to a regional zoom (not street level)
// so toggling a category shows its points immediately at the default/metro view —
// MapLibre only draws the in-viewport subset, so the full 69k stays performant.
export const POI_MINZOOM = 8;

export const srcId = (key: string) => `poi-src-${key}`;
export const lyrId = (key: string) => `poi-lyr-${key}`;

const CATEGORY_BY_KEY = new Map(POI_CATEGORIES.map((c) => [c.key, c]));
const OVERLAY_BY_KEY = new Map(GEO_OVERLAYS.map((o) => [o.key, o]));

// --- Emoji icons rendered to canvas images (NOT a glyph/text-field symbol, which
// depends on the external glyph CDN and can blank the map — see MapView's marker
// note). icon-image symbols use these locally-added images, so no glyph dependency.
const ICON_PX = 48;
const poiIconId = (key: string) => `poi-icon-${key}`;

function emojiImageData(emoji: string): ImageData | null {
  const canvas = document.createElement("canvas");
  canvas.width = ICON_PX;
  canvas.height = ICON_PX;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.font = `${Math.floor(ICON_PX * 0.8)}px "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(emoji, ICON_PX / 2, ICON_PX / 2 + ICON_PX * 0.06);
  return ctx.getImageData(0, 0, ICON_PX, ICON_PX);
}

// Idempotent — adds the category's emoji as a map image once (re-added after a
// setStyle drops it, since map.hasImage() is then false).
function ensurePoiIcon(map: maplibregl.Map, key: string, emoji: string): boolean {
  const id = poiIconId(key);
  if (map.hasImage(id)) return true;
  const img = emojiImageData(emoji);
  if (!img) return false;
  map.addImage(id, { width: ICON_PX, height: ICON_PX, data: img.data }, { pixelRatio: 2 });
  return true;
}

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
    // Prefer emoji icons; fall back to coloured dots if the canvas image failed.
    if (ensurePoiIcon(map, key, cat.icon)) {
      map.addLayer({
        id: lyrId(key),
        type: "symbol",
        source: srcId(key),
        minzoom: POI_MINZOOM,
        layout: {
          "icon-image": poiIconId(key),
          "icon-size": ["interpolate", ["linear"], ["zoom"], 8, 0.22, 12, 0.4, 16, 0.7],
          "icon-allow-overlap": false, // collision-declutter: overlapping icons hide
          "icon-padding": 2,
        },
      });
    } else {
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
    }
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
