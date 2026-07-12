import { STEPS, type StepKey } from "../lib/journey";

// The builder journey as a labelled dropdown (replaces the numbered 1–7 tracker — users
// pick a named view instead of decoding step numbers). Non-linear: jump to any view.
// Rendered below the subject form; the active view's question is shown beneath the select.
export function Stepper({
  active,
  onSelect,
}: {
  active: StepKey;
  onSelect: (k: StepKey) => void;
}) {
  const activeStep = STEPS.find((s) => s.key === active) ?? STEPS[0];

  return (
    <div className="border-b border-line px-4 py-3">
      <label htmlFor="journey-view" className="label-eyebrow mb-1 block">
        View
      </label>
      <select
        id="journey-view"
        value={active}
        onChange={(e) => onSelect(e.target.value as StepKey)}
        className="input"
        aria-label="Decision view"
      >
        {STEPS.map((s) => (
          <option key={s.key} value={s.key}>
            {s.label} — {s.question}
          </option>
        ))}
      </select>
      <p className="mt-1.5 text-2xs text-ink-mute">{activeStep.question}</p>
    </div>
  );
}
