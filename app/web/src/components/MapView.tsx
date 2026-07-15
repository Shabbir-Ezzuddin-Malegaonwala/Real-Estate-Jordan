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
import { POI_CATEGORIES, GEO_OVERLAYS, type PoiType } from "../lib/poi";
import { addLayerFor, setLayerVisible, raisePoiPoints, lyrId, srcId, configFor, registerTypeIcons, setHiddenTypes } from "../lib/mapPoiLayers";

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

// Distinct fill per area so neighbouring cells read as separate regions at a
// glance. Soft, mid-light hues that sit under POI icons/labels on the light
// basemap; a stable name hash keeps an area's colour constant across reloads.
const AREA_PALETTE = [
  "#9ec9e2", "#f3c08a", "#a6d8b9", "#cbb0dd", "#f4dd8e", "#eaa985",
  "#93cbe0", "#f2a9a2", "#8fd0c0", "#dcc3e6", "#b8d99a", "#f6c27a",
  "#b7c2cc", "#f5b8b0", "#a9dfe0", "#d3b48c",
];
function areaColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return AREA_PALETTE[h % AREA_PALETTE.length];
}

// Joins opportunity scores onto whichever polygon surface we have, stamping
// `__opp` (score), `__lown` (low-data flag) and `__fill` (distinct area colour)
// per feature so the paint is source-agnostic.
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
          __fill: areaColor(name ?? ""),
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
  poiTypes,
  hiddenTypes,
  onLayerLoading,
  sellMode = false,
  sellPin = null,
  onSellPin,
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
  poiTypes: PoiType[];
  hiddenTypes: Record<string, string[]>;
  onLayerLoading?: (key: string, loading: boolean) => void;
  sellMode?: boolean;
  sellPin?: [number, number] | null;
  onSellPin?: (pin: [number, number]) => void;
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
  const poiTypesRef = useRef(poiTypes);
  poiTypesRef.current = poiTypes;
  const hiddenTypesRef = useRef(hiddenTypes);
  hiddenTypesRef.current = hiddenTypes;
  const onLayerLoadingRef = useRef(onLayerLoading);
  onLayerLoadingRef.current = onLayerLoading;
  const sellMarkerRef = useRef<maplibregl.Marker | null>(null);
  const onSellPinRef = useRef(onSellPin);
  onSellPinRef.current = onSellPin;
  // Cache fetched category/overlay geojson so a theme swap re-adds without refetch.
  const poiDataRef = useRef<Map<string, FeatureCollection>>(new Map());
  const markersRef = useRef<HTMLElement[]>([]);

  // Lazy category/overlay layers: fetch on first toggle-on (cached), then just
  // flip visibility. Heavy layers (water, 8.4 MB) report a loading state. Reads
  // refs so it stays stable and is safe to call from map events + effects.
  const applyPoi = useCallback(async (map: maplibregl.Map) => {
    const state = poiStateRef.current;
    registerTypeIcons(map, poiTypesRef.current); // idempotent; ensures per-type images exist
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
            const res = await fetch(cfg.file, { cache: "no-store" });
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
      setHiddenTypes(map, key, hiddenTypesRef.current[key] ?? []); // per-type filtering
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
      updateLabelVisibility(map, markersRef);
      readyRef.current = true;
      applySelection(map, selectedRef.current, bundleRef.current);
      applyVisibility(map, layersRef.current, geo, pal);
      applyOpportunity(map, geo, oppRef.current, showOppRef.current);
      void applyPoi(map);
    };
    map.on("load", initLayers);
    map.on("zoom", () => updateLabelVisibility(map, markersRef));
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
          const emoji = p.emoji ? `${String(p.emoji)} ` : "";
          const kind = String(p.subcategory || p.type || "").replace(/_/g, " ");
          popup(
            map,
            e.lngLat,
            `<b>${emoji}${esc(String(p.name || "POI"))}</b><br/><span style="color:#8a94a5">${esc(kind)}${p.neighborhood ? " · " + esc(String(p.neighborhood)) : ""}</span>`,
          );
          return;
        }
      }
      const clickable = ["opp-fill"].filter((id) => map.getLayer(id));
      const hits = map.queryRenderedFeatures(e.point, { layers: clickable });
      const name = hits.length > 0 ? areaNameOf(hits[0].properties as Record<string, unknown>) : null;
      if (name) {
        onSelectRef.current(name);
      } else {
        onOutsideRef.current();
      }
    });
    for (const lyr of ["opp-fill", "poi", "cmp-pts", "future-pts", "area-prices", "listings"]) {
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
  }, [poiState, poiTypes, hiddenTypes, applyPoi]);

  // Seller "drop a pin" mode — a draggable 📍 marker whose position feeds the
  // valuation form (onSellPin). Placed at the current pin, else the selected
  // area's centre, else the map centre; removed when leaving sell mode.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (!sellMode) {
      sellMarkerRef.current?.remove();
      sellMarkerRef.current = null;
      return;
    }
    if (sellMarkerRef.current) return;
    let lngLat: [number, number];
    if (sellPin) {
      lngLat = sellPin;
    } else {
      const c = selectedRef.current ? bundleRef.current.results[selectedRef.current]?.centroid : null;
      lngLat = (c as [number, number]) ?? [map.getCenter().lng, map.getCenter().lat];
    }
    const el = document.createElement("div");
    el.textContent = "📍";
    el.style.cssText = "font-size:30px;cursor:grab;line-height:1;filter:drop-shadow(0 2px 3px rgba(0,0,0,.45))";
    const marker = new maplibregl.Marker({ element: el, draggable: true, anchor: "bottom" }).setLngLat(lngLat).addTo(map);
    marker.on("dragend", () => {
      const p = marker.getLngLat();
      onSellPinRef.current?.([p.lng, p.lat]);
    });
    sellMarkerRef.current = marker;
    onSellPinRef.current?.(lngLat);
    map.flyTo({ center: lngLat, zoom: Math.max(map.getZoom(), 13) });
  }, [sellMode, sellPin]);

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
  // Areas are now the Voronoi cells (distinct colour + border via the "opp"
  // layers above); the old approximate-circle overlay (nbhd-*) is retired.
}

// Opportunity choropleth over the Voronoi tessellation when present, else the
// approximate neighbourhood polygons. Data-driven on the stamped `__opp` score;
// features with no score (< 0) render transparent. Inserted beneath "poi" so POI
// dots and neighbourhood outlines stay legible on top.
function addOpportunityLayer(map: maplibregl.Map) {
  if (map.getSource("opp")) return;
  map.addSource("opp", { type: "geojson", data: EMPTY });
  // Transparent fill — kept ONLY so clicking inside an area selects it. No colour
  // (colours washed out the place names); the border lines below define the areas,
  // Google-Maps style, and the basemap's own city/town labels show through.
  map.addLayer(
    {
      id: "opp-fill",
      type: "fill",
      source: "opp",
      paint: { "fill-color": "#000000", "fill-opacity": 0.001 },
    },
    "poi",
  );
  // Crisp border lines between areas — the separation, no fill.
  map.addLayer(
    {
      id: "opp-border",
      type: "line",
      source: "opp",
      paint: {
        "line-color": "rgba(70,82,98,0.5)",
        "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0.4, 11, 0.9, 15, 1.6],
        "line-opacity": 0.75,
      },
    },
    "poi",
  );
  // Selection outline for the clicked cell — its whole shape to its borders.
  map.addLayer(
    {
      id: "opp-sel",
      type: "line",
      source: "opp",
      filter: ["==", ["get", "__area"], "__none__"],
      paint: { "line-color": "#1d4ed8", "line-width": 3, "line-opacity": 0.95 },
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

// Secondary labels (every other area cell across Jordan) read lighter and smaller
// than the curated primary labels, so the map fills with names without shouting.
function markerCssSecondary(pal: MapPalette): string {
  return `font:500 10px "IBM Plex Sans",sans-serif;letter-spacing:.04em;color:${pal.markerColor};opacity:.72;text-shadow:${pal.markerShadow};pointer-events:none;white-space:nowrap;`;
}

// Largest span of a polygon ring in degrees — a proxy for how much map room the
// cell owns. Big (sparse, outer-Jordan) cells earn an early label; tiny (dense
// Amman) cells only reveal on zoom-in, so labels never collide into mush.
function cellSpanDeg(coords: number[][][]): number {
  const ring = coords[0] ?? [];
  if (ring.length === 0) return 0;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of ring) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return Math.max(maxX - minX, maxY - minY);
}

// Bigger cell → lower reveal zoom. Tuned so outer-governorate cells (Aqaba, Ma'an,
// Karak…) name themselves at the country view while Amman's fine mesh waits.
function spanToMinZoom(span: number): number {
  if (span >= 0.15) return 6.5;
  if (span >= 0.07) return 8;
  if (span >= 0.035) return 9.5;
  if (span >= 0.015) return 11;
  return 12.5;
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
  const curated = new Set<string>();
  for (const f of geo.neighborhoods.features) {
    const name = f.properties.neighborhood;
    curated.add(name.trim().toLowerCase());
    const el = document.createElement("div");
    el.textContent = name;
    el.style.cssText = css;
    const isCity = (f.properties as { kind?: string }).kind === "city";
    el.dataset.minzoom = String(isCity ? 7.3 : 11);
    new maplibregl.Marker({ element: el }).setLngLat(polygonCentroid(f.geometry.coordinates)).addTo(map);
    markersRef.current.push(el);
  }
  // Every OTHER area cell nationwide (the Voronoi tessellation) — so the whole of
  // Jordan reads as named, not just Amman. Size-gated: large outer cells label at
  // the country view, dense inner cells reveal on zoom-in. Skip names already shown
  // as a curated label to avoid doubling.
  const secondaryCss = markerCssSecondary(pal);
  for (const f of geo.voronoi?.features ?? []) {
    const name = (f.properties as { neighborhood?: string }).neighborhood;
    if (!name || curated.has(name.trim().toLowerCase())) continue;
    if (f.geometry.type !== "Polygon") continue;
    const el = document.createElement("div");
    el.textContent = name;
    el.style.cssText = secondaryCss;
    el.dataset.minzoom = String(spanToMinZoom(cellSpanDeg(f.geometry.coordinates)));
    new maplibregl.Marker({ element: el }).setLngLat(polygonCentroid(f.geometry.coordinates)).addTo(map);
    markersRef.current.push(el);
  }
}

// Each label carries its own reveal zoom (dataset.minzoom): governorate capitals
// and big outer cells from the country view, dense Amman names on zoom-in. This
// fills the whole map with names while never letting them collide into mush.
function updateLabelVisibility(map: maplibregl.Map, markersRef: { current: HTMLElement[] }) {
  const z = map.getZoom();
  for (const el of markersRef.current) {
    const minZoom = Number(el.dataset.minzoom ?? "11");
    el.style.display = z >= minZoom ? "" : "none";
  }
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
