export type StatusTone = "ready" | "wait" | "review";

const TONE_CLASSES: Record<StatusTone, string> = {
  ready: "bg-[#e3f4ee] text-[#0a7a5b]",
  wait: "bg-[#fdece0] text-stitch-warn",
  review: "bg-[#e7f1fb] text-stitch-brand-dark",
};

const TONE_DOT: Record<StatusTone, string> = {
  ready: "bg-[#0a7a5b]",
  wait: "bg-stitch-warn",
  review: "bg-stitch-brand-dark",
};

// Small rounded status indicator (e.g. "READY TO LAUNCH", "AWAITING DATA",
// "NEEDS REVIEW") — Demo-G's `.status` chip.
export function StatusPill({ tone, label }: { tone: StatusTone; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide ${TONE_CLASSES[tone]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[tone]}`} aria-hidden />
      {label}
    </span>
  );
}
