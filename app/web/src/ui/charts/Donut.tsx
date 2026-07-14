export interface DonutSegment {
  label: string;
  value: number;
  color?: string;
}

const DEFAULT_COLORS = ["#0072B2", "#D55E00", "#009E73", "#5b636b"];

// Unit-mix / cost-split donut — the one place a circular chart is the right
// pick (part-of-whole, ≤4 segments). Pure SVG stroke-dasharray rings.
export function Donut({
  segments,
  caption,
  title = "Split",
  size = 120,
}: {
  segments: DonutSegment[];
  caption?: string;
  title?: string;
  size?: number;
}) {
  const total = segments.reduce((s, seg) => s + seg.value, 0) || 1;
  const radius = size / 2 - 10;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className="flex items-center gap-4">
      <svg role="img" aria-label={title} width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <title>{title}</title>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#f3f6f9" strokeWidth={14} />
          {segments.map((seg, i) => {
            const length = (seg.value / total) * circumference;
            const dash = `${length} ${circumference - length}`;
            const el = (
              <circle
                key={seg.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={seg.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]}
                strokeWidth={14}
                strokeDasharray={dash}
                strokeDashoffset={-offset}
              />
            );
            offset += length;
            return el;
          })}
        </g>
      </svg>
      <div className="flex flex-col gap-1.5">
        {segments.map((seg, i) => (
          <div key={seg.label} className="flex items-center gap-1.5 text-[12px]">
            <span
              className="h-2 w-2 flex-none rounded-full"
              style={{ background: seg.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length] }}
              aria-hidden
            />
            <span className="text-stitch-ink">{seg.label}</span>
            <span className="tabular-nums text-stitch-muted">{Math.round((seg.value / total) * 100)}%</span>
          </div>
        ))}
        {caption && <div className="mt-1 text-[11px] text-stitch-muted">{caption}</div>}
      </div>
    </div>
  );
}
