// Copies the real pipeline GeoJSON into public/ so the dev server and build
// serve the actual processed data (roads / POIs / neighborhoods). Re-run on
// every dev/build start, so the frontend always reflects the latest pipeline
// output. If the Decision Engine has emitted sample_output.json, it is copied
// to public/engine_output.json and the app loads it in place of the mock.
import { existsSync, mkdirSync, copyFileSync, statSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const repoRoot = resolve(webRoot, "..", "..");
const processed = resolve(repoRoot, "data", "processed");
const engineDir = resolve(repoRoot, "app", "engine");
const publicData = resolve(webRoot, "public", "data");

mkdirSync(publicData, { recursive: true });

const geo = [
  "neighborhoods.geojson",
  "poi.geojson",
  "roads.geojson",
  "zoning.geojson",
  // Gap-free Voronoi surface (290 cells) + baked opportunity heatmap. Optional —
  // the app falls back to the 5 approximate circles if these are absent.
  "neighborhoods_voronoi.geojson",
  "opportunity_heatmap.geojson",
  // Nationwide POI layers, one file per GROUP; each feature carries its curated
  // type + emoji (scrapers/poi_taxonomy.py). Plus the taxonomy manifest and the
  // per-area type counts the layer panel reads.
  "poi_education.geojson",
  "poi_health.geojson",
  "poi_shopping.geojson",
  "poi_food.geojson",
  "poi_recreation.geojson",
  "poi_religious.geojson",
  "poi_transport.geojson",
  "poi_services.geojson",
  "poi_negative.geojson",
  "poi_types.json",
  "area_poi_counts.json",
  "water.geojson",
  "green.geojson",
  "major_roads.geojson",
  // Nationwide price layers (scrapers/export_map_full.py): every geocoded listing
  // as a point + median asking JD/m2 per neighbourhood. Optional — map still works
  // without them.
  "listings.geojson",
  "area_prices.geojson",
];
let copied = 0;
for (const f of geo) {
  const src = resolve(processed, f);
  if (existsSync(src)) {
    copyFileSync(src, resolve(publicData, f));
    const kb = (statSync(src).size / 1024).toFixed(0);
    console.log(`  data/${f}  (${kb} KB)`);
    copied++;
  } else {
    console.warn(`  MISSING: ${src}`);
  }
}

const engineOut = resolve(engineDir, "sample_output.json");
if (existsSync(engineOut)) {
  copyFileSync(engineOut, resolve(webRoot, "public", "engine_output.json"));
  console.log("  engine_output.json  (real Decision Engine output wired)");
} else {
  console.log("  engine_output.json not present — app falls back to mock_recommendation.json");
}

// Minimal CSV parser (RFC-4180 quotes). Enough for the amenities table, which
// has one quoted free-text `notes` column.
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row); }
  return rows;
}

// area_amenities.csv → public/data/area_amenities.json, keyed by neighborhood, so
// the "What's nearby" panel reads it client-side (no backend change).
const amenitiesCsv = resolve(processed, "area_amenities.csv");
if (existsSync(amenitiesCsv)) {
  const rows = parseCsv(readFileSync(amenitiesCsv, "utf8"));
  const header = rows[0];
  const numeric = new Set(header.filter((h) => h.endsWith("_n") || h.startsWith("km_")));
  const out = {};
  for (const r of rows.slice(1)) {
    if (r.length < header.length) continue;
    const rec = {};
    header.forEach((h, i) => {
      const v = r[i];
      rec[h] = numeric.has(h) ? (v === "" ? 0 : Number(v)) : v;
    });
    if (rec.neighborhood) out[rec.neighborhood] = rec;
  }
  writeFileSync(resolve(publicData, "area_amenities.json"), JSON.stringify(out));
  console.log(`  area_amenities.json  (${Object.keys(out).length} areas)`);
} else {
  console.warn(`  MISSING: ${amenitiesCsv}`);
}

console.log(`prepare-data: ${copied}/${geo.length} GeoJSON layers ready.`);
