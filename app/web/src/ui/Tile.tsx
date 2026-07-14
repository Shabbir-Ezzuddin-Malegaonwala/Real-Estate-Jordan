import type { ReactNode } from "react";
import { Card } from "./Card";

// A labelled stat block (caption + big value + optional hint) — the "big"
// number pattern from Demo-G (e.g. launch price, land value, build cost).
export function Tile({
  label,
  value,
  unit,
  hint,
  tone = "default",
  className = "",
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: string;
  tone?: "default" | "brand" | "green" | "warn";
  className?: string;
}) {
  const valueColor =
    tone === "brand"
      ? "text-stitch-brand-dark"
      : tone === "green"
        ? "text-stitch-green"
        : tone === "warn"
          ? "text-stitch-warn"
          : "text-stitch-ink";

  return (
    <Card className={className}>
      <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">{label}</div>
      <div className={`mt-1.5 text-[32px] font-bold leading-none ${valueColor}`}>
        {value}
        {unit && <span className="ml-1.5 text-sm font-semibold text-stitch-muted">{unit}</span>}
      </div>
      {hint && <div className="mt-2 text-[13px] text-stitch-muted">{hint}</div>}
    </Card>
  );
}
