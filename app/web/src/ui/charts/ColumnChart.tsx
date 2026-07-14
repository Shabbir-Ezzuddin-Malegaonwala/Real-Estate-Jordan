export interface ColumnItem {
  label: string;
  value: number;
}

// Monthly-values column chart (e.g. market-news volume, sales/month).
export function ColumnChart({
  data,
  caption,
  title = "Monthly values",
  height = 100,
  formatValue = (v: number) => v.toLocaleString(),
}: {
  data: ColumnItem[];
  caption?: string;
  title?: string;
  height?: number;
  formatValue?: (v: number) => string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div>
      <div role="img" aria-label={title} className="flex items-end gap-1.5" style={{ height }}>
        {data.map((d) => (
          <div key={d.label} className="flex flex-1 flex-col items-center gap-1">
            <span className="text-[10px] tabular-nums text-stitch-muted">{formatValue(d.value)}</span>
            <div
              className="w-full rounded-t-sm bg-stitch-brand"
              style={{ height: `${Math.max(2, (d.value / max) * (height - 26))}px` }}
              title={`${d.label}: ${formatValue(d.value)}`}
            />
            <span className="text-[10px] text-stitch-muted">{d.label}</span>
          </div>
        ))}
      </div>
      {caption && <div className="mt-1.5 text-[11px] text-stitch-muted">{caption}</div>}
    </div>
  );
}
