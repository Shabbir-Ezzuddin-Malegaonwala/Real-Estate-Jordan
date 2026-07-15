import { useState, type ReactNode } from "react";
import type { AreaBundle, BuildabilityItem, LaunchScenario } from "../lib/contract";
import { requestResidual } from "../lib/intel";
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

// Editable inputs that re-run the residual-land-value calc for THIS area, so the
// land value / margin / build cost react to the developer's own plot/cost/profit.
function InputsPanel({
  area, gdv, defaults, onResult,
}: {
  area: string;
  gdv: number;
  defaults: { buildable: number; construction: number; profit: number; finish: string };
  onResult: (landValueK: number | null, profit: number, construction: number) => void;
}) {
  const [buildable, setBuildable] = useState(defaults.buildable);
  const [construction, setConstruction] = useState(defaults.construction);
  const [profit, setProfit] = useState(defaults.profit);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function analyse() {
    setLoading(true);
    setErr(null);
    const r = await requestResidual(
      { neighborhood: area, buildable_area_m2: buildable, construction_cost_per_m2: construction,
        finance_pct: 6, fees_pct: 5, profit_pct: profit },
      gdv,
    );
    setLoading(false);
    if (!r || typeof r.max_land_value_per_m2 !== "number") {
      setErr("Couldn't recompute — is the API running?");
      onResult(null, profit, construction);
      return;
    }
    onResult(Math.round(r.max_land_value_per_m2), profit, construction);
  }

  const fld = "w-full rounded-md border border-stitch-soft px-2 py-1.5 text-sm text-stitch-ink focus:border-stitch-brand focus:outline-none";
  const lbl = "mb-1 block text-[11px] font-semibold uppercase tracking-wide text-stitch-muted";
  return (
    <Card>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Your inputs — press Analyse</div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className={lbl} htmlFor="cp-build">Buildable (m²)</label>
          <input id="cp-build" type="number" min={100} className={fld} value={buildable} onChange={(e) => setBuildable(Number(e.target.value) || 0)} />
        </div>
        <div>
          <label className={lbl} htmlFor="cp-cost">Build JD/m²</label>
          <input id="cp-cost" type="number" min={100} className={fld} value={construction} onChange={(e) => setConstruction(Number(e.target.value) || 0)} />
        </div>
        <div>
          <label className={lbl} htmlFor="cp-profit">Target profit %</label>
          <input id="cp-profit" type="number" min={5} max={50} className={fld} value={profit} onChange={(e) => setProfit(Number(e.target.value) || 0)} />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button type="button" onClick={analyse} disabled={loading}
          className="rounded-md bg-stitch-brand px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-40">
          {loading ? "Analysing…" : "Analyse"}
        </button>
        <span className="text-[12px] text-stitch-muted">Land value below updates for a {gdv.toLocaleString()} JD/m² sale.</span>
      </div>
      {err && <p className="mt-2 text-[12.5px] text-red-600">{err}</p>}
    </Card>
  );
}

export function CostProfitView({ bundle, focus }: { bundle: AreaBundle; focus: Focus }) {
  const { costProfit, summary } = bundle;
  // Live overrides from the InputsPanel (null until the user presses Analyse).
  const [landK, setLandK] = useState<number | null>(null);
  const [profitPct, setProfitPct] = useState<number>(costProfit.marginPct);
  const [buildJdM2, setBuildJdM2] = useState<number>(costProfit.buildCostJdM2);
  const shownLandK = landK ?? costProfit.landValueK;
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
        value={shownLandK.toLocaleString()}
        unit="K JD/dunum"
        tone="brand"
        hint={landK != null ? "Recomputed from your inputs — above this the project stops making your target profit." : "Above this, the project stops making a normal profit. Press Analyse to use your own inputs."}
      />
    ),
    margin: (
      <Card>
        <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Profit margin</div>
        <div className="mt-1 text-[32px] font-bold leading-none text-stitch-green">{profitPct}%</div>
        <div className="mt-3">
          <MarginBar costPct={100 - profitPct} profitPct={profitPct} />
        </div>
        <div className="mt-2 text-[13px] text-stitch-muted">Developers usually target 15–25%.</div>
      </Card>
    ),
    build: (
      <Tile
        label="Estimated build cost"
        value={`~${buildJdM2.toLocaleString()}`}
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
      <InputsPanel
        area={summary.name}
        gdv={summary.price}
        defaults={{ buildable: Math.round(costProfit.plotSizeDunum * 1000), construction: costProfit.buildCostJdM2, profit: costProfit.marginPct, finish: costProfit.finish }}
        onResult={(k, p, c) => { setLandK(k); setProfitPct(p); setBuildJdM2(c); }}
      />
      {order.map((k) => (
        <div key={k}>{tiles[k]}</div>
      ))}
    </div>
  );
}
