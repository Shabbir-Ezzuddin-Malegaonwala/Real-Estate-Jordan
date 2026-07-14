import { useCallback, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { FeatureCollection, Point, Polygon, LineString } from "geojson";
import type {
  NeighborhoodProps,
  PoiProps,
  RoadProps,
  ZoningProps,
  RecommendationBundle,
  OpportunityScore,
} from "../types";
import {
  themeStyle,
  addBasemap,
  AMMAN_CENTER,
  AMMAN_ZOOM,
  POI_COLORS,
  mapPalette,
  type MapPalette,
} from "../lib/mapStyle";
import type { Theme } from "../lib/theme";
import { jd } from "../lib/format";
import type { LayerState } from "./MapLayers";
import { POI_CATEGORIES, GEO_OVERLAYS } from "../lib/poi";
import { addLayerFor, setLayerVisible, raisePoiPoints, lyrId, srcId, configFor } from "../lib/mapPoiLayers";

const ALL_POI_KEYS = [...POI_CATEGORIES.map((c) => c.key), ...GEO_OVERLAYS.map((o) => o.key)];

interface Geo {
  neighborhoods: FeatureCollection<Polygon, NeighborhoodProps>;
  pois: FeatureCollection<Point, PoiProps>;
  roads: FeatureCollection<LineString, RoadProps>;
  zoning: FeatureCollection<Polygon, ZoningProps>;
  voronoi?: FeatureCollection<Polygon>;
  listings?: FeatureCollection<Point>;
  areaPrices?: FeatureCollection<Point>;
}

// Sequential blue scale for the asking-price layers (distinct from the opportunity
// heat scale). Stops in JD/m² spanning the national range.
const PRICE_COLOR: maplibregl.ExpressionSpecification = [
  "interpolate", ["linear"], ["get", "ppm2"],
  200, "#dbeafe", 450, "#93c5fd", 700, "#3b82f6", 1000, "#1d4ed8", 1400, "#1e3a8a",
];

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

// Area name lives under different keys across sources (neighbourhood polygons vs
// a Voronoi tessellation) — resolve any of them.
function areaNameOf(props: Record<string, unknown> | null): string | null {
  if (!props) return null;
  const v = props.neighborhood ?? props.area ?? props.name;
  return typeof v === "string" ? v : null;
}

// Joins opportunity scores onto whichever polygon surface we have, stamping
// `__opp` (score) and `__lown` (low-data flag) per feature so the choropleth
// paint is source-agnostic. Low-n cells are muted, not hidden — they stay on the
// gap-free surface but recede so a 4-listing cell never headlines as opportunity.
function oppFeatureCollection(
  base: FeatureCollection<Polygon>,
  opportunity: OpportunityScore[],
): FeatureCollection {
  const info = new Map(opportunity.map((o) => [o.area, o]));
  return {
    type: "FeatureCollection",
    features: base.features.map((f) => {
      const name = areaNameOf(f.properties as Record<string, unknown>);
      const o = name != null ? info.get(name) : undefined;
      return {
        type: "Feature",
        geometry: f.geometry,
        properties: {
          ...(f.properties as object),
          __area: name ?? "",
          __opp: o ? o.score : -1,
          __lown: o?.low_data ? 1 : 0,
        },
      };
    }),
  };
}

export function MapView({
  geo,
  bundle,
  selected,
  onSelect,
  onOutside,
  layers,
  theme,
  opportunity,
  showOpportunity,
  poiState,
  onLayerLoading,
}: {
  geo: Geo;
  bundle: RecommendationBundle;
  selected: string | null;
  onSelect: (nb: string) => void;
  onOutside: () => void;
  layers: LayerState;
  theme: Theme;
  opportunity: OpportunityScore[];
  showOpportunity: boolean;
  poiState: Record<string, boolean>;
  onLayerLoading?: (key: string, loading: boolean) => void;
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
  const oppRef = useRef(opportunity);
  oppRef.current = opportunity;
  const showOppRef = useRef(showOpportunity);
  showOppRef.current = showOpportunity;
  const poiStateRef = useRef(poiState);
  poiStateRef.current = poiState;
  const onLayerLoadingRef = useRef(onLayerLoading);
  onLayerLoadingRef.current = onLayerLoading;
  // Cache fetched category/overlay geojson so a theme swap re-adds without refetch.
  const poiDataRef = useRef<Map<string, FeatureCollection>>(new Map());
  const markersRef = useRef<HTMLElement[]>([]);

  // Lazy category/overlay layers: fetch on first toggle-on (cached), then just
  // flip visibility. Heavy layers (water, 8.4 MB) report a loading state. Reads
  // refs so it stays stable and is safe to call from map events + effects.
  const applyPoi = useCallback(async (map: maplibregl.Map) => {
    const state = poiStateRef.current;
    for (const key of ALL_POI_KEYS) {
      if (!state[key]) {
        setLayerVisible(map, key, false);
        continue;
      }
      if (!map.getSource(srcId(key))) {
        let data = poiDataRef.current.get(key);
        if (!data) {
          const cfg = configFor(key);
          if (!cfg) continue;
          onLayerLoadingRef.current?.(key, true);
          try {
            const res = await fetch(cfg.file);
            data = (await res.json()) as FeatureCollection;
            poiDataRef.current.set(key, data);
          } catch {
            onLayerLoadingRef.current?.(key, false);
            continue;
          }
          onLayerLoadingRef.current?.(key, false);
        }
        if (!map.getSource(srcId(key))) addLayerFor(map, key, data);
      }
      setLayerVisible(map, key, true);
    }
    raisePoiPoints(map);
  }, []);

  // Init once — geo is loaded before this component mounts, so it is stable.
  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: themeStyle(themeRef.current),
      center: AMMAN_CENTER,
      zoom: AMMAN_ZOOM,
      minZoom: 6.5,
      maxZoom: 17,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    mapRef.current = map;

    // Idempotent layer install. The basemap raster tiles/glyphs are external; if
    // that CDN is unreachable the "load" event can stall (tiles are a "required
    // resource"). So we also install once the style JSON is parsed — the vector
    // analytical layers (roads, POIs, opportunity choropleth) then render over
    // the background colour without waiting on tiles. Guards make double-call safe.
    const initLayers = () => {
      if (readyRef.current) return;
      const pal = mapPalette(themeRef.current);
      installLayers(map, geo, pal, themeRef.current);
      addNbhdMarkers(map, geo, pal, markersRef);
      readyRef.current = true;
      applySelection(map, selectedRef.current, bundleRef.current);
      applyVisibility(map, layersRef.current, geo, pal);
      applyOpportunity(map, geo, oppRef.current, showOppRef.current);
      void applyPoi(map);
    };
    map.on("load", initLayers);
    const fallback = window.setTimeout(() => {
      if (!readyRef.current && map.isStyleLoaded()) initLayers();
    }, 1500);

    // Neighborhood selection — click inside a polygon selects it; clicking
    // outside all five polygons is an honest "no coverage here" signal. Layer-
    // scoped handlers persist across setStyle, so they are bound once here.
    map.on("click", (e) => {
      if (!readyRef.current) return;
      // A POI point click shows its popup and does not re-select the area beneath.
      const poiLayers = POI_CATEGORIES.map((c) => lyrId(c.key)).filter((id) => map.getLayer(id));
      if (poiLayers.length > 0) {
        const poiHit = map.queryRenderedFeatures(e.point, { layers: poiLayers })[0];
        if (poiHit) {
          const p = poiHit.properties as Record<string, unknown>;
          const cfg = configFor(String(p.category ?? ""));
          const dot = cfg && "color" in cfg ? cfg.color : "#5fb2c9";
          popup(
            map,
            e.lngLat,
            `<b>${esc(String(p.name || "POI"))}</b><br/><span style="color:${dot}">${esc(String(p.subcategory || p.category))}</span> · <span style="color:#8a94a5">${esc(String(p.neighborhood ?? ""))}</span>`,
          );
          return;
        }
      }
      const clickable = ["nbhd-fill"];
      if (map.getLayer("opp-fill")) clickable.unshift("opp-fill");
      const hits = map.queryRenderedFeatures(e.point, { layers: clickable });
      const name = hits.length > 0 ? areaNameOf(hits[0].properties as Record<string, unknown>) : null;
      if (name) {
        onSelectRef.current(name);
      } else {
        onOutsideRef.current();
      }
    });
    for (const lyr of ["opp-fill", "nbhd-fill", "poi", "cmp-pts", "future-pts", "area-prices", "listings"]) {
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
    // Asking-price-per-area popup (median of the area's listings; asking, not appraised).
    map.on("click", "area-prices", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const p = f.properties as Record<string, unknown>;
      popup(
        map,
        e.lngLat,
        `<b>${esc(String(p.neighborhood))}</b><br/><b style="color:#1d4ed8">${jd(Number(p.ppm2))} JD/m²</b> <span style="color:#8a94a5">median asking · ${esc(String(p.n))} listings</span>`,
      );
    });
    map.on("click", "listings", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const p = f.properties as Record<string, unknown>;
      const ppm2 = p.ppm2 != null ? `<b style="color:#1d4ed8">${jd(Number(p.ppm2))} JD/m²</b> · ` : "";
      popup(
        map,
        e.lngLat,
        `${ppm2}<span style="color:#8a94a5">${esc(String(p.pt || "listing"))}${p.nb ? " · " + esc(String(p.nb)) : ""}</span><br/><span style="color:#8a94a5">${jd(Number(p.price))} JD asking</span>`,
      );
    });

    return () => {
      window.clearTimeout(fallback);
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

  // Opportunity choropleth — recolour on new scores or toggle.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    applyOpportunity(map, geo, opportunity, showOpportunity);
  }, [opportunity, showOpportunity, geo]);

  // POI category + geo-overlay toggles (lazy load on first enable).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    void applyPoi(map);
  }, [poiState, applyPoi]);

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
      installLayers(map, geo, pal, theme);
      for (const el of markersRef.current) el.style.cssText = markerCss(pal);
      applySelection(map, selectedRef.current, bundleRef.current);
      applyVisibility(map, layersRef.current, geo, pal);
      applyOpportunity(map, geo, oppRef.current, showOppRef.current);
      void applyPoi(map);
      readyRef.current = true;
    });
  }, [theme, geo]);

  return <div ref={containerRef} className="absolute inset-0" aria-label="Map of Amman submarkets" />;
}

// ---------------------------------------------------------------------------

function installLayers(map: maplibregl.Map, geo: Geo, pal: MapPalette, theme: Theme) {
  addBasemap(map, theme);
  addBaseLayers(map, geo, pal);
  addOpportunityLayer(map);
  addNbhdSourceLayers(map, geo, pal);
}

// Opportunity choropleth over the Voronoi tessellation when present, else the
// approximate neighbourhood polygons. Data-driven on the stamped `__opp` score;
// features with no score (< 0) render transparent. Inserted beneath "poi" so POI
// dots and neighbourhood outlines stay legible on top.
function addOpportunityLayer(map: maplibregl.Map) {
  if (map.getSource("opp")) return;
  map.addSource("opp", { type: "geojson", data: EMPTY });
  map.addLayer(
    {
      id: "opp-fill",
      type: "fill",
      source: "opp",
      layout: { visibility: "none" },
      paint: {
        "fill-color": [
          "case",
          ["<", ["to-number", ["get", "__opp"]], 0],
          "rgba(0,0,0,0)",
          [
            "step",
            ["to-number", ["get", "__opp"]],
            "#b06a5f",
            25, "#c98a5f",
            40, "#e6a94b",
            52, "#c9a75f",
            66, "#5fa47f",
            78, "#3f8f63",
          ],
        ],
        // Low-n cells recede (confidence-as-opacity); trustworthy high-n areas pop.
        "fill-opacity": ["case", ["==", ["get", "__lown"], 1], 0.12, 0.5],
        "fill-outline-color": "rgba(255,255,255,0.15)",
      },
    },
    "poi",
  );
  // Selection outline for the clicked cell (works for all 290, incl. context).
  map.addLayer(
    {
      id: "opp-sel",
      type: "line",
      source: "opp",
      filter: ["==", ["get", "__area"], "__none__"],
      paint: { "line-color": "#e6a94b", "line-width": 2.4, "line-opacity": 0.95 },
    },
    "poi",
  );
}

// Joins live scores onto the polygon surface and toggles the choropleth. Called
// on load, on opportunity/visibility change, and after a theme reload.
function applyOpportunity(
  map: maplibregl.Map,
  geo: Geo,
  opportunity: OpportunityScore[],
  show: boolean,
) {
  const src = map.getSource("opp") as maplibregl.GeoJSONSource | undefined;
  if (!src) return;
  const surface = geo.voronoi ?? geo.neighborhoods;
  src.setData(oppFeatureCollection(surface, opportunity));
  if (map.getLayer("opp-fill")) {
    map.setLayoutProperty("opp-fill", "visibility", show ? "visible" : "none");
  }
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

  // Every geocoded listing (~19.5k) — small dots so density reads at city zoom;
  // hidden by default and zoom-gated so the country view isn't a wall of points.
  map.addSource("listings", { type: "geojson", data: geo.listings ?? EMPTY });
  map.addLayer({
    id: "listings",
    type: "circle",
    source: "listings",
    minzoom: 8,
    layout: { visibility: "none" },
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 1.2, 16, 4],
      "circle-color": PRICE_COLOR,
      "circle-opacity": 0.55,
    },
  });

  // Median asking JD/m² per neighbourhood — graduated circles coloured by price,
  // visible at every zoom so the whole country is covered, not just Amman.
  map.addSource("areaprices", { type: "geojson", data: geo.areaPrices ?? EMPTY });
  map.addLayer({
    id: "area-prices",
    type: "circle",
    source: "areaprices",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 4, 11, 9, 15, 16],
      "circle-color": PRICE_COLOR,
      "circle-opacity": 0.82,
      "circle-stroke-width": 1,
      "circle-stroke-color": "rgba(255,255,255,0.85)",
    },
  });

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
  if (map.getLayer("opp-sel")) {
    map.setFilter("opp-sel", ["==", ["get", "__area"], selected ?? "__none__"]);
  }
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
  set("listings", layers.listings);
  set("area-prices", layers.areaPrices);
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
