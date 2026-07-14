// Mock DataSource implementing the UI contract. The fresh UI builds against THIS.
// Later, an adapter over the real engine implements the same DataSource interface — UI unchanged.
import type { AreaBundle, AreaListItem, AreaSummary, DataSource } from "./contract";

type Seed = {
  price: number; minSafe: number; premium: number; conf: AreaSummary["confidence"]; dots: 1 | 2 | 3;
  comps: number; land: number; margin: number; trend: number[]; c: [number, number];
  sc: number; un: number; ho: number; bs: number;
};

const SEEDS: Record<string, Seed> = {
  Abdoun: { price: 918, minSafe: 597, premium: 1239, conf: "Good", dots: 2, comps: 12, land: 480, margin: 22, trend: [905, 910, 912, 908, 915, 918, 916, 918], c: [35.88, 31.94], sc: 17, un: 3, ho: 1, bs: 8 },
  Dabouq: { price: 950, minSafe: 618, premium: 1283, conf: "Good", dots: 2, comps: 12, land: 510, margin: 20, trend: [930, 940, 935, 945, 948, 950, 949, 950], c: [35.80, 31.99], sc: 6, un: 1, ho: 0, bs: 3 },
  Sweifieh: { price: 839, minSafe: 545, premium: 1133, conf: "Good", dots: 2, comps: 12, land: 410, margin: 24, trend: [820, 825, 830, 828, 835, 839, 838, 839], c: [35.86, 31.95], sc: 11, un: 2, ho: 2, bs: 6 },
  Shmeisani: { price: 696, minSafe: 506, premium: 885, conf: "Strong", dots: 3, comps: 16, land: 330, margin: 26, trend: [690, 692, 695, 694, 696, 695, 696, 696], c: [35.90, 31.96], sc: 9, un: 4, ho: 3, bs: 5 },
  Khalda: { price: 672, minSafe: 482, premium: 863, conf: "Good", dots: 2, comps: 12, land: 300, margin: 25, trend: [665, 668, 670, 669, 672, 671, 672, 672], c: [35.82, 31.97], sc: 8, un: 1, ho: 1, bs: 4 },
  "Deir Ghbar": { price: 1020, minSafe: 660, premium: 1360, conf: "Good", dots: 2, comps: 9, land: 560, margin: 19, trend: [1000, 1010, 1015, 1012, 1020, 1018, 1020, 1020], c: [35.84, 31.98], sc: 5, un: 1, ho: 0, bs: 2 },
  Jubeiha: { price: 560, minSafe: 410, premium: 720, conf: "Good", dots: 2, comps: 14, land: 240, margin: 27, trend: [555, 558, 560, 559, 562, 561, 560, 560], c: [35.87, 32.02], sc: 12, un: 5, ho: 2, bs: 6 },
  "Marj Al Hamam": { price: 470, minSafe: 350, premium: 610, conf: "Fair", dots: 1, comps: 7, land: 190, margin: 28, trend: [465, 468, 470, 469, 472, 471, 470, 470], c: [35.83, 31.88], sc: 6, un: 0, ho: 1, bs: 3 },
};

function summary(name: string, s: Seed): AreaSummary {
  return {
    name, status: "READY", price: s.price, minSafe: s.minSafe, premium: s.premium,
    confidence: s.conf, confidenceDots: s.dots, comps: s.comps, trend: s.trend,
    land: s.land, margin: s.margin,
    amenities: { schools: s.sc, universities: s.un, hospitals: s.ho, busStops: s.bs },
    centroid: s.c,
  };
}

function bundle(name: string, s: Seed): AreaBundle {
  return {
    summary: summary(name, s),
    pricing: {
      summary: summary(name, s),
      reasons: [
        { ok: true, text: "Near public transport" },
        { ok: true, text: "Open view" },
        { ok: false, text: "Irregular plot shape" },
      ],
      comparables: [
        { size: 180, asking: 1139, adjusted: 1139 },
        { size: 172, asking: 1000, adjusted: 1000 },
        { size: 165, asking: 667, adjusted: 667 },
      ],
    },
    costProfit: { landValueK: s.land, marginPct: s.margin, buildCostJdM2: 330, finish: "Standard", plotSizeDunum: 1.25 },
    market: {
      status: "Market stable", changesThisWeek: 4,
      news: [
        { date: "Oct 24", text: "A competitor launched 150 units nearby at 780 JD/m².", action: "Consider holding your price." },
        { date: "Oct 20", text: "New road project approved nearby — usually lifts prices over time." },
        { date: "Oct 15", text: "Construction material prices steady this month." },
      ],
      competitors: [
        { name: "Abdoun Terraces", price: 1620 }, { name: "The Gate", price: 980 }, { name: "Skyline Res.", price: 1050 },
      ],
      trend: s.trend,
    },
    location: {
      verdicts: [
        { tag: "good", title: "Education", subtitle: `${s.sc} schools + ${s.un} universities within 1 km — above the area average.` },
        s.ho >= 1
          ? { tag: "good", title: "Healthcare", subtitle: `${s.ho} hospital(s) within 1 km.` }
          : { tag: "watch", title: "Healthcare", subtitle: "No hospital within 1 km — nearest is a short drive." },
        { tag: "good", title: "Transport", subtitle: `${s.bs} bus stops within 1 km.` },
      ],
      infrastructure: [
        { when: "2028", text: "Planned metro line ~1.2 km away — typically lifts prices ~8%." },
        { when: "Now", text: "BRT bus line operational nearby." },
      ],
    },
  };
}

export const mockSource: DataSource = {
  listAreas(): AreaListItem[] {
    return Object.entries(SEEDS).map(([name, s]) => ({ name, price: s.price, centroid: s.c }));
  },
  getBundle(area: string): AreaBundle | null {
    const s = SEEDS[area];
    return s ? bundle(area, s) : null;
  },
};
