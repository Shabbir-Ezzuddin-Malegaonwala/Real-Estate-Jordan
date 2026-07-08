import { STEPS, type StepKey } from "../lib/journey";

// The 7-step builder journey as a compact numbered tracker. Every step is
// reachable at any time (non-linear) — a builder jumps to Economics or Pricing
// directly. The active step's question is shown beneath the nodes.
export function Stepper({
  active,
  onSelect,
}: {
  active: StepKey;
  onSelect: (k: StepKey) => void;
}) {
  const activeStep = STEPS.find((s) => s.key === active) ?? STEPS[0];

  return (
    <div className="border-b border-line px-4 py-2.5">
      <div className="flex items-center justify-between" role="tablist" aria-label="Builder journey">
        {STEPS.map((s, i) => {
          const isActive = s.key === active;
          const isDone = i < activeStep.n - 1;
          return (
            <div key={s.key} className="flex items-center" style={{ flex: i < STEPS.length - 1 ? "1 1 0%" : "0 0 auto" }}>
              <button
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-label={`Step ${s.n}: ${s.label}`}
                title={`${s.label} — ${s.question}`}
                onClick={() => onSelect(s.key)}
                className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border text-2xs font-semibold tnum transition-colors ${
                  isActive
                    ? "border-accent bg-accent/15 text-accent"
                    : isDone
                      ? "border-accent/40 bg-accent/[0.06] text-accent/80 hover:border-accent"
                      : "border-line bg-panel text-ink-mute hover:border-cyan-dim hover:text-ink"
                }`}
              >
                {s.n}
              </button>
              {i < STEPS.length - 1 && (
                <span className={`mx-1 h-px flex-1 ${isDone ? "bg-accent/40" : "bg-line"}`} aria-hidden />
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xs font-medium uppercase tracking-wide text-accent">
          Step {activeStep.n} of 7
        </span>
        <span className="text-[13px] font-semibold text-ink">{activeStep.label}</span>
        <span className="truncate text-2xs text-ink-mute">{activeStep.question}</span>
      </div>
    </div>
  );
}
