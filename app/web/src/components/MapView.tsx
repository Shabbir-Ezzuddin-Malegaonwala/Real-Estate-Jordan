import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { FeatureCollection, Point, Polygon, LineString } from "geojson";
import type {
  NeighborhoodProps,
  PoiProps,
  RoadProps,
  ZoningProps,
  RecommendationBundle,
} from "../types";
import {
  themeStyle,
  AMMAN_CENTER,
  AMMAN_ZOOM,
  POI_COLORS,
  mapPalette,
  type MapPalette,
} from "../lib/mapStyle";
import type { Theme } from "../lib/theme";
import { jd } from "../lib/format";
import type { LayerState } from "./LayerControl";

interface Geo {
  neighborhoods: FeatureCollection<Polygon, NeighborhoodProps>;
  pois: FeatureCollection<Point, PoiProps>;
  roads: FeatureCollection<LineString, RoadProps>;
  zoning: FeatureCollection<Polygon, ZoningProps>;
}

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

export function MapView({
  geo,
  bundle,
  selected,
  onSelect,
  onOutside,
  layers,
  theme,
}: {
  geo: Geo;
  bundle: RecommendationBundle;
  selected: string | null;
  onSelect: (nb: string) => void;
  onOutside: () => void;
  layers: LayerState;
  theme: Theme;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const onOutsideRef = useRef(onOutside);
  onOutsideRef.current = onOutside;
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const bundleRef = useRef(bundle);
  bundleRef.current = bundle;
  const layersRef = useRef(layers);
  layersRef.current = layers;
  const themeRef = useRef(theme);
  themeRef.current = theme;
  const markersRef = useRef<HTMLElement[]>([]);

  // Init once — geo is loaded before this component mounts, so it is stable.
  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: themeStyle(themeRef.current),
      center: AMMAN_CENTER,
      zoom: AMMAN_ZOOM,
      minZoom: 10,
      maxZoom: 17,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    mapRef.current = map;

    map.on("load", () => {
      const pal = mapPalette(themeRef.current);
      installLayers(map, geo, pal);
      addNbhdMarkers(map, geo, pal, markersRef);
      readyRef.current = true;
      applySelection(map, selectedRef.current, bundleRef.current);
      applyVisibility(map, layersRef.current, geo, pal);
    });

    // Neighborhood selection — click inside a polygon selects it; clicking
    // outside all five polygons is an honest "no coverage here" signal. Layer-
    // scoped handlers persist across setStyle, so they are bound once here.
    map.on("click", (e) => {
      if (!readyRef.current) return;
      const hits = map.queryRenderedFeatures(e.point, { layers: ["nbhd-fill"] });
      if (hits.length > 0) {
        onSelectRef.current((hits[0].properties as NeighborhoodProps).neighborhood);
      } else {
        onOutsideRef.current();
      }
    });
    for (const lyr of ["nbhd-fill", "poi", "cmp-pts", "future-pts"]) {
      map.on("mouseenter", lyr, () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", lyr, () => (map.getCanvas().style.cursor = ""));
    }

    // POI popup
    map.on("click", "poi", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const p = f.properties as PoiProps;
      popup(map, e.lngLat, `<b>${esc(p.name || "POI")}</b><br/><span style="color:#8a94a5">${esc(p.category)} · ${esc(p.neighborhood)}</span>`);
    });
    map.on("click", "cmp-pts", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const p = f.properties as Record<string, unknown>;
      popup(
        map,
        e.lngLat,
        `<b>${jd(Number(p.price_per_m2))} JD/m²</b><br/><span style="color:#8a94a5">${esc(String(p.portal))} · ${jd(Number(p.area_m2))} m² · ${esc(String(p.view))} view</span>`,
      );
    });
    map.on("click", "future-pts", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const p = f.properties as Record<string, unknown>;
      popup(
        map,
        e.lngLat,
        `<b style="color:#3d9fb5">${esc(String(p.factor))}</b><br/><span style="color:#8a94a5">Future signal${p.expected_year ? " · ~" + p.expected_year : ""}</span>`,
      );
    });

    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current = [];
      readyRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Selection → highlight + comparables/future data + fly
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    applySelection(map, selected, bundle);
  }, [selected, bundle]);

  // Layer visibility toggles
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    applyVisibility(map, layers, geo, mapPalette(theme));
  }, [layers, geo, theme]);

  // Theme swap — setStyle drops all sources/layers; re-add them on style.load.
  // Markers are DOM overlays that survive setStyle, so they are only restyled.
  // Selection + view are preserved (refs), so nothing the user set is lost.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const pal = mapPalette(theme);
    readyRef.current = false;
    // diff:false forces a full reload — the two CARTO styles share source/layer
    // ids, so diff mode would skip the reload, never fire style.load, and leave
    // the basemap (and readyRef) stuck. A full reload drops the custom layers,
    // which the style.load handler below re-adds deterministically.
    map.setStyle(themeStyle(theme), { diff: false });
    map.once("style.load", () => {
      installLayers(map, geo, pal);
      for (const el of markersRef.current) el.style.cssText = markerCss(pal);
      applySelection(map, selectedRef.current, bundleRef.current);
      applyVisibility(map, layersRef.current, geo, pal);
      readyRef.current = true;
    });
  }, [theme, geo]);

  return <div ref={containerRef} className="absolute inset-0" aria-label="Map of Amman submarkets" />;
}

// ---------------------------------------------------------------------------

function installLayers(map: maplibregl.Map, geo: Geo, pal: MapPalette) {
  addBaseLayers(map, geo, pal);
  addNbhdSourceLayers(map, geo, pal);
}

// The 3.4 MB OSM land-use layer is added lazily on first toggle — keeping it out
// of the initial source batch. Tiling it synchronously alongside the other
// polygon source (neighbourhoods) at load starved/stalled the geojson worker and
// silently dropped both polygon layers; deferring it fixes neighbourhood rendering
// (and avoids parsing 3.4 MB the user may never view).
function ensureZoning(map: maplibregl.Map, geo: Geo, pal: MapPalette) {
  if (map.getSource("zoning")) return;
  const z = pal.zoning;
  map.addSource("zoning", { type: "geojson", data: geo.zoning });
  map.addLayer(
    {
      id: "zoning-fill",
      type: "fill",
      source: "zoning",
      paint: {
        "fill-color": [
          "match",
          ["get", "type"],
          "residential", z.residential,
          "farmland", z.farmland,
          "orchard", z.orchard,
          ["recreation_groun", "recreation_ground"], z.recreation_ground,
          "quarry", z.quarry,
          "industrial", z.industrial,
          ["commercial", "retail"], z.commercial,
          "forest", z.forest,
          "cemetery", z.cemetery,
          "construction", z.construction,
          pal.zoningDefault,
        ],
        "fill-opacity": 0.5,
        "fill-outline-color": pal.zoningOutline,
      },
    },
    "roads",
  );
}

function polygonCentroid(coords: number[][][]): [number, number] {
  const ring = coords[0] ?? [];
  let sx = 0;
  let sy = 0;
  for (const [x, y] of ring) {
    sx += x;
    sy += y;
  }
  const n = Math.max(1, ring.length);
  return [sx / n, sy / n];
}

function markerCss(pal: MapPalette): string {
  return `font:600 11px "IBM Plex Sans",sans-serif;letter-spacing:.09em;text-transform:uppercase;color:${pal.markerColor};text-shadow:${pal.markerShadow};pointer-events:none;white-space:nowrap;`;
}

// Neighbourhood labels are DOM markers, NOT a symbol layer. A glyph-dependent
// symbol layer on this source fails to tile whenever the external glyph CDN is
// unreachable, which silently drops ALL of the source's layers (fill/line) and
// leaves the map blank and unclickable. DOM markers need no glyphs, decoupling
// map interactivity from font availability — and they survive setStyle, so a
// theme swap only restyles them.
function addNbhdMarkers(
  map: maplibregl.Map,
  geo: Geo,
  pal: MapPalette,
  markersRef: { current: HTMLElement[] },
) {
  const css = markerCss(pal);
  for (const f of geo.neighborhoods.features) {
    const el = document.createElement("div");
    el.textContent = f.properties.neighborhood;
    el.style.cssText = css;
    new maplibregl.Marker({ element: el }).setLngLat(polygonCentroid(f.geometry.coordinates)).addTo(map);
    markersRef.current.push(el);
  }
}

// Fill/line/selection layers, inserted beneath "poi" to preserve z-order
// (roads < nbhd < poi). No markers here — those are added once and persist.
function addNbhdSourceLayers(map: maplibregl.Map, geo: Geo, pal: MapPalette) {
  if (map.getSource("nbhd")) return;
  map.addSource("nbhd", { type: "geojson", data: geo.neighborhoods });
  map.addLayer(
    { id: "nbhd-fill", type: "fill", source: "nbhd", paint: { "fill-color": pal.nbhdFill, "fill-opacity": 0.05 } },
    "poi",
  );
  map.addLayer(
    {
      id: "nbhd-line",
      type: "line",
      source: "nbhd",
      paint: { "line-color": pal.nbhdLine, "line-width": 1, "line-dasharray": [3, 2], "line-opacity": 0.7 },
    },
    "poi",
  );
  map.addLayer(
    {
      id: "nbhd-sel",
      type: "line",
      source: "nbhd",
      filter: ["==", ["get", "neighborhood"], "__none__"],
      paint: { "line-color": pal.nbhdSel, "line-width": 2.2, "line-opacity": 0.95 },
    },
    "poi",
  );
}

function addBaseLayers(map: maplibregl.Map, geo: Geo, pal: MapPalette) {
  map.addSource("poi", { type: "geojson", data: geo.pois });
  map.addSource("cmp", { type: "geojson", data: EMPTY });
  map.addSource("future", { type: "geojson", data: EMPTY });
  map.addSource("roads", { type: "geojson", data: geo.roads });

  // Roads — subtle, weighted by hierarchy.
  map.addLayer({
    id: "roads",
    type: "line",
    source: "roads",
    paint: {
      "line-color": [
        "match",
        ["get", "highway"],
        ["motorway", "trunk"], pal.roadMotorway,
        ["primary"], pal.roadPrimary,
        ["secondary"], pal.roadSecondary,
        pal.roadOther,
      ],
      "line-width": [
        "interpolate", ["linear"], ["zoom"],
        11, ["match", ["get", "highway"], ["motorway", "trunk"], 1.4, ["primary"], 1, 0.3],
        16, ["match", ["get", "highway"], ["motorway", "trunk"], 5, ["primary"], 3.5, ["secondary"], 2, 1],
      ],
      "line-opacity": 0.85,
    },
  });

  // POIs — colored by category.
  map.addLayer({
    id: "poi",
    type: "circle",
    source: "poi",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 2, 16, 5],
      "circle-color": [
        "match",
        ["get", "category"],
        "mosque", POI_COLORS.mosque,
        "school", POI_COLORS.school,
        "university", POI_COLORS.university,
        "hospital", POI_COLORS.hospital,
        "mall", POI_COLORS.mall,
        "park", POI_COLORS.park,
        "transport", POI_COLORS.transport,
        "#5fb2c9",
      ],
      "circle-opacity": 0.85,
      "circle-stroke-width": 0.5,
      "circle-stroke-color": pal.poiStroke,
    },
  });

  // Comparables — hollow amber rings (selection-driven).
  map.addLayer({
    id: "cmp-pts",
    type: "circle",
    source: "cmp",
    paint: {
      "circle-radius": 6,
      "circle-color": "#e6a94b",
      "circle-opacity": 0.18,
      "circle-stroke-width": 1.6,
      "circle-stroke-color": "#e6a94b",
    },
  });

  // Future signals — cyan diamonds (selection-driven).
  map.addLayer({
    id: "future-pts",
    type: "circle",
    source: "future",
    paint: {
      "circle-radius": 7,
      "circle-color": "#5fb2c9",
      "circle-opacity": 0.22,
      "circle-stroke-width": 1.6,
      "circle-stroke-color": "#5fb2c9",
    },
  });
}

function applySelection(map: maplibregl.Map, selected: string | null, bundle: RecommendationBundle) {
  if (!map.getLayer("nbhd-sel")) return;
  map.setFilter("nbhd-sel", ["==", ["get", "neighborhood"], selected ?? "__none__"]);

  const r = selected ? bundle.results[selected] : null;

  const cmp = map.getSource("cmp") as maplibregl.GeoJSONSource | undefined;
  if (cmp) {
    cmp.setData({
      type: "FeatureCollection",
      features: (r?.comparables ?? [])
        .filter((c) => c.lng != null && c.lat != null)
        .map((c) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [c.lng as number, c.lat as number] },
          properties: { portal: c.portal, price_per_m2: c.price_per_m2, area_m2: c.area_m2, view: c.view },
        })),
    });
  }

  const fut = map.getSource("future") as maplibregl.GeoJSONSource | undefined;
  if (fut && r?.centroid) {
    const [clon, clat] = r.centroid;
    const signals = r.evidence_objects.filter((e) => e.category === "future_signal");
    fut.setData({
      type: "FeatureCollection",
      features: signals.map((e, i) => {
        const ang = (i / Math.max(1, signals.length)) * Math.PI * 2;
        return {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [clon + 0.006 * Math.cos(ang), clat + 0.006 * Math.sin(ang)],
          },
          properties: { factor: e.factor, expected_year: e.expected_year ?? "" },
        };
      }),
    });
  } else if (fut) {
    fut.setData(EMPTY);
  }

  if (r?.centroid) {
    map.easeTo({ center: r.centroid, zoom: Math.max(map.getZoom(), 13.2), duration: 600, padding: { left: 440, top: 0, right: 0, bottom: 0 } });
  }
}

function applyVisibility(map: maplibregl.Map, layers: LayerState, geo: Geo, pal: MapPalette) {
  if (layers.zoning) ensureZoning(map, geo, pal);
  const set = (id: string, on: boolean) =>
    map.getLayer(id) && map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
  set("zoning-fill", layers.zoning);
  set("roads", layers.roads);
  set("poi", layers.pois);
  set("cmp-pts", layers.comparables);
  set("future-pts", layers.future);
}

function popup(map: maplibregl.Map, lngLat: maplibregl.LngLatLike, html: string) {
  new maplibregl.Popup({ closeButton: false, offset: 10, maxWidth: "240px" })
    .setLngLat(lngLat)
    .setHTML(`<div style="font-size:12px;line-height:1.4">${html}</div>`)
    .addTo(map);
}

function esc(s: string): string {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
}
