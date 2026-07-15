import { useEffect, useState } from "react";
import type { RecommendationResult, ScenarioOverrides, ScenarioResult } from "../types";
import { requestScenario, localScenario } from "../lib/intel";
import { jd, pct } from "../lib/format";

const FINISH = ["standard", "basic", "high", "luxury"];

// "What-if" levers over the base recommendation. Toggling any lever recomputes
// base vs scenario + a labelled, signed delta list + a plain explanation. Wires
// to POST /scenario when live; until then the deterministic local model runs.
export function ScenarioPanel({ r }: { r: RecommendationResult }) {
  const [ov, setOv] = useState<ScenarioOverrides>({
    floors: 20,
    target_floor: 15,
    finish: "standard",
    construction_cost_delta_pct: 0,
    metro_delay_years: 0,
    launch_delay_months: 0,
    apply_height_view_premium: true,
  });
  const [res, setRes] = useState<ScenarioResult>(() => localScenario(r, ov));

  useEffect(() => {
    let alive = true;
    const t = setTimeout(async () => {
      const out = await requestScenario(r, ov);
      if (alive) setRes(out);
    }, 250);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [r, ov]);

  const net =
    r.recommended_jd_m2 > 0
      ? (res.scenario.recommended_jd_m2 - res.base.recommended_jd_m2) / res.base.recommended_jd_m2
      : 0;

  return (
    <section className="px-4 pt-5" aria-label="Scenario simulation">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-[13px] font-semibold text-ink">Try changes (What-if)</h3>
        <span className="text-2xs text-ink-mute">{res.source === "local" ? "quick estimate" : "live"}</span>
      </div>

      <div className="card space-y-2.5 p-3">
        <Slider id="sc-floors" label="How many floors" value={ov.floors ?? 0} min={4} max={40} step={1}
          onChange={(v) => setOv((p) => ({ ...p, floors: v, target_floor: Math.min(p.target_floor ?? v, v) }))} />
        <Slider id="sc-target" label="Which floor to sell" value={ov.target_floor ?? 0} min={1} max={ov.floors ?? 40} step={1}
          onChange={(v) => setOv((p) => ({ ...p, target_floor: v }))} />
        <div className="grid grid-cols-2 gap-2">
          <label htmlFor="sc-finish" className="block">
            <span className="mb-0.5 block text-2xs text-ink-mute">Finish quality</span>
            <select id="sc-finish" value={ov.finish} onChange={(e) => setOv((p) => ({ ...p, finish: e.target.value }))} className="input">
              {FINISH.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>
          <label className="flex items-end gap-2 pb-1">
            <input type="checkbox" checked={!!ov.apply_height_view_premium}
              onChange={(e) => setOv((p) => ({ ...p, apply_height_view_premium: e.target.checked }))}
              className="h-3.5 w-3.5 accent-[rgb(var(--c-accent))]" />
            <span className="text-2xs text-ink-dim">Add city-view bonus</span>
          </label>
        </div>
        <Slider id="sc-cost" label="Building cost change" value={ov.construction_cost_delta_pct ?? 0} min={-20} max={40} step={5} suffix="%"
          onChange={(v) => setOv((p) => ({ ...p, construction_cost_delta_pct: v }))} />
        <Slider id="sc-metro" label="Metro delayed (years)" value={ov.metro_delay_years ?? 0} min={0} max={5} step={1}
          onChange={(v) => setOv((p) => ({ ...p, metro_delay_years: v }))} />
        <Slider id="sc-launch" label="Selling delayed (months)" value={ov.launch_delay_months ?? 0} min={0} max={24} step={3}
          onChange={(v) => setOv((p) => ({ ...p, launch_delay_months: v }))} />
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2">
        <BandCard label="Now" band={res.base.recommended_jd_m2} sub={`${jd(res.base.min_safe_jd_m2)}–${jd(res.base.premium_jd_m2)}`} />
        <BandCard label="After changes" band={res.scenario.recommended_jd_m2}
          sub={`${jd(res.scenario.min_safe_jd_m2)}–${jd(res.scenario.premium_jd_m2)}`} primary delta={net} />
      </div>

      {res.deltas.length > 0 && (
        <div className="card mt-2 divide-y divide-line-soft">
          {res.deltas.map((d) => (
            <div key={d.label} className="px-2.5 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12px] text-ink-dim">{d.label}</span>
                {d.delta_pct !== 0 && (
                  <span className={`tnum text-[12px] ${d.delta_pct >= 0 ? "text-pos" : "text-neg"}`}>{pct(d.delta_pct)}</span>
                )}
              </div>
              {d.detail && <p className="mt-0.5 text-2xs leading-relaxed text-ink-faint">{d.detail}</p>}
            </div>
          ))}
        </div>
      )}

      <p className="mt-2 text-2xs leading-relaxed text-ink-dim">{res.explanation}</p>
    </section>
  );
}

function Slider({
  id, label, value, min, max, step, onChange, suffix = "",
}: {
  id: string; label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; suffix?: string;
}) {
  return (
    <label htmlFor={id} className="block">
      <span className="mb-0.5 flex items-center justify-between text-2xs text-ink-mute">
        <span>{label}</span>
        <span className="tnum text-ink-dim">{value > 0 && suffix === "%" ? "+" : ""}{value}{suffix}</span>
      </span>
      <input id={id} type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1 w-full cursor-pointer accent-[rgb(var(--c-accent))]" />
    </label>
  );
}

function BandCard({
  label, band, sub, primary, delta,
}: { label: string; band: number; sub: string; primary?: boolean; delta?: number }) {
  return (
    <div className={`rounded-[3px] border p-2.5 ${primary ? "border-accent/60 bg-accent/[0.07]" : "border-line bg-panel"}`}>
      <div className={`text-2xs uppercase tracking-wide ${primary ? "text-accent" : "text-ink-mute"}`}>{label}</div>
      <div className={`tnum mt-1 font-mono font-medium leading-none ${primary ? "text-[22px] text-accent" : "text-[20px] text-ink"}`}>{jd(band)}</div>
      <div className="mt-1 flex items-center gap-1.5 text-2xs tnum text-ink-mute">
        <span>{sub}</span>
        {primary && delta != null && delta !== 0 && (
          <span className={delta >= 0 ? "text-pos" : "text-neg"}>{pct(delta)}</span>
        )}
      </div>
    </div>
  );
}
