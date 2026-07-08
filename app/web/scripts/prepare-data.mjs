// Copies the real pipeline GeoJSON into public/ so the dev server and build
// serve the actual processed data (roads / POIs / neighborhoods). Re-run on
// every dev/build start, so the frontend always reflects the latest pipeline
// output. If the Decision Engine has emitted sample_output.json, it is copied
// to public/engine_output.json and the app loads it in place of the mock.
import { existsSync, mkdirSync, copyFileSync, statSync } from "node:fs";
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

console.log(`prepare-data: ${copied}/${geo.length} GeoJSON layers ready.`);
