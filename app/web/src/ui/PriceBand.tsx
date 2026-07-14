// The safe → recommended → premium launch-price rail (Demo-G `.band`).
// Renders three ticks over a soft fill; labels sit under each tick.
export function PriceBand({
  min,
  rec,
  premium,
  unit,
  formatValue = (v: number) => v.toLocaleString(),
  className = "",
}: {
  min: number;
  rec: number;
  premium: number;
  unit?: string;
  formatValue?: (v: number) => string;
  className?: string;
}) {
  const span = premium - min || 1;
  const pct = (v: number) => Math.min(100, Math.max(0, ((v - min) / span) * 100));
  const minPct = pct(min);
  const recPct = pct(rec);
  const premiumPct = pct(premium);

  return (
    <div className={`relative mt-6 mb-8 mx-1 h-2 rounded-md bg-stitch-soft ${className}`}>
      <div
        className="absolute h-full rounded-md bg-stitch-brand/20"
        style={{ left: `${minPct}%`, width: `${premiumPct - minPct}%` }}
      />
      <div
        className="absolute -top-[5px] w-[2px] h-[18px] bg-stitch-brand-dark"
        style={{ left: `${minPct}%` }}
        aria-hidden
      />
      <div
        className="absolute -top-[7px] w-[3px] h-[22px] bg-stitch-brand"
        style={{ left: `${recPct}%` }}
        aria-hidden
      />
      <div
        className="absolute -top-[5px] w-[2px] h-[18px] bg-stitch-brand-dark"
        style={{ left: `${premiumPct}%` }}
        aria-hidden
      />

      <div
        className="absolute top-3 -translate-x-1/2 whitespace-nowrap text-[11px] text-stitch-muted"
        style={{ left: `${minPct}%` }}
      >
        Safe <b className="text-stitch-brand-dark">{formatValue(min)}</b>
      </div>
      <div
        className="absolute top-3 -translate-x-1/2 whitespace-nowrap text-[11px] text-stitch-muted"
        style={{ left: `${recPct}%` }}
      >
        Best <b className="text-stitch-brand-dark">{formatValue(rec)}</b>
      </div>
      <div
        className="absolute top-3 -translate-x-1/2 whitespace-nowrap text-[11px] text-stitch-muted"
        style={{ left: `${premiumPct}%` }}
      >
        Premium <b className="text-stitch-brand-dark">{formatValue(premium)}</b>
        {unit && <span className="ml-0.5">{unit}</span>}
      </div>
    </div>
  );
}
