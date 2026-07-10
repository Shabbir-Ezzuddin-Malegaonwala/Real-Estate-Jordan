import type { OpportunityScore } from "../types";
import { levelFromScore } from "../lib/intel";

const COMPONENT_LABELS: Record<string, string> = {
  price_level: "Price headroom",
  price_growth: "Price growth",
  demand_density: "Sale demand",
  supply_pressure: "Low competition",
  future_signals: "Future signals",
};

const BAR: Record<string, string> = { High: "bg-pos", Medium: "bg-warn", Low: "bg-neg" };

// The opportunity score + its 5 drivers — answers "why is this area ranked here?"
// before any project form. Score ring on the left, component bars on the right.
export function OpportunityMeter({ opp }: { opp: OpportunityScore }) {
  const level = levelFromScore(opp.score);
  const entries = Object.entries(opp.components) as [keyof typeof opp.components, number][];

  const sourceLabel =
    opp.source === "local" ? "locally computed" : opp.source === "heatmap" ? "area heatmap" : "engine-scored";

  return (
    <div className={`card p-3 ${opp.low_data ? "opacity-90" : ""}`}>
      <div className="flex items-center gap-3">
        <ScoreRing score={opp.score} level={opp.low_data ? "Low" : level} />
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-2xs uppercase tracking-wide text-ink-mute">Opportunity score</span>
            {opp.low_data && (
              <span className="rounded-[2px] border border-warn/40 bg-warn/10 px-1.5 py-[1px] text-2xs font-medium uppercase tracking-wide text-warn">
                Low data · n={opp.listing_count ?? 0}
              </span>
            )}
          </div>
          <div className={`text-[13px] font-semibold ${opp.low_data ? "text-ink-dim" : tone(level)}`}>
            {opp.low_data ? "Too thin to rank" : `${level} · where to build`}
          </div>
          <div className="mt-0.5 text-2xs text-ink-faint">
            {sourceLabel}
            {opp.covered ? "" : " · context area"}
            {opp.governorate ? ` · ${opp.governorate}` : ""}
          </div>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {entries.map(([key, val]) => {
          const lvl = levelFromScore(val);
          const reason = opp.component_reasons?.[key];
          return (
            <div key={key}>
              <div className="grid grid-cols-[96px_1fr_auto] items-center gap-2">
                <span className="truncate text-2xs text-ink-dim" title={COMPONENT_LABELS[key] ?? key}>
                  {COMPONENT_LABELS[key] ?? key}
                </span>
                <div className="relative h-1.5 overflow-hidden rounded-full bg-raised">
                  <div
                    className={`absolute inset-y-0 left-0 rounded-full ${BAR[lvl]}`}
                    style={{ width: `${val}%` }}
                    aria-hidden
                  />
                </div>
                <span className="tnum text-2xs text-ink-mute">{val}</span>
              </div>
              {reason && <p className="mt-0.5 pl-[104px] text-2xs leading-snug text-ink-faint">{reason}</p>}
            </div>
          );
        })}
      </div>

      {opp.reason && (
        <p className="mt-2 text-2xs leading-relaxed text-ink-faint">{opp.reason}</p>
      )}
    </div>
  );
}

function ScoreRing({ score, level }: { score: number; level: string }) {
  const color = level === "High" ? "var(--c-pos)" : level === "Low" ? "var(--c-neg)" : "var(--c-warn)";
  return (
    <div
      className="grid h-14 w-14 shrink-0 place-items-center rounded-full"
      style={{
        background: `conic-gradient(rgb(${color}) ${score * 3.6}deg, rgb(var(--c-raised)) 0deg)`,
      }}
      aria-hidden
    >
      <div className="grid h-11 w-11 place-items-center rounded-full bg-panel">
        <span className={`tnum font-mono text-[17px] font-medium ${tone(level)}`}>{score}</span>
      </div>
    </div>
  );
}

function tone(level: string): string {
  return level === "High" ? "text-pos" : level === "Low" ? "text-neg" : "text-warn";
}
