import { useState } from "react";
import type { AreaEntry, OpportunityScore, RecommendationResult } from "../../types";
import { shortDate } from "../../lib/format";
import { OpportunityMeter } from "../OpportunityMeter";
import { PriceBands } from "../PriceBands";
import { ConfidenceBreakdown } from "../ConfidenceBreakdown";
import { AdjustmentWaterfall } from "../AdjustmentWaterfall";
import { EvidenceSection } from "../EvidenceSection";
import { Comparables } from "../Comparables";
import { RiskAndNarrative } from "../RiskAndNarrative";
import { ResidualLandValue } from "../ResidualLandValue";
import { ScenarioPanel } from "../ScenarioPanel";
import { AskPanel } from "../AskPanel";
import { NoStructuredData, WorkspaceHeader } from "./shared";

// BUILDER — the hero. Decision-first: opportunity (where to build) leads, then
// the launch-price defence and the land/scenario tools. Same evidence base as
// the other roles, arranged around the builder's core question.
export function BuilderWorkspace({
  area,
  result,
  opportunity,
  computing,
}: {
  area: AreaEntry | null;
  result: RecommendationResult | null;
  opportunity: OpportunityScore | null;
  computing: boolean;
}) {
  const [evalOpen, setEvalOpen] = useState(false);

  if (!area) return <PickAreaPrompt />;

  const covered = area.covered && result;
  const future = result?.evidence_objects.filter((e) => e.category === "future_signal") ?? [];

  return (
    <div className={`pb-2 transition-opacity ${computing ? "opacity-50" : "opacity-100"}`}>
      <WorkspaceHeader
        title={area.name}
        nameAr={area.name_ar}
        sub={
          covered && result
            ? `${result.tier ? result.tier + " · " : ""}${result.property_type}${result.as_of ? " · as of " + shortDate(result.as_of) : ""}`
            : "Context area"
        }
        note={result?.source_note}
      />

      {opportunity && (
        <section className="px-4 pt-4" aria-label="Opportunity">
          <div className="mb-2 label-eyebrow">Where to build · opportunity</div>
          <OpportunityMeter opp={opportunity} />
        </section>
      )}

      {covered && result ? (
        <>
          <PriceBands r={result} />
          <ConfidenceBreakdown r={result} />

          <section className="px-4 pt-5">
            <button
              type="button"
              onClick={() => setEvalOpen((v) => !v)}
              aria-expanded={evalOpen}
              className="flex w-full items-center justify-between rounded-[3px] border border-accent/50 bg-accent/[0.08] px-3 py-2.5 text-left transition-colors hover:bg-accent/15"
            >
              <span>
                <span className="block text-[13px] font-semibold text-accent">Evaluate a project here</span>
                <span className="block text-2xs text-ink-mute">Residual land value + what-if scenario</span>
              </span>
              <span aria-hidden className={`text-accent transition-transform ${evalOpen ? "rotate-90" : ""}`}>▸</span>
            </button>
          </section>

          {evalOpen && (
            <>
              <ResidualLandValue neighborhood={result.neighborhood} recommendedJdM2={result.recommended_jd_m2} />
              <ScenarioPanel r={result} />
            </>
          )}

          <AdjustmentWaterfall r={result} />

          {future.length > 0 && (
            <EvidenceSection
              title="Future Signals"
              eyebrow="positioning, not applied to today's band"
              tone="future"
              items={future}
            />
          )}

          <Comparables items={result.comparables} />
          <RiskAndNarrative risks={result.risk_factors} narrative={result.narrative} />
        </>
      ) : (
        <NoStructuredData area={area} />
      )}

      <AskPanel area={area.name} />
    </div>
  );
}

function PickAreaPrompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Where should you build?</div>
      <p className="mt-1 max-w-[260px] text-2xs leading-relaxed text-ink-mute">
        The map is coloured by opportunity score. Click the strongest area, or search above, to open
        its intelligence and evaluate a project.
      </p>
    </div>
  );
}
