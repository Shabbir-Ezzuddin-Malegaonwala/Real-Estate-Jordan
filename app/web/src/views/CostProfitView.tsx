import type { ReactNode } from "react";
import type { AreaBundle } from "../lib/contract";
import { Card, Tile } from "../ui";
import { MarginBar } from "../ui/charts";

type Focus = "land" | "margin" | "build";
const ORDER: Focus[] = ["land", "margin", "build"];

export function CostProfitView({ bundle, focus }: { bundle: AreaBundle; focus: Focus }) {
  const { costProfit } = bundle;

  const tiles: Record<Focus, ReactNode> = {
    land: (
      <Tile
        label="Land value — most you can pay"
        value={costProfit.landValueK.toLocaleString()}
        unit="K JD/dunum"
        tone="brand"
        hint="Above this, the project stops making a normal profit."
      />
    ),
    margin: (
      <Card>
        <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Profit margin</div>
        <div className="mt-1 text-[32px] font-bold leading-none text-stitch-green">{costProfit.marginPct}%</div>
        <div className="mt-3">
          <MarginBar costPct={100 - costProfit.marginPct} profitPct={costProfit.marginPct} />
        </div>
        <div className="mt-2 text-[13px] text-stitch-muted">Developers usually target 15–25%.</div>
      </Card>
    ),
    build: (
      <Tile
        label="Estimated build cost"
        value={`~${costProfit.buildCostJdM2.toLocaleString()}`}
        unit="JD/m²"
        hint={`${costProfit.finish} finish · from official cost data.`}
      />
    ),
  };

  const order = [focus, ...ORDER.filter((k) => k !== focus)];

  return (
    <div className="flex flex-col gap-3">
      {order.map((k) => (
        <div key={k}>{tiles[k]}</div>
      ))}
      <Card>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Inputs</div>
        <div className="flex flex-col gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-stitch-muted">Plot size</span>
            <span className="font-semibold text-stitch-ink">{costProfit.plotSizeDunum} dunum</span>
          </div>
          <div className="flex justify-between">
            <span className="text-stitch-muted">Finish</span>
            <span className="font-semibold text-stitch-ink">{costProfit.finish}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
