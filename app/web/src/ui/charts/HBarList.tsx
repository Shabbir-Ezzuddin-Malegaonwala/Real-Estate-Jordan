export interface HBarItem {
  label: string;
  value: number;
  highlighted?: boolean;
}

// Horizontal bar comparison — area/competitor "position" chart (Power-BI
// style per DEVELOPMENT-PLAN §3): no pie/gauge for comparisons.
export function HBarList({
  items,
  caption,
  formatValue = (v: number) => v.toLocaleString(),
  title = "Comparison",
}: {
  items: HBarItem[];
  caption?: string;
  formatValue?: (v: number) => string;
  title?: string;
}) {
  const max = Math.max(...items.map((i) => i.value), 1);

  return (
    <div role="img" aria-label={title}>
      <div className="flex flex-col gap-2.5">
        {items.map((item) => (
          <div key={item.label}>
            <div className="mb-1 flex items-center justify-between text-[13px]">
              <span className={item.highlighted ? "font-semibold text-stitch-brand-dark" : "text-stitch-ink"}>
                {item.label}
              </span>
              <span className="tabular-nums font-semibold text-stitch-ink">{formatValue(item.value)}</span>
            </div>
            <div className="h-2 rounded-full bg-stitch-soft">
              <div
                className={`h-full rounded-full ${item.highlighted ? "bg-stitch-brand" : "bg-stitch-brand/40"}`}
                style={{ width: `${(item.value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      {caption && <div className="mt-2 text-[11px] text-stitch-muted">{caption}</div>}
    </div>
  );
}
