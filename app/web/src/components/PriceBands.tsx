import type { RecommendationResult } from "../types";
import { jd } from "../lib/format";
import { ConfidenceBadge } from "./ConfidenceBadge";

// Three-tier launch band — never a naked point estimate (MASTER-PLAN §6).
export function PriceBands({ r }: { r: RecommendationResult }) {
  const tiers = [
    { key: "min", label: "Lowest safe price", value: r.min_safe_jd_m2, hint: "Don't sell below this" },
    { key: "rec", label: "Best price to ask", value: r.recommended_jd_m2, hint: "What we suggest you sell at", primary: true },
    { key: "prm", label: "Highest price", value: r.premium_jd_m2, hint: "The most you can ask for" },
  ];

  const span = r.premium_jd_m2 - r.min_safe_jd_m2 || 1;
  const recPos = ((r.recommended_jd_m2 - r.min_safe_jd_m2) / span) * 100;

  return (
    <section className="px-4 pt-4" aria-label="Recommended launch price band">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-eyebrow">Price per square metre ({r.unit})</span>
        <ConfidenceBadge confidence={r.confidence} compact />
      </div>

      <div className="grid grid-cols-3 gap-2">
        {tiers.map((t) => (
          <div
            key={t.key}
            className={`rounded-[3px] border p-2.5 ${
              t.primary ? "border-accent/60 bg-accent/[0.07]" : "border-line bg-panel"
            }`}
          >
            <div className={`text-2xs uppercase tracking-wide ${t.primary ? "text-accent" : "text-ink-mute"}`}>
              {t.label}
            </div>
            <div
              className={`tnum mt-1 font-mono font-medium leading-none ${
                t.primary ? "text-[26px] text-accent" : "text-[20px] text-ink"
              }`}
            >
              {jd(t.value)}
            </div>
            <div className="mt-1 text-2xs text-ink-mute">{t.hint}</div>
          </div>
        ))}
      </div>

      {/* Band rail — recommended tick inside the min→premium range. */}
      <div className="relative mt-3 h-1.5 rounded-full bg-raised">
        <div className="absolute inset-y-0 left-0 rounded-full bg-accent/25" style={{ width: "100%" }} />
        <div
          className="absolute top-1/2 h-3 w-[2px] -translate-y-1/2 bg-accent"
          style={{ left: `calc(${recPos}% - 1px)` }}
          aria-hidden
        />
      </div>
      <div className="mt-1 flex justify-between text-2xs tnum text-ink-mute">
        <span>{jd(r.min_safe_jd_m2)}</span>
        <span className="text-ink-dim">typical nearby {jd(r.base_value_jd_m2)}</span>
        <span>{jd(r.premium_jd_m2)}</span>
      </div>
    </section>
  );
}
