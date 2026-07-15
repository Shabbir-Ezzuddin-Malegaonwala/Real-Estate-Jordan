import { useEffect, useState } from "react";
import type { RecommendationResult, ScenarioComparison, ScenarioOverrides } from "../types";
import { requestScenarioCompare } from "../lib/intel";
import { jd, pct } from "../lib/format";

// Light side-by-side comparison of a few preset scenarios vs the base launch.
// Calls POST /scenario/compare when live; deterministic local model until then.
const PRESETS: { label: string; overrides: ScenarioOverrides }[] = [
  {
    label: "Build taller",
    overrides: { floors: 30, target_floor: 27, apply_height_view_premium: true, finish: "standard" },
  },
  {
    label: "Fancier finish",
    overrides: { floors: 20, target_floor: 15, apply_height_view_premium: true, finish: "luxury" },
  },
  {
    label: "Building costs +20%",
    overrides: { floors: 20, target_floor: 15, construction_cost_delta_pct: 20 },
  },
];

export function ScenarioCompare({ r }: { r: RecommendationResult }) {
  const [cmp, setCmp] = useState<ScenarioComparison | null>(null);

  useEffect(() => {
    let alive = true;
    requestScenarioCompare(r, PRESETS).then((c) => {
      if (alive) setCmp(c);
    });
    return () => {
      alive = false;
    };
  }, [r]);

  if (!cmp) return null;

  return (
    <section className="px-4 pt-5" aria-label="Scenario comparison">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-[13px] font-semibold text-ink">Compare options</h3>
        <span className="text-2xs text-ink-mute">{cmp.source === "local" ? "quick estimate" : "live"}</span>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-line-soft text-2xs uppercase tracking-wide text-ink-mute">
              <th className="px-2.5 py-2 text-left font-medium">Option</th>
              <th className="px-2.5 py-2 text-right font-medium">Best price</th>
              <th className="px-2.5 py-2 text-right font-medium">Range</th>
              <th className="px-2.5 py-2 text-right font-medium">vs now</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line-soft">
            <tr>
              <td className="px-2.5 py-2 text-ink-dim">Now</td>
              <td className="tnum px-2.5 py-2 text-right text-ink">{jd(cmp.base.recommended_jd_m2)}</td>
              <td className="tnum px-2.5 py-2 text-right text-ink-mute">
                {jd(cmp.base.min_safe_jd_m2)}–{jd(cmp.base.premium_jd_m2)}
              </td>
              <td className="px-2.5 py-2 text-right text-ink-faint">—</td>
            </tr>
            {cmp.columns.map((col) => (
              <tr key={col.label}>
                <td className="px-2.5 py-2 text-ink">{col.label}</td>
                <td className="tnum px-2.5 py-2 text-right font-medium text-accent">{jd(col.band.recommended_jd_m2)}</td>
                <td className="tnum px-2.5 py-2 text-right text-ink-mute">
                  {jd(col.band.min_safe_jd_m2)}–{jd(col.band.premium_jd_m2)}
                </td>
                <td className={`tnum px-2.5 py-2 text-right ${col.net_pct >= 0 ? "text-pos" : "text-neg"}`}>
                  {col.net_pct === 0 ? "±0%" : pct(col.net_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-1.5 text-2xs leading-relaxed text-ink-faint">
        The bonus for taller floors and fancier finish is our best guess, not from real sales.
      </p>
    </section>
  );
}
