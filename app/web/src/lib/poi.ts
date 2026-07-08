// Config-driven POI amenity layers + geo overlays. The map and the layer control
// both read these tables so a category is defined once. Colours are mid-saturation
// so they read on both the light and dark basemaps.

export interface PoiCategory {
  key: string;
  label: string;
  color: string;
  icon: string; // emoji — used in the control legend + amenity panel, NOT on the GL map
  file: string;
}

export const POI_CATEGORIES: PoiCategory[] = [
  { key: "education", label: "Education", color: "#5fb2c9", icon: "🎓", file: "/data/poi_education.geojson" },
  { key: "health", label: "Health", color: "#c9736f", icon: "🏥", file: "/data/poi_health.geojson" },
  { key: "shopping", label: "Shopping", color: "#e6a94b", icon: "🛍️", file: "/data/poi_shopping.geojson" },
  { key: "food_leisure", label: "Food & Leisure", color: "#d0894f", icon: "🍽️", file: "/data/poi_food_leisure.geojson" },
  { key: "recreation", label: "Recreation", color: "#5fa47f", icon: "🌳", file: "/data/poi_recreation.geojson" },
  { key: "religious", label: "Religious", color: "#8b93a4", icon: "🕌", file: "/data/poi_religious.geojson" },
  { key: "transport", label: "Transport", color: "#c9a75f", icon: "🚌", file: "/data/poi_transport.geojson" },
  { key: "services", label: "Services", color: "#7f8fd0", icon: "🏦", file: "/data/poi_services.geojson" },
  { key: "negative", label: "Negatives", color: "#b06a8f", icon: "⚠️", file: "/data/poi_negative.geojson" },
];

export interface GeoOverlay {
  key: string;
  label: string;
  icon: string;
  file: string;
  kind: "fill" | "line";
  color: string;
  heavy?: boolean; // large file — lazy-load with a loading state (water is 8.4 MB)
}

export const GEO_OVERLAYS: GeoOverlay[] = [
  { key: "water", label: "Water", icon: "💧", file: "/data/water.geojson", kind: "fill", color: "#5b8fb0", heavy: true },
  { key: "green", label: "Green / parks", icon: "🌿", file: "/data/green.geojson", kind: "fill", color: "#6fa06f" },
  { key: "major_roads", label: "Major roads", icon: "🛣️", file: "/data/major_roads.geojson", kind: "line", color: "#b8804a" },
];

// Default-on so the map is informative but not cluttered on first load.
export const DEFAULT_POI_ON = ["transport", "education"];

// --- Per-area amenity counts (area_amenities.json, keyed by neighborhood) ------

export interface AreaAmenities {
  schools_n: number;
  universities_n: number;
  hospitals_n: number;
  pharmacies_n: number;
  malls_n: number;
  supermarkets_n: number;
  restaurants_n: number;
  cafes_n: number;
  hotels_n: number;
  parks_n: number;
  playgrounds_n: number;
  stadiums_n: number;
  sports_n: number;
  mosques_n: number;
  churches_n: number;
  banks_n: number;
  atms_n: number;
  fuel_n: number;
  transport_n: number;
  police_n: number;
  negatives_n: number;
  total_poi_n: number;
  nearest_airport: string;
  km_to_airport: number;
  km_to_highway: number;
}

// Groups the flat counts into the amenity panel, mirroring the map categories.
export const AMENITY_GROUPS: {
  key: string;
  label: string;
  icon: string;
  color: string;
  items: { field: keyof AreaAmenities; label: string }[];
}[] = [
  { key: "education", label: "Education", icon: "🎓", color: "#5fb2c9", items: [
    { field: "schools_n", label: "Schools" }, { field: "universities_n", label: "Universities" } ] },
  { key: "health", label: "Health", icon: "🏥", color: "#c9736f", items: [
    { field: "hospitals_n", label: "Hospitals" }, { field: "pharmacies_n", label: "Pharmacies" } ] },
  { key: "shopping", label: "Shopping", icon: "🛍️", color: "#e6a94b", items: [
    { field: "malls_n", label: "Malls" }, { field: "supermarkets_n", label: "Supermarkets" } ] },
  { key: "food_leisure", label: "Food & Leisure", icon: "🍽️", color: "#d0894f", items: [
    { field: "restaurants_n", label: "Restaurants" }, { field: "cafes_n", label: "Cafés" }, { field: "hotels_n", label: "Hotels" } ] },
  { key: "recreation", label: "Recreation", icon: "🌳", color: "#5fa47f", items: [
    { field: "parks_n", label: "Parks" }, { field: "playgrounds_n", label: "Playgrounds" },
    { field: "stadiums_n", label: "Stadiums" }, { field: "sports_n", label: "Sports" } ] },
  { key: "religious", label: "Religious", icon: "🕌", color: "#8b93a4", items: [
    { field: "mosques_n", label: "Mosques" }, { field: "churches_n", label: "Churches" } ] },
  { key: "services", label: "Services", icon: "🏦", color: "#7f8fd0", items: [
    { field: "banks_n", label: "Banks" }, { field: "atms_n", label: "ATMs" },
    { field: "fuel_n", label: "Fuel" }, { field: "police_n", label: "Police" } ] },
  { key: "transport", label: "Transport", icon: "🚌", color: "#c9a75f", items: [
    { field: "transport_n", label: "Transport stops" } ] },
  { key: "negative", label: "Negatives", icon: "⚠️", color: "#b06a8f", items: [
    { field: "negatives_n", label: "Nuisances nearby" } ] },
];
