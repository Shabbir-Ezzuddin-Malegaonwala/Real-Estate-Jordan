import type { RecommendationResult } from "../types";
import { confidenceComponents, levelFromScore } from "../lib/intel";
import { jd } from "../lib/format";

const BAR: Record<string, string> = {
  High: "bg-pos",
  Medium: "bg-warn",
  Low: "bg-neg",
};

// Replaces the single H/M/L badge with the overall score plus the 5 component
// bars and their reasons. When the engine hasn't emitted components yet, a
// clearly-labelled local estimate is shown instead of hiding the breakdown.
export function ConfidenceBreakdown({ r }: { r: RecommendationResult }) {
  const { components: allComponents, source } = confidenceComponents(r);
  // Future signals were dropped from the product (date-backed evidence only), so
  // the future-signals reliability bar no longer makes sense here — filter it out.
  const components = allComponents.filter((c) => c.key !== "future_signals");
  const overall = r.confidence.score;
  const overallLevel = r.confidence.level;

  return (
    <section className="px-4 pt-4" aria-label="Confidence breakdown">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-eyebrow">Confidence</span>
        <span className="text-2xs text-ink-faint">
          {source === "local" ? "components estimated locally" : "engine-decomposed"}
        </span>
      </div>

      <div className="card p-3">
        <div className="flex items-end justify-between">
          <div>
            <div className={`text-2xs uppercase tracking-wide ${labelTone(overallLevel)}`}>
              {overallLevel} confidence
            </div>
            <div className="mt-0.5 text-2xs text-ink-mute tnum">
              justified band {jd(r.confidence.range_low)}–{jd(r.confidence.range_high)} JD/m²
            </div>
          </div>
          <div className={`tnum font-mono text-[26px] font-medium leading-none ${labelTone(overallLevel)}`}>
            {overall}
          </div>
        </div>

        <div className="mt-3 space-y-2">
          {components.map((c) => {
            const level = levelFromScore(c.score);
            return (
              <div key={c.key}>
                <div className="flex items-center justify-between gap-2 text-2xs">
                  <span className="text-ink-dim">{c.label}</span>
                  <span className="tnum text-ink-mute">{c.score}</span>
                </div>
                <div className="relative mt-1 h-1.5 w-full overflow-hidden rounded-full bg-raised">
                  <div
                    className={`absolute inset-y-0 left-0 rounded-full ${BAR[level]}`}
                    style={{ width: `${c.score}%` }}
                    aria-hidden
                  />
                </div>
                {c.reason && (
                  <p className="mt-0.5 text-2xs leading-relaxed text-ink-faint">{c.reason}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function labelTone(level: string): string {
  return level === "High" ? "text-pos" : level === "Low" ? "text-neg" : "text-warn";
}
