import type { AreaEntry, OpportunityScore, RecommendationResult } from "../../types";
import type { AreaAmenities } from "../../lib/poi";
import type { StepKey } from "../../lib/journey";
import { shortDate } from "../../lib/format";
import { OpportunityMeter } from "../OpportunityMeter";
import { PriceBands } from "../PriceBands";
import { ConfidenceBreakdown } from "../ConfidenceBreakdown";
import { Comparables } from "../Comparables";
import { ResidualLandValue } from "../ResidualLandValue";
import { ScenarioPanel } from "../ScenarioPanel";
import { ScenarioCompare } from "../ScenarioCompare";
import { NearbyAmenities } from "../NearbyAmenities";
import { WorkspaceHeader, NoStructuredData } from "../workspaces/shared";
import { MonitoringStep } from "./MonitoringStep";

export function StepContent({
  step,
  area,
  result,
  opportunity,
  amenities,
  computing,
  generatedAt,
}: {
  step: StepKey;
  area: AreaEntry | null;
  result: RecommendationResult | null;
  opportunity: OpportunityScore | null;
  amenities: AreaAmenities | null;
  computing: boolean;
  generatedAt: string;
}) {
  // "Covered" here means the area is not just in the catalogue but actually priceable:
  // the engine returned a real band. Areas with too little sale data yet come back
  // unpriceable (a 0/0/0 band) — show the honest "no data yet" state instead of a 0,
  // and they flip to a real price automatically once more data is collected.
  const covered = !!(area?.covered && result && result.recommended_jd_m2 > 0);
  const header = area && (
    <WorkspaceHeader
      title={area.name}
      nameAr={area.name_ar}
      sub={
        covered && result
          ? `${result.property_type}${result.as_of ? " · as of " + shortDate(result.as_of) : ""}`
          : "Context area"
      }
      note={result?.source_note}
    />
  );

  const body = (() => {
    switch (step) {
      case "opportunity":
        if (!area) return <OpportunityPrompt />;
        return (
          <>
            <section className="px-4 pt-4">
              <div className="mb-2 label-eyebrow">How good is this area to build in?</div>
              {opportunity ? <OpportunityMeter opp={opportunity} /> : <Awaiting note="We can't rate this area yet." />}
            </section>
            <NearbyAmenities amenities={amenities} />
          </>
        );
      case "economics":
        if (!area) return <StepPrompt label="Land price" hint="Pick an area to see the most you can pay for the land." />;
        return covered && result ? (
          <ResidualLandValue neighborhood={result.neighborhood} recommendedJdM2={result.recommended_jd_m2} />
        ) : (
          <NoStructuredData area={area} />
        );
      case "pricing":
        if (!area) return <StepPrompt label="Sell price" hint="Pick an area to see the price to sell at." />;
        return covered && result ? (
          <div className={`transition-opacity ${computing ? "opacity-50" : "opacity-100"}`}>
            <PriceBands r={result} />
            <ConfidenceBreakdown r={result} />
            <Comparables items={result.comparables} />
            <ScenarioPanel r={result} />
            <ScenarioCompare r={result} />
            <PlainWords narrative={result.narrative} />
          </div>
        ) : (
          <NoStructuredData area={area} />
        );
      case "monitoring":
        return <MonitoringStep area={area} result={result} generatedAt={generatedAt} />;
    }
  })();

  return (
    <div className="pb-2">
      {header}
      {body}
    </div>
  );
}

// Plain-English summary of the recommendation (the "In plain words" card from the
// old UI). The "Things to watch out for" risk list was intentionally removed.
function PlainWords({ narrative }: { narrative: string }) {
  if (!narrative) return null;
  return (
    <section className="px-4 pb-6 pt-5" aria-label="Plain-language summary">
      <h3 className="mb-2 text-[13px] font-semibold text-ink">In simple words</h3>
      <p className="card p-3 text-[12px] leading-relaxed text-ink-dim">{narrative}</p>
    </section>
  );
}

function OpportunityPrompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Where should you build?</div>
      <p className="mt-1 max-w-[260px] text-2xs leading-relaxed text-ink-mute">
        The map shows which areas are best to build in. Click a bright area, or search above, to
        see it.
      </p>
    </div>
  );
}

function StepPrompt({ label, hint }: { label: string; hint: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">{label}</div>
      <p className="mt-1 max-w-[240px] text-2xs leading-relaxed text-ink-mute">{hint}</p>
    </div>
  );
}

function Awaiting({ note }: { note: string }) {
  return (
    <div className="card border-dashed p-3">
      <div className="text-2xs font-medium uppercase tracking-wide text-ink-mute">No data yet</div>
      <p className="mt-1 text-2xs leading-relaxed text-ink-dim">{note}</p>
    </div>
  );
}
