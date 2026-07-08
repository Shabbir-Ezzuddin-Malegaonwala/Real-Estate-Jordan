import { useState } from "react";
import type { AreaEntry, RecommendationResult } from "../../types";
import { shortDate } from "../../lib/format";
import { salesNarrative } from "../../lib/narrative";
import { PriceBands } from "../PriceBands";
import { AdjustmentWaterfall } from "../AdjustmentWaterfall";
import { Comparables } from "../Comparables";
import { AskPanel } from "../AskPanel";
import { NoStructuredData, WorkspaceHeader } from "./shared";

// AGENT — "what is this unit worth, with evidence I can show a client?" Leads
// with the valuation band + a copy-ready sales narrative, then the evidence.
export function AgentWorkspace({
  area,
  result,
  computing,
}: {
  area: AreaEntry | null;
  result: RecommendationResult | null;
  computing: boolean;
}) {
  const [copied, setCopied] = useState(false);
  if (!area) return <Prompt />;

  const covered = area.covered && result;

  return (
    <div className={`pb-2 transition-opacity ${computing ? "opacity-50" : "opacity-100"}`}>
      <WorkspaceHeader
        title={area.name}
        nameAr={area.name_ar}
        sub={covered && result ? `${result.property_type}${result.as_of ? " · as of " + shortDate(result.as_of) : ""}` : "Context area"}
        note={result?.source_note}
      />

      {covered && result ? (
        <>
          <PriceBands r={result} />

          <section className="px-4 pt-5" aria-label="Sales narrative">
            <div className="mb-2 flex items-center gap-2">
              <span className="inline-block h-3 w-[3px] rounded-full bg-cyan" aria-hidden />
              <h3 className="text-[13px] font-semibold text-ink">Sales narrative</h3>
              <span className="label-eyebrow ml-auto">draft · client-ready</span>
            </div>
            <div className="card p-3">
              <p className="text-[12px] leading-relaxed text-ink-dim">{salesNarrative(result)}</p>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard?.writeText(salesNarrative(result));
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1600);
                }}
                aria-label="Copy sales narrative"
                className="mt-2 rounded-[3px] border border-cyan/50 bg-cyan/10 px-3 py-1 text-2xs font-medium text-cyan transition-colors hover:bg-cyan/20"
              >
                {copied ? "Copied ✓" : "Copy draft"}
              </button>
              <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
                Composed from the evidence below — no facts added. Verify before sending.
              </p>
            </div>
          </section>

          <AdjustmentWaterfall r={result} />
          <Comparables items={result.comparables} />
        </>
      ) : (
        <NoStructuredData area={area} />
      )}

      <AskPanel area={area.name} />
    </div>
  );
}

function Prompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Value a unit</div>
      <p className="mt-1 max-w-[260px] text-2xs leading-relaxed text-ink-mute">
        Search an area or click the map to get an evidence-backed valuation band and a client-ready
        narrative you can show.
      </p>
    </div>
  );
}
