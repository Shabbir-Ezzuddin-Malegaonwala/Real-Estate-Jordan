// Minimal trend line (price history) — Demo-G's inline `spark()` helper,
// promoted to a typed component. Pure SVG, no library.
export function Sparkline({
  data,
  width = 120,
  height = 34,
  caption,
  title = "Trend",
}: {
  data: number[];
  width?: number;
  height?: number;
  caption?: string;
  title?: string;
}) {
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * (width - 4) + 2;
      const y = height - 2 - ((v - min) / span) * (height - 4);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div>
      <svg
        role="img"
        aria-label={title}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
      >
        <title>{title}</title>
        <polyline points={points} fill="none" stroke="#0072B2" strokeWidth={2} strokeLinejoin="round" />
      </svg>
      {caption && <div className="mt-1 text-[11px] text-stitch-muted">{caption}</div>}
    </div>
  );
}
