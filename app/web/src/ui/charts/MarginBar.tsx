// Cost% vs profit% split bar — Demo-G's `.mbar` (Cost & Profit view).
export function MarginBar({
  costPct,
  profitPct,
  caption,
  title = "Cost vs profit split",
}: {
  costPct: number;
  profitPct: number;
  caption?: string;
  title?: string;
}) {
  return (
    <div>
      <div
        role="img"
        aria-label={title}
        className="relative h-6 overflow-hidden rounded-lg bg-stitch-soft"
      >
        <div
          className="absolute inset-y-0 left-0 flex items-center pl-2 text-[12px] font-bold text-stitch-warn"
          style={{ width: `${costPct}%`, background: "#f6d3c2" }}
        >
          Cost {Math.round(costPct)}%
        </div>
        <div
          className="absolute inset-y-0 right-0 flex items-center justify-end pr-2 text-[12px] font-bold text-[#0a7a5b]"
          style={{ width: `${profitPct}%`, background: "#cdeede" }}
        >
          Profit {Math.round(profitPct)}%
        </div>
      </div>
      {caption && <div className="mt-1.5 text-[13px] text-stitch-muted">{caption}</div>}
    </div>
  );
}
