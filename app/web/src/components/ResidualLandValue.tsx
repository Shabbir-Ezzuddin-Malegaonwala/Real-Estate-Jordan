import { useEffect, useMemo, useState } from "react";
import type { ResidualBreakdown, ResidualInputs } from "../types";
import { requestResidual, localResidual } from "../lib/intel";
import { jd } from "../lib/format";

type Inputs = Omit<ResidualInputs, "neighborhood">;

const DEFAULTS: Inputs = {
  buildable_area_m2: 2000,
  construction_cost_per_m2: 450,
  finance_pct: 6,
  fees_pct: 5, // matches the engine default (professional fees = 5% of construction)
  profit_pct: 20,
};

// The builder's core land question: "what can I pay for the land and still hit my
// margin?" Residual method = GDV − construction − finance − fees − profit. The
// local path is exact (pure formula); it wires to POST /residual-land-value when
// that endpoint deploys. GDV defaults to the engine's recommended launch price.
export function ResidualLandValue({
  neighborhood,
  recommendedJdM2,
}: {
  neighborhood: string;
  recommendedJdM2: number;
}) {
  const [inp, setInp] = useState<Inputs>(DEFAULTS);
  const initial = useMemo(
    () => localResidual({ ...DEFAULTS, neighborhood }, recommendedJdM2),
    [neighborhood, recommendedJdM2],
  );
  const [out, setOut] = useState<ResidualBreakdown>(initial);

  useEffect(() => {
    let alive = true;
    const t = setTimeout(async () => {
      const full: ResidualInputs = { ...inp, neighborhood };
      const res = await requestResidual(full, recommendedJdM2);
      if (alive) setOut(res);
    }, 300);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [inp, neighborhood, recommendedJdM2]);

  const num = (key: keyof Inputs) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setInp((p) => ({ ...p, [key]: e.target.value === "" ? 0 : Number(e.target.value) }));

  const viable = out.max_land_value > 0;

  return (
    <section className="px-4 pt-5" aria-label="Residual land value">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-[13px] font-semibold text-ink">Residual Land Value</h3>
        <span className="text-2xs text-ink-mute">
          {out.source === "local" ? "computed locally" : "engine"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <NumField id="rlv-area" label="Buildable area (m²)" value={inp.buildable_area_m2} onChange={num("buildable_area_m2")} />
        <NumField id="rlv-cost" label="Build cost (JD/m²)" value={inp.construction_cost_per_m2} onChange={num("construction_cost_per_m2")} />
        <NumField id="rlv-fin" label="Finance (%)" value={inp.finance_pct} onChange={num("finance_pct")} step={0.5} />
        <NumField id="rlv-fees" label="Fees (%)" value={inp.fees_pct} onChange={num("fees_pct")} step={0.5} />
        <NumField id="rlv-profit" label="Target profit (%)" value={inp.profit_pct} onChange={num("profit_pct")} step={1} />
        <NumField id="rlv-gdv" label="GDV (JD/m²)" value={Math.round(out.gdv_per_m2)} readOnly hint="= recommended launch" />
      </div>

      <div className={`mt-3 rounded-[3px] border p-3 ${viable ? "border-accent/60 bg-accent/[0.07]" : "border-neg/50 bg-neg/[0.06]"}`}>
        <div className="flex items-end justify-between">
          <div>
            <div className={`text-2xs uppercase tracking-wide ${viable ? "text-accent" : "text-neg"}`}>
              Max defensible land price
            </div>
            <div className="mt-0.5 text-2xs text-ink-mute tnum">
              {viable ? `${jd(out.max_land_value_per_m2)} JD per buildable m²` : "negative — project not viable at these inputs"}
            </div>
          </div>
          <div className={`tnum font-mono text-[24px] font-medium leading-none ${viable ? "text-accent" : "text-neg"}`}>
            {jd(out.max_land_value)}
          </div>
        </div>
      </div>

      <div className="card mt-2 divide-y divide-line-soft">
        <Row label="Gross development value (GDV)" value={out.gdv} tone="pos" />
        <Row label="− Construction cost" value={-out.construction_cost} />
        <Row label="− Finance cost" value={-out.finance_cost} />
        <Row label="− Fees" value={-out.fees} />
        <Row label="− Developer profit" value={-out.developer_profit} />
        <Row label="= Residual land value" value={out.max_land_value} tone={viable ? "accent" : "neg"} bold />
      </div>
      <p className="mt-1.5 text-2xs leading-relaxed text-ink-faint">
        Deterministic residual method. Land above this figure erodes the target margin — the
        builder's ceiling for what to pay, not a market land quote.
      </p>
    </section>
  );
}

function NumField({
  id, label, value, onChange, step = 1, readOnly, hint,
}: {
  id: string; label: string; value: number;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  step?: number; readOnly?: boolean; hint?: string;
}) {
  return (
    <label htmlFor={id} className="block">
      <span className="mb-0.5 block text-2xs text-ink-mute">{label}</span>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        step={step}
        value={value}
        onChange={onChange}
        readOnly={readOnly}
        className={`input tnum ${readOnly ? "opacity-70" : ""}`}
      />
      {hint && <span className="mt-0.5 block text-2xs text-ink-faint">{hint}</span>}
    </label>
  );
}

function Row({ label, value, tone, bold }: { label: string; value: number; tone?: "pos" | "accent" | "neg"; bold?: boolean }) {
  const color = tone === "accent" ? "text-accent" : tone === "neg" ? "text-neg" : tone === "pos" ? "text-ink" : "text-ink-dim";
  return (
    <div className="flex items-center justify-between px-2.5 py-1.5 text-[12px]">
      <span className={bold ? "font-medium text-ink" : "text-ink-dim"}>{label}</span>
      <span className={`tnum ${bold ? "font-medium" : ""} ${color}`}>{jd(Math.abs(value))}</span>
    </div>
  );
}
