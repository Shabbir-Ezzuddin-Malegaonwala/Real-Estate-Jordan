import type { ReactNode } from "react";
import type { AreaBundle, BuildabilityItem, LaunchScenario } from "../lib/contract";
import { Card, Tile } from "../ui";
import { HBarList, MarginBar } from "../ui/charts";

type Focus = "land" | "margin" | "build" | "scenarios" | "buildability";
const ORDER: Focus[] = ["land", "margin", "build", "scenarios", "buildability"];

const STATUS_LABEL: Record<BuildabilityItem["status"], string> = {
  ok: "Clear",
  partial: "Partial",
  caution: "Caution",
  risk: "Risk",
  unknown: "Awaiting data — not yet collected",
};
const STATUS_CLASS: Record<BuildabilityItem["status"], string> = {
  ok: "bg-[#e3f4ee] text-[#0a7a5b]",
  partial: "bg-[#fdece0] text-stitch-warn",
  caution: "bg-[#fdece0] text-stitch-warn",
  risk: "bg-stitch-warn text-white",
  unknown: "bg-stitch-soft text-stitch-muted",
};

function ScenariosCard({ scenarios }: { scenarios: LaunchScenario[] }) {
  const items = scenarios.map((s) => ({ label: s.name, value: s.price, highlighted: s.name === "Recommended" }));
  return (
    <Card>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Launch scenarios</div>
      <HBarList items={items} formatValue={(v) => `${v.toLocaleString()} JD/m²`} title="Launch scenarios" />
      <ul className="mt-3 flex flex-col gap-2">
        {scenarios.map((s) => (
          <li key={s.name} className="text-[13px]">
            <span className="font-semibold text-stitch-ink">{s.name}</span>
            <span className="ml-1.5 text-stitch-muted">{s.rationale}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function BuildabilityCard({ items }: { items: BuildabilityItem[] }) {
  return (
    <Card>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Buildability checklist</div>
      <ul className="flex flex-col">
        {items.map((it) => (
          <li key={it.label} className="flex items-start gap-2.5 border-b border-stitch-soft py-2.5 text-sm last:border-b-0">
            <span className={`mt-0.5 flex-none rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${STATUS_CLASS[it.status]}`}>
              {STATUS_LABEL[it.status]}
            </span>
            <div>
              <span className="font-semibold text-stitch-ink">{it.label}</span>
              <span className="block text-xs text-stitch-muted mt-0.5">{it.reason}</span>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function CostProfitView({ bundle, focus }: { bundle: AreaBundle; focus: Focus }) {
  const { costProfit, summary } = bundle;
  // Fallback scenarios when the real adapter hasn't populated costProfit.scenarios
  // (or in mock mode) — derived from the same min/rec/premium band shown in Pricing,
  // so the sub-view still renders honestly instead of going blank.
  const scenarios: LaunchScenario[] =
    costProfit.scenarios ?? [
      { name: "Minimum-safe", price: summary.minSafe, rationale: "The defensible floor — still clears even if the market softens." },
      { name: "Recommended", price: summary.price, rationale: "The engine's best estimate — balances launch speed against upside." },
      { name: "Premium launch", price: summary.premium, rationale: "The ceiling — achievable with strong differentiation, view, or timing." },
    ];
  const buildability: BuildabilityItem[] =
    costProfit.buildability ?? [
      "Zoning & permitted height",
      "Slope & flood risk",
      "Soil & geotechnical",
      "Road access",
      "Utilities (water / power / sewer)",
    ].map((label) => ({ label, status: "unknown", reason: "Awaiting data — not yet collected" }));

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
    scenarios: <ScenariosCard scenarios={scenarios} />,
    buildability: <BuildabilityCard items={buildability} />,
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
