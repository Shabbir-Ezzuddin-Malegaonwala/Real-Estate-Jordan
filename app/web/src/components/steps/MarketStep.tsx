import type { AreaEntry, OpportunityScore, RecommendationResult } from "../../types";
import { jd } from "../../lib/format";
import { Comparables } from "../Comparables";
import { NoStructuredData } from "../workspaces/shared";

// Step 3 — "who will buy here?" Demand signals (from the opportunity index) +
// the comparable sales the pricing rests on.
export function MarketStep({
  area,
  result,
  opportunity,
}: {
  area: AreaEntry | null;
  result: RecommendationResult | null;
  opportunity: OpportunityScore | null;
}) {
  if (!area) return <Prompt />;

  return (
    <div className="pb-2">
      <div className="px-4 pt-4">
        <div className="mb-2 label-eyebrow">Market · who will buy here?</div>
        <div className="card grid grid-cols-3 divide-x divide-line-soft">
          <Stat label="Listings seen" value={area.listing_count != null ? jd(area.listing_count) : "—"} />
          <Stat label="Sale demand" value={area.sale_listing_count != null ? jd(area.sale_listing_count) : "—"} />
          <Stat
            label="Demand index"
            value={opportunity ? `${opportunity.components.demand_density}` : "—"}
          />
        </div>
        {opportunity?.component_reasons?.demand_density && (
          <p className="mt-1.5 text-2xs leading-relaxed text-ink-faint">
            {opportunity.component_reasons.demand_density}
          </p>
        )}
      </div>

      {area.covered && result ? (
        <Comparables items={result.comparables} />
      ) : (
        <NoStructuredData area={area} />
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-3 py-2.5">
      <div className="text-2xs uppercase tracking-wide text-ink-mute">{label}</div>
      <div className="tnum mt-0.5 text-[16px] font-medium text-ink">{value}</div>
    </div>
  );
}

function Prompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Pick an area first</div>
      <p className="mt-1 max-w-[240px] text-2xs leading-relaxed text-ink-mute">
        See demand density and the comparable sales behind the price.
      </p>
    </div>
  );
}
