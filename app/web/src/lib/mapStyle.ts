import type { StyleSpecification } from "maplibre-gl";

// Free, key-less dark basemap: CARTO dark-matter raster tiles (OSM data).
// No paid key, no Google. If tile fetching is blocked in a locked-down
// environment the vector layers still render over the solid base color, so
// the analytical layers remain fully functional.
export const CARTO_DARK: StyleSpecification = {
  version: 8,
  glyphs: "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf",
  sources: {
    carto: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#0a0d12" } },
    { id: "carto", type: "raster", source: "carto", paint: { "raster-opacity": 0.82 } },
  ],
};

// National framing — opens on Amman (the dense core) but zoom-out reveals the
// whole country and the secondary-city circles. Kept the export names stable.
export const AMMAN_CENTER: [number, number] = [35.94, 31.72];
export const AMMAN_ZOOM = 8.1;

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
// zoning). Deliberately low-saturation so the analytical layers stay dominant.
export const ZONING_COLORS: Record<string, string> = {
  residential: "#2b3140",
  farmland: "#2c3528",
  orchard: "#2f3a2c",
  recreation_groun: "#26362f",
  recreation_ground: "#26362f",
  quarry: "#3a3230",
  industrial: "#34303a",
  commercial: "#3a3326",
  retail: "#3a3326",
  forest: "#25322a",
  cemetery: "#2e2e33",
  construction: "#332f2a",
};
export const ZONING_DEFAULT = "#242a34";
