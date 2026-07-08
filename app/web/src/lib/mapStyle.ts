import type { StyleSpecification } from "maplibre-gl";
import type { Theme } from "./theme";

const ATTRIB =
  '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a>';

const cartoTiles = (variant: "dark_all" | "light_all") => [
  `https://a.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}@2x.png`,
  `https://b.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}@2x.png`,
  `https://c.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}@2x.png`,
  `https://d.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}@2x.png`,
];

// Background-only base style — NO external required resources, so MapLibre's
// "load" fires immediately even when the tile/glyph CDN is unreachable. The
// CARTO raster basemap is attached afterwards as a best-effort bottom layer
// (see addBasemap); if its tiles are blocked the analytical vector layers still
// render over the background colour and the map stays fully functional.
export const CARTO_DARK: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#0a0d12" } }],
};

export const CARTO_LIGHT: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#eef1f5" } }],
};

export const themeStyle = (theme: Theme): StyleSpecification =>
  theme === "light" ? CARTO_LIGHT : CARTO_DARK;

// Attaches the raster basemap above the background, below all vector layers.
// Best-effort: tile failures are silent and never block the rest of the map.
export function addBasemap(map: import("maplibre-gl").Map, theme: Theme): void {
  if (map.getSource("carto")) return;
  const variant = theme === "light" ? "light_all" : "dark_all";
  map.addSource("carto", { type: "raster", tiles: cartoTiles(variant), tileSize: 256, attribution: ATTRIB });
  // No beforeId → sits directly above "bg" and below every vector layer.
  map.addLayer({ id: "carto", type: "raster", source: "carto", paint: { "raster-opacity": theme === "light" ? 1 : 0.82 } });
}

// Amman premium submarkets — view framing.
export const AMMAN_CENTER: [number, number] = [35.855, 31.97];
export const AMMAN_ZOOM = 12.2;

// POI marker colors are mid-saturation and read on both basemaps — shared.
export const POI_COLORS: Record<string, string> = {
  mosque: "#8b93a4",
  school: "#5fb2c9",
  university: "#7f8fd0",
  hospital: "#c9736f",
  mall: "#e6a94b",
  park: "#5fa47f",
  transport: "#c9a75f",
};

// Muted land-use fills for the zoning backdrop (OSM landuse, not GAM regulatory
// zoning). Deliberately low-saturation so the analytical layers stay dominant —
// one palette per theme so the backdrop reads on light and dark basemaps.
const ZONING_DARK: Record<string, string> = {
  residential: "#2b3140",
  farmland: "#2c3528",
  orchard: "#2f3a2c",
  recreation_ground: "#26362f",
  quarry: "#3a3230",
  industrial: "#34303a",
  commercial: "#3a3326",
  forest: "#25322a",
  cemetery: "#2e2e33",
  construction: "#332f2a",
};
const ZONING_LIGHT: Record<string, string> = {
  residential: "#e4e9f1",
  farmland: "#e9efe1",
  orchard: "#e6f0e2",
  recreation_ground: "#e0efe8",
  quarry: "#efe7df",
  industrial: "#ebe6f1",
  commercial: "#f1eadd",
  forest: "#e0efe4",
  cemetery: "#eaeaf0",
  construction: "#f1ebe0",
};

// Opportunity choropleth ramp — muted so it reads as a data surface, not a
// heat poster. Low → amber-red, mid → amber, high → green (higher = build here).
export function opportunityColor(score: number): string {
  if (score >= 78) return "#3f8f63";
  if (score >= 66) return "#5fa47f";
  if (score >= 52) return "#c9a75f";
  if (score >= 40) return "#e6a94b";
  if (score >= 25) return "#c98a5f";
  return "#b06a5f";
}

export interface MapPalette {
  roadMotorway: string;
  roadPrimary: string;
  roadSecondary: string;
  roadOther: string;
  poiStroke: string;
  nbhdFill: string;
  nbhdLine: string;
  nbhdSel: string;
  zoning: Record<string, string>;
  zoningDefault: string;
  zoningOutline: string;
  markerColor: string;
  markerShadow: string;
}

export function mapPalette(theme: Theme): MapPalette {
  if (theme === "light") {
    return {
      roadMotorway: "#9aa6b6",
      roadPrimary: "#a9b4c2",
      roadSecondary: "#bcc5d1",
      roadOther: "#cdd5df",
      poiStroke: "#ffffff",
      nbhdFill: "#b0791a",
      nbhdLine: "#a97d38",
      nbhdSel: "#b0791a",
      zoning: ZONING_LIGHT,
      zoningDefault: "#eef1f5",
      zoningOutline: "#d2d9e2",
      markerColor: "#1a2230",
      markerShadow: "0 0 4px #ffffff,0 1px 2px rgba(255,255,255,0.9)",
    };
  }
  return {
    roadMotorway: "#3a4658",
    roadPrimary: "#313c4c",
    roadSecondary: "#28313f",
    roadOther: "#1e2733",
    poiStroke: "#0a0d12",
    nbhdFill: "#e6a94b",
    nbhdLine: "#a97d38",
    nbhdSel: "#e6a94b",
    zoning: ZONING_DARK,
    zoningDefault: "#242a34",
    zoningOutline: "#10151d",
    markerColor: "#d6deea",
    markerShadow: "0 0 4px #0a0d12,0 1px 2px #0a0d12",
  };
}
