import type { AreaEntry, OpportunityScore, RecommendationResult } from "../../types";
import { buyerSummary } from "../../lib/narrative";
import { PriceBands } from "../PriceBands";
import { EvidenceSection } from "../EvidenceSection";
import { AskPanel } from "../AskPanel";
import { NoStructuredData, WorkspaceHeader } from "./shared";

// BUYER — conversational, plain-language. "Is this fair? / is the area good? /
// what's the catch?" built from the same evidence, no jargon, no fake numbers.
export function BuyerWorkspace({
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
  if (!area) return <Prompt />;
  const covered = area.covered && result;
  const future = result?.evidence_objects.filter((e) => e.category === "future_signal") ?? [];

  return (
    <div className={`pb-2 transition-opacity ${computing ? "opacity-50" : "opacity-100"}`}>
      <WorkspaceHeader title={area.name} nameAr={area.name_ar} sub={covered ? "Buyer view" : "Context area"} note={result?.source_note} />

      {covered && result ? (
        <>
          {(() => {
            const s = buyerSummary(result, opportunity);
            return (
              <div className="px-4 pt-4">
                <Bubble title="Is this price fair?" tone="cyan">{s.fairness}</Bubble>
                <Bubble title="Is the area good?" tone="accent">{s.area}</Bubble>
                {s.redFlags.length > 0 ? (
                  <div className="mt-2 rounded-[3px] border border-warn/40 bg-warn/[0.06] p-3">
                    <div className="text-2xs font-semibold uppercase tracking-wide text-warn">What to watch</div>
                    <ul className="mt-1.5 space-y-1.5">
                      {s.redFlags.map((f, i) => (
                        <li key={i} className="flex gap-2 text-2xs leading-relaxed text-ink-dim">
                          <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-warn" aria-hidden />
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <Bubble title="What's the catch?" tone="pos">
                    No material red flags in the evidence for this area — but always view in person and
                    check the specific unit's floor, view and finish.
                  </Bubble>
                )}
              </div>
            );
          })()}

          <PriceBands r={result} />

          {future.length > 0 && (
            <EvidenceSection
              title="What's coming to the area"
              eyebrow="future signals"
              tone="future"
              items={future}
            />
          )}
        </>
      ) : (
        <NoStructuredData area={area} />
      )}

      <AskPanel area={area.name} />
    </div>
  );
}

function Bubble({ title, tone, children }: { title: string; tone: "cyan" | "accent" | "pos"; children: React.ReactNode }) {
  const bar = tone === "cyan" ? "bg-cyan" : tone === "pos" ? "bg-pos" : "bg-accent";
  return (
    <div className="mt-2 first:mt-0">
      <div className="mb-1 flex items-center gap-2">
        <span className={`inline-block h-3 w-[3px] rounded-full ${bar}`} aria-hidden />
        <span className="text-[12px] font-semibold text-ink">{title}</span>
      </div>
      <p className="card p-3 text-[12px] leading-relaxed text-ink-dim">{children}</p>
    </div>
  );
}

function Prompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Thinking of buying?</div>
      <p className="mt-1 max-w-[260px] text-2xs leading-relaxed text-ink-mute">
        Search an area or tap the map for a plain-language read on whether the price is fair, whether
        the area is good, and what to watch out for.
      </p>
    </div>
  );
}
