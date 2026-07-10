import type { OpportunityScore, RecommendationResult } from "../types";
import { readinessFor, levelFromScore } from "../lib/intel";

const BAR: Record<string, string> = { High: "bg-pos", Medium: "bg-warn", Low: "bg-neg" };

// The 8-dimension decision-readiness board (+ Overall) so a builder can compare
// areas before pricing. Null dimensions render muted as "data not yet available"
// — never zero. Low-data areas carry a confidence caveat on every dimension.
export function DecisionReadiness({
  opp,
  result,
}: {
  opp: OpportunityScore | null;
  result: RecommendationResult | null;
}) {
  if (!opp) return null;
  const dims = readinessFor(opp, result);
  const overall = dims.find((d) => d.key === "overall");
  const rest = dims.filter((d) => d.key !== "overall");

  return (
    <section className="px-4 pt-4" aria-label="Decision readiness">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-eyebrow">Decision readiness</span>
        <span className="text-2xs text-ink-faint">
          {opp.readiness ? "engine-scored" : "from opportunity signals"}
        </span>
      </div>

      <div className="card p-3">
        {overall && (
          <div className="mb-3 flex items-end justify-between border-b border-line-soft pb-2.5">
            <div>
              <div className="text-2xs uppercase tracking-wide text-ink-mute">Overall</div>
              <div className="mt-0.5 text-2xs text-ink-faint">{overall.reason}</div>
            </div>
            {overall.score != null ? (
              <div className={`tnum font-mono text-[24px] font-medium leading-none ${tone(overall.score)}`}>
                {overall.score}
              </div>
            ) : (
              <Unavailable />
            )}
          </div>
        )}

        <div className="space-y-2">
          {rest.map((d) => (
            <div key={d.key}>
              <div className="flex items-center justify-between gap-2 text-2xs">
                <span className="text-ink-dim">{d.label}</span>
                {d.score != null ? (
                  <span className="tnum text-ink-mute">{d.score}</span>
                ) : (
                  <span className="text-ink-faint">n/a</span>
                )}
              </div>
              {d.score != null ? (
                <div className="relative mt-1 h-1.5 w-full overflow-hidden rounded-full bg-raised">
                  <div
                    className={`absolute inset-y-0 left-0 rounded-full ${BAR[levelFromScore(d.score)]}`}
                    style={{ width: `${d.score}%` }}
                    aria-hidden
                  />
                </div>
              ) : (
                <div className="mt-1 flex h-1.5 items-center">
                  <div className="h-px w-full border-t border-dashed border-line" aria-hidden />
                </div>
              )}
              <p className={`mt-0.5 text-2xs leading-snug text-ink-faint ${d.score == null ? "italic" : ""}`}>
                {d.score == null && !/not yet available|pending/i.test(d.reason)
                  ? "Data not yet available — " + d.reason
                  : d.reason}
              </p>
            </div>
          ))}
        </div>

        {opp.low_data && (
          <p className="mt-2 rounded-[2px] border border-warn/30 bg-warn/[0.06] px-2 py-1 text-2xs text-warn">
            Low data (n={opp.listing_count ?? 0}) — readiness is indicative only for this area.
          </p>
        )}
      </div>
    </section>
  );
}

function Unavailable() {
  return <span className="text-2xs italic text-ink-faint">data not yet available</span>;
}

function tone(score: number): string {
  const l = levelFromScore(score);
  return l === "High" ? "text-pos" : l === "Low" ? "text-neg" : "text-warn";
}
