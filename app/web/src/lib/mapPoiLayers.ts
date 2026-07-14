import type maplibregl from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { POI_CATEGORIES, GEO_OVERLAYS, type PoiCategory, type GeoOverlay, type PoiType } from "./poi";

// POI points render from this zoom up (regional), so toggling a group shows its
// points at the default/metro view — MapLibre only draws the in-viewport subset.
export const POI_MINZOOM = 8;

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

// --- Per-TYPE emoji icons (canvas images via addImage — glyph-free, so the map
// can't blank if the glyph CDN is down). One image per curated type; each point
// draws its own via icon-image ["get","type"], with a neutral dot fallback. ------
const ICON_PX = 48;

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

function dotImageData(): ImageData | null {
  const canvas = document.createElement("canvas");
  canvas.width = ICON_PX;
  canvas.height = ICON_PX;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.beginPath();
  ctx.arc(ICON_PX / 2, ICON_PX / 2, ICON_PX * 0.24, 0, Math.PI * 2);
  ctx.fillStyle = "#6b7280";
  ctx.fill();
  return ctx.getImageData(0, 0, ICON_PX, ICON_PX);
}

// Registers the fallback dot + one image per type. Idempotent (skips existing),
// so it is safe to call again after a setStyle drops the image registry.
export function registerTypeIcons(map: maplibregl.Map, types: PoiType[]): void {
  if (!map.hasImage("poi-dot")) {
    const d = dotImageData();
    if (d) map.addImage("poi-dot", { width: ICON_PX, height: ICON_PX, data: d.data }, { pixelRatio: 2 });
  }
  for (const t of types) {
    if (map.hasImage(t.key)) continue;
    const img = emojiImageData(t.emoji);
    if (img) map.addImage(t.key, { width: ICON_PX, height: ICON_PX, data: img.data }, { pixelRatio: 2 });
  }
}

const ICON_IMAGE: maplibregl.ExpressionSpecification = [
  "coalesce",
  ["image", ["get", "type"]],
  ["image", "poi-dot"],
];

// Adds the source + layer for a POI group (symbol, per-type icon) or a geo overlay
// (fill/line). Idempotent — returns early if the source already exists.
export function addLayerFor(map: maplibregl.Map, key: string, data: FeatureCollection): void {
  if (map.getSource(srcId(key))) return;
  const cat = CATEGORY_BY_KEY.get(key);
  if (cat) {
    map.addSource(srcId(key), { type: "geojson", data });
    map.addLayer({
      id: lyrId(key),
      type: "symbol",
      source: srcId(key),
      minzoom: POI_MINZOOM,
      layout: {
        "icon-image": ICON_IMAGE,
        "icon-size": ["interpolate", ["linear"], ["zoom"], 8, 0.22, 12, 0.42, 16, 0.72],
        "icon-allow-overlap": false, // collision-declutter: overlapping icons hide
        "icon-padding": 2,
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

// Hides specific types within a group's symbol layer (per-type filtering). Empty
// set (or none hidden) clears the filter so all types show.
export function setHiddenTypes(map: maplibregl.Map, groupKey: string, hidden: string[]): void {
  const id = lyrId(groupKey);
  if (!map.getLayer(id)) return;
  if (hidden.length === 0) {
    map.setFilter(id, null);
  } else {
    map.setFilter(id, ["!", ["in", ["get", "type"], ["literal", hidden]]]);
  }
}

// Keeps POI points above the overlay fills regardless of toggle order.
export function raisePoiPoints(map: maplibregl.Map): void {
  for (const c of POI_CATEGORIES) {
    if (map.getLayer(lyrId(c.key))) map.moveLayer(lyrId(c.key));
  }
}
