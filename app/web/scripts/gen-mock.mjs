// Generates public/mock_recommendation.json — an internally-consistent
// RecommendationBundle used until the Decision Engine emits sample_output.json.
// The waterfall math is real: recommended = base * Π(1 + current_state pct).
// Numbers are illustrative placeholders (clearly flagged in the UI disclaimer);
// the SHAPE is the contract the engine must satisfy.
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const repoRoot = resolve(webRoot, "..", "..");
const nbhdPath = resolve(repoRoot, "data", "processed", "neighborhoods.geojson");

function centroids() {
  const out = {};
  if (!existsSync(nbhdPath)) return out;
  const gj = JSON.parse(readFileSync(nbhdPath, "utf-8"));
  for (const f of gj.features) {
    const name = f.properties.neighborhood;
    let sx = 0, sy = 0, n = 0;
    for (const ring of f.geometry.coordinates)
      for (const [x, y] of ring) { sx += x; sy += y; n++; }
    out[name] = [+(sx / n).toFixed(5), +(sy / n).toFixed(5)];
  }
  return out;
}

const CT = centroids();
const AS_OF = "2026-07-06";
const CAP = "2026-07-05";

// Source shorthands ------------------------------------------------------
const S = {
  bayut: (u) => ({ name: "Bayut", url: u || "https://www.bayut.jo/en/amman/apartments-for-sale/", capture_date: CAP }),
  opensooq: (u) => ({ name: "OpenSooq", url: u || "https://jo.opensooq.com/en/real-estate-for-sale/apartments-for-sale", capture_date: CAP }),
  cbj: () => ({ name: "Central Bank of Jordan — Real Estate Price Index", url: "https://www.cbj.gov.jo/Pages/viewpage.aspx?pageID=139", capture_date: "2026-06-30" }),
  dos: () => ({ name: "Dept. of Statistics — Building Permits", url: "http://dosweb.dos.gov.jo/economic/construction/", capture_date: "2026-06-30" }),
  dls: () => ({ name: "Dept. of Lands & Survey — Monthly Trading", url: "https://www.dls.gov.jo/", capture_date: "2026-06-30" }),
  gam: () => ({ name: "Greater Amman Municipality — Master Plan", url: "https://www.amman.jo/", capture_date: "2026-05-20" }),
  news: (n, u, d) => ({ name: n, url: u, capture_date: d }),
};

// Per-neighborhood tuning ------------------------------------------------
const PROFILES = {
  Abdoun: {
    name_ar: "عبدون", base: 1010, tier: "Prime diplomatic / luxury",
    band: [0.14, 0.20], conf: { level: "High", score: 82 },
    current: [
      { factor: "Panoramic / open view", pct: 0.09, conf: "High", method: "paired listing comparison (n=16)", src: [S.bayut(), S.opensooq()], note: "Matched units with unobstructed valley/city view list 9% above equivalent inward-facing units in the same building band." },
      { factor: "High floor (7+)", pct: 0.045, conf: "High", method: "paired comparison (n=22)", src: [S.bayut()], note: "Upper-floor premium isolated by holding view, area and finish constant." },
      { factor: "Covered parking (2 bays)", pct: 0.03, conf: "Medium", method: "attribute regression (n=61)", src: [S.bayut(), S.opensooq()], note: "Two covered bays is the Abdoun norm; absence is penalised more than presence is rewarded." },
      { factor: "Luxury finish", pct: 0.06, conf: "High", method: "finish-class paired comparison (n=12)", src: [S.bayut()], note: "Luxury vs standard finish gap for otherwise-matched Abdoun units." },
      { factor: "Building age > 12 yr", pct: -0.05, conf: "Medium", method: "age-depreciation curve (n=40)", src: [S.bayut(), S.opensooq()], note: "Depreciation applied to older stock relative to <5yr comparables." },
      { factor: "Ask-to-transaction calibration", pct: -0.07, conf: "High", method: "documented discount factor (client PDF, 5–15%)", src: [S.dls()], note: "Listings are asking prices; calibrated to expected transaction level using the mid of the documented gap." },
    ],
    future: [
      { factor: "Abdoun Corridor upgrade", pct: 0.0, conf: "Medium", year: 2027, area: "Abdoun", method: "GAM master-plan corridor", src: [S.gam()], note: "Streetscape and mixed-use frontage upgrade along the Abdoun corridor supports premium positioning; effect is appreciation, not applied to today's band." },
      { factor: "New international school (announced)", pct: 0.0, conf: "Medium", year: 2027, area: "Abdoun / Deir Ghbar", method: "news, cited", src: [S.news("Roya News", "https://en.royanews.tv/", "2026-06-18")], note: "Announced campus strengthens family-buyer demand over a 12–24 month horizon." },
    ],
    risks: [
      { title: "Thin luxury liquidity", severity: "medium", detail: "Absorption at the top of the band is slow; premium pricing depends on 1–2 comparable sales rather than a deep pool." },
      { title: "Ask-price dispersion", severity: "low", detail: "Wide spread between aspirational and realistic listings; confidence relies on the transaction calibration holding." },
    ],
    narrative:
      "Abdoun sits at the top of the Amman apartment market. The evidenced grid places the justified launch band at a premium to the neighbourhood median, driven by view, finish and floor, and disciplined by the ask-to-transaction calibration. Future-signal corridor and amenity upgrades support a raise-later posture rather than a reduction.",
  },
  Dabouq: {
    name_ar: "دابوق", base: 880, tier: "Villa / low-density premium",
    band: [0.15, 0.22], conf: { level: "Medium", score: 71 },
    current: [
      { factor: "Low-density / villa setting", pct: 0.07, conf: "Medium", method: "segment comparison (n=9)", src: [S.bayut()], note: "Premium for plot size and privacy relative to apartment-dense comparables." },
      { factor: "Open mountain view", pct: 0.06, conf: "Medium", method: "paired comparison (n=8)", src: [S.bayut(), S.opensooq()], note: "West-facing open-view units carry a measurable premium." },
      { factor: "New build (<3 yr)", pct: 0.04, conf: "High", method: "age curve (n=18)", src: [S.bayut()], note: "Newer delivery reduces depreciation drag." },
      { factor: "Distance to core services", pct: -0.04, conf: "Medium", method: "POI accessibility (haversine)", src: [S.opensooq()], note: "Fewer within-radius amenities than inner submarkets; mild discount." },
      { factor: "Ask-to-transaction calibration", pct: -0.08, conf: "High", method: "documented discount factor (client PDF)", src: [S.dls()], note: "Larger ask-gap observed for higher-ticket villa listings." },
    ],
    future: [
      { factor: "Airport road widening", pct: 0.0, conf: "High", year: 2027, area: "West Amman", method: "gov announcement, cited", src: [S.news("Jordan Times", "https://www.jordantimes.com/", "2026-05-30")], note: "Improved arterial access shortens effective commute; appreciation driver for outer west submarkets." },
      { factor: "Planned retail node", pct: 0.0, conf: "Low", year: 2028, area: "Dabouq", method: "master-plan, dated", src: [S.gam()], note: "Proposed neighbourhood retail centre would close the amenity gap noted in the current-state discount." },
    ],
    risks: [
      { title: "Small comparable pool", severity: "high", detail: "Villa-class transactions are sparse; the band leans on a handful of listings and carries wider uncertainty." },
      { title: "Amenity dependency", severity: "medium", detail: "Value is sensitive to the future retail/services node materialising on schedule." },
    ],
    narrative:
      "Dabouq is a low-density villa submarket where premium is a function of plot, privacy and view rather than density. Comparable liquidity is thin, so confidence is medium and the band is wider. Future arterial and retail signals underpin an appreciation story for a patient launch.",
  },
  Sweifieh: {
    name_ar: "الصويفية", base: 820, tier: "Commercial-adjacent mid-high",
    band: [0.12, 0.17], conf: { level: "High", score: 79 },
    current: [
      { factor: "Walkable retail proximity", pct: 0.05, conf: "High", method: "POI density (walkability proxy)", src: [S.opensooq()], note: "High within-radius retail/F&B density supports a walkability premium." },
      { factor: "City view", pct: 0.035, conf: "Medium", method: "paired comparison (n=11)", src: [S.bayut()], note: "City-facing units above the podium line." },
      { factor: "Covered parking", pct: 0.03, conf: "Medium", method: "attribute regression (n=54)", src: [S.bayut(), S.opensooq()], note: "Parking scarcity in the commercial core raises the premium for covered bays." },
      { factor: "Street noise / commercial frontage", pct: -0.035, conf: "Medium", method: "paired comparison (n=10)", src: [S.opensooq()], note: "Units on active commercial frontage discount vs set-back residential." },
      { factor: "Ask-to-transaction calibration", pct: -0.06, conf: "High", method: "documented discount factor (client PDF)", src: [S.dls()], note: "Tighter ask-gap in a liquid, transaction-rich submarket." },
    ],
    future: [
      { factor: "BRT feeder extension (study)", pct: 0.0, conf: "Low", year: 2028, area: "South Amman", method: "news, cited", src: [S.news("Ammon News", "https://www.ammonnews.net/", "2026-06-02")], note: "Feasibility-stage transit feeder; low certainty but material if delivered." },
      { factor: "Pedestrianisation pilot", pct: 0.0, conf: "Medium", year: 2027, area: "Sweifieh", method: "GAM programme", src: [S.gam()], note: "Retail-street pedestrianisation would reinforce the walkability premium." },
    ],
    risks: [
      { title: "Mixed-use noise", severity: "medium", detail: "Commercial frontage cuts both ways — footfall lifts retail value but discounts residential quiet." },
      { title: "Supply pipeline", severity: "low", detail: "Steady permit issuance in the corridor could compress premiums if absorption lags." },
    ],
    narrative:
      "Sweifieh trades on walkability and liquidity. A transaction-rich pool gives high confidence and a tighter band. The evidenced grid rewards retail proximity and parking while discounting active-frontage noise. Transit and pedestrianisation signals support a hold-and-raise stance.",
  },
  Khalda: {
    name_ar: "خلدا", base: 720, tier: "Family residential mid",
    band: [0.12, 0.16], conf: { level: "High", score: 80 },
    current: [
      { factor: "School / mosque proximity", pct: 0.045, conf: "High", method: "POI accessibility (haversine)", src: [S.opensooq()], note: "Dense family-amenity cluster supports a family-buyer premium." },
      { factor: "Mid floor (3–6)", pct: 0.02, conf: "Medium", method: "paired comparison (n=19)", src: [S.bayut()], note: "Modest floor premium; ceiling lower than in prime submarkets." },
      { factor: "Semi-furnished", pct: 0.025, conf: "Medium", method: "furnishing paired comparison (n=14)", src: [S.bayut(), S.opensooq()], note: "Semi-furnished units clear faster and list slightly higher." },
      { factor: "Building age 8–12 yr", pct: -0.03, conf: "Medium", method: "age curve (n=33)", src: [S.bayut()], note: "Moderate depreciation for mid-age stock." },
      { factor: "Ask-to-transaction calibration", pct: -0.06, conf: "High", method: "documented discount factor (client PDF)", src: [S.dls()], note: "Standard mid-market ask-gap applied." },
    ],
    future: [
      { factor: "Ring-road interchange upgrade", pct: 0.0, conf: "Medium", year: 2027, area: "NW Amman", method: "gov announcement, cited", src: [S.news("Jordan Times", "https://www.jordantimes.com/", "2026-04-22")], note: "Interchange upgrade improves connectivity for the north-west residential belt." },
      { factor: "New community park (planned)", pct: 0.0, conf: "Low", year: 2028, area: "Khalda", method: "master-plan, dated", src: [S.gam()], note: "Planned green space would lift the amenity score of adjacent blocks." },
    ],
    risks: [
      { title: "Elastic mid-market supply", severity: "medium", detail: "Family mid-market has the deepest pipeline; over-pricing risks slow absorption against ample alternatives." },
    ],
    narrative:
      "Khalda is a deep, liquid family submarket. Value is driven by amenity access and unit practicality rather than luxury attributes. High comparable density gives strong confidence and a tight band; the main discipline is not over-reaching against elastic supply.",
  },
  Shmeisani: {
    name_ar: "الشميساني", base: 760, tier: "Business-district mid-high",
    band: [0.12, 0.18], conf: { level: "Medium", score: 74 },
    current: [
      { factor: "Business-district centrality", pct: 0.05, conf: "High", method: "accessibility (road hierarchy)", src: [S.opensooq()], note: "Proximity to the CBD and offices supports a rental-led premium." },
      { factor: "Rental-yield support", pct: 0.03, conf: "Medium", method: "yield = annual rent/m² ÷ sale/m² (n=27)", src: [S.bayut(), S.opensooq()], note: "Above-median gross yield underpins investor demand and the sale premium." },
      { factor: "City view (upper floors)", pct: 0.03, conf: "Medium", method: "paired comparison (n=9)", src: [S.bayut()], note: "Upper-floor city view over the district." },
      { factor: "Older core stock", pct: -0.055, conf: "Medium", method: "age curve (n=29)", src: [S.bayut(), S.opensooq()], note: "A share of the core is ageing; depreciation applied vs newer infill." },
      { factor: "Ask-to-transaction calibration", pct: -0.06, conf: "High", method: "documented discount factor (client PDF)", src: [S.dls()], note: "Standard ask-gap; slightly tighter for investor-grade units." },
    ],
    future: [
      { factor: "Office-to-residential conversions", pct: 0.0, conf: "Medium", year: 2027, area: "Shmeisani", method: "market news, cited", src: [S.news("Ammon News", "https://www.ammonnews.net/", "2026-06-11")], note: "Adaptive reuse trend tightens residential supply in the core." },
      { factor: "CBJ index uptrend", pct: 0.0, conf: "High", year: 2026, area: "Amman", method: "official time series", src: [S.cbj()], note: "Time-adjustment factor from the CBJ Real Estate Price Index trends positive for Amman apartments." },
    ],
    risks: [
      { title: "Ageing core", severity: "medium", detail: "Mixed building vintages widen dispersion; the band assumes a mid-vintage subject." },
      { title: "Office-cycle sensitivity", severity: "low", detail: "Demand is partly tied to the commercial office cycle." },
    ],
    narrative:
      "Shmeisani is a business-district submarket where yield and centrality drive value against an ageing core. Confidence is medium given vintage dispersion. Conversion pressure and a positive official index trend support the appreciation narrative behind a firm launch band.",
  },
};

function build(nb, p) {
  const factor = p.current.reduce((a, e) => a * (1 + e.pct), 1);
  const recommended = Math.round((p.base * factor) / 5) * 5;
  const minSafe = Math.round((recommended * (1 - p.band[0])) / 5) * 5;
  const premium = Math.round((recommended * (1 + p.band[1])) / 5) * 5;

  const mk = (e, category) => ({
    factor: e.factor,
    adjustment: `${e.pct > 0 ? "+" : e.pct < 0 ? "−" : "±"}${Math.abs(e.pct * 100).toFixed(1)}%`,
    adjustment_pct: e.pct,
    direction: e.pct > 0 ? "increase" : e.pct < 0 ? "decrease" : "neutral",
    confidence: e.conf,
    method: e.method,
    datasets: category === "future_signal" ? ["evidence_items"] : ["listings"],
    sources: e.src,
    category,
    explanation: e.note,
    expected_year: e.year ?? null,
    impact_area: e.area ?? null,
  });

  const evidence = [
    ...p.current.map((e) => mk(e, "current_state")),
    ...p.future.map((e) => mk(e, "future_signal")),
  ];

  return {
    neighborhood: nb,
    name_ar: p.name_ar,
    tier: p.tier,
    property_type: "apartment",
    as_of: AS_OF,
    currency: "JOD",
    unit: "JD/m²",
    base_value_jd_m2: p.base,
    min_safe_jd_m2: minSafe,
    recommended_jd_m2: recommended,
    premium_jd_m2: premium,
    confidence: {
      level: p.conf.level,
      score: p.conf.score,
      range_low: minSafe,
      range_high: premium,
      drivers: [
        `${p.current.length} evidenced adjustments`,
        `${comps(nb, p).length} comparables`,
        p.conf.level === "High" ? "low dispersion" : "moderate dispersion",
        "recent captures (≤30d)",
      ],
    },
    evidence_objects: evidence,
    comparables: comps(nb, p),
    risk_factors: p.risks,
    narrative: p.narrative,
    centroid: CT[nb] ?? null,
  };
}

function comps(nb, p) {
  const views = ["city", "panoramic", "garden", "none", "mountain"];
  const portals = ["Bayut", "OpenSooq"];
  const rng = seeded(nb);
  const [clon, clat] = CT[nb] ?? [35.85, 31.97];
  const n = 5 + Math.floor(rng() * 3);
  const out = [];
  for (let i = 0; i < n; i++) {
    const area = 120 + Math.round(rng() * 140);
    const ppm = Math.round((p.base * (0.82 + rng() * 0.5)) / 5) * 5;
    const portal = portals[Math.floor(rng() * portals.length)];
    const dist = +(0.2 + rng() * 1.6).toFixed(2);
    const ang = rng() * Math.PI * 2;
    const lat = +(clat + (dist / 111) * Math.sin(ang)).toFixed(5);
    const lng = +(clon + (dist / (111 * Math.cos((clat * Math.PI) / 180))) * Math.cos(ang)).toFixed(5);
    out.push({
      id: `${nb.toLowerCase()}-cmp-${i + 1}`,
      portal,
      neighborhood: nb,
      price_jd: ppm * area,
      area_m2: area,
      price_per_m2: ppm,
      bedrooms: 2 + Math.floor(rng() * 3),
      floor_level: 1 + Math.floor(rng() * 9),
      view: views[Math.floor(rng() * views.length)],
      building_age_years: Math.floor(rng() * 18),
      seller_type: rng() > 0.6 ? "agent" : "private",
      url:
        portal === "Bayut"
          ? "https://www.bayut.jo/en/amman/apartments-for-sale/"
          : "https://jo.opensooq.com/en/real-estate-for-sale/apartments-for-sale",
      capture_date: CAP,
      distance_km: dist,
      similarity: +(0.6 + rng() * 0.38).toFixed(2),
      lat,
      lng,
    });
  }
  return out.sort((a, b) => b.similarity - a.similarity);
}

function seeded(str) {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function () {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
}

const results = {};
for (const [nb, p] of Object.entries(PROFILES)) results[nb] = build(nb, p);

const bundle = {
  generated_at: new Date().toISOString(),
  engine_version: "mock-0.1 (shape-compatible with Decision Engine RecommendationResult)",
  disclaimer:
    "Illustrative figures for interface demonstration. Price bands are placeholders pending the Decision Engine; the data shape is the production contract. Neighborhood polygons are approximate circles.",
  currency: "JOD",
  unit: "JD/m²",
  results,
};

const outDir = resolve(webRoot, "public");
mkdirSync(outDir, { recursive: true });
writeFileSync(resolve(outDir, "mock_recommendation.json"), JSON.stringify(bundle, null, 2));
console.log(`gen-mock: wrote ${Object.keys(results).length} neighborhoods → public/mock_recommendation.json`);
