import { useState } from "react";
import type { RecommendationResult, EvidenceObject } from "../types";
import { jd } from "../lib/format";
import { SourceChip } from "./SourceChip";

// The explainability centrepiece — written for a NON-EXPERT. Plain-English headline
// per row; the technical "how we know" (method + source listings) is tucked behind an
// expand arrow so the default view is calm and readable.
export function AdjustmentWaterfall({ r }: { r: RecommendationResult }) {
  const current = r.evidence_objects.filter((e) => e.category === "current_state");
  const pctRows = current.filter((e) => (e.kind ?? "pct") === "pct");
  const anchors = current.filter((e) => e.kind === "anchor");
  const contextRows = current.filter((e) => e.kind === "context");

  return (
    <section className="px-4 pt-5" aria-label="How we got to this price">
      <div className="mb-2">
        <h3 className="text-[13px] font-semibold text-ink">How we got to this price</h3>
        <p className="mt-0.5 text-2xs leading-relaxed text-ink-mute">
          We start from what similar apartments nearby are listed at, then add or subtract for
          the differences. Tap <span className="text-ink-dim">▸</span> on any line to see the proof.
        </p>
      </div>

      <div className="card overflow-hidden">
        {/* Starting point */}
        <div className="flex items-center justify-between bg-surface/40 px-2.5 py-2 text-[12px]">
          <span className="text-ink-dim">Starting point · what similar apartments are listed at</span>
          <span className="tnum text-ink">{jd(r.base_value_jd_m2)}</span>
        </div>

        {pctRows.map((e) => (
          <AdjRow key={e.factor} ev={e} />
        ))}

        {anchors.length > 0 && <AnchorBlock anchors={anchors} />}
        {contextRows.length > 0 && <ContextBlock rows={contextRows} />}

        {/* Conclusion */}
        <div className="border-t border-accent/30 bg-accent/[0.06]">
          <div className="flex items-center justify-between px-2.5 py-2.5">
            <span className="text-[12px] font-semibold text-accent">Our recommended price</span>
            <span className="tnum text-[15px] font-medium text-accent">
              {jd(r.recommended_jd_m2)} <span className="text-2xs text-accent/70">JD/m²</span>
            </span>
          </div>
          <div className="flex items-center justify-between border-t border-accent/15 px-2.5 py-1.5 text-2xs tnum text-ink-mute">
            <span>Safe floor {jd(r.min_safe_jd_m2)}</span>
            <span className="text-ink-faint">sensible range</span>
            <span>Top end {jd(r.premium_jd_m2)}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

// --- one adjustment line, collapsible ------------------------------------------
function AdjRow({ ev }: { ev: EvidenceObject }) {
  const [open, setOpen] = useState(false);
  const up = ev.direction === "increase";
  const down = ev.direction === "decrease";
  return (
    <div className="border-t border-line-soft">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-start justify-between gap-2 px-2.5 py-2 text-left transition-colors hover:bg-surface/30"
      >
        <div className="flex min-w-0 items-start gap-1.5">
          <span
            className={`mt-[3px] shrink-0 text-2xs text-ink-mute transition-transform ${open ? "rotate-90" : ""}`}
            aria-hidden
          >
            ▸
          </span>
          <div className="min-w-0">
            <span className="text-[12px] text-ink">{plainFactor(ev.factor)}</span>
            <p className="mt-0.5 text-2xs leading-relaxed text-ink-mute">{plainLine(ev)}</p>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className={`tnum text-[12px] ${up ? "text-pos" : down ? "text-neg" : "text-ink-dim"}`}>
            {ev.adjustment}
          </div>
          <ConfidenceDot level={ev.confidence} />
        </div>
      </button>

      {open && (
        <div className="border-t border-line-soft bg-surface/20 px-2.5 py-2 pl-6">
          <div className="text-2xs text-ink-mute">
            <span className="text-ink-dim">How we know:</span> {plainWhy(ev)}
          </div>
          {ev.sources.length > 0 && (
            <div className="mt-1.5">
              <div className="mb-1 text-2xs text-ink-faint">From these sources:</div>
              <div className="flex flex-wrap gap-1">
                {ev.sources.map((s, i) => (
                  <SourceChip key={i} source={s} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ConfidenceDot({ level }: { level: string }) {
  const map: Record<string, [string, string]> = {
    High: ["bg-pos", "Strong evidence"],
    Medium: ["bg-cyan-dim", "Fair evidence"],
    Low: ["bg-warn", "Weak evidence"],
  };
  const [color, label] = map[level] ?? ["bg-ink-faint", level];
  return (
    <span className="mt-1 inline-flex items-center gap-1 text-2xs text-ink-faint" title={label}>
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} aria-hidden />
      {label}
    </span>
  );
}

// --- cross-checks: written plainly --------------------------------------------
function AnchorBlock({ anchors }: { anchors: EvidenceObject[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-line bg-surface/30">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 px-2.5 py-2 text-left text-2xs text-ink-mute hover:bg-surface/40"
      >
        <span className={`text-ink-mute transition-transform ${open ? "rotate-90" : ""}`} aria-hidden>▸</span>
        We also sanity-checked the price two other ways
      </button>
      {open && (
        <div className="space-y-1.5 px-2.5 pb-2 pl-6">
          {anchors.map((a) => (
            <div key={a.factor} className="flex items-start justify-between gap-2">
              <span className="text-2xs text-ink-dim">{plainAnchor(a.factor)}</span>
              <span className="tnum shrink-0 text-2xs text-cyan">{a.adjustment}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ContextBlock({ rows }: { rows: EvidenceObject[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-line bg-surface/30">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 px-2.5 py-2 text-left text-2xs text-ink-mute hover:bg-surface/40"
      >
        <span className={`text-ink-mute transition-transform ${open ? "rotate-90" : ""}`} aria-hidden>▸</span>
        About this neighbourhood ({rows.length} facts)
      </button>
      {open && (
        <div className="space-y-2 px-2.5 pb-2 pl-6">
          {rows.map((c) => (
            <div key={c.factor}>
              <span className="text-2xs text-ink-dim">{c.factor}</span>
              <p className="mt-0.5 text-2xs leading-relaxed text-ink-mute">{c.explanation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- plain-language helpers ----------------------------------------------------
function plainFactor(factor: string): string {
  const vs = factor.match(/^(\w[\w\s]*?):\s*(.+?)\s+vs\s+/i);
  if (vs) {
    const kind = vs[1].trim().toLowerCase();
    const level = vs[2].trim();
    return `${cap(level)} ${kind}`; // "Garden view", "Covered parking"
  }
  if (/ask.?to.?transaction/i.test(factor)) return "Asking price → likely sale price";
  if (/^size/i.test(factor)) return "Size of the unit";
  return factor;
}

function plainLine(ev: EvidenceObject): string {
  if (ev.explanation && ev.explanation.length > 0) return ev.explanation;
  if (/ask.?to.?transaction/i.test(ev.factor))
    return "Listed prices sit above what buyers actually pay, so we trim it down.";
  return `${ev.direction === "increase" ? "Adds to" : "Reduces"} the price.`;
}

function plainWhy(ev: EvidenceObject): string {
  const m = ev.method ?? "";
  const paired = m.match(/n_[^\s=]+=(\d+),\s*n_[^\s=]+=(\d+)/);
  if (paired) return `We compared ${paired[1]} listings that have this against ${paired[2]} that don't, and measured the price gap.`;
  const ols = m.match(/n=(\d+)/);
  if (ols) return `We measured this from ${ols[1]} nearby listings (a best-fit trend line through their prices).`;
  if (/ask.?to.?transaction/i.test(ev.factor))
    return "A documented ~10% gap between asking prices and final sale prices in Jordan's market.";
  return m || "Derived from the market data.";
}

function plainAnchor(factor: string): string {
  if (/cost/i.test(factor)) return "Cost to rebuild it (you'd never sell below this)";
  if (/income/i.test(factor)) return "What a rental investor would pay (based on rents)";
  return factor;
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
