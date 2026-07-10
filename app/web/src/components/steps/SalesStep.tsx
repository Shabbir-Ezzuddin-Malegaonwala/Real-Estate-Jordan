import { useState } from "react";
import type { AreaEntry, OpportunityScore, RecommendationResult } from "../../types";
import { executiveSummary, salesNarrative } from "../../lib/narrative";
import { NoStructuredData } from "../workspaces/shared";

// Step 6 — "how do I justify it?" Two client-side drafts composed from the same
// evidence (no facts added): an Executive Summary for the builder and a
// copy-ready Sales Narrative for the sales team. Investor Memorandum = Phase 2.
export function SalesStep({
  area,
  result,
  opportunity,
}: {
  area: AreaEntry | null;
  result: RecommendationResult | null;
  opportunity: OpportunityScore | null;
}) {
  if (!area) return <Prompt />;
  if (!area.covered || !result) return <NoStructuredData area={area} />;

  return (
    <div className="px-4 pt-4">
      <div className="mb-2 label-eyebrow">Sales · how do I justify it?</div>

      <Draft
        title="Executive summary"
        badge="for the builder"
        text={executiveSummary(result, opportunity)}
      />
      <Draft
        title="Sales narrative"
        badge="copy-ready · sales team"
        text={salesNarrative(result)}
      />

      <div className="mt-3 rounded-[3px] border border-dashed border-line bg-panel p-2.5">
        <div className="text-2xs font-medium uppercase tracking-wide text-ink-mute">Investor memorandum</div>
        <p className="mt-1 text-2xs leading-relaxed text-ink-faint">
          A full investor memorandum (financials, phasing, sensitivity) is Phase 2 — not fabricated here.
        </p>
      </div>
    </div>
  );
}

function Draft({ title, badge, text }: { title: string; badge: string; text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <section className="mb-3" aria-label={title}>
      <div className="mb-1.5 flex items-center gap-2">
        <span className="inline-block h-3 w-[3px] rounded-full bg-cyan" aria-hidden />
        <h3 className="text-[13px] font-semibold text-ink">{title}</h3>
        <span className="label-eyebrow ml-auto">{badge} · draft</span>
      </div>
      <div className="card p-3">
        <p className="text-[12px] leading-relaxed text-ink-dim">{text}</p>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard?.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 1600);
          }}
          aria-label={`Copy ${title}`}
          className="mt-2 rounded-[3px] border border-cyan/50 bg-cyan/10 px-3 py-1 text-2xs font-medium text-cyan transition-colors hover:bg-cyan/20"
        >
          {copied ? "Copied ✓" : "Copy draft"}
        </button>
        <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
          Composed from the evidence — no facts added. Verify before sending.
        </p>
      </div>
    </section>
  );
}

function Prompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Pick an area first</div>
      <p className="mt-1 max-w-[240px] text-2xs leading-relaxed text-ink-mute">
        Once an area is priced, this step drafts the summary and sales narrative to justify it.
      </p>
    </div>
  );
}
