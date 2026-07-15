import type { EngineResult } from "./types";
import { jd } from "../../lib/format";

// Inline rich card for an engine price result: the min-safe -> recommended ->
// premium band, confidence, honest coverage flags, and top comps. Rendered in
// the chat whenever get_recommendation priced something.
export function EngineCard({ r }: { r: EngineResult }) {
  const conf = r.confidence;
  const [lo, hi] = conf.interval_jd_m2 ?? [r.min_safe_price_jd_m2, r.premium_price_jd_m2];
  const thin = r.coverage?.thin_data;
  const notDerivable = (r.evidence_objects ?? []).filter((e) =>
    /not[_ ]derivable/i.test(e.adjustment ?? ""),
  );

  return (
    <div className="card mt-2 overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <div>
          <div className="label-eyebrow">Engine price · {r.property_type}</div>
          <div className="text-[13px] font-semibold text-ink">{r.resolution?.resolved_to ?? r.neighborhood}</div>
        </div>
        <ConfidenceBadge label={conf.label} numeric={conf.numeric} />
      </div>

      <div className="grid grid-cols-3 divide-x divide-line">
        <Band label="Min-safe" value={r.min_safe_price_jd_m2} />
        <Band label="Recommended" value={r.recommended_price_jd_m2} accent />
        <Band label="Premium" value={r.premium_price_jd_m2} />
      </div>

      <div className="border-t border-line px-3 py-2 text-2xs text-ink-mute tnum">
        Confidence interval {jd(lo)}–{jd(hi)} JD/m² · {r.resolution?.sale_comps_in_area ?? "?"} comps in area
      </div>

      {thin && (
        <div className="border-t border-warn/30 bg-warn/10 px-3 py-2 text-2xs text-warn">
          ⚠ Thin comp coverage — treat this band as indicative.
        </div>
      )}
      {notDerivable.length > 0 && (
        <div className="border-t border-line px-3 py-2 text-2xs text-ink-mute">
          Not derivable from data: {notDerivable.map((e) => e.factor).join(", ")}.
        </div>
      )}

      {r.comparables && r.comparables.length > 0 && (
        <div className="border-t border-line px-3 py-2">
          <div className="label-eyebrow mb-1">Top comparables</div>
          <div className="space-y-1">
            {r.comparables.slice(0, 4).map((c, i) => (
              <div key={i} className="flex items-center justify-between text-2xs text-ink-dim tnum">
                <span>
                  {c.area_m2 ? `${jd(c.area_m2)} m²` : "—"}
                  {c.bedrooms != null ? ` · ${c.bedrooms} bed` : ""}
                  {c.view && c.view !== "unknown" ? ` · ${c.view}` : ""}
                </span>
                <span className="text-ink">{jd(c.price_per_m2 ?? c.original_ppm2 ?? 0)} JD/m²</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Band({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="px-3 py-2 text-center">
      <div className="label-eyebrow">{label}</div>
      <div className={`tnum text-[15px] font-semibold ${accent ? "text-accent" : "text-ink"}`}>{jd(value)}</div>
      <div className="text-2xs text-ink-faint">JD/m²</div>
    </div>
  );
}

function ConfidenceBadge({ label, numeric }: { label: string; numeric: number }) {
  const full = { H: "High", M: "Medium", L: "Low" }[label] ?? label;
  const tone = label === "H" ? "text-pos border-pos/40" : label === "L" ? "text-neg border-neg/40" : "text-warn border-warn/40";
  return (
    <span className={`rounded-[3px] border px-2 py-[3px] text-2xs font-medium ${tone}`}>
      {full} · {Math.round(numeric)}
    </span>
  );
}
