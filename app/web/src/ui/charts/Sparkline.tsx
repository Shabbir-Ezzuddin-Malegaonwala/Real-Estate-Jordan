// A real trend chart (pure SVG, no library): the line PLUS the numbers that make
// it meaningful — start/end values, the % change with an up/down indicator, and
// the min–max range. Honest when there's nothing to show (flat or single point).
export function Sparkline({
  data,
  width = 120,
  height = 34,
  caption,
  title = "Trend",
  unit = "JD/m²",
  period,
}: {
  data: number[];
  width?: number;
  height?: number;
  caption?: string;
  title?: string;
  unit?: string;
  period?: string;
}) {
  const clean = data.filter((v) => typeof v === "number" && isFinite(v));
  if (clean.length < 2) {
    return <div className="text-[12px] text-stitch-muted">No trend data yet.</div>;
  }

  const first = clean[0];
  const last = clean[clean.length - 1];
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const span = max - min || 1;
  const changePct = first ? ((last - first) / first) * 100 : 0;
  const flat = Math.abs(changePct) < 0.5;
  const up = changePct > 0;
  const dir = flat ? "flat" : up ? "up" : "down";
  const color = flat ? "#8a94a5" : up ? "#2f9e6f" : "#c9736f";
  const arrow = flat ? "→" : up ? "▲" : "▼";

  const chartH = height - 2;
  const pts = clean.map((v, i) => {
    const x = (i / (clean.length - 1)) * (width - 4) + 2;
    const y = chartH - 2 - ((v - min) / span) * (chartH - 4);
    return [x, y] as const;
  });
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `2,${chartH} ${line} ${(width - 2).toFixed(1)},${chartH}`;
  const fmt = (n: number) => Math.round(n).toLocaleString();

  return (
    <div style={{ width }}>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-lg font-extrabold text-stitch-ink">{fmt(last)}<span className="ml-1 text-[11px] font-semibold text-stitch-muted">{unit}</span></span>
        <span className="text-[12px] font-bold" style={{ color }}>
          {arrow} {flat ? "flat" : `${up ? "+" : ""}${changePct.toFixed(1)}%`}
        </span>
      </div>
      <svg role="img" aria-label={`${title}: ${dir} ${changePct.toFixed(1)}%`} width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <title>{title}</title>
        <polygon points={area} fill={color} opacity={0.1} />
        <polyline points={line} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r={2.6} fill={color} />
      </svg>
      <div className="mt-0.5 flex justify-between text-[10.5px] text-stitch-muted">
        <span>{fmt(first)}{period ? ` · ${period} ago` : ""}</span>
        <span>range {fmt(min)}–{fmt(max)}</span>
      </div>
      {caption && <div className="mt-1 text-[11px] text-stitch-muted">{caption}</div>}
    </div>
  );
}
