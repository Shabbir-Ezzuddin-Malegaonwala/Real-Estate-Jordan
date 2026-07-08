// Composes plain-language text from the SAME evidence objects the panels show —
// no new facts invented. Every sentence traces to an evidence row or a band
// figure already on screen. Labelled a "draft" in the UI; the retrieval-grounded
// AI will replace this once wired.
import type { OpportunityScore, RecommendationResult } from "../types";
import { jd } from "./format";

function positives(r: RecommendationResult): string[] {
  return r.evidence_objects
    .filter((e) => e.category === "current_state" && e.direction === "increase")
    .map((e) => e.factor.toLowerCase());
}

function futureDrivers(r: RecommendationResult): string[] {
  return r.evidence_objects
    .filter((e) => e.category === "future_signal")
    .map((e) => e.factor.toLowerCase());
}

// AGENT — a client-ready listing paragraph grounded in the evidenced band.
export function salesNarrative(r: RecommendationResult): string {
  const pos = positives(r);
  const fut = futureDrivers(r);
  const parts: string[] = [];

  parts.push(
    `Positioned in ${r.neighborhood}, this ${r.property_type.toLowerCase()} sits within an evidenced range of ${jd(r.min_safe_jd_m2)}–${jd(r.premium_jd_m2)} JD/m², with a defensible asking level around ${jd(r.recommended_jd_m2)} JD/m².`,
  );

  if (pos.length > 0) {
    const list = pos.slice(0, 3).join(", ");
    parts.push(`Its value is supported by ${list} — each reflected in comparable sales, not asserted.`);
  }

  if (fut.length > 0) {
    parts.push(
      `Looking forward, ${fut.slice(0, 2).join(" and ")} position the area for appreciation, strengthening the case beyond today's comparables.`,
    );
  }

  parts.push(
    `The figure is decision-support built from ${r.comps_considered ?? r.comparables.length} comparable listings with a ${r.confidence.level.toLowerCase()}-confidence read — every adjustment is traceable to its source.`,
  );

  return parts.join(" ");
}

// BUYER — an honest "is this fair / is the area good / what's the catch" read.
export function buyerSummary(
  r: RecommendationResult,
  opp: OpportunityScore | null,
): { fairness: string; area: string; redFlags: string[] } {
  const pos = positives(r);
  const fairness = `A fair price here lands between ${jd(r.min_safe_jd_m2)} and ${jd(r.premium_jd_m2)} JD per m², centred near ${jd(r.recommended_jd_m2)}. Below ${jd(r.min_safe_jd_m2)} looks like a genuine deal; well above ${jd(r.premium_jd_m2)} you're paying a premium the comparable evidence doesn't yet support.`;

  const areaBits: string[] = [];
  if (opp) {
    const lvl = opp.score >= 66 ? "strong" : opp.score >= 40 ? "moderate" : "softer";
    areaBits.push(`${r.neighborhood} scores ${opp.score}/100 on our opportunity index — a ${lvl} area on price level, demand and competition.`);
  }
  if (pos.length > 0) areaBits.push(`Buyers here pay for ${pos.slice(0, 3).join(", ")}.`);
  const area = areaBits.join(" ") || `${r.neighborhood} is one of our covered submarkets.`;

  const redFlags: string[] = r.risk_factors
    .filter((rf) => rf.severity !== "low")
    .slice(0, 3)
    .map((rf) => rf.detail || rf.title);
  if (r.confidence.level === "Low") {
    redFlags.push("Confidence is low for this area — treat the figure as indicative and verify with a local agent.");
  }

  return { fairness, area, redFlags };
}
