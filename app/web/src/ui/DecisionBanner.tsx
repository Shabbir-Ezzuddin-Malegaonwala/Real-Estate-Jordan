// The one-line conclusion banner — decision-first, always the first thing a
// view renders (MASTER-PLAN principle: "one conclusion, then detail").
export function DecisionBanner({
  verdict,
  subtitle,
  className = "",
}: {
  verdict: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl bg-gradient-to-br from-stitch-brand-dark to-stitch-brand px-4 py-3.5 text-white ${className}`}
    >
      <div className="text-base font-bold leading-snug">{verdict}</div>
      {subtitle && <div className="mt-0.5 text-[13px] text-white/90">{subtitle}</div>}
    </div>
  );
}
