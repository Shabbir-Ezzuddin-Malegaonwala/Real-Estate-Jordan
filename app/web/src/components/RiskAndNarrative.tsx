import type { RiskFactor, Severity } from "../types";

const DOT: Record<Severity, string> = {
  high: "bg-neg",
  medium: "bg-warn",
  low: "bg-ink-mute",
};

export function RiskAndNarrative({
  risks,
  narrative,
}: {
  risks: RiskFactor[];
  narrative: string;
}) {
  return (
    <section className="px-4 pb-6 pt-5" aria-label="Risk factors and analyst narrative">
      <h3 className="mb-2 text-[13px] font-semibold text-ink">Risk Factors</h3>
      <div className="card divide-y divide-line-soft">
        {risks.map((r) => (
          <div key={r.title} className="flex gap-2.5 p-2.5">
            <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${DOT[r.severity]}`} aria-hidden />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[12px] font-medium text-ink">{r.title}</span>
                <span className="text-2xs uppercase tracking-wide text-ink-mute">{r.severity}</span>
              </div>
              <p className="mt-0.5 text-2xs leading-relaxed text-ink-dim">{r.detail}</p>
            </div>
          </div>
        ))}
      </div>

      <h3 className="mb-2 mt-5 text-[13px] font-semibold text-ink">Analyst Narrative</h3>
      <p className="card p-3 text-[12px] leading-relaxed text-ink-dim">{narrative}</p>
    </section>
  );
}
