// Minimal horizontal bar — hand-rolled to hold the terminal aesthetic
// (thin bars, tabular labels, no animation). A charting dependency is not
// justified for two small charts.
export function BarRow({
  label,
  value,
  display,
  max,
  color,
  highlight,
}: {
  label: string;
  value: number;
  display: string;
  max: number;
  color: string;
  highlight?: boolean;
}) {
  const w = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="grid grid-cols-[76px_1fr_auto] items-center gap-2 py-[3px]">
      <span
        className={`truncate text-2xs ${highlight ? "font-medium text-ink" : "text-ink-dim"}`}
        title={label}
      >
        {label}
      </span>
      <span className="h-2 overflow-hidden rounded-[2px] bg-raised">
        <span className="block h-full rounded-[2px]" style={{ width: `${w}%`, background: color }} />
      </span>
      <span className="tnum w-14 text-right text-2xs text-ink-dim">{display}</span>
    </div>
  );
}
