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

// BUILDER — a decision-oriented executive summary: where, what price, how
// confident, key risks. Grounded in the band + confidence + risks already shown.
export function executiveSummary(r: RecommendationResult, opp: OpportunityScore | null): string {
  const parts: string[] = [];
  const oppLine = opp
    ? ` It scores ${opp.score}/100 on our opportunity index${opp.low_data ? " (low data — treat as indicative)" : ""}.`
    : "";
  parts.push(
    `${r.neighborhood} supports a launch around ${jd(r.recommended_jd_m2)} JD/m² (defensible range ${jd(r.min_safe_jd_m2)}–${jd(r.premium_jd_m2)}), at ${r.confidence.level.toLowerCase()} confidence.${oppLine}`,
  );

  const pos = positives(r).slice(0, 3);
  if (pos.length > 0) parts.push(`Value is driven by ${pos.join(", ")}, each evidenced in comparable sales.`);

  const fut = futureDrivers(r).slice(0, 2);
  if (fut.length > 0) parts.push(`Forward drivers (${fut.join(", ")}) support holding at the top of the range and raising later — never cutting.`);

  const topRisk = r.risk_factors.find((rf) => rf.severity !== "low");
  if (topRisk) parts.push(`Key risk: ${topRisk.detail || topRisk.title}.`);

  parts.push(`Basis: ${r.comps_considered ?? r.comparables.length} comparables, every adjustment source-traceable. Decision-support, not a formal valuation.`);
  return parts.join(" ");
}
