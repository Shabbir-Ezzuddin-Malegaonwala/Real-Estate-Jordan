import type { ReactNode } from "react";
import { useApp } from "../lib/store";
import type { AreaBundle, LaunchStatus, PricingData } from "../lib/contract";
import { Card, StatusPill, PriceBand, Confidence } from "../ui";
import type { StatusTone } from "../ui";
import { Sparkline } from "../ui/charts";

const STATUS_LABEL: Record<LaunchStatus, string> = {
  READY: "READY TO LAUNCH",
  WAIT: "AWAITING DATA",
  REVIEW: "NEEDS REVIEW",
};
const STATUS_TONE: Record<LaunchStatus, StatusTone> = { READY: "ready", WAIT: "wait", REVIEW: "review" };
const SEVERITY_CLASSES: Record<"high" | "medium" | "low", string> = {
  high: "bg-stitch-warn text-white",
  medium: "bg-stitch-warn/15 text-stitch-warn",
  low: "bg-stitch-soft text-stitch-muted",
};

function trendLabel(trend: number[]): string {
  if (trend.length < 2) return "→ Stable";
  const change = ((trend[trend.length - 1] - trend[0]) / trend[0]) * 100;
  if (change > 2) return "↗ Rising";
  if (change < -2) return "↘ Falling";
  return "→ Stable";
}

// Native <details> expander — collapsed by default, no JS state needed.
// Progressive disclosure per the UI/UX blueprint: simple on the face, depth on demand.
function Expander({ label, children }: { label: string; children: ReactNode }) {
  return (
    <details className="group rounded-xl border border-stitch-line bg-stitch-card">
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-xs font-semibold uppercase tracking-wide text-stitch-muted">
        {label}
        <span className="text-stitch-muted transition-transform group-open:rotate-180">▾</span>
      </summary>
      <div className="px-4 pb-4">{children}</div>
    </details>
  );
}

function Waterfall({ rows }: { rows: NonNullable<PricingData["waterfall"]> }) {
  const max = Math.max(...rows.map((r) => Math.abs(r.pct)), 1);
  return (
    <div className="flex flex-col gap-2.5">
      {rows.map((r) => (
        <div key={r.factor}>
          <div className="mb-1 flex items-center justify-between text-[13px]">
            <span className="text-stitch-ink">{r.factor}</span>
            <span className={`tabular-nums font-semibold ${r.positive ? "text-stitch-green" : "text-stitch-warn"}`}>
              {r.positive ? "+" : ""}
              {r.pct.toFixed(1)}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-stitch-soft">
            <div
              className={`h-full rounded-full ${r.positive ? "bg-stitch-green" : "bg-stitch-warn"}`}
              style={{ width: `${(Math.abs(r.pct) / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function ConfidenceBreakdown({ rows }: { rows: NonNullable<PricingData["confidenceBreakdown"]> }) {
  return (
    <div className="flex flex-col gap-3">
      {rows.map((r) => (
        <div key={r.label}>
          <div className="mb-1 flex items-center justify-between text-[13px]">
            <span className="text-stitch-ink">{r.label}</span>
            <span className="tabular-nums font-semibold text-stitch-brand-dark">{Math.round(r.score)}/100</span>
          </div>
          <div className="h-2 rounded-full bg-stitch-soft">
            <div className="h-full rounded-full bg-stitch-brand" style={{ width: `${Math.max(0, Math.min(100, r.score))}%` }} />
          </div>
          {r.reason && <div className="mt-1 text-[12px] text-stitch-muted">{r.reason}</div>}
        </div>
      ))}
    </div>
  );
}

function Risks({ rows }: { rows: NonNullable<PricingData["risks"]> }) {
  return (
    <ul className="flex flex-col gap-2.5">
      {rows.map((r) => (
        <li key={r.factor} className="flex items-start gap-2.5 text-sm">
          <span className={`mt-0.5 flex-none rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${SEVERITY_CLASSES[r.severity]}`}>
            {r.severity}
          </span>
          <div>
            <span className="font-semibold text-stitch-ink">{r.factor}</span>
            <span className="block text-xs text-stitch-muted mt-0.5">{r.detail}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function Sources({ rows }: { rows: NonNullable<PricingData["evidence"]> }) {
  return (
    <ul className="flex flex-col gap-2">
      {rows.map((s) => (
        <li key={s.name} className="text-[13px]">
          {s.url ? (
            <a href={s.url} target="_blank" rel="noreferrer" className="font-semibold text-stitch-brand hover:underline">
              {s.name}
            </a>
          ) : (
            <span className="font-semibold text-stitch-ink">{s.name}</span>
          )}
          <span className="ml-1.5 text-stitch-muted">
            {[s.what, s.date].filter(Boolean).join(" · ")}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function PricingView({ bundle, focus }: { bundle: AreaBundle; focus: "price" | "comps" | "trend" }) {
  const { setView } = useApp();
  const { summary, reasons, comparables, waterfall, confidenceBreakdown, risks, evidence, narrative } = bundle.pricing;
  const margin = bundle.costProfit.marginPct;

  const askLink = (
    <button
      type="button"
      onClick={() => setView("chatnew")}
      className="mt-1 text-left text-[12.5px] font-semibold text-stitch-brand hover:underline"
    >
      🤖 Ask the assistant why
    </button>
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl bg-gradient-to-br from-stitch-brand-dark to-stitch-brand px-4 py-3.5 text-white">
        <div className="text-base font-bold leading-snug">Launch at {summary.price.toLocaleString()} JD/m²</div>
        <div className="mt-0.5 text-[13px] text-white/90">
          {STATUS_LABEL[summary.status]} · {margin}% margin · in line with the market
        </div>
      </div>

      {focus === "trend" && (
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Price trend</div>
          <div className="mt-2 text-lg font-bold text-stitch-ink">{trendLabel(summary.trend)}</div>
          <div className="mt-2">
            <Sparkline data={summary.trend} width={320} height={110} title="90-day price trend" />
          </div>
          <div className="mt-2 text-[13px] text-stitch-muted">How the area price moved over the last 90 days.</div>
        </Card>
      )}

      {focus === "comps" && (
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Comparable evidence</div>
          <table className="mt-2 w-full text-left text-[13px]">
            <thead>
              <tr>
                <th className="border-b border-stitch-line pb-2 text-[10px] font-semibold uppercase text-stitch-muted">Size</th>
                <th className="border-b border-stitch-line pb-2 text-[10px] font-semibold uppercase text-stitch-muted">Asking</th>
                <th className="border-b border-stitch-line pb-2 text-[10px] font-semibold uppercase text-stitch-muted">Adjusted</th>
              </tr>
            </thead>
            <tbody>
              {comparables.map((c) => (
                <tr key={`${c.size}-${c.asking}`}>
                  <td className="border-b border-stitch-line py-2">{c.size} m²</td>
                  <td className="border-b border-stitch-line py-2">{c.asking.toLocaleString()}</td>
                  <td className="border-b border-stitch-line py-2">{c.adjusted.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-2 text-[13px] text-stitch-muted">{summary.comps} comparable sales behind this price.</div>
        </Card>
      )}

      {focus === "price" && (
        <>
          <Card>
            <StatusPill tone={STATUS_TONE[summary.status]} label={STATUS_LABEL[summary.status]} />
            <div className="mt-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">
              Recommended launch price
            </div>
            <div className="mt-1 text-[32px] font-bold leading-none text-stitch-brand-dark">
              {summary.price.toLocaleString()}
              <span className="ml-1.5 text-sm font-semibold text-stitch-muted">JD/m²</span>
            </div>
            <div className="mt-3 flex items-center gap-2 text-[13px] text-stitch-muted">
              <span>{trendLabel(summary.trend)} · 90 days</span>
              <Sparkline data={summary.trend} title="90-day price trend" />
            </div>
          </Card>

          <Card>
            <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Price range</div>
            <PriceBand min={summary.minSafe} rec={summary.price} premium={summary.premium} unit="JD/m²" />
          </Card>

          <Card>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Confidence</div>
            <Confidence word={summary.confidence} filled={summary.confidenceDots} caption={`${summary.comps} nearby sales`} />
          </Card>

          <Card>
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Why this price</div>
            <ul className="flex flex-col gap-1.5">
              {reasons.map((r) => (
                <li key={r.text} className="flex items-center gap-2 text-sm">
                  <span className={r.ok ? "text-stitch-green" : "text-stitch-warn"}>{r.ok ? "✓" : "✗"}</span>
                  <span className="text-stitch-ink">{r.text}</span>
                </li>
              ))}
            </ul>
            {narrative && <div className="mt-3 border-t border-stitch-soft pt-3 text-[13px] text-stitch-muted">{narrative}</div>}
          </Card>

          {waterfall && waterfall.length > 0 && (
            <Expander label="Why this price — full breakdown">
              <Waterfall rows={waterfall} />
            </Expander>
          )}

          {confidenceBreakdown && confidenceBreakdown.length > 0 && (
            <Expander label="Confidence detail">
              <ConfidenceBreakdown rows={confidenceBreakdown} />
            </Expander>
          )}

          {risks && risks.length > 0 && (
            <Expander label="Risks">
              <Risks rows={risks} />
            </Expander>
          )}

          {evidence && evidence.length > 0 && (
            <Expander label="Why we believe this — sources">
              <Sources rows={evidence} />
            </Expander>
          )}
        </>
      )}

      {askLink}
    </div>
  );
}
